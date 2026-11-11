import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, basename } from 'node:path';
import { candleCachePath, readSavedCandles, saveBrokerCandles } from '../src/candle-store.js';

const rows = Array.from({length:60}, (_,i)=>{
  const time=new Date(Date.UTC(2026,10,11,4,i));
  return {timestamp:time.toISOString(),open:100+i,high:101+i,low:99+i,close:100.5+i,volume:1000+i};
});

test('persisted broker candles survive a simulated restart and never store credentials',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'dhanpulse-candle-test-'));
  const key='REAL_CLIENT_CODE|NSE|99926000|ONE_MINUTE|confirmed';
  try {
    const saved=await saveBrokerCandles(key,rows,{directory:dir});
    assert.equal(saved,true);
    const file=candleCachePath(key,dir);
    assert.ok(/^[a-f0-9]{64}\.json$/.test(basename(file)));
    const contents=await readFile(file,'utf8');
    assert.ok(!contents.includes('REAL_CLIENT_CODE'));
    assert.ok(!contents.includes('99926000'));
    assert.ok(!contents.includes('jwtToken'));
    assert.equal(JSON.parse(contents).candles.length,60);
    const restored=await readSavedCandles(key,{directory:dir});
    assert.equal(restored.candles.length,60);
    assert.equal(restored.candles.at(-1).close,159.5);
    assert.ok(Number.isFinite(restored.savedAt));
    assert.equal(await readSavedCandles('ANOTHER_CLIENT|NSE|99926000|ONE_MINUTE|confirmed',{directory:dir}),null);
  }finally{await rm(dir,{recursive:true,force:true});}
});

test('a corrupt or incomplete disk file never fabricates broker candles',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'dhanpulse-candle-test-'));
  const key='CLIENT|BSE|99919000|FIFTEEN_MINUTE|confirmed';
  try {
    assert.equal(await readSavedCandles(key,{directory:dir}),null);
    await writeFile(candleCachePath(key,dir),'{ broken JSON');
    assert.equal(await readSavedCandles(key,{directory:dir}),null);
    await writeFile(candleCachePath(key,dir),JSON.stringify({version:1,candles:rows.slice(0,4)}));
    assert.equal(await readSavedCandles(key,{directory:dir}),null);
    await writeFile(candleCachePath(key,dir),JSON.stringify({version:2,candles:rows}));
    assert.equal(await readSavedCandles(key,{directory:dir}),null);
  }finally{await rm(dir,{recursive:true,force:true});}
});

test('invalid OHLC rows are excluded and duplicate candle timestamps are resolved',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'dhanpulse-candle-test-'));
  const key='CLIENT|NSE|123|ONE_MINUTE|confirmed';
  try{
    const duplicate={...rows.at(-1),close:160.25,high:161};
    const invalid={timestamp:rows[0].timestamp,open:50,high:40,low:50,close:50,volume:100};
    await saveBrokerCandles(key,[...rows,duplicate,invalid],{directory:dir});
    const result=await readSavedCandles(key,{directory:dir});
    assert.equal(result.candles.length,60);
    assert.equal(result.candles.at(-1).close,160.25);
  }finally{await rm(dir,{recursive:true,force:true});}
});

test('cache refuses to write fewer than 35 historical candles',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'dhanpulse-candle-test-'));
  try{
    assert.equal(await saveBrokerCandles('short',rows.slice(0,10),{directory:dir}),false);
    assert.equal(await readSavedCandles('short',{directory:dir}),null);
  }finally{await rm(dir,{recursive:true,force:true});}
});
