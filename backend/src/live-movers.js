import { instrumentMaster, marketData, parseFetched, quoteFeedAgeMs, quoteLtp } from './angel.js';
import { stockWatchlist, quoteSpread } from './stock-scanner.js';

const NIFTY_500_URLS = [
  'https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv',
  'https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv'
];
const IST_MS = 330 * 60_000;
const QUOTE_MAX_AGE = 20_000;
const QUOTE_BATCH_SIZE = 50; // Official Angel One FULL mode limit is 50 tokens.
const CACHE_MS = 120_000;
const WATCH_MAX = 10;
const sessions = new Map();
let universeCache = {at:0,items:[],source:''};

const round = (x,places=2) => Number.isFinite(x) ? Number(x.toFixed(places)) : null;
const ist = time => new Date(time + IST_MS);
const dateKey = time => ist(time).toISOString().slice(0,10);
const minuteOfDay = time => {const d=ist(time);return d.getUTCHours()*60+d.getUTCMinutes();};
export function moversMarketOpen(now = new Date()) {
  const time=now.getTime(),day=ist(time).getUTCDay(),mins=minuteOfDay(time);
  return day>=1 && day<=5 && mins>=555 && mins<930;
}
function csvRow(s) {
  let out=[],word='',quotes=false;
  for(let i=0;i<s.length;i++){
    if(s[i]==='"' && quotes && s[i+1]==='"'){word+='"';i++;}
    else if(s[i]==='"')quotes=!quotes;
    else if(s[i]===','&&!quotes){out.push(word.trim());word='';}
    else word+=s[i];
  }
  return [...out,word.trim()];
}
export function parseNifty500Csv(csv) {
  const rows=String(csv||'').replace(/^\uFEFF/,'').split(/\r?\n/).filter(Boolean);
  const headers=csvRow(rows.shift()||'').map(s=>s.toLowerCase());
  const symbolIndex=headers.indexOf('symbol'), industryIndex=headers.indexOf('industry');
  if(symbolIndex<0) throw new Error('NSE Nifty 500 constituent file is missing symbol column');
  const unique=new Map();
  for(const line of rows){
    const cols=csvRow(line);
    const symbol=String(cols[symbolIndex]||'').toUpperCase();
    if(/^[A-Z0-9&-]{2,25}$/.test(symbol))
      unique.set(symbol,{symbol,sector:cols[industryIndex]||'Unclassified'});
  }
  if(unique.size<450 || unique.size>550)throw new Error('NSE Nifty 500 list failed constituent count validation');
  return [...unique.values()];
}
async function moversUniverse() {
  if(universeCache.items.length&&Date.now()-universeCache.at<6*60*60_000)return universeCache;
  for(const url of NIFTY_500_URLS) {
    try{
      const res=await fetch(url,{signal:AbortSignal.timeout(8000)});
      if(!res.ok)throw new Error('NSE constituent feed unavailable');
      const items=parseNifty500Csv(await res.text());
      universeCache={at:Date.now(),items,source:'Official NSE Nifty 500 constituent list'};
      return universeCache;
    }catch{ /* Try alternate official NSE index file. */ }
  }
  // Never mislabel the limited fallback as a Nifty 500 scan.
  const limited=await stockWatchlist();
  const items=[...limited.items];
  if(!items.some(x=>x.symbol==='ASHOKLEY'))
    items.push({symbol:'ASHOKLEY',sector:'Unclassified'});
  universeCache={at:Date.now(),items,
    source:'LIMITED fallback stock watchlist (including ASHOKLEY); NSE 500 file unavailable'};
  return universeCache;
}
export function evaluateMoverQuote(stock,quote,now=Date.now()) {
  const price=quoteLtp(quote);
  const prevClose=Number(quote?.close),open=Number(quote?.open),high=Number(quote?.high);
  const volume=Number(quote?.tradeVolume);
  const age=quoteFeedAgeMs(quote,now);
  const spread=quoteSpread(quote);
  const turnover=price*volume;
  const valid=Number.isFinite(price)&&price>=50&&Number.isFinite(prevClose)&&prevClose>0&&
    Number.isFinite(open)&&open>0&&Number.isFinite(high)&&high>=price&&
    Number.isFinite(volume)&&volume>0&&Number.isFinite(age)&&age>=0&&age<=QUOTE_MAX_AGE;
  if(!valid)return null;
  const changePct=(price/prevClose-1)*100;
  const gapPct=(open/prevClose-1)*100;
  const fromOpenPct=(price/open-1)*100;
  const distanceHighPct=(high-price)/high*100;
  // Use BOTH gap continuation and session momentum. Day change alone is
  // not sufficient to imply intraday strength, nor does a quote prove a breakout.
  const openingContinuation=gapPct>=1.5&&fromOpenPct>=0.65&&distanceHighPct<=2;
  const sessionMomentum=changePct>=2&&fromOpenPct>=1.75&&distanceHighPct<=2;
  if(!openingContinuation&&!sessionMomentum)return null;
  if(turnover<10_000_000)return null;
  const spreadPct=spread!=null?spread/price*100:null;
  const upperCircuit=Number(quote?.upperCircuit);
  const circuitBufferPct=Number.isFinite(upperCircuit)&&upperCircuit>price
    ?(upperCircuit-price)/price*100:null;
  const liquidityVerified=spreadPct!=null && spreadPct<=0.20;
  const circuitSafe=circuitBufferPct!=null&&circuitBufferPct>=1;
  const extended=changePct>=9||fromOpenPct>=6;
  const needsReview=!liquidityVerified||!circuitSafe||extended;
  const score=changePct*1.5 + Math.max(0,fromOpenPct)*2 +
    Math.max(0,1.5-distanceHighPct)*1.5 + Math.log10(Math.max(1,turnover))*0.45;
  return {
    symbol:stock.symbol, sector:stock.sector,token:String(stock.instrument?.token||''),
    price:round(price),priorClose:round(prevClose),open:round(open),dayHigh:round(high),
    changePct:round(changePct),gapPct:round(gapPct),fromOpenPct:round(fromOpenPct),
    distanceHighPct:round(distanceHighPct),estimatedTurnover:round(turnover),
    spreadPct:round(spreadPct),circuitBufferPct:round(circuitBufferPct),
    quoteTime: new Date(now-age).toISOString(),ageSeconds:round(age/1000,1),
    pattern:openingContinuation?'GAP_CONTINUATION':'INTRADAY_MOMENTUM',
    score:round(score,3),
    status:needsReview?'WATCH_CAUTION':'LIVE_MOVER',
    warnings:[
      ...(spreadPct==null?['Bid and ask spread not available']:spreadPct>0.2?['Bid and ask spread exceeds 0.2%']:[]),
      ...(circuitBufferPct==null?['Upper circuit buffer not verified']:circuitBufferPct<1?['Price is within 1% of upper circuit']:[]),
      ...(extended?['Price already extended; avoid chasing the move']:[])
    ],
    note:'LIVE QUOTE WATCH ONLY. Historical candles, average volume, corporate actions and exact entry levels are not verified.'
  };
}
export function moverMarketBreadth(rows){
  const valid=rows.filter(x=>Number.isFinite(x.pct));
  const up=valid.filter(x=>x.pct>0).length,down=valid.filter(x=>x.pct<0).length;
  const bySector=new Map();
  for(const r of valid){if(!bySector.has(r.sector))bySector.set(r.sector,[]);bySector.get(r.sector).push(r.pct);}
  const sectorBreadth=[...bySector.entries()].filter(([,values])=>values.length>=3)
    .map(([sector,pcts])=>({sector,count:pcts.length,advancers:pcts.filter(x=>x>0).length,
      averageChangePct:round(pcts.reduce((a,b)=>a+b,0)/pcts.length)}))
    .sort((a,b)=>b.averageChangePct-a.averageChangePct).slice(0,6);
  return {scanned:valid.length,advancers:up,decliners:down,unchanged:valid.length-up-down,
    advancingPct:valid.length?round(up/valid.length*100):null,sectorBreadth,
    note:'Breadth calculated only from fresh NSE cash quotes scanned by DhanPulse, not the NSE index heatmap.'};
}
async function run(session,now,state) {
  if(!moversMarketOpen(now)){
    state.status='MARKET_CLOSED';state.note='Live Movers scans during the NSE cash session (09:15 to 15:30 IST).';
    state.updatedAt=new Date().toISOString();return;
  }
  const universe=await moversUniverse();
  state.universeSource=universe.source;state.universeCount=universe.items.length;
  const master=await instrumentMaster();
  const eq=new Map(master.filter(r=>r.exch_seg==='NSE'&&String(r.symbol||'').endsWith('-EQ'))
    .map(r=>[String(r.symbol).slice(0,-3),r]));
  const stocks=universe.items.map(r=>({...r,instrument:eq.get(r.symbol)})).filter(r=>r.instrument);
  state.eligibleUniverse=stocks.length;
  const allRows=[], movers=[];
  for(let i=0;i<stocks.length;i+=QUOTE_BATCH_SIZE){
    const group=stocks.slice(i,i+QUOTE_BATCH_SIZE);
    try{
      const raw=await marketData(session,{NSE:group.map(x=>String(x.instrument.token))},'FULL');
      const byToken=new Map(parseFetched(raw).map(q=>[String(q.symbolToken??q.symboltoken??q.token),q]));
      for(const stock of group){
        const q=byToken.get(String(stock.instrument.token));
        const price=quoteLtp(q),age=quoteFeedAgeMs(q,Date.now());
        const prev=Number(q?.close);
        if(price>0&&prev>0&&Number.isFinite(age)&&age>=0&&age<=QUOTE_MAX_AGE)
          allRows.push({sector:stock.sector,pct:(price/prev-1)*100});
        const candidate=evaluateMoverQuote(stock,q,Date.now());
        if(candidate)movers.push(candidate);
      }
    }catch(error){
      state.batchErrors++;
      state.lastError=String(error?.message||'Quote data unavailable').slice(0,180);
    }
    state.processed=Math.min(stocks.length,i+group.length);
    state.movers=movers.sort((a,b)=>b.score-a.score).slice(0,WATCH_MAX);
    state.breadth=moverMarketBreadth(allRows);
    state.updatedAt=new Date().toISOString();
  }
  state.status=state.batchErrors?'PARTIAL':'COMPLETE';
  state.note=state.movers.length
    ?state.movers.length+' fresh quote movers found across '+state.breadth.scanned+' verified quotes. These are WATCH alerts, not trading recommendations.'
    :'No quote movers passed freshness, turnover and momentum filters. Do not invent a trade signal.';
  if(state.batchErrors)state.note+=' Some quote batches failed. Scan coverage is incomplete.';
}
export async function scanLiveMovers(session,now=new Date(),force=false) {
  const client=String(session?.clientCode||session?.apiKey||'unknown');
  const key=client+':'+dateKey(now.getTime());
  const last=sessions.get(key);
  if(last&&(last.state.status==='RUNNING'||Date.now()-last.at<(force?60_000:CACHE_MS)))return last.state;
  const state={status:'RUNNING',timestamp:now.toISOString(),updatedAt:now.toISOString(),
    universeSource:'',universeCount:0,eligibleUniverse:0,processed:0,
    batchErrors:0,lastError:null,movers:[],breadth:moverMarketBreadth([]),
    note:'Screening a broad NSE stock universe using current FULL quotes. No historical candles are required.'};
  sessions.set(key,{at:Date.now(),state});
  void run(session,now,state).catch(err=>{
    state.status='UNAVAILABLE';state.note=String(err?.message||'Quote scanner unavailable').slice(0,180);
    state.updatedAt=new Date().toISOString();
  });
  if(sessions.size>75)for(const k of sessions.keys()){sessions.delete(k);if(sessions.size<=50)break;}
  return state;
}
