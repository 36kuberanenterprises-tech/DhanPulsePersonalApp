import { candleData, instrumentMaster, marketData, parseCandles, parseFetched, quoteFeedAgeMs, quoteLtp } from './angel.js';
import { rsi, supertrend } from './indicators.js';
import { quoteSpread, shortlistStocks, stockWatchlist, scannerSession } from './stock-scanner.js';

const IST_MS = 330 * 60_000;
const DAY_MS = 86_400_000;
const FIVE_MIN = 300_000;
const SETTLE_MS = 20_000;
const CACHE_MS = 5 * 60_000;
const RESCAN_GAP_MS = 120_000;
const HISTORY_BLOCK_RECHECK_MS = 5 * 60_000;
const maxCandidates = 8;
const results = new Map();
export function normalizedQuoteTime(raw, now = Date.now()) {
  const age=quoteFeedAgeMs({exchFeedTime:raw},now);
  return Number.isFinite(age) && age >= 0 ? new Date(now-age).toISOString() : null;
}
export function quoteWatchlistCandidates(selected, maxCount = 3) {
  return selected.slice(0, maxCount).map((row,index)=>({
    symbol:row.symbol, sector:row.sector,price:rounded(row.price),
    quoteTime:normalizedQuoteTime(row.quote?.exchFeedTime), rank:index+1,
    changePct:rounded(row.pct), turnoverEstimate:rounded(row.turnover),
    spreadPct:rounded(100 * quoteSpread(row.quote) / row.price),
    status:'QUOTE_SCREENED',
    reason:'Passed live quote freshness, price, turnover, spread and movement filters. This is not a confirmed seven condition strategy match.'
  }));
}

const istDate = time => new Date(time + IST_MS);
const day = time => istDate(time).toISOString().slice(0, 10);
const minute = time => {
  const d = istDate(time);
  return d.getUTCHours() * 60 + d.getUTCMinutes();
};
const format = ms => istDate(ms).toISOString().slice(0, 16).replace('T',' ');
const rounded = n => Number.isFinite(n) ? Number(n.toFixed(2)) : null;
const valid = c => c && Number.isFinite(Date.parse(c.timestamp)) &&
  [c.open, c.high, c.low, c.close, c.volume].every(Number.isFinite) &&
  c.low > 0 && c.high >= Math.max(c.open, c.close, c.low) &&
  c.low <= Math.min(c.open, c.close) && c.volume >= 0;

// NSE cash session begins at 09:15. Higher timeframe buckets must align to
// that time, never to midnight. A partial last two hour bucket is discarded.
export function resampleNseCandles(source, windowMinutes, now) {
  if (![15, 120].includes(windowMinutes)) throw new Error('Unsupported Keep Eye timeframe');
  const size = windowMinutes / 5;
  const slots = new Map();
  const unique = new Map(source.filter(valid).map(c => [Date.parse(c.timestamp), c]));
  for (const [ms, candle] of unique) {
    const m = minute(ms);
    if (m < 555 || m >= 930 || (m - 555) % 5 !== 0) continue;
    if (ms + FIVE_MIN + SETTLE_MS > now.getTime()) continue;
    const slot = Math.floor((m - 555) / windowMinutes);
    const startMinute = 555 + slot * windowMinutes;
    if (startMinute + windowMinutes > 930) continue;
    const key = day(ms) + ':' + slot;
    if (!slots.has(key)) slots.set(key, []);
    slots.get(key).push([ms,candle]);
  }
  return [...slots.values()].flatMap(group => {
    group.sort(([a],[b])=>a-b);
    if (group.length !== size || group.some(([ms],i) => i && ms-group[i-1][0] !== FIVE_MIN)) return [];
    const start = group[0][0];
    if (start + windowMinutes * 60_000 + SETTLE_MS > now.getTime()) return [];
    const candles = group.map(([,c])=>c);
    return [{timestamp:new Date(start).toISOString(),open:candles[0].open,
      high:Math.max(...candles.map(c=>c.high)),low:Math.min(...candles.map(c=>c.low)),
      close:candles.at(-1).close,volume:candles.reduce((s,c)=>s+c.volume,0)}];
  }).sort((a,b)=>Date.parse(a.timestamp)-Date.parse(b.timestamp));
}

export function completedDailyCandles(source, now) {
  const today = day(now.getTime());
  const isTodayComplete = minute(now.getTime()) >= 935;
  const unique = new Map();
  for (const c of source.filter(valid)) {
    const ms = Date.parse(c.timestamp), d = day(ms);
    if (d > today || (d === today && !isTodayComplete)) continue;
    unique.set(d,c);
  }
  return [...unique.values()].sort((a,b)=>Date.parse(a.timestamp)-Date.parse(b.timestamp));
}

export function upperBollinger(closes, period = 20, deviations = 2) {
  if (!Array.isArray(closes) || closes.length < period ||
      closes.slice(-period).some(x=>!Number.isFinite(x))) return null;
  const xs = closes.slice(-period), mean = xs.reduce((s,n)=>s+n,0)/period;
  const variance = xs.reduce((s,n)=>s+(n-mean)**2,0)/period;
  return mean + deviations * Math.sqrt(variance);
}
export function simpleMovingAverage(closes, period = 20) {
  if (!Array.isArray(closes) || closes.length < period ||
      closes.slice(-period).some(x=>!Number.isFinite(x))) return null;
  return closes.slice(-period).reduce((s,n)=>s+n,0)/period;
}

function makeCheck(name, timeframe, last, reference, comparison, evidence) {
  const observed = last && Number.isFinite(last.close) ? rounded(last.close) : null;
  const limit = Number.isFinite(reference) ? rounded(reference) : null;
  const known = observed != null && limit != null;
  return {name,timeframe,observed,reference:limit,
    status: !known ? 'DATA_UNAVAILABLE' : comparison === 'GT'
      ? (last.close > reference ? 'PASS' : 'FAIL') : (last.close < reference ? 'PASS' : 'FAIL'),
    comparison, candleTime:last?.timestamp || null,
    detail:known ? evidence : 'Complete and verified candles are needed for this indicator.'};
}

// Use only completed 120 minute, daily and 15 minute candles. This is a
// long breakout filter plus a short term pullback, not a buy recommendation.
export function evaluateKeepEye({symbol,sector,price,quoteTime,fiveMinute,daily,now,smaPeriod=20}) {
  const higher = resampleNseCandles(fiveMinute,120,now);
  const short = resampleNseCandles(fiveMinute,15,now);
  const dayBars = completedDailyCandles(daily,now);
  const h = higher.at(-1), d = dayBars.at(-1), m = short.at(-1);
  const hClose = higher.map(c=>c.close), dClose = dayBars.map(c=>c.close), mClose = short.map(c=>c.close);
  const hSt = higher.length >= 21 ? supertrend(higher,7,3) : null;
  const dSt = dayBars.length >= 21 ? supertrend(dayBars,7,3) : null;
  const hRsi = higher.length >= 21 ? rsi(hClose,14) : null;
  const dRsi = dayBars.length >= 21 ? rsi(dClose,14) : null;
  const hBb = upperBollinger(hClose);
  const dBb = upperBollinger(dClose);
  const ma = simpleMovingAverage(mClose,smaPeriod);
  const check = (name,timeframe,last,level,comparison,desc) => makeCheck(name,timeframe,last,level,comparison,desc);
  const rsiCheck = (timeframe,latest,value) => ({
    name:'RSI(14) > 60',timeframe,observed:rounded(value),reference:60,comparison:'GT',
    candleTime:latest?.timestamp || null,status:Number.isFinite(value) ? (value > 60?'PASS':'FAIL') : 'DATA_UNAVAILABLE',
    detail:Number.isFinite(value)?'Wilder RSI on completed candles':'At least 21 completed candles required.'
  });
  const checks = [
    check('Close > Supertrend(7,3)','2H',h,hSt?.value,'GT','Two hour completed close above Supertrend'),
    check('Close > Supertrend(7,3)','1D',d,dSt?.value,'GT','Last completed daily close above Supertrend'),
    rsiCheck('2H',h,hRsi),
    rsiCheck('1D',d,dRsi),
    check('Close > Upper Bollinger(20,2)','2H',h,hBb,'GT','Two hour breakout above upper band'),
    check('Close > Upper Bollinger(20,2)','1D',d,dBb,'GT','Completed daily breakout above upper band'),
    check('Close < SMA(' + smaPeriod + ')','15M',m,ma,'LT','Short term pullback below the 15 minute moving average')
  ];
  const passes=checks.filter(c=>c.status==='PASS').length;
  const unavailable=checks.filter(c=>c.status==='DATA_UNAVAILABLE').length;
  const status=passes===checks.length?'MATCH':checks.some(c=>c.status==='FAIL')?'NOT_MATCH':'DATA_UNAVAILABLE';
  return {symbol,sector,price:rounded(price),quoteTime:quoteTime || null,
    status,passed:passes,total:checks.length,unavailable,checks,
    latestTwoHour:h?.timestamp||null,latestDaily:d?.timestamp||null,latestFifteenMinute:m?.timestamp||null,
    bars:{twoHour:higher.length,daily:dayBars.length,fifteenMinute:short.length},
    message:status==='MATCH'?'All seven conditions passed on completed candles. Research watch only, not a trade entry.'
      :unavailable?'Historical candles are incomplete. Missing checks must not be treated as passed.'
      :'At least one Keep Eye condition is not met. No confirmed match.'};
}

export function classifyKeepEyeHistoryError(error, now = Date.now()) {
  const raw = String(error?.message || 'Data unavailable');
  // HTTP 403 alone proves access was denied, not that the caller exceeded a rate limit.
  // The shared history budget may cool down for every 403, but the user-facing
  // cause must be based on the actual broker error text or explicit rate metadata.
  const rateLimited = error?.rateLimited === true || error?.status === 429 ||
    /cooldown|exceeding access rate|rate limit|too many requests|AB1021|\b429\b/i.test(raw);
  const forbidden = error?.status === 403 || /\b403\b|forbidden/i.test(raw);
  const retryAt = Number.isFinite(error?.retryAt)
    ? error.retryAt : now + HISTORY_BLOCK_RECHECK_MS;
  if (rateLimited) return {
    code: 'BROKER_RATE_LIMIT', block: true, retryAt,
    message: 'Angel One historical requests are rate limited or in cooldown. Live stock prices may still work. Wait for broker access before evaluating all seven conditions.'
  };
  if (forbidden) return {
    code: 'BROKER_ACCESS_DENIED', block: true, retryAt,
    message: 'Angel One denied historical candles (HTTP 403). This can be a broker permission, IP or access restriction, not necessarily excessive requests. Verify the broker response and backend egress IP.'
  };
  if (/timeout/i.test(raw)) return {
    code: 'BROKER_TIMEOUT', block: false, retryAt,
    message: 'Angel One historical candle request timed out. No technical match can be confirmed.'
  };
  return {
    code: 'DATA_UNAVAILABLE', block: false, retryAt,
    message: 'Verified historical candle data unavailable. ' + raw.slice(0, 140)
  };
};
const errorText = error => classifyKeepEyeHistoryError(error).message;
export async function evaluateKeepEyeCandidates(session, now, state, selected, fetchHistory = candleData) {
  state.note='Analysing up to eight shortlisted stocks. Broker candle calls are paced across all DhanPulse markets.';
  let blocked = null;
  for (let i = 0; i < selected.length; i++) {
    const item = selected[i];
    if (blocked) {
      state.results[i] = { ...state.results[i], status: 'DATA_UNAVAILABLE', unavailable: 7,
        checks: [], message: 'Not analysed because the broker blocked historical access for ' +
          blocked.symbol + '. Further history requests are paused to avoid repeated rejections.' };
    } else {
      try {
        const token = String(item.instrument.token);
        // Completed 5-minute and daily history are required to validate each rule.
        const five = await fetchHistory(session, { exchange: 'NSE', symboltoken: token,
          interval: 'FIVE_MINUTE', fromdate: format(now.getTime() - 35*DAY_MS), todate: format(now.getTime()) });
        const daily = await fetchHistory(session, { exchange: 'NSE', symboltoken: token,
          interval: 'ONE_DAY', fromdate: format(now.getTime() - 100*DAY_MS), todate: format(now.getTime()) });
        state.results[i] = evaluateKeepEye({ symbol: item.symbol, sector: item.sector, price: item.price,
          quoteTime: item.quote?.exchFeedTime, fiveMinute: parseCandles(five), daily: parseCandles(daily), now });
      } catch (error) {
        const diagnosis = classifyKeepEyeHistoryError(error);
        state.results[i] = { ...state.results[i], status: 'DATA_UNAVAILABLE', unavailable: 7,
          checks: [], message: diagnosis.message };
        if (diagnosis.block) {
          blocked = { code: diagnosis.code, symbol: item.symbol, retryAt: diagnosis.retryAt };
          state.brokerBlock = blocked;
        }
      }
      state.checked++;
    }
    state.matched = state.results.filter(x => x.status === 'MATCH').length;
    state.needData = state.results.filter(x => x.status === 'DATA_UNAVAILABLE').length;
    state.verified = state.results.filter(x => x.checks.length === 7 &&
      x.checks.every(check => check.status !== 'DATA_UNAVAILABLE')).length;
    state.updatedAt = new Date().toISOString();
  }
  state.status = blocked ? 'BROKER_HISTORY_BLOCKED' : state.needData === state.results.length
    ? 'DATA_UNAVAILABLE' : 'COMPLETE';
  state.note = blocked
    ? 'Historical broker access is blocked (' + blocked.code.replace(/_/g, ' ') +
      '). Only ' + state.checked + ' of ' + selected.length +
      ' shortlisted stocks had historical requests attempted. The remaining stocks are quote watchlist candidates only, not rejected strategy matches. Retry after broker cooldown.'
    : state.matched
    ? state.matched + ' stock(s) passed all seven verified conditions. Research watch only, not an entry signal.'
    : state.needData
    ? state.needData + ' shortlisted stocks lack enough verified historical data. No valid strategy match can be decided for those stocks.'
    : 'No stocks passed all seven conditions on verified historical candles.';
}

async function run(session,now,state) {
  const list=await stockWatchlist();
  state.universeSource=list.source;
  if (scannerSession(now) === 'MARKET_CLOSED') {
    state.status='MARKET_CLOSED';
    state.note='This finder requires live, eligible NSE cash stock quotes. Open during market hours to screen stocks.';
    return;
  }
  const master=await instrumentMaster();
  const names=new Map(master.filter(r=>r.exch_seg==='NSE' && String(r.symbol||'').endsWith('-EQ'))
    .map(r=>[String(r.symbol).slice(0,-3),r]));
  const stocks=list.items.map(x=>({...x,instrument:names.get(x.symbol)})).filter(x=>x.instrument);
  const tokens=stocks.map(x=>String(x.instrument.token));
  const quotes=[];
  for(let i=0;i<tokens.length;i+=50)
    quotes.push(...parseFetched(await marketData(session,{NSE:tokens.slice(i,i+50)},'FULL')));
  const byToken=new Map(quotes.map(q=>[String(q.symbolToken??q.symboltoken??q.token),q]));
  const candidates=stocks.map(stock=>{
    const q=byToken.get(String(stock.instrument.token));
    const price=quoteLtp(q),age=quoteFeedAgeMs(q,Date.now());
    return {...stock,quote:q,price,age,pct:Number(q?.percentChange),
      turnover:price * Number(q?.tradeVolume||0),
      fresh:age!=null && age>=0 && age<=15_000 && price>0};
  });
  const selected=shortlistStocks(candidates).slice(0,maxCandidates);
  state.scanned=stocks.length;
  state.selected=selected.length;
  // A valid quote-based shortlist is an observable result even if the broker
  // refuses all historical candle requests. Never call it a technical match.
  state.quoteWatchlist=quoteWatchlistCandidates(selected);
  state.results=selected.map((row,index)=>({symbol:row.symbol,sector:row.sector,price:rounded(row.price),
    selectionRank:index+1,quoteTime:row.quote?.exchFeedTime||null,status:'CHECKING',
    passed:0,total:7,checks:[],message:'Loading completed candles for Keep Eye checks.'}));
  if(!selected.length){
    state.status='NO_CANDIDATES';
    state.note='No fresh stock quotes passed the existing liquidity, spread and movement filters. No match is inferred.';
    return;
  }
  await evaluateKeepEyeCandidates(session, now, state, selected);
  // Previous Android clients do not parse the quoteWatchlist field, so keep
  // the quote shortlisted names visible in their existing scanner summary.
  if (state.quoteWatchlist.length) {
    const symbols=state.quoteWatchlist.map(row=>row.symbol).join(', ');
    state.note='Live quote watchlist: '+symbols+
      '. NOT seven condition matches or BUY recommendations. '+state.note;
  }
}

export async function keepEyeScan(session,now=new Date(),force=false) {
  const client=String(session.clientCode||session.apiKey||'');
  const key=client+':'+day(now.getTime());
  const item=results.get(key);
  if(item && (item.data.status==='RUNNING' ||
    (item.data.brokerBlock && Date.now() < item.data.brokerBlock.retryAt) ||
    Date.now()-item.at<(force?RESCAN_GAP_MS:CACHE_MS))) return item.data;
  const state={status:'RUNNING',timestamp:now.toISOString(),updatedAt:now.toISOString(),
    scanned:0,selected:0,checked:0,verified:0,matched:0,needData:0,brokerBlock:null,
    quoteWatchlist:[],universeSource:'',results:[],
    note:'Loading NSE cash universe and eligible live quotes.'};
  results.set(key,{at:Date.now(),data:state});
  // Return status immediately, then publish progress without blocking the API.
  void run(session,now,state).catch(err=>{
    state.status='DATA_UNAVAILABLE';state.note=errorText(err);state.updatedAt=new Date().toISOString();
  });
  if(results.size>100)for(const oldest of results.keys()){results.delete(oldest);if(results.size<=50)break;}
  return state;
}
