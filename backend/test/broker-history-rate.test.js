import test from 'node:test';
import assert from 'node:assert/strict';
import { candleData, marketData, positions, rmsLimit } from '../src/angel.js';

const session = { apiKey: 'test', jwt: 'test' };
const payload = { exchange: 'BSE', symboltoken: '1', interval: 'FIVE_MINUTE', fromdate: '2026-10-01 09:15', todate: '2026-10-01 09:50' };

test('parallel broker history requests are paced and a rate rejection pauses the queue', async () => {
  const previousFetch = globalThis.fetch;
  const starts = [];
  try {
    globalThis.fetch = async () => {
      starts.push(Date.now());
      return new Response(JSON.stringify({ status: true, data: [] }), { status: 200 });
    };
    await Promise.all([candleData(session, payload), candleData(session, payload)]);
    assert.equal(starts.length, 2);
    assert.ok(starts[1] - starts[0] >= 1000, `history calls started only ${starts[1] - starts[0]}ms apart`);

    globalThis.fetch = async () => {
      starts.push(Date.now());
      return new Response('Access denied because of exceeding access rate', { status: 403 });
    };
    await assert.rejects(candleData(session, payload), /exceeding access rate/);
    const requestsAtRejection = starts.length;
    await assert.rejects(candleData(session, payload), /exceeding access rate.*cooldown/i);
    assert.equal(starts.length, requestsAtRejection, 'cooldown must not send another broker request');
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test('quote and account reads start apart, while an order safety check can bypass the queue', async () => {
  const previousFetch = globalThis.fetch;
  const starts = [];
  try {
    globalThis.fetch = async url => {
      starts.push({ url: String(url), at: Date.now() });
      return new Response(JSON.stringify({ status: true, data: {} }), { status: 200 });
    };
    await Promise.all([
      marketData(session, { BSE: ['99919000'] }),
      rmsLimit(session),
      positions(session)
    ]);
    assert.equal(starts.length, 3);
    assert.ok(starts[1].at - starts[0].at >= 450);
    assert.ok(starts[2].at - starts[1].at >= 450);

    // Safety checks for an exit must not wait behind another quote refresh.
    const queued = marketData(session, { BSE: ['99919000'] });
    await positions(session, true);
    await queued;
    assert.ok(starts.at(-2).url.includes('getPosition'));
  } finally {
    globalThis.fetch = previousFetch;
  }
});
