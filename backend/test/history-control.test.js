import test from 'node:test';
import assert from 'node:assert/strict';
import { HistoryBudget, validateCandlePayload } from '../src/history-control.js';
import { candleData } from '../src/angel.js';

test('client cooldown respects broker retry time, grows on repeated rejection and does not block another client', async () => {
  let now = 1000, requests = 0;
  const budget = new HistoryBudget({ now: () => now, sleep: async ms => { now += ms; } });
  const request = async () => { requests++; throw Object.assign(new Error('Too many requests AB1021'), { status: 429, retryAfterMs: 90_000 }); };
  await assert.rejects(budget.run('A', async () => {}, request), e => e.retryAt === 91_000);
  await assert.rejects(budget.run('A', async () => {}, request), /cooldown/);
  assert.equal(requests, 1);
  assert.equal(await budget.run('B', async () => {}, async () => 'ok'), 'ok');
  now = 91_000;
  await assert.rejects(budget.run('A', async () => {}, request), e => e.retryAt === 211_000);
  now = 211_000;
  await budget.run('A', async () => {}, async () => 'ok');
  assert.equal(budget.state('A').failures, 0);
});

test('minute and hour budgets reject excess calls before sending, even with small configured spacing', async () => {
  for (const [minute, hour, wait] of [[2, 10, 60_000], [10, 2, 3_600_000]]) {
    let now = 0, sent = 0;
    const budget = new HistoryBudget({ now: () => now, sleep: async ms => { now += ms; }, limits: { gap: 1, minute, hour } });
    for (let i = 0; i < 2; i++) await budget.run('A', async () => {}, async () => { sent++; });
    await assert.rejects(budget.run('A', async () => {}, async () => { sent++; }), e => e.retryAt === wait);
    assert.equal(sent, 2);
  }
});

test('history spacing applies after other broker reads have delayed a permit', async () => {
  let now = 0;
  const budget = new HistoryBudget({ now: () => now, sleep: async ms => { now += ms; } });
  const starts = [];
  await Promise.all(Array.from({ length: 3 }, () => budget.run('A', async () => { now += 300; }, async () => starts.push(now))));
  assert.ok(starts[1] - starts[0] >= 1100);
  assert.ok(starts[2] - starts[1] >= 1100);
});

const payload = { exchange: 'BSE', symboltoken: '99919000', interval: 'FIVE_MINUTE', fromdate: '2026-10-01 09:15', todate: '2026-10-01 09:50' };
test('bad candle dates and excessive ranges fail before broker access', () => {
  assert.doesNotThrow(() => validateCandlePayload(payload));
  for (const bad of [{ fromdate: '2026-02-30 09:15' }, { todate: payload.fromdate }, { interval: 'INVALID' }, { fromdate: '2025-01-01 09:15' }]) {
    assert.throws(() => validateCandlePayload({ ...payload, ...bad }), /invalid/);
  }
});

test('identical history requests share one call and JSON errors preserve HTTP status and Retry-After', async () => {
  const previous = globalThis.fetch;
  let calls = 0;
  try {
    globalThis.fetch = async () => {
      calls++;
      return new Response(JSON.stringify({ status: false, message: 'Too many requests', errorcode: 'AB1021' }),
        { status: 429, headers: { 'Retry-After': '120' } });
    };
    const session = { clientCode: 'json-error-test', apiKey: 'test', jwt: 'test' };
    const results = await Promise.allSettled([candleData(session, payload), candleData(session, payload)]);
    assert.equal(calls, 1);
    for (const result of results) {
      assert.equal(result.status, 'rejected');
      assert.equal(result.reason.status, 429);
      assert.equal(result.reason.brokerCode, 'AB1021');
      assert.ok(result.reason.retryAfterMs >= 120_000);
    }
    await assert.rejects(candleData(session, payload), /cooldown/);
    assert.equal(calls, 1);
  } finally { globalThis.fetch = previous; }
});
