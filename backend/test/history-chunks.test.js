import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { readHistoryChunk, saveHistoryChunk } from '../src/history-chunk-store.js';
import { HistoryChunks } from '../src/history-chunks.js';
const payload = { exchange: 'NSE', symboltoken: '99926000', interval: 'FIVE_MINUTE',
  fromdate: '2026-09-01 09:15', todate: '2026-09-30 15:30' };

test('research retry reuses successful chunks, retries failed chunk, and isolates accounts and intervals', async () => {
  const cache = new HistoryChunks({ now: () => Date.parse('2026-10-22T10:00:00Z') });
  const second = { ...payload, fromdate: '2026-10-01 09:15', todate: '2026-10-21 15:30' };
  let calls = 0, fail = true;
  const read = p => cache.get('client1', p, async () => {
    calls++; if (p === second && fail) throw new Error('HTTP 403'); return [p.fromdate];
  });
  await read(payload);
  await assert.rejects(read(second), /403/);
  fail = false;
  await read(payload); await read(second);
  assert.equal(calls, 3, 'first chunk was retained despite later failure');
  await cache.get('client2', payload, async () => { calls++; return ['other account']; });
  await cache.get('client1', { ...payload, interval: 'ONE_MINUTE' }, async () => { calls++; return ['other interval']; });
  assert.equal(calls, 5);
});

test('simultaneous requests share one download; active and empty chunks refresh', async () => {
  let now = Date.parse('2026-10-22T10:00:00Z'), calls = 0;
  const cache = new HistoryChunks({ now: () => now });
  const today = { ...payload, todate: '2026-10-22 15:30' };
  const load = async () => { calls++; return ['bar']; };
  await Promise.all([cache.get('c', today, load), cache.get('c', today, load)]);
  assert.equal(calls, 1);
  now += 16_000;
  await cache.get('c', today, load);
  assert.equal(calls, 2);
  const empty = async () => { calls++; return []; };
  await cache.get('empty', payload, empty); await cache.get('empty', payload, empty);
  assert.equal(calls, 4);
});

test('research chunk cache respects its row budget', async () => {
  const cache = new HistoryChunks({ maxRows: 2 });
  let calls = 0;
  const load = async () => { calls++; return [1, 2]; };
  await cache.get('a', payload, load); await cache.get('b', payload, load);
  await cache.get('a', payload, load);
  assert.equal(calls, 3);
  assert.equal(cache.rows, 2);
});

test('confirmed historical research chunks survive process restart without another broker call', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'dhanpulse-research-'));
  const at = Date.parse('2026-11-18T10:00:00Z');
  const sample = [{ timestamp: '2026-09-01T04:00:00.000Z', open: 100, high: 110, low: 95,
    close: 105, volume: 200 }];
  try {
    const cache1 = new HistoryChunks({ now: () => at, persistent: true, directory: dir });
    let calls = 0;
    assert.deepEqual(await cache1.get('account-one', payload, async () => { calls++; return sample; }), sample);
    const filenames = await readdir(dir);
    assert.equal(filenames.length, 1);
    assert.ok(!filenames[0].includes('account-one'));
    const cache2 = new HistoryChunks({ now: () => at + 2000, persistent: true, directory: dir });
    assert.deepEqual(await cache2.get('account-one', payload, async () => {
      calls++; throw new Error('Broker should not be asked for saved chunk');
    }), sample);
    assert.equal(calls, 1);
    assert.deepEqual(await cache2.get('another-account', payload, async () => { calls++; return sample; }), sample);
    assert.equal(calls, 2);
  } finally { await rm(dir, { recursive: true, force: true }); }
});

test('unfinished current-day chunks and invalid bars are never persisted as historical proof', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'dhanpulse-research-'));
  const at = Date.parse('2026-11-18T10:00:00Z');
  const sameDay = { ...payload, fromdate: '2026-11-17 09:15', todate: '2026-11-18 15:30' };
  const sample = [{ timestamp: '2026-11-17T04:00:00.000Z', open: 100,
    high: 110, low: 95, close: 105, volume: 200 }];
  try {
    assert.equal(await saveHistoryChunk('day', sameDay, sample, { directory: dir, now: at }), false);
    assert.equal(await saveHistoryChunk('invalid', payload, [{ ...sample[0], high: 1 }],
      { directory: dir, now: at }), false);
    assert.equal((await readdir(dir)).length, 0);
    assert.equal(await readHistoryChunk('day', { directory: dir, now: at }), null);
  } finally { await rm(dir, { recursive: true, force: true }); }
});
