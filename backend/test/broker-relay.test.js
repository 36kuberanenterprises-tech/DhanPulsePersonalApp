import test from 'node:test';
import assert from 'node:assert/strict';
import { probeOrderRelay, requestCandleViaRelay } from '../src/broker-relay.js';

test('configured order relay remains blocked until its actual IP is verified', async () => {
  const url = 'https://static.example.test';
  const secret = 'test-secret';
  const registered = ['34.70.199.153'];
  const wrong = await probeOrderRelay(url, secret, registered, async () =>
    new Response(JSON.stringify({ ready: true, actualPublicIp: '74.220.52.132',
      expectedPublicIp: '34.70.199.153' }), { status: 200 }));
  assert.equal(wrong.ready, false);
  assert.equal(wrong.status, 'RELAY_IP_UNVERIFIED');

  const missingSecret = await probeOrderRelay(url, '', registered);
  assert.equal(missingSecret.status, 'RELAY_SECRET_MISSING');
  assert.equal(missingSecret.ready, false);

  const insecure = await probeOrderRelay('http://static.example.test', secret, registered);
  assert.equal(insecure.status, 'RELAY_URL_INVALID');
  assert.equal(insecure.ready, false);

  const matching = await probeOrderRelay(url, secret, registered, async () =>
    new Response(JSON.stringify({ ready: true, actualPublicIp: '34.70.199.153',
      expectedPublicIp: '34.70.199.153' }), { status: 200 }));
  assert.equal(matching.ready, true);
  assert.equal(matching.status, 'READY');
});

test('history relay preserves broker candle response and rejection', async () => {
  const payload = { exchange: 'NSE', symboltoken: '99926000', interval: 'FIVE_MINUTE',
    fromdate: '2026-10-12 09:15', todate: '2026-10-12 10:00' };
  const session = { apiKey: 'key', jwt: 'token' };
  let requests = 0;
  const fetcher = async (url, init) => {
    requests++;
    assert.equal(url, 'https://static.example.test/api/angel/candles');
    assert.equal(init.headers['X-Relay-Secret'], 'secret');
    assert.deepEqual(JSON.parse(init.body), { apiKey: 'key', jwt: 'token', payload });
    return new Response(JSON.stringify({ ok: true, candles: { status: true, data: [[1, 2, 3]] } }), { status: 200 });
  };
  const accepted = await requestCandleViaRelay('https://static.example.test/', 'secret', session, payload, fetcher);
  assert.deepEqual(accepted.data, [[1, 2, 3]]);
  assert.equal(requests, 1);

  await assert.rejects(
    requestCandleViaRelay('https://static.example.test', 'secret', session, payload,
      async () => new Response(JSON.stringify({ ok: false,
        error: 'Access denied because of exceeding access rate' }), { status: 403 })),
    /exceeding access rate.*HTTP 403/i
  );
});
