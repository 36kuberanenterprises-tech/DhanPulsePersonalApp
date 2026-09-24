import { instrumentMaster, resolveUnderlying, candleData, parseCandles } from './angel.js';

const IST_MS = 330 * 60 * 1000;
const MAX_DAYS = { ONE_MINUTE:30, THREE_MINUTE:60, FIVE_MINUTE:100, TEN_MINUTE:100, FIFTEEN_MINUTE:200 };
const MINUTES = { ONE_MINUTE:1, THREE_MINUTE:3, FIVE_MINUTE:5, TEN_MINUTE:10, FIFTEEN_MINUTE:15 };
const cache = new Map();

const sleep = ms => new Promise(r => setTimeout(r, ms));
const round = (v,d=2) => Number.isFinite(v) ? Number(v.toFixed(d)) : null;
const exchangeOf = row => row.exch_seg || row.exchange || 'NSE';

function fmtIst(d){
  const x=new Date(d.getTime()+IST_MS), p=z=>String(z).padStart(2,'0');
  return x.getUTCFullYear()+'-'+p(x.getUTCMonth()+1)+'-'+p(x.getUTCDate())+' '+p(x.getUTCHours())+':'+p(x.getUTCMinutes());
}
function istParts(d=new Date()){
  const x=new Date(d.getTime()+IST_MS);
  return {y:x.getUTCFullYear(),m:x.getUTCMonth(),day:x.getUTCDate()};
}
function makeIstDate(y,m,day,hh,mm){ return new Date(Date.UTC(y,m,day,hh,mm)-IST_MS); }
function yearsAgoStart(years){ const p=istParts(); return makeIstDate(p.y-years,p.m,p.day,9,15); }
function todayEnd(){
  const p=istParts(), now=new Date(), close=makeIstDate(p.y,p.m,p.day,15,30);
  return now<close?now:close;
}
async function candleWithRetry(session,payload){
  let last;
  for(let a=0;a<3;a++){
    try{return await candleData(session,payload);}
    catch(e){last=e;if(a<2)await sleep(1200*(a+1));}
  }
  throw last;
}

export async function historicalCandles(session,symbol,interval,years){
  const key=symbol+'|'+interval+'|'+years;
  const hit=cache.get(key);
  if(hit && Date.now()-hit.at<6*60*60*1000) return hit.rows;

  const master=await instrumentMaster();
  const underlying=resolveUnderlying(master,symbol);
  const exchange=exchangeOf(underlying), token=String(underlying.token);
  const maxDays=MAX_DAYS[interval];
  if(!maxDays) throw new Error('Unsupported historical interval');

  const start=yearsAgoStart(years), end=todayEnd(), rows=[];
  let cursor=new Date(start);
  while(cursor<end){
    let chunkEnd=new Date(cursor.getTime()+(maxDays-1)*86400000);
    if(chunkEnd>end) chunkEnd=new Date(end);
    const cp=istParts(chunkEnd);
    chunkEnd=makeIstDate(cp.y,cp.m,cp.day,15,30);
    if(chunkEnd>end) chunkEnd=new Date(end);
    const raw=await candleWithRetry(session,{
      exchange,
      symboltoken:token,
      interval,
      fromdate:fmtIst(cursor),
      todate:fmtIst(chunkEnd)
    });
    rows.push(...parseCandles(raw));
    cursor=new Date(chunkEnd.getTime()+60000);
    if(cursor<end) await sleep(450);
  }

  const unique=[...new Map(rows.map(x=>[x.timestamp,x])).values()]
    .filter(x=>[x.open,x.high,x.low,x.close].every(Number.isFinite))
    .sort((a,b)=>new Date(a.timestamp)-new Date(b.timestamp));
  cache.set(key,{at:Date.now(),rows:unique});
  return unique;
}

function emaSeries(values,period){
  const out=Array(values.length).fill(null);
  if(values.length<period)return out;
  const k=2/(period+1);
  let e=values.slice(0,period).reduce((a,b)=>a+b,0)/period;
  out[period-1]=e;
  for(let i=period;i<values.length;i++){e=values[i]*k+e*(1-k);out[i]=e;}
  return out;
}
function rsiSeries(values,period=14){
  const out=Array(values.length).fill(null);
  if(values.length<=period)return out;
  let gain=0,loss=0;
  for(let i=1;i<=period;i++){const d=values[i]-values[i-1];if(d>=0)gain+=d;else loss-=d;}
  let ag=gain/period,al=loss/period;
  out[period]=al===0?100:100-100/(1+ag/al);
  for(let i=period+1;i<values.length;i++){
    const d=values[i]-values[i-1];
    ag=(ag*(period-1)+Math.max(d,0))/period;
    al=(al*(period-1)+Math.max(-d,0))/period;
    out[i]=al===0?100:100-100/(1+ag/al);
  }
  return out;
}
function macdHistogramSeries(values,fast=12,slow=26,signal=9){
  const f=emaSeries(values,fast),s=emaSeries(values,slow);
  const line=values.map((_,i)=>f[i]!=null&&s[i]!=null?f[i]-s[i]:null);
  const idx=[],valid=[],out=Array(values.length).fill(null);
  for(let i=0;i<line.length;i++)if(line[i]!=null){idx.push(i);valid.push(line[i]);}
  const sig=emaSeries(valid,signal);
  for(let j=0;j<valid.length;j++)if(sig[j]!=null)out[idx[j]]=valid[j]-sig[j];
  return out;
}
function atrSeries(candles,period=14){
  const out=Array(candles.length).fill(null);
  if(candles.length<=period)return out;
  const tr=Array(candles.length).fill(null);
  for(let i=1;i<candles.length;i++){
    const c=candles[i],p=candles[i-1];
    tr[i]=Math.max(c.high-c.low,Math.abs(c.high-p.close),Math.abs(c.low-p.close));
  }
  let a=tr.slice(1,period+1).reduce((x,y)=>x+y,0)/period;
  out[period]=a;
  for(let i=period+1;i<candles.length;i++){a=(a*(period-1)+tr[i])/period;out[i]=a;}
  return out;
}
function supertrendDirSeries(candles,period=10,multiplier=3){
  const out=Array(candles.length).fill(null);
  if(candles.length<period+2)return out;
  const tr=[0];
  for(let i=1;i<candles.length;i++){
    const c=candles[i],p=candles[i-1];
    tr.push(Math.max(c.high-c.low,Math.abs(c.high-p.close),Math.abs(c.low-p.close)));
  }
  const atrs=Array(candles.length).fill(null);
  let a=tr.slice(1,period+1).reduce((x,y)=>x+y,0)/period;
  atrs[period]=a;
  for(let i=period+1;i<candles.length;i++){a=(a*(period-1)+tr[i])/period;atrs[i]=a;}
  const fu=Array(candles.length).fill(null),fl=Array(candles.length).fill(null),st=Array(candles.length).fill(null);
  for(let i=period;i<candles.length;i++){
    const mid=(candles[i].high+candles[i].low)/2,u=mid+multiplier*atrs[i],l=mid-multiplier*atrs[i];
    if(i===period){fu[i]=u;fl[i]=l;st[i]=candles[i].close<=u?u:l;out[i]=candles[i].close>st[i]?1:-1;continue;}
    fu[i]=(u<fu[i-1]||candles[i-1].close>fu[i-1])?u:fu[i-1];
    fl[i]=(l>fl[i-1]||candles[i-1].close<fl[i-1])?l:fl[i-1];
    st[i]=st[i-1]===fu[i-1]?(candles[i].close<=fu[i]?fu[i]:fl[i]):(candles[i].close>=fl[i]?fl[i]:fu[i]);
    out[i]=candles[i].close>st[i]?1:-1;
  }
  return out;
}
function adxSeries(candles,period=14){
  const out=Array(candles.length).fill(null);
  if(candles.length<period*2+2)return out;
  const tr=Array(candles.length).fill(0),plus=Array(candles.length).fill(0),minus=Array(candles.length).fill(0);
  for(let i=1;i<candles.length;i++){
    const c=candles[i],p=candles[i-1];
    tr[i]=Math.max(c.high-c.low,Math.abs(c.high-p.close),Math.abs(c.low-p.close));
    const up=c.high-p.high,dn=p.low-c.low;
    plus[i]=up>dn&&up>0?up:0;minus[i]=dn>up&&dn>0?dn:0;
  }
  let trS=tr.slice(1,period+1).reduce((a,b)=>a+b,0);
  let pS=plus.slice(1,period+1).reduce((a,b)=>a+b,0);
  let mS=minus.slice(1,period+1).reduce((a,b)=>a+b,0);
  const dx=Array(candles.length).fill(null);
  for(let i=period;i<candles.length;i++){
    if(i>period){trS=trS-trS/period+tr[i];pS=pS-pS/period+plus[i];mS=mS-mS/period+minus[i];}
    if(trS===0)continue;
    const pdi=100*pS/trS,mdi=100*mS/trS;
    dx[i]=(pdi+mdi)===0?0:100*Math.abs(pdi-mdi)/(pdi+mdi);
  }
  const first=dx.slice(period,period*2).filter(v=>v!=null);
  if(first.length<period)return out;
  let a=first.reduce((x,y)=>x+y,0)/period;
  out[period*2-1]=a;
  for(let i=period*2;i<candles.length;i++)if(dx[i]!=null){a=(a*(period-1)+dx[i])/period;out[i]=a;}
  return out;
}
function sessionMeanSeries(candles){
  const out=Array(candles.length).fill(null);
  let key='',sum=0,count=0;
  for(let i=0;i<candles.length;i++){
    const k=String(candles[i].timestamp).slice(0,10);
    if(k!==key){key=k;sum=0;count=0;}
    sum+=(candles[i].high+candles[i].low+candles[i].close)/3;
    count++;out[i]=sum/count;
  }
  return out;
}
function percentile(values,q){
  const a=values.filter(Number.isFinite).slice().sort((x,y)=>x-y);
  if(!a.length)return null;
  const pos=(a.length-1)*q,lo=Math.floor(pos),hi=Math.ceil(pos);
  if(lo===hi)return a[lo];
  return a[lo]+(a[hi]-a[lo])*(pos-lo);
}
function seriesFor(candles){
  const closes=candles.map(c=>c.close);
  const atr=atrSeries(candles,14);
  const atrPct=atr.map((a,i)=>a!=null&&candles[i].close?a/candles[i].close:null);
  const valid=atrPct.filter(Number.isFinite);
  return {
    ema8:emaSeries(closes,8),ema9:emaSeries(closes,9),ema10:emaSeries(closes,10),
    ema15:emaSeries(closes,15),ema16:emaSeries(closes,16),
    rsi:rsiSeries(closes,14),macd:macdHistogramSeries(closes),atr,atrPct,
    st:supertrendDirSeries(candles,10,3),adx:adxSeries(candles,14),
    sessionMean:sessionMeanSeries(candles),
    volLow:percentile(valid,0.33),volHigh:percentile(valid,0.67)
  };
}
function higherContext(entryCandles,higherCandles,entryMinutes){
  const hs=seriesFor(higherCandles),out=Array(entryCandles.length).fill(null);
  let j=-1;
  for(let i=0;i<entryCandles.length;i++){
    const signalClose=new Date(entryCandles[i].timestamp).getTime()+entryMinutes*60000;
    while(j+1<higherCandles.length && new Date(higherCandles[j+1].timestamp).getTime()+15*60000<=signalClose)j++;
    if(j>=0)out[i]={
      bull:hs.ema9[j]!=null&&hs.ema15[j]!=null&&hs.ema9[j]>hs.ema15[j]&&hs.st[j]===1,
      bear:hs.ema9[j]!=null&&hs.ema15[j]!=null&&hs.ema9[j]<hs.ema15[j]&&hs.st[j]===-1
    };
  }
  return out;
}
function signalAt(strategy,candles,s,htf,i,cfg={}){
  const c=candles[i],fast=s[cfg.fastKey||'ema9'][i],slow=s[cfg.slowKey||'ema15'][i];
  const r=s.rsi[i],m=s.macd[i],st=s.st[i],a=s.atr[i];
  if([fast,slow,r,m,st,a].some(v=>v==null))return 'WAIT';

  if(strategy==='CURRENT_CORE'){
    const bull=[c.close>fast,fast>slow,r>=55,m>0,st===1].filter(Boolean).length;
    const bear=[c.close<fast,fast<slow,r<=45,m<0,st===-1].filter(Boolean).length;
    if(bull>=4&&bull>=bear+2)return 'CE';
    if(bear>=4&&bear>=bull+2)return 'PE';
    return 'WAIT';
  }

  const hc=htf[i];
  if(!hc)return 'WAIT';
  const mean=s.sessionMean[i],touchBull=c.low<=fast*1.0015&&c.close>fast,touchBear=c.high>=fast*0.9985&&c.close<fast;

  if(strategy==='TREND_PRO'){
    const bullRsi=cfg.bullRsi??52,bearRsi=cfg.bearRsi??48;
    if(hc.bull&&c.close>fast&&fast>slow&&r>=bullRsi&&r<=75&&m>0&&st===1&&c.close>mean&&touchBull)return 'CE';
    if(hc.bear&&c.close<fast&&fast<slow&&r<=bearRsi&&r>=25&&m<0&&st===-1&&c.close<mean&&touchBear)return 'PE';
    return 'WAIT';
  }

  const adx=s.adx[i],atrPct=s.atrPct[i],adxMin=cfg.adxMin??22;
  if(adx==null||adx<adxMin||atrPct==null||atrPct>0.0045)return 'WAIT';
  if(hc.bull&&c.close>fast&&fast>slow&&r>52&&m>0&&st===1)return 'CE';
  if(hc.bear&&c.close<fast&&fast<slow&&r<48&&m<0&&st===-1)return 'PE';
  return 'WAIT';
}
function istHm(ts){const x=new Date(new Date(ts).getTime()+IST_MS);return x.getUTCHours()*60+x.getUTCMinutes();}
function istWeekday(ts){
  const d=String(ts).slice(0,10).split('-').map(Number);
  if(d.length!==3||d.some(x=>!Number.isFinite(x)))return 'UNKNOWN';
  return ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][new Date(Date.UTC(d[0],d[1]-1,d[2],12,0,0)).getUTCDay()];
}
function isStandardTradingDay(ts){
  const w=istWeekday(ts);
  return w==='Mon'||w==='Tue'||w==='Wed'||w==='Thu'||w==='Fri';
}
const dayKey=ts=>String(ts).slice(0,10);
function timeBucket(ts){const m=istHm(ts);if(m<630)return '09:25-10:30';if(m<720)return '10:30-12:00';if(m<810)return '12:00-13:30';return '13:30-15:00';}
function regimeBucket(adx){if(adx==null)return 'UNKNOWN';if(adx>=25)return 'TRENDING';if(adx<18)return 'RANGE';return 'TRANSITION';}
function volatilityBucket(atrPct,s){if(atrPct==null||s.volLow==null||s.volHigh==null)return 'UNKNOWN';if(atrPct<=s.volLow)return 'LOW VOL';if(atrPct>=s.volHigh)return 'HIGH VOL';return 'NORMAL VOL';}
function phaseBucket(i,length){const p=i/Math.max(1,length-1);if(p<0.60)return 'DEVELOPMENT 60%';if(p<0.80)return 'VALIDATION 20%';return 'OUT OF SAMPLE 20%';}

function summarizeSlice(label,trades){
  const wins=trades.filter(t=>t.netR>0),losses=trades.filter(t=>t.netR<=0);
  const winR=wins.reduce((a,t)=>a+t.netR,0),lossR=Math.abs(losses.reduce((a,t)=>a+t.netR,0));
  const net=trades.reduce((a,t)=>a+t.netR,0);
  return {
    label,trades:trades.length,
    winRate:trades.length?round(100*wins.length/trades.length,1):0,
    profitFactor:lossR>0?round(winR/lossR,2):null,
    expectancyR:trades.length?round(net/trades.length,3):0,
    netR:round(net,2)
  };
}
function groupSummaries(trades,key,order=[]){
  const map=new Map();
  for(const t of trades){const k=t[key]||'UNKNOWN';if(!map.has(k))map.set(k,[]);map.get(k).push(t);}
  const keys=[...map.keys()].sort((a,b)=>{
    const ia=order.indexOf(a),ib=order.indexOf(b);
    if(ia>=0||ib>=0)return (ia<0?999:ia)-(ib<0?999:ib);
    return String(a).localeCompare(String(b));
  });
  return keys.map(k=>summarizeSlice(k,map.get(k)));
}

function simulate(strategy,candles,entryInterval,higherCandles,cfg={}){
  const s=cfg.series||seriesFor(candles),htf=cfg.htf||higherContext(candles,higherCandles,MINUTES[entryInterval]||5);
  const trades=[];
  let lastExit=-10,dailyCount=0,activeDay='';
  const stopAtr=cfg.stopAtr??1,t1Atr=cfg.t1Atr??1.5,t2Atr=cfg.t2Atr??2,maxTrades=cfg.maxTradesPerDay??3,frictionR=cfg.frictionR??0.05;

  for(let i=40;i<candles.length-1;i++){
    const dk=dayKey(candles[i].timestamp);
    const wd=istWeekday(candles[i].timestamp);
    if(!['Mon','Tue','Wed','Thu','Fri'].includes(wd)) continue;
    if(dk!==activeDay){activeDay=dk;dailyCount=0;}
    if(i<=lastExit+2||dailyCount>=maxTrades)continue;
    const minute=istHm(candles[i].timestamp);
    if(minute<565||minute>895)continue;

    const side=signalAt(strategy,candles,s,htf,i,cfg);
    if(side==='WAIT')continue;
    const atr=s.atr[i];
    if(!atr||atr<=0)continue;

    const entryIndex=i+1,entry=candles[entryIndex].open,dir=side==='CE'?1:-1,riskDistance=stopAtr*atr;
    const stop=entry-dir*riskDistance,t1=entry+dir*t1Atr*atr,t2=entry+dir*t2Atr*atr;
    let t1Hit=false,grossR=null,exitIndex=entryIndex,reason='EOD';

    for(let j=entryIndex;j<candles.length;j++){
      if(dayKey(candles[j].timestamp)!==dk){exitIndex=Math.max(entryIndex,j-1);break;}
      const bar=candles[j],stopLevel=t1Hit?entry:stop;
      const stopHit=dir===1?bar.low<=stopLevel:bar.high>=stopLevel;
      const t1HitNow=dir===1?bar.high>=t1:bar.low<=t1;
      const t2HitNow=dir===1?bar.high>=t2:bar.low<=t2;
      const t1R=t1Atr/stopAtr,t2R=t2Atr/stopAtr;

      if(!t1Hit){
        if(stopHit){grossR=-1;exitIndex=j;reason='SL';break;}
        if(t1HitNow){
          t1Hit=true;
          if(t2HitNow){grossR=0.5*t1R+0.5*t2R;exitIndex=j;reason='T2';break;}
        }
      }else{
        if(stopHit){grossR=0.5*t1R;exitIndex=j;reason='T1+BE';break;}
        if(t2HitNow){grossR=0.5*t1R+0.5*t2R;exitIndex=j;reason='T2';break;}
      }

      if(istHm(bar.timestamp)>=920||j===candles.length-1){
        const moveR=dir*(bar.close-entry)/riskDistance;
        grossR=t1Hit?0.5*t1R+0.5*Math.max(0,Math.min(t2R,moveR)):Math.max(-1,Math.min(t1R,moveR));
        exitIndex=j;reason='EOD';break;
      }
    }
    if(grossR==null)continue;
    const netR=grossR-frictionR;
    trades.push({
      date:dk,side,entry:round(entry),exit:round(candles[exitIndex]?.close),grossR:round(grossR,3),netR:round(netR,3),reason,
      timeBucket:timeBucket(candles[i].timestamp),weekday:wd,
      regime:regimeBucket(s.adx[i]),volatility:volatilityBucket(s.atrPct[i],s),phase:phaseBucket(i,candles.length)
    });
    lastExit=exitIndex;dailyCount++;i=exitIndex;
  }
  return {trades,series:s,htf};
}

function buildStrategyResult(strategy,trades,capital,riskPct){
  const base=summarizeSlice('ALL',trades),wins=trades.filter(t=>t.netR>0),losses=trades.filter(t=>t.netR<=0);
  let equity=capital,peak=capital,maxDdPct=0,lossStreak=0,maxLossStreak=0;
  const equityCurve=[];
  for(const t of trades){
    const risk=Math.max(0,equity)*(riskPct/100);
    equity+=t.netR*risk;
    peak=Math.max(peak,equity);
    if(peak>0)maxDdPct=Math.max(maxDdPct,100*(peak-equity)/peak);
    if(t.netR<=0){lossStreak++;maxLossStreak=Math.max(maxLossStreak,lossStreak);}else lossStreak=0;
    if(equityCurve.length===0 || t.date!==equityCurve[equityCurve.length-1].date)equityCurve.push({date:t.date,equity:round(equity,0)});
    else equityCurve[equityCurve.length-1].equity=round(equity,0);
  }

  return {
    strategy,
    label:strategy==='CURRENT_CORE'?'Current DhanPulse Core':strategy==='TREND_PRO'?'Trend Pro':'Regime Pro',
    totalTrades:base.trades,wins:wins.length,losses:losses.length,winRate:base.winRate,profitFactor:base.profitFactor,
    expectancyR:base.expectancyR,netR:base.netR,
    startingCapital:round(capital,0),endingCapital:round(equity,0),modelPnl:round(equity-capital,0),
    modelReturnPct:round(100*(equity-capital)/capital,1),maxDrawdownPct:round(maxDdPct,1),
    maxConsecutiveLosses:maxLossStreak,
    avgWinR:wins.length?round(wins.reduce((a,t)=>a+t.netR,0)/wins.length,2):0,
    avgLossR:losses.length?round(losses.reduce((a,t)=>a+t.netR,0)/losses.length,2):0,
    diagnostics:{
      sides:groupSummaries(trades,'side',['CE','PE']),
      times:groupSummaries(trades,'timeBucket',['09:25-10:30','10:30-12:00','12:00-13:30','13:30-15:00']),
      weekdays:groupSummaries(trades,'weekday',['Mon','Tue','Wed','Thu','Fri']),
      regimes:groupSummaries(trades,'regime',['TRENDING','TRANSITION','RANGE']),
      volatility:groupSummaries(trades,'volatility',['LOW VOL','NORMAL VOL','HIGH VOL']),
      exits:groupSummaries(trades,'reason',['SL','T1+BE','T2','EOD']),
      phases:groupSummaries(trades,'phase',['DEVELOPMENT 60%','VALIDATION 20%','OUT OF SAMPLE 20%']),
      years:groupSummaries(trades.map(t=>({...t,year:t.date.slice(0,4)})),'year')
    },
    equityCurve
  };
}

function robustnessSweep(candles,interval,higher,capital,baseSeries,baseHtf){
  const emaPairs=[['ema8','ema15','8/15'],['ema9','ema15','9/15'],['ema10','ema15','10/15'],['ema9','ema16','9/16']];
  const stops=[0.8,1.0,1.2],rows=[];
  for(const [fastKey,slowKey,label] of emaPairs){
    for(const stopAtr of stops){
      const sim=simulate('TREND_PRO',candles,interval,higher,{series:baseSeries,htf:baseHtf,fastKey,slowKey,stopAtr,t1Atr:1.5,t2Atr:2,frictionR:0.05});
      const s=summarizeSlice('x',sim.trades);
      rows.push({ema:label,stopAtr,profitFactor:s.profitFactor,expectancyR:s.expectancyR,netR:s.netR,trades:s.trades});
    }
  }
  const pfs=rows.map(x=>x.profitFactor).filter(Number.isFinite).sort((a,b)=>a-b);
  const profitable=rows.filter(x=>x.expectancyR>0 && (x.profitFactor??0)>1).length;
  const best=rows.slice().sort((a,b)=>(b.expectancyR??-999)-(a.expectancyR??-999))[0]||null;
  const medianPf=pfs.length?pfs[Math.floor(pfs.length/2)]:null;
  return {
    combinations:rows.length,profitableCombinations:profitable,profitablePct:round(100*profitable/Math.max(1,rows.length),1),
    minProfitFactor:pfs.length?round(pfs[0],2):null,maxProfitFactor:pfs.length?round(pfs[pfs.length-1],2):null,
    medianProfitFactor:round(medianPf,2),best,
    rows
  };
}


function filterByRule(trades,filters){
  return trades.filter(t=>{
    if(filters.side?.length && !filters.side.includes(t.side))return false;
    if(filters.timeBucket?.length && !filters.timeBucket.includes(t.timeBucket))return false;
    if(filters.weekday?.length && !filters.weekday.includes(t.weekday))return false;
    if(filters.regime?.length && !filters.regime.includes(t.regime))return false;
    if(filters.volatility?.length && !filters.volatility.includes(t.volatility))return false;
    return true;
  });
}

function choiceSets(devTrades,key,minCategoryTrades=25){
  const grouped=new Map();
  for(const t of devTrades){
    const k=t[key]||'UNKNOWN';
    if(!grouped.has(k))grouped.set(k,[]);
    grouped.get(k).push(t);
  }
  const stats=[...grouped.entries()]
    .map(([label,rows])=>({...summarizeSlice(label,rows),value:label}))
    .filter(x=>x.trades>=minCategoryTrades);

  const positive=stats
    .filter(x=>(x.profitFactor??0)>=1.02 && x.expectancyR>=0.01)
    .sort((a,b)=>b.expectancyR-a.expectancyR);

  const out=[{label:'ALL',values:null}];
  for(const x of positive.slice(0,3)) out.push({label:x.value,values:[x.value]});
  if(positive.length>=2){
    out.push({label:'Positive group',values:positive.map(x=>x.value)});
  }
  return out;
}

function candidateScore(s,filterCount){
  if(!s||s.trades<80)return -Infinity;
  const pf=s.profitFactor??0;
  if(s.expectancyR<=0||pf<=1)return -Infinity;
  return s.expectancyR*Math.sqrt(s.trades)+Math.max(0,pf-1)*0.6-filterCount*0.03;
}

function filterCount(filters){
  return Object.values(filters).filter(v=>Array.isArray(v)&&v.length>0).length;
}

function candidateRuleText(filters){
  const parts=[];
  if(filters.side?.length)parts.push('Side '+filters.side.join('/'));
  if(filters.timeBucket?.length)parts.push('Time '+filters.timeBucket.join(' or '));
  if(filters.weekday?.length)parts.push('Days '+filters.weekday.join('/'));
  if(filters.regime?.length)parts.push('Regime '+filters.regime.join('/'));
  if(filters.volatility?.length)parts.push('Vol '+filters.volatility.join('/'));
  return parts.length?parts.join(' • '):'No extra filters';
}

function discoverForSimulation(trades,configName){
  const dev=trades.filter(t=>t.phase==='DEVELOPMENT 60%');
  if(dev.length<120)return [];

  const dimensions=[
    ['side','side'],
    ['timeBucket','timeBucket'],
    ['weekday','weekday'],
    ['regime','regime'],
    ['volatility','volatility']
  ];

  let beam=[{filters:{},dev:summarizeSlice('DEV',dev),score:0}];
  for(const [filterKey,tradeKey] of dimensions){
    const choices=choiceSets(dev,tradeKey);
    const expanded=[];
    for(const b of beam){
      for(const ch of choices){
        const filters={...b.filters};
        if(ch.values)filters[filterKey]=ch.values;
        const rows=filterByRule(dev,filters);
        const s=summarizeSlice('DEV',rows);
        const score=candidateScore(s,filterCount(filters));
        if(Number.isFinite(score))expanded.push({filters,dev:s,score});
      }
    }
    const dedup=new Map();
    for(const x of expanded){
      const key=JSON.stringify(x.filters);
      const old=dedup.get(key);
      if(!old||x.score>old.score)dedup.set(key,x);
    }
    beam=[...dedup.values()].sort((a,b)=>b.score-a.score).slice(0,30);
    if(!beam.length)break;
  }

  return beam.slice(0,15).map(x=>({...x,configName,ruleText:candidateRuleText(x.filters)}));
}

function adaptiveResearch(candles,interval,higher,capital,baseSeries,baseHtf){
  const configs=[
    {name:'EMA 9/15 • SL 1.0',fastKey:'ema9',slowKey:'ema15',stopAtr:1.0,t1Atr:1.5,t2Atr:2.0},
    {name:'EMA 9/15 • SL 1.2',fastKey:'ema9',slowKey:'ema15',stopAtr:1.2,t1Atr:1.5,t2Atr:2.0},
    {name:'EMA 8/15 • SL 1.0',fastKey:'ema8',slowKey:'ema15',stopAtr:1.0,t1Atr:1.5,t2Atr:2.0},
    {name:'EMA 10/15 • SL 1.0',fastKey:'ema10',slowKey:'ema15',stopAtr:1.0,t1Atr:1.5,t2Atr:2.0},
    {name:'EMA 9/16 • SL 1.0',fastKey:'ema9',slowKey:'ema16',stopAtr:1.0,t1Atr:1.5,t2Atr:2.0},
    {name:'EMA 9/15 • T1 1.25',fastKey:'ema9',slowKey:'ema15',stopAtr:1.0,t1Atr:1.25,t2Atr:2.0},
    {name:'EMA 9/15 • T1 1.75',fastKey:'ema9',slowKey:'ema15',stopAtr:1.0,t1Atr:1.75,t2Atr:2.5}
  ];

  const allCandidates=[];
  const simByConfig=new Map();
  for(const cfg of configs){
    const sim=simulate('TREND_PRO',candles,interval,higher,{
      ...cfg,series:baseSeries,htf:baseHtf,frictionR:0.05
    });
    simByConfig.set(cfg.name,sim.trades);
    allCandidates.push(...discoverForSimulation(sim.trades,cfg.name));
  }

  if(!allCandidates.length){
    return {
      status:'NO_EDGE',
      gatePassed:false,
      message:'No development-period filter had enough trades with positive expectancy. Live Adaptive Auto remains blocked.',
      searchedConfigs:configs.length,
      candidates:0
    };
  }

  const devShortlist=allCandidates.sort((a,b)=>b.score-a.score).slice(0,40);
  const validated=[];
  for(const x of devShortlist){
    const all=simByConfig.get(x.configName)||[];
    const valRows=filterByRule(all.filter(t=>t.phase==='VALIDATION 20%'),x.filters);
    const val=summarizeSlice('VALIDATION',valRows);
    if(val.trades>=25 && (val.profitFactor??0)>=1.03 && val.expectancyR>=0.01 && val.netR>0){
      validated.push({...x,validation:val});
    }
  }

  if(!validated.length){
    const best=devShortlist[0];
    return {
      status:'VALIDATION_FAILED',
      gatePassed:false,
      message:'The engine found development-period candidates, but none stayed positive in validation. Live Adaptive Auto remains blocked.',
      searchedConfigs:configs.length,
      candidates:allCandidates.length,
      selected:{
        configName:best.configName,
        ruleText:best.ruleText,
        development:best.dev,
        validation:null,
        outOfSample:null
      }
    };
  }

  validated.sort((a,b)=>{
    const as=a.validation.expectancyR*Math.sqrt(a.validation.trades)+(a.validation.profitFactor??0)-1;
    const bs=b.validation.expectancyR*Math.sqrt(b.validation.trades)+(b.validation.profitFactor??0)-1;
    return bs-as;
  });

  const selected=validated[0];
  const all=simByConfig.get(selected.configName)||[];
  const oosRows=filterByRule(all.filter(t=>t.phase==='OUT OF SAMPLE 20%'),selected.filters);
  const oos=summarizeSlice('OUT OF SAMPLE',oosRows);
  const allFiltered=filterByRule(all,selected.filters);
  const combined=buildStrategyResult('ADAPTIVE_PRO',allFiltered,capital,0.5);

  const gatePassed=
    selected.dev.trades>=80 &&
    (selected.dev.profitFactor??0)>=1.05 &&
    selected.dev.expectancyR>=0.015 &&
    selected.validation.trades>=25 &&
    (selected.validation.profitFactor??0)>=1.05 &&
    selected.validation.expectancyR>=0.015 &&
    oos.trades>=25 &&
    (oos.profitFactor??0)>=1.05 &&
    oos.expectancyR>=0.015 &&
    oos.netR>0;

  return {
    status:gatePassed?'PASSED':'OOS_FAILED',
    gatePassed,
    message:gatePassed
      ? 'A rule selected from development, chosen on validation, also stayed positive on untouched out-of-sample data. It is eligible for paper-auto testing, not guaranteed live profit.'
      : 'A candidate survived development and validation but did not meet the untouched out-of-sample gate. Live Adaptive Auto remains blocked.',
    searchedConfigs:configs.length,
    candidates:allCandidates.length,
    configName:selected.configName,
    ruleText:selected.ruleText,
    filters:selected.filters,
    development:selected.dev,
    validation:selected.validation,
    outOfSample:oos,
    combined:{
      totalTrades:combined.totalTrades,
      winRate:combined.winRate,
      profitFactor:combined.profitFactor,
      expectancyR:combined.expectancyR,
      netR:combined.netR,
      modelPnl:combined.modelPnl,
      modelReturnPct:combined.modelReturnPct,
      maxDrawdownPct:combined.maxDrawdownPct
    }
  };
}


function interpretationSummary(strategies,adaptive){
  const trend=strategies.find(x=>x.strategy==='TREND_PRO');
  const oos=adaptive?.outOfSample;
  let verdict='NOT READY';
  let reason='No validated edge yet.';
  if(adaptive?.gatePassed){
    verdict='PAPER TEST';
    reason='Adaptive rule passed development, validation and untouched out-of-sample gates. Paper trading is the next step.';
  }else if(oos && (oos.profitFactor??0)>1 && oos.expectancyR>0){
    verdict='PROMISING, NOT READY';
    reason='Recent unseen data is positive, but the full validation gate is not strong enough yet.';
  }else if(trend && (trend.profitFactor??0)>=0.98){
    verdict='NEAR BREAKEVEN';
    reason='Trend Pro is close to breakeven overall, but still lacks a durable historical edge.';
  }
  return {
    verdict,
    reason,
    focus:[
      'Adaptive gate status',
      'Untouched out-of-sample Profit Factor and expectancy',
      'Maximum drawdown',
      'Trade count',
      'Robustness across nearby parameters'
    ],
    ignoreForDecision:[
      'One weekday alone',
      'One time window alone',
      'Raw win rate without Profit Factor',
      'Small Saturday/Sunday samples'
    ]
  };
}

export async function runBacktest(session,{symbol='NIFTY',interval='FIVE_MINUTE',years=3,capital=20000}={}){
  symbol=String(symbol).toUpperCase();interval=String(interval).toUpperCase();
  years=[1,3,5].includes(Number(years))?Number(years):3;
  capital=Math.max(1000,Math.min(10000000,Number(capital)||20000));
  if(!['NIFTY','BANKNIFTY','SENSEX'].includes(symbol))throw new Error('Supported symbols: NIFTY, BANKNIFTY, SENSEX');
  if(!MAX_DAYS[interval])throw new Error('Unsupported interval');

  const rawEntry=await historicalCandles(session,symbol,interval,years);
  const rawHigher=interval==='FIFTEEN_MINUTE'?rawEntry:await historicalCandles(session,symbol,'FIFTEEN_MINUTE',years);
  const weekendCandlesExcluded=rawEntry.filter(x=>!isStandardTradingDay(x.timestamp)).length;
  const weekendHigherExcluded=rawHigher.filter(x=>!isStandardTradingDay(x.timestamp)).length;
  const entry=rawEntry.filter(x=>isStandardTradingDay(x.timestamp));
  const higher=rawHigher.filter(x=>isStandardTradingDay(x.timestamp));
  if(entry.length<300||higher.length<100)throw new Error('Not enough weekday historical candles returned for '+symbol+' '+interval);

  const sharedSeries=seriesFor(entry),sharedHtf=higherContext(entry,higher,MINUTES[interval]||5),riskPct=1;
  const strategies=[];
  for(const name of ['CURRENT_CORE','TREND_PRO','REGIME_PRO']){
    const sim=simulate(name,entry,interval,higher,{series:sharedSeries,htf:sharedHtf,frictionR:0.05});
    strategies.push(buildStrategyResult(name,sim.trades,capital,riskPct));
  }
  const robustness=robustnessSweep(entry,interval,higher,capital,sharedSeries,sharedHtf);
  const adaptive=adaptiveResearch(entry,interval,higher,capital,sharedSeries,sharedHtf);

  return {
    version:'CLARITY_V1_2',
    symbol,interval,years,capital,
    period:{from:entry[0].timestamp,to:entry[entry.length-1].timestamp},
    candles:entry.length,higherTimeframe:'FIFTEEN_MINUTE',
    dataQuality:{
      rawCandles:rawEntry.length,
      usedCandles:entry.length,
      weekendOrSpecialCandlesExcluded:weekendCandlesExcluded,
      higherTimeframeExcluded:weekendHigherExcluded,
      note:'Standard backtest uses Monday-Friday sessions only. Weekend/special-session candles are excluded from strategy statistics and weekday diagnostics.'
    },
    assumptions:{
      entry:'Signal on candle close; entry at next candle open',
      stop:'1 ATR baseline',
      target1:'1.5 ATR, 50% booked',
      target2:'2 ATR, remaining 50%',
      afterTarget1:'Remaining stop moved to breakeven',
      intradayExit:'Open positions closed around 15:20 IST',
      maxTradesPerDay:3,riskPerTradePct:riskPct,executionFrictionR:0.05,
      equityModel:'1% of current equity risked per trade (compounding)'
    },
    strategies,robustness,adaptive,
    interpretation:interpretationSummary(strategies,adaptive),
    limitations:[
      'This diagnostic test measures the underlying index signal engine, not historical option premium P&L.',
      'Angel index candles do not provide usable volume, so true historical VWAP is not reconstructed; Trend Pro uses a session typical-price mean proxy.',
      'Historical PCR and complete expired option-chain snapshots are not included.',
      'Execution friction is modeled as 0.05R per trade; exact option brokerage, tax, spread and IV effects require Stage 2 option-contract data.'
    ],
    generatedAt:new Date().toISOString()
  };
}
