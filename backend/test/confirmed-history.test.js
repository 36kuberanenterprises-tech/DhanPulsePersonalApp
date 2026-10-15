import test from 'node:test';
import assert from 'node:assert/strict';
import { confirmedBrokerCandles, brokerHistoryFresh } from '../src/analysis.js';

test('every market requires a completed current broker candle, not merely a fresh quote', () => {
  const now = new Date('2026-10-15T04:05:25Z'); // 09:35:25 IST
  const bar = timestamp => ({ timestamp, open: 100, high: 101, low: 99, close: 100 });
  assert.equal(brokerHistoryFresh([bar('2026-10-15T03:55:00Z')], 'FIVE_MINUTE', now), false);
  assert.equal(brokerHistoryFresh([bar('2026-10-15T04:00:00Z')], 'FIVE_MINUTE', now), true);
  assert.equal(brokerHistoryFresh([bar('2026-10-15T04:05:00Z')], 'FIVE_MINUTE', now), false);
  assert.equal(brokerHistoryFresh([], 'FIVE_MINUTE', now), false);
});

test('confirmed SENSEX candles are not repolled every refresh; failed refresh retains only stale evidence', async () => {
  const previousFetch = globalThis.fetch;
  const previousNow = Date.now;
  let clock = Date.parse('2026-10-05T03:50:00Z');
  let calls = 0;
  const history = Array.from({ length: 60 }, (_, i) => [
    new Date(clock - (60 - i) * 300_000).toISOString(), 72_000, 72_005, 71_995, 72_000, 0
  ]);
  try {
    Date.now = () => clock;
    globalThis.fetch = async url => {
      if (String(url).includes('api.ipify.org')) return new Response('{"ip":"74.220.52.132"}');
      calls++;
      return calls === 1
        ? new Response(JSON.stringify({ status: true, data: history }), { status: 200 })
        : new Response('Access denied because of exceeding access rate', { status: 403 });
    };
    const args = [{ apiKey: 'test', jwt: 'test' }, 'BSE', 'test-sensex-cache', 'FIVE_MINUTE'];
    const first = await confirmedBrokerCandles(...args, new Date(clock));
    assert.equal(first.length, 60);
    clock += 60_000;
    const second = await confirmedBrokerCandles(...args, new Date(clock));
    assert.equal(calls, 1, 'one-minute app refresh must not hit the broker again');
    assert.equal(second.length, 60);
    clock += 5 * 60_000;
    const retained = await confirmedBrokerCandles(...args, new Date(clock));
    assert.equal(calls, 2, 'the next completed bar may trigger one broker refresh');
    assert.deepEqual(retained, first, 'failed refresh retains only verified old bars');
    clock += 60_000;
    await confirmedBrokerCandles(...args, new Date(clock));
    assert.equal(calls, 2, 'broker rejection must not cause a refresh loop');
  } finally {
    globalThis.fetch = previousFetch;
    Date.now = previousNow;
  }
});
