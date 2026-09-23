import { instrumentMaster, resolveUnderlying, candleData, parseCandles } from './angel.js';

const IST_MS = 330 * 60 * 1000;
const MAX_DAYS = {
  ONE_MINUTE: 30,
  THREE_MINUTE: 60,
  FIVE_MINUTE: 100,
  TEN_MINUTE: 100,
  FIFTEEN_MINUTE: 200
};
const MINUTES = {
  ONE_MINUTE: 1,
  THREE_MINUTE: 3,
  FIVE_MINUTE: 5,
  TEN_MINUTE: 10,
  FIFTEEN_MINUTE: 15
};
const cache = new Map();

const sleep = ms => new Promise(r => setTimeout(r, ms));
const n = v => Number.isFinite(Number(v)) ? Number(v) : null;
const round = (v, d = 2) => Number.isFinite(v) ? Number(v.toFixed(d)) : null;

function exchangeOf(row) { return row.exch_seg || row.exchange || 'NSE'; }

function fmtIst(d) {
  const x = new Date(d.getTime() + IST_MS);
  const p = z => String(z).padStart(2, '0');
  return `${x.getUTCFullYear()}-${p(x.getUTCMonth()+1)}-${p(x.getUTCDate())} ${p(x.getUTCHours())}:${p(x.getUTCMinutes())}`;
}

function istDateParts(d = new Date()) {
  const x = new Date(d.getTime() + IST_MS);
  return { y:x.getUTCFullYear(), m:x.getUTCMonth(), day:x.getUTCDate() };
}

function makeIstDate(y, m, day, hh, mm) {
  return new Date(Date.UTC(y, m, day, hh, mm) - IST_MS);
}

function yearsAgoStart(years) {
  const p = istDateParts();
  return makeIstDate(p.y - years, p.m, p.day, 9, 15);
}

function todayEnd() {
  const p = istDateParts();
  const now = new Date();
  const close = makeIstDate(p.y, p.m, p.day, 15, 30);
  return now < close ? now : close;
}

async function candleWithRetry(session, payload) {
  let last;
  for (let attempt = 0; attempt < 3; attempt++) {
    try { return await candleData(session, payload); }
    catch (e) {
      last = e;
      if (attempt < 2) await sleep(1200 * (attempt + 1));
    }
  }
  throw last;
}

export async function historicalCandles(session, symbol, interval, years) {
  const key = `${symbol}|${interval}|${years}`;
  const hit = cache.get(key);
  if (hit && Date.now() - hit.at < 6 * 60 * 60 * 1000) return hit.rows;

  const master = await instrumentMaster();
  const underlying = resolveUnderlying(master, symbol);
  const exchange = exchangeOf(underlying);
  const token = String(underlying.token);
  const maxDays = MAX_DAYS[interval];
  if (!maxDays) throw new Error('Unsupported historical interval');

  const start = yearsAgoStart(years);
  const end = todayEnd();
  const rows = [];
  let cursor = new Date(start);

  while (cursor < end) {
    let chunkEnd = new Date(cursor.getTime() + (maxDays - 1) * 24 * 60 * 60 * 1000);
    if (chunkEnd > end) chunkEnd = new Date(end);
    const cp = istDateParts(chunkEnd);
    chunkEnd = makeIstDate(cp.y, cp.m, cp.day, 15, 30);
    if (chunkEnd > end) chunkEnd = new Date(end);

    const raw = await candleWithRetry(session, {
      exchange,
      symboltoken: token,
      interval,
      fromdate: fmtIst(cursor),
      todate: fmtIst(chunkEnd)
    });
    rows.push(...parseCandles(raw));
    cursor = new Date(chunkEnd.getTime() + 60 * 1000);
    if (cursor < end) await sleep(450);
  }

  const unique = [...new Map(rows.map(c => [c.timestamp, c])).values()]
    .filter(c => [c.open,c.high,c.low,c.close].every(Number.isFinite))
    .sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp));
  cache.set(key, { at: Date.now(), rows: unique });
  return unique;
}

function emaSeries(values, period) {
  const out = Array(values.length).fill(null);
  if (values.length < period) return out;
  const k = 2 / (period + 1);
  let e = values.slice(0, period).reduce((a,b)=>a+b,0) / period;
  out[period-1] = e;
  for (let i=period;i<values.length;i++) {
    e = values[i] * k + e * (1-k);
    out[i] = e;
  }
  return out;
}

function rsiSeries(values, period=14) {
  const out = Array(values.length).fill(null);
  if (values.length <= period) return out;
  let gain=0, loss=0;
  for (let i=1;i<=period;i++) {
    const d=values[i]-values[i-1];
    if (d>=0) gain+=d; else loss-=d;
  }
  let ag=gain/period, al=loss/period;
  out[period] = al===0 ? 100 : 100 - 100/(1+ag/al);
  for (let i=period+1;i<values.length;i++) {
    const d=values[i]-values[i-1];
    ag=(ag*(period-1)+Math.max(d,0))/period;
    al=(al*(period-1)+Math.max(-d,0))/period;
    out[i]=al===0 ? 100 : 100 - 100/(1+ag/al);
  }
  return out;
}

function macdHistogramSeries(values, fast=12, slow=26, signal=9) {
  const f=emaSeries(values,fast), s=emaSeries(values,slow);
  const line=values.map((_,i)=>f[i]!=null&&s[i]!=null?f[i]-s[i]:null);
  const out=Array(values.length).fill(null);
  const validIdx=[];
  const valid=[];
  for(let i=0;i<line.length;i++) if(line[i]!=null){validIdx.push(i);valid.push(line[i]);}
  const sig=emaSeries(valid,signal);
  for(let j=0;j<valid.length;j++) if(sig[j]!=null) out[validIdx[j]]=valid[j]-sig[j];
  return out;
}

function atrSeries(candles, period=14) {
  const out=Array(candles.length).fill(null);
  if(candles.length<=period) return out;
  const tr=Array(candles.length).fill(null);
  for(let i=1;i<candles.length;i++){
    const c=candles[i],p=candles[i-1];
    tr[i]=Math.max(c.high-c.low,Math.abs(c.high-p.close),Math.abs(c.low-p.close));
  }
  let a=tr.slice(1,period+1).reduce((x,y)=>x+y,0)/period;
  out[period]=a;
  for(let i=period+1;i<candles.length;i++){
    a=(a*(period-1)+tr[i])/period;
    out[i]=a;
  }
  return out;
}

function supertrendDirSeries(candles, period=10, multiplier=3) {
  const out=Array(candles.length).fill(null);
  if(candles.length<period+2) return out;
  const tr=[0];
  for(let i=1;i<candles.length;i++){
    const c=candles[i],p=candles[i-1];
    tr.push(Math.max(c.high-c.low,Math.abs(c.high-p.close),Math.abs(c.low-p.close)));
  }
  const atrs=Array(candles.length).fill(null);
  let a=tr.slice(1,period+1).reduce((x,y)=>x+y,0)/period;
  atrs[period]=a;
  for(let i=period+1;i<candles.length;i++){a=(a*(period-1)+tr[i])/period;atrs[i]=a;}
  const fu=Array(candles.length).fill(null), fl=Array(candles.length).fill(null), st=Array(candles.length).fill(null);
  for(let i=period;i<candles.length;i++){
    const mid=(candles[i].high+candles[i].low)/2;
    const u=mid+multiplier*atrs[i], l=mid-multiplier*atrs[i];
    if(i===period){fu[i]=u;fl[i]=l;st[i]=candles[i].close<=u?u:l;out[i]=candles[i].close>st[i]?1:-1;continue;}
    fu[i]=(u<fu[i-1]||candles[i-1].close>fu[i-1])?u:fu[i-1];
    fl[i]=(l>fl[i-1]||candles[i-1].close<fl[i-1])?l:fl[i-1];
    st[i]=st[i-1]===fu[i-1]?(candles[i].close<=fu[i]?fu[i]:fl[i]):(candles[i].close>=fl[i]?fl[i]:fu[i]);
    out[i]=candles[i].close>st[i]?1:-1;
  }
  return out;
}

function adxSeries(candles, period=14) {
  const out=Array(candles.length).fill(null);
  if(candles.length < period*2+2) return out;
  const tr=Array(candles.length).fill(0), plus=Array(candles.length).fill(0), minus=Array(candles.length).fill(0);
  for(let i=1;i<candles.length;i++){
    const c=candles[i],p=candles[i-1];
    tr[i]=Math.max(c.high-c.low,Math.abs(c.high-p.close),Math.abs(c.low-p.close));
    const up=c.high-p.high, dn=p.low-c.low;
    plus[i]=up>dn&&up>0?up:0;
    minus[i]=dn>up&&dn>0?dn:0;
  }
  let trS=tr.slice(1,period+1).reduce((a,b)=>a+b,0);
  let pS=plus.slice(1,period+1).reduce((a,b)=>a+b,0);
  let mS=minus.slice(1,period+1).reduce((a,b)=>a+b,0);
  const dx=Array(candles.length).fill(null);
  for(let i=period;i<candles.length;i++){
    if(i>period){trS=trS-trS/period+tr[i];pS=pS-pS/period+plus[i];mS=mS-mS/period+minus[i];}
    if(trS===0) continue;
    const pdi=100*pS/trS, mdi=100*mS/trS;
    dx[i]=(pdi+mdi)===0?0:100*Math.abs(pdi-mdi)/(pdi+mdi);
  }
  const first=dx.slice(period,period*2).filter(v=>v!=null);
  if(first.length<period) return out;
  let a=first.reduce((x,y)=>x+y,0)/period;
  out[period*2-1]=a;
  for(let i=period*2;i<candles.length;i++) if(dx[i]!=null){a=(a*(period-1)+dx[i])/period;out[i]=a;}
  return out;
}

function sessionMeanSeries(candles) {
  const out=Array(candles.length).fill(null);
  let key='', sum=0, count=0;
  for(let i=0;i<candles.length;i++){
    const k=String(candles[i].timestamp).slice(0,10);
    if(k!==key){key=k;sum=0;count=0;}
    sum+=(candles[i].high+candles[i].low+candles[i].close)/3;
    count++;
    out[i]=sum/count;
  }
  return out;
}

function seriesFor(candles) {
  const closes=candles.map(c=>c.close);
  return {
    ema9:emaSeries(closes,9),
    ema15:emaSeries(closes,15),
    rsi:rsiSeries(closes,14),
    macd:macdHistogramSeries(closes),
    atr:atrSeries(candles,14),
    st:supertrendDirSeries(candles,10,3),
    adx:adxSeries(candles,14),
    sessionMean:sessionMeanSeries(candles)
  };
}

function higherContext(entryCandles, higherCandles, entryMinutes) {
  const hs=seriesFor(higherCandles);
  const out=Array(entryCandles.length).fill(null);
  let j=-1;
  for(let i=0;i<entryCandles.length;i++){
    const signalClose=new Date(entryCandles[i].timestamp).getTime()+entryMinutes*60*1000;
    while(j+1<higherCandles.length && new Date(higherCandles[j+1].timestamp).getTime()+15*60*1000<=signalClose) j++;
    if(j>=0) out[i]={
      bull:hs.ema9[j]!=null&&hs.ema15[j]!=null&&hs.ema9[j]>hs.ema15[j]&&hs.st[j]===1,
      bear:hs.ema9[j]!=null&&hs.ema15[j]!=null&&hs.ema9[j]<hs.ema15[j]&&hs.st[j]===-1
    };
  }
  return out;
}

function signalAt(strategy, candles, s, htf, i) {
  const c=candles[i];
  const e9=s.ema9[i], e15=s.ema15[i], r=s.rsi[i], m=s.macd[i], st=s.st[i], a=s.atr[i];
  if([e9,e15,r,m,st,a].some(v=>v==null)) return 'WAIT';
  if(strategy==='CURRENT_CORE'){
    const bull=[c.close>e9,e9>e15,r>=55,m>0,st===1].filter(Boolean).length;
    const bear=[c.close<e9,e9<e15,r<=45,m<0,st===-1].filter(Boolean).length;
    if(bull>=4&&bull>=bear+2) return 'CE';
    if(bear>=4&&bear>=bull+2) return 'PE';
    return 'WAIT';
  }
  const hc=htf[i];
  if(!hc) return 'WAIT';
  const mean=s.sessionMean[i];
  const touchBull=c.low<=e9*1.0015&&c.close>e9;
  const touchBear=c.high>=e9*0.9985&&c.close<e9;
  if(strategy==='TREND_PRO'){
    if(hc.bull&&c.close>e9&&e9>e15&&r>=52&&r<=75&&m>0&&st===1&&c.close>mean&&touchBull) return 'CE';
    if(hc.bear&&c.close<e9&&e9<e15&&r<=48&&r>=25&&m<0&&st===-1&&c.close<mean&&touchBear) return 'PE';
    return 'WAIT';
  }
  const adx=s.adx[i];
  const atrPct=a/c.close;
  if(adx==null||adx<22||atrPct>0.0045) return 'WAIT';
  if(hc.bull&&c.close>e9&&e9>e15&&r>52&&m>0&&st===1) return 'CE';
  if(hc.bear&&c.close<e9&&e9<e15&&r<48&&m<0&&st===-1) return 'PE';
  return 'WAIT';
}

function istHm(timestamp) {
  const d=new Date(timestamp);
  const x=new Date(d.getTime()+IST_MS);
  return x.getUTCHours()*60+x.getUTCMinutes();
}

function dayKey(timestamp){ return String(timestamp).slice(0,10); }

function simulate(strategy, candles, entryInterval, higherCandles, capital, riskPct=1, frictionR=0.05) {
  const s=seriesFor(candles);
  const htf=higherContext(candles,higherCandles,MINUTES[entryInterval] || 5);
  const trades=[];
  let lastExit=-10, dailyCount=0, activeDay='';

  for(let i=40;i<candles.length-1;i++){
    const dk=dayKey(candles[i].timestamp);
    if(dk!==activeDay){activeDay=dk;dailyCount=0;}
    if(i<=lastExit+2||dailyCount>=3) continue;
    const minute=istHm(candles[i].timestamp);
    if(minute<9*60+25||minute>14*60+55) continue;

    const side=signalAt(strategy,candles,s,htf,i);
    if(side==='WAIT') continue;
    const atr=s.atr[i];
    if(!atr||atr<=0) continue;

    const entryIndex=i+1;
    const entry=candles[entryIndex].open;
    const dir=side==='CE'?1:-1;
    const stop=entry-dir*atr;
    const t1=entry+dir*1.5*atr;
    const t2=entry+dir*2*atr;
    let t1Hit=false, grossR=null, exitIndex=entryIndex, reason='EOD';

    for(let j=entryIndex;j<candles.length;j++){
      if(dayKey(candles[j].timestamp)!==dk){exitIndex=j-1;break;}
      const bar=candles[j];
      const stopLevel=t1Hit?entry:stop;
      const stopHit=dir===1?bar.low<=stopLevel:bar.high>=stopLevel;
      const target1Hit=dir===1?bar.high>=t1:bar.low<=t1;
      const target2Hit=dir===1?bar.high>=t2:bar.low<=t2;

      if(!t1Hit){
        if(stopHit){grossR=-1;exitIndex=j;reason='SL';break;}
        if(target1Hit){
          t1Hit=true;
          if(target2Hit){grossR=1.75;exitIndex=j;reason='T2';break;}
        }
      } else {
        if(stopHit){grossR=0.75;exitIndex=j;reason='T1+BE';break;}
        if(target2Hit){grossR=1.75;exitIndex=j;reason='T2';break;}
      }

      const hm=istHm(bar.timestamp);
      if(hm>=15*60+20 || j===candles.length-1){
        const moveR=dir*(bar.close-entry)/atr;
        grossR=t1Hit?0.75+0.5*Math.max(0,Math.min(2,moveR)):Math.max(-1,Math.min(1.5,moveR));
        exitIndex=j;reason='EOD';break;
      }
    }
    if(grossR==null) continue;
    const netR=grossR-frictionR;
    trades.push({
      date:dk, side, entry:round(entry), stop:round(stop), target1:round(t1), target2:round(t2),
      exit:round(candles[exitIndex]?.close), grossR:round(grossR,3), netR:round(netR,3), reason
    });
    lastExit=exitIndex;
    dailyCount++;
    i=exitIndex;
  }

  const wins=trades.filter(t=>t.netR>0), losses=trades.filter(t=>t.netR<=0);
  const grossWin=wins.reduce((a,t)=>a+t.netR,0);
  const grossLoss=Math.abs(losses.reduce((a,t)=>a+t.netR,0));
  const netR=trades.reduce((a,t)=>a+t.netR,0);
  let equity=0, peak=0, maxDd=0, lossStreak=0, maxLossStreak=0;
  const monthly={};
  const yearly={};
  for(const t of trades){
    equity+=t.netR; peak=Math.max(peak,equity); maxDd=Math.max(maxDd,peak-equity);
    if(t.netR<=0){lossStreak++;maxLossStreak=Math.max(maxLossStreak,lossStreak);}else lossStreak=0;
    const mo=t.date.slice(0,7), yr=t.date.slice(0,4);
    monthly[mo]=(monthly[mo]||0)+t.netR;
    yearly[yr]=(yearly[yr]||0)+t.netR;
  }
  const riskAmount=capital*(riskPct/100);
  return {
    strategy,
    label: strategy==='CURRENT_CORE'?'Current DhanPulse Core':strategy==='TREND_PRO'?'Trend Pro':'Regime Pro',
    totalTrades:trades.length,
    wins:wins.length,
    losses:losses.length,
    winRate:trades.length?round(100*wins.length/trades.length,1):0,
    profitFactor:grossLoss>0?round(grossWin/grossLoss,2):null,
    expectancyR:trades.length?round(netR/trades.length,3):0,
    netR:round(netR,2),
    modelPnl:round(netR*riskAmount,0),
    modelReturnPct:round((netR*riskAmount/capital)*100,1),
    maxDrawdownR:round(maxDd,2),
    maxDrawdownPct:round(maxDd*riskPct,1),
    maxConsecutiveLosses:maxLossStreak,
    avgWinR:wins.length?round(wins.reduce((a,t)=>a+t.netR,0)/wins.length,2):0,
    avgLossR:losses.length?round(losses.reduce((a,t)=>a+t.netR,0)/losses.length,2):0,
    yearly:Object.entries(yearly).map(([year,r])=>({year,netR:round(r,2),modelPnl:round(r*riskAmount,0)})),
    monthly:Object.entries(monthly).map(([month,r])=>({month,netR:round(r,2),modelPnl:round(r*riskAmount,0)})),
    sampleTrades:trades.slice(-8).reverse()
  };
}

export async function runBacktest(session, { symbol='NIFTY', interval='FIVE_MINUTE', years=3, capital=20000 }={}) {
  symbol=String(symbol).toUpperCase();
  interval=String(interval).toUpperCase();
  years=[1,3,5].includes(Number(years))?Number(years):3;
  capital=Math.max(1000,Math.min(10000000,Number(capital)||20000));
  if(!['NIFTY','BANKNIFTY','SENSEX'].includes(symbol)) throw new Error('Supported symbols: NIFTY, BANKNIFTY, SENSEX');
  if(!MAX_DAYS[interval]) throw new Error('Unsupported interval');

  const entry=await historicalCandles(session,symbol,interval,years);
  const higher=interval==='FIFTEEN_MINUTE'?entry:await historicalCandles(session,symbol,'FIFTEEN_MINUTE',years);
  if(entry.length<300||higher.length<100) throw new Error(`Not enough historical candles returned for ${symbol} ${interval}`);

  const strategies=['CURRENT_CORE','TREND_PRO','REGIME_PRO'].map(x=>simulate(x,entry,interval,higher,capital));
  return {
    symbol, interval, years, capital,
    period:{from:entry[0].timestamp,to:entry[entry.length-1].timestamp},
    candles:entry.length,
    higherTimeframe:'FIFTEEN_MINUTE',
    assumptions:{
      entry:'Signal on candle close; entry at next candle open',
      stop:'1 ATR',
      target1:'1.5 ATR, 50% booked',
      target2:'2 ATR, remaining 50%',
      afterTarget1:'Remaining stop moved to breakeven',
      intradayExit:'Open positions closed around 15:20 IST',
      maxTradesPerDay:3,
      riskPerTradePct:1,
      executionFrictionR:0.05
    },
    strategies,
    limitations:[
      'This first-stage test is on the underlying index, not historical option premium P&L.',
      'Angel index candles have zero volume, so true historical VWAP cannot be reconstructed. Trend Pro uses a session typical-price mean proxy and labels it as such.',
      'Historical PCR and full expired option-chain snapshots are not included in this stage.',
      'Model P&L converts R to rupees using 1% of starting capital per trade; it is not a brokerage statement or guaranteed option return.'
    ],
    generatedAt:new Date().toISOString()
  };
}
