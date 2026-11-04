import test from 'node:test';
import assert from 'node:assert/strict';
import { resampleNseCandles, completedDailyCandles, upperBollinger, simpleMovingAverage, evaluateKeepEye } from '../src/keep-eye-finder.js';

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
