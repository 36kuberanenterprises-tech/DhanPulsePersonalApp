import test from 'node:test';
import assert from 'node:assert/strict';

process.env.NODE_ENV = 'test';
process.env.SESSION_ENCRYPTION_KEY = 'ab'.repeat(32);
const { app } = await import('../src/server.js');
const { sealSession } = await import('../src/session-token.js');

test('all tab read routes reject missing sessions and return structured errors', async () => {
  const server = app.listen(0, '127.0.0.1');
  await new Promise(resolve => server.once('listening', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    for (const path of ['/api/analysis/NIFTY', '/api/analysis/SENSEX', '/api/analysis/BANKNIFTY',
      '/api/markets/mcx', '/api/stocks/scanner', '/api/stocks/opportunity', '/api/stocks/options/catalog',
      '/api/stocks/options/RELIANCE', '/api/account', '/api/order/diagnostics', '/api/backtest/catalog']) {
      const response = await fetch(base + path);
      assert.equal(response.status, 401, path);
      assert.equal((await response.json()).error, 'Login required', path);
    }
    const health = await (await fetch(base + '/health')).json();
    assert.equal(health.version, '2.9.8');
  } finally { await new Promise(resolve => server.close(resolve)); }
});

test('broker account failure remains an explicit service error, never an empty successful balance', async () => {
  const originalFetch = global.fetch;
  let brokerCalls = 0;
  global.fetch = async (url, init) => {
    if (String(url).startsWith('http://127.0.0.1:')) return originalFetch(url, init);
    brokerCalls++;
    return new Response(JSON.stringify({ status: false, message: 'Broker unavailable' }), { status: 503 });
  };
  const server = app.listen(0, '127.0.0.1');
  await new Promise(resolve => server.once('listening', resolve));
  const session = sealSession({ apiKey: 'test-key', clientCode: 'route-test', jwt: 'test-jwt',
    createdAt: Date.now(), expiresAt: Date.now() + 60_000 });
  try {
    const url = `http://127.0.0.1:${server.address().port}/api/account`;
    const responses = await Promise.all([fetch(url, { headers: { 'X-Session-Id': session } }), fetch(url, { headers: { 'X-Session-Id': session } })]);
    for (const response of responses) {
      assert.equal(response.status, 503);
      const body = await response.json();
      assert.ok(body.error);
      assert.equal(body.availableCash, undefined);
    }
    assert.ok(brokerCalls > 0);
  } finally {
    global.fetch = originalFetch;
    await new Promise(resolve => server.close(resolve));
  }
});
