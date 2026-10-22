import test from 'node:test';
import assert from 'node:assert/strict';
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
