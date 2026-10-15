import test from 'node:test';
import assert from 'node:assert/strict';
import { aggregateMcxMinutes, createMcxHistoryLoader } from '../src/mcx-history.js';

const now = new Date('2026-10-15T08:00:30Z');
const rows = Array.from({ length: 240 }, (_,i) => ({
  timestamp: new Date(Date.parse('2026-10-15T04:00:00Z') + i*60_000).toISOString(),
  open:100+i, high:102+i, low:99+i, close:101+i, volume:10
}));
const raw = bars => ({ status:true, data:bars.map(c=>[c.timestamp,c.open,c.high,c.low,c.close,c.volume]) });

test('MCX recovery aggregates only complete contiguous broker minute candles', () => {
  const bars = aggregateMcxMinutes(rows,'FIVE_MINUTE',now);
  assert.equal(bars.length,48);
  assert.deepEqual(bars[0],{ timestamp:rows[0].timestamp,open:100,high:106,low:99,close:105,volume:50 });
  assert.equal(aggregateMcxMinutes(rows.filter((_,i)=>i!==2),'FIVE_MINUTE',now).length,47);
  assert.equal(aggregateMcxMinutes([...rows,rows[0]],'FIVE_MINUTE',now).length,48);
  assert.equal(aggregateMcxMinutes(rows,'FIVE_MINUTE',new Date('2026-10-15T04:05:10Z')).length,0);
});

test('MCX short history recovers from the same token and uses cached completed bars', async () => {
  const calls=[];
  const load=createMcxHistoryLoader(async(_,p)=>{ calls.push(p);return p.interval==='ONE_MINUTE'?raw(rows):raw([]); });
  const args=[{clientCode:'mcx-test'},'MCX','573422','FIVE_MINUTE'];
  const result=await load(...args,now);
  assert.equal(result.length,48);
  assert.deepEqual(calls.map(p=>[p.exchange,p.symboltoken,p.interval]),[
    ['MCX','573422','FIVE_MINUTE'],['MCX','573422','ONE_MINUTE']]);
  assert.deepEqual(await load(...args,new Date(now.getTime()+3000)),result);
  assert.equal(calls.length,2);
});

test('MCX never issues a fallback request after a broker rate rejection', async () => {
  let calls=0;
  const error=Object.assign(new Error('HTTP 403 exceeding access rate'),{status:403,retryAt:Date.now()+120_000});
  const load=createMcxHistoryLoader(async()=>{calls++;throw error;});
  const args=[{clientCode:'mcx-rate'},'MCX','99920005','FIVE_MINUTE',now];
  await assert.rejects(load(...args),/403/);
  await assert.rejects(load(...args),/403/);
  assert.equal(calls,1);
});

test('an MCX token with no historical data remains unavailable and does not loop', async () => {
  let calls=0;
  const load=createMcxHistoryLoader(async()=>{calls++;return raw([]);});
  const args=[{clientCode:'mcx-empty'},'MCX','99920005','FIVE_MINUTE',now];
  await assert.rejects(load(...args),/0 completed candles/);
  await assert.rejects(load(...args),/35 are required/);
  assert.equal(calls,2);
});
