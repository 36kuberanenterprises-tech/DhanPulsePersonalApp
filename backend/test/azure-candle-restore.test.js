import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { saveBrokerCandles } from '../src/candle-store.js';
import { confirmedBrokerCandles, brokerHistoryFresh, historyCacheStatus } from '../src/analysis.js';

test('after a simulated Azure restart, broker-confirmed disk candles survive a 403 but cannot become fresh signals',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'dhanpulse-restore-test-'));
  const previousDir=process.env.DHANPULSE_CANDLE_CACHE_DIR;
  const previousFetch=globalThis.fetch;
  const session={clientCode:'restore-only-account',apiKey:'test',jwt:'test'};
  const cacheKey='restore-only-account|NSE|99926000|ONE_MINUTE|confirmed';
  const start=Date.parse('2026-11-10T04:00:00.000Z');
  const rows=Array.from({length:60},(_,i)=>({
    timestamp:new Date(start+i*60_000).toISOString(),open:100+i,
    high:101+i,low:99+i,close:100+i,volume:1000+i
  }));
  const now=new Date('2026-11-11T05:30:00Z');
  let brokerCalls=0;
  try{
    process.env.DHANPULSE_CANDLE_CACHE_DIR=dir;
    await saveBrokerCandles(cacheKey,rows);
    globalThis.fetch=async()=>{brokerCalls++;return new Response('Access denied because of exceeding access rate',{status:403});};
    const output=await confirmedBrokerCandles(session,'NSE','99926000','ONE_MINUTE',now);
    assert.equal(output.length,60);
    assert.equal(output.at(-1).close,159);
    assert.equal(brokerCalls,1);
    assert.equal(brokerHistoryFresh(output,'ONE_MINUTE',now),false);
    const status=historyCacheStatus(session);
    assert.equal(status.total,1);
    assert.equal(status.entries[0].restoredFromDisk,true);
    assert.equal(status.entries[0].interval,'ONE_MINUTE');
    assert.equal(status.entries[0].bars,60);
    assert.ok(!JSON.stringify(status).includes('restore-only-account'));
  }finally{
    globalThis.fetch=previousFetch;
    if(previousDir===undefined)delete process.env.DHANPULSE_CANDLE_CACHE_DIR;
    else process.env.DHANPULSE_CANDLE_CACHE_DIR=previousDir;
    await rm(dir,{recursive:true,force:true});
  }
});
