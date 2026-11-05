import test from 'node:test';
import assert from 'node:assert/strict';
import { resampleNseCandles, completedDailyCandles, upperBollinger, simpleMovingAverage, evaluateKeepEye, classifyKeepEyeHistoryError, evaluateKeepEyeCandidates, quoteWatchlistCandidates, normalizedQuoteTime } from '../src/keep-eye-finder.js';

const start=Date.parse('2026-11-04T03:45:00Z'); // 09:15 IST
const now=new Date('2026-11-04T10:15:30Z'); // 15:45 IST
const make=(ms,price=100)=>({timestamp:new Date(ms).toISOString(),open:price-0.1,high:price+1,low:price-1,close:price,volume:100});

test('2H NSE aggregation uses exact 09:15 anchor and rejects partial 15:15 session tail',()=>{
  const five=Array.from({length:75},(_,i)=>make(start+i*300_000,100+i*0.1));
  const h=resampleNseCandles(five,120,now);
  const m=resampleNseCandles(five,15,now);
  assert.equal(h.length,3);
  assert.equal(m.length,25);
  assert.equal(h[0].timestamp,new Date(start).toISOString());
  assert.equal(h[1].timestamp,new Date(start+120*60_000).toISOString());
  assert.equal(h[2].timestamp,new Date(start+240*60_000).toISOString());
  assert.equal(h[0].close,five[23].close);
  assert.equal(m.at(-1).close,five[74].close);
});

test('incomplete 15m or 2H groups and time windows never become completed candles',()=>{
  const five=Array.from({length:75},(_,i)=>make(start+i*300_000));
  const withoutFive=five.filter((_,i)=>i!==7);
  assert.equal(resampleNseCandles(withoutFive,120,now).length,2);
  assert.equal(resampleNseCandles(withoutFive,15,now).length,24);
  assert.equal(resampleNseCandles(five,120,new Date('2026-11-04T05:14:59Z')).length,0); // before first 2h closes
});

test('daily inputs exclude the current unfinished session',()=>{
  const yesterday=make(Date.parse('2026-11-03T03:45:00Z'));
  const today=make(start);
  const rows=[yesterday,today];
  const morning=new Date('2026-11-04T05:00:00Z');
  assert.deepEqual(completedDailyCandles(rows,morning),[yesterday]);
  assert.equal(completedDailyCandles(rows,now).length,2);
});

test('bollinger and SMA use latest full period only',()=>{
  const xs=Array.from({length:20},()=>100);
  assert.equal(upperBollinger(xs),100);
  assert.equal(simpleMovingAverage(xs),100);
  assert.equal(upperBollinger(xs.slice(1)),null);
  assert.equal(simpleMovingAverage(xs.slice(1)),null);
});

test('the seven mandatory checks must all have completed data before any match',()=>{
  const result=evaluateKeepEye({symbol:'TEST',sector:'Testing',price:100,quoteTime:null,
    fiveMinute:[],daily:[],now});
  assert.equal(result.status,'DATA_UNAVAILABLE');
  assert.equal(result.total,7);
  assert.equal(result.passed,0);
  assert.equal(result.unavailable,7);
  assert.equal(result.checks.length,7);
  assert.deepEqual(result.checks.map(c=>c.timeframe),['2H','1D','2H','1D','2H','1D','15M']);
  assert.ok(result.checks.every(c=>c.status==='DATA_UNAVAILABLE'));
});


test('generic HTTP 403 reports access denial rather than claiming the account exceeded rate limits', () => {
  const x = classifyKeepEyeHistoryError(Object.assign(new Error('Candle data HTTP 403 Forbidden'), { status: 403 }), 0);
  assert.equal(x.code, 'BROKER_ACCESS_DENIED');
  assert.equal(x.block, true);
  assert.match(x.message, /permission, IP or access restriction/);
});

test('explicit broker rate response reports a rate cooldown independently from HTTP 403 denial', () => {
  const error = Object.assign(new Error('HTTP 403 Access denied because of exceeding access rate'), { status: 403, retryAt: 300_000 });
  const x = classifyKeepEyeHistoryError(error, 0);
  assert.equal(x.code, 'BROKER_RATE_LIMIT');
  assert.equal(x.retryAt, 300_000);
  assert.equal(x.block, true);
});

test('one denied history request prevents repeatedly retrying seven more shortlisted stocks', async () => {
  const selected = ['A','B','C'].map((symbol,i) => ({
    symbol, sector: 'Test', price: 110 + i, instrument: { token: String(i + 100) }, quote: {}
  }));
  const state = { checked: 0, matched: 0, needData: 0, brokerBlock: null,
    results: selected.map(x => ({ symbol: x.symbol, status: 'CHECKING', total: 7, passed: 0, checks: [] })) };
  let calls = 0;
  const fetchHistory = async () => {
    calls++;
    throw Object.assign(new Error('HTTP 403 Forbidden'), { status: 403 });
  };
  await evaluateKeepEyeCandidates({clientCode:'test'}, new Date('2026-11-05T04:15:00Z'), state, selected, fetchHistory);
  assert.equal(calls, 1);
  assert.equal(state.checked, 1);
  assert.equal(state.needData, 3);
  assert.equal(state.matched, 0);
  assert.equal(state.status, 'BROKER_HISTORY_BLOCKED');
  assert.equal(state.brokerBlock.code, 'BROKER_ACCESS_DENIED');
  assert.ok(state.results.every(x => x.status === 'DATA_UNAVAILABLE'));
  assert.match(state.note, /quote watchlist candidates only, not rejected strategy matches/);
});

test('a live quote screened stock is visible without inventing a historical strategy match', () => {
  const q = (symbol, price, rank) => ({
    symbol, sector:'Financial Services', price, pct:0.5+rank,
    turnover:20_000_000 + rank, quote:{exchFeedTime:'2026-11-05T09:47:00+05:30',
      depth:{buy:[{price:price-0.1}],sell:[{price:price+0.1}]}}
  });
  const result=quoteWatchlistCandidates([q('A',100,1),q('B',110,2),q('C',120,3),q('D',130,4)]);
  assert.equal(result.length,3);
  assert.deepEqual(result.map(r=>r.symbol),['A','B','C']);
  assert.equal(result[0].rank,1);
  assert.equal(result[0].status,'QUOTE_SCREENED');
  assert.equal(result[0].price,100);
  assert.ok(result[0].spreadPct>0);
  assert.match(result[0].reason,/not a confirmed seven condition/);
  assert.equal(result.some(row=>row.status==='MATCH'),false);
});

test('Angel One exchange quote time is converted to ISO for the Android watchlist', () => {
  const now=Date.parse('2026-11-05T04:17:30Z');
  const actual=normalizedQuoteTime('05-Nov-2026 09:47:00',now);
  assert.equal(actual,'2026-11-05T04:17:00.000Z');
  assert.equal(normalizedQuoteTime('unverified',now),null);
});
