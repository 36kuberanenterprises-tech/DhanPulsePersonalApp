import test from 'node:test';
import assert from 'node:assert/strict';
import { analyse } from '../src/analysis.js';

test('a SENSEX history rate rejection is shown as unavailable for new and older clients', async () => {
  const previousFetch = globalThis.fetch;
  const master = [{ token: '99919000', symbol: 'SENSEX', name: 'SENSEX', exch_seg: 'BSE', instrumenttype: 'AMXIDX' }];
  try {
    globalThis.fetch = async url => {
      const path = String(url);
      if (path.includes('OpenAPIScripMaster.json')) return new Response(JSON.stringify(master), { status: 200 });
      if (path.includes('/market/v1/quote/')) return new Response(JSON.stringify({ status: true,
        data: { fetched: [{ symbolToken: '99919000', ltp: 55_000 }] } }), { status: 200 });
      if (path.includes('/historical/v1/getCandleData')) return new Response('Access denied because of exceeding access rate', { status: 403 });
      throw new Error('Unexpected broker request');
    };
    for (const policy of ['sensex-families-v1', null]) {
      const result = await analyse({ apiKey: 'test', jwt: 'test' }, 'SENSEX', 'FIVE_MINUTE', null, policy);
      assert.equal(result.tradeDecision.status, 'HISTORY_UNAVAILABLE');
      assert.equal(result.tradeDecision.direction, 'WAIT');
      assert.equal(result.tradeDecision.setupAllowed, false);
      assert.equal(result.tradeDecision.autoEntryAllowed, false);
      assert.equal(result.dataFresh, false);
      assert.match(result.tradeDecision.message, /exceeding access rate/i);
    }
  } finally {
    globalThis.fetch = previousFetch;
  }
});
