import test from 'node:test';
import assert from 'node:assert/strict';
import { analyse } from '../src/analysis.js';

test('NIFTY and BANKNIFTY do not analyse a live quote without broker candles', async () => {
  const previousFetch = globalThis.fetch;
  const previousNow = Date.now;
  const now = Date.parse('2026-10-12T04:10:00Z'); // Monday 09:40 IST
  Date.now = () => now;
  const master = [
    { token: '99926000', symbol: 'NIFTY', name: 'NIFTY', exch_seg: 'NSE', instrumenttype: 'AMXIDX' },
    { token: '99926009', symbol: 'BANKNIFTY', name: 'BANKNIFTY', exch_seg: 'NSE', instrumenttype: 'AMXIDX' }
  ];
  const requestedHistory = [];
  try {
    globalThis.fetch = async url => {
      const path = String(url);
      if (path.includes('api.ipify.org')) return new Response('{"ip":"74.220.52.132"}');
      if (path.includes('OpenAPIScripMaster.json')) return new Response(JSON.stringify(master), { status: 200 });
      if (path.includes('/market/v1/quote/')) return new Response(JSON.stringify({ status: true, data: {
        fetched: master.map(row => ({ symbolToken: row.token, ltp: row.symbol === 'NIFTY' ? 25000 : 56000,
          exchFeedTime: '12-Oct-2026 09:40:00' }))
      } }), { status: 200 });
      if (path.includes('/historical/v1/getCandleData')) {
        requestedHistory.push(path);
        return new Response('Access denied because of exceeding access rate', { status: 403 });
      }
      throw new Error(`Unexpected request: ${path}`);
    };
    for (const symbol of ['NIFTY', 'BANKNIFTY']) {
      const result = await analyse({ apiKey: 'test', jwt: 'test' }, symbol, 'FIVE_MINUTE');
      assert.equal(result.tradeDecision.status, 'HISTORY_UNAVAILABLE', symbol);
      assert.equal(result.tradeDecision.direction, 'WAIT', symbol);
      assert.equal(result.tradeDecision.setupAllowed, false, symbol);
      assert.equal(result.tradeDecision.autoEntryAllowed, false, symbol);
      assert.equal(result.dataFresh, false, symbol);
      assert.equal(result.signal, 'WAIT', symbol);
      assert.equal(result.suggestedContract, null, symbol);
      assert.equal(result.levels, null, symbol);
      assert.equal(result.market.lastCandleTime, null, symbol);
    }
    assert.ok(requestedHistory.length >= 1);
  } finally {
    globalThis.fetch = previousFetch;
    Date.now = previousNow;
  }
});
