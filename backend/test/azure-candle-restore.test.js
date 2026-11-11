import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { saveBrokerCandles, readSavedCandles } from '../src/candle-store.js';
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


test('an unfinished broker candle is never saved as a completed candle across process restarts',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'dhanpulse-partial-bar-test-'));
  const previousDir=process.env.DHANPULSE_CANDLE_CACHE_DIR;
  const previousFetch=globalThis.fetch;
  const clientCode='partial-bar-client';
  const token='test-partial-candle-token';
  const key=clientCode+'|NSE|'+token+'|ONE_MINUTE|confirmed';
  const now=new Date('2026-11-11T05:08:30.000Z');
  // Most recent 1m bar opened at 05:08 UTC but was sampled only 30 seconds
  // into that interval. It is valid in RAM for display, not for disk recovery.
  const rows=Array.from({length:60},(_,i)=>{
    const time=new Date(now.getTime()-(59-i)*60_000-30_000);
    return [time.toISOString(),100,101,99,100,500];
  });
  try{
    process.env.DHANPULSE_CANDLE_CACHE_DIR=dir;
    globalThis.fetch=async()=>new Response(JSON.stringify({status:true,data:rows}),{status:200});
    const output=await confirmedBrokerCandles(
      {clientCode,apiKey:'test',jwt:'test'},'NSE',token,'ONE_MINUTE',now);
    assert.equal(output.length,60);
    const restored=await readSavedCandles(key,{directory:dir});
    assert.ok(restored);
    assert.equal(restored.candles.length,59);
    assert.equal(restored.candles.at(-1).timestamp,rows.at(-2)[0]);
    assert.equal(brokerHistoryFresh(restored.candles,'ONE_MINUTE',now),true);
  }finally{
    globalThis.fetch=previousFetch;
    if(previousDir===undefined)delete process.env.DHANPULSE_CANDLE_CACHE_DIR;
    else process.env.DHANPULSE_CANDLE_CACHE_DIR=previousDir;
    await rm(dir,{recursive:true,force:true});
  }
});
