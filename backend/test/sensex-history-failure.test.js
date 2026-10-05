import test from 'node:test';
import assert from 'node:assert/strict';
import { analyse } from '../src/analysis.js';

test('a SENSEX history rate rejection is shown as unavailable for new and older clients', async () => {
  const previousFetch = globalThis.fetch;
  const master = [
    { token: '99919000', symbol: 'SENSEX', name: 'SENSEX', exch_seg: 'BSE', instrumenttype: 'AMXIDX' },
    ...[55000, 55100, 55200].flatMap((strike, i) => ['CE', 'PE'].map((side, j) => ({
      token: String(1000 + i * 2 + j), symbol: `SENSEX31DEC30${strike}${side}`, name: 'SENSEX',
      exch_seg: 'BFO', instrumenttype: 'OPTIDX', strike: String(strike * 100),
      expiry: '31DEC2030', lotsize: '20'
    })))
  ];
  const indiaNow = new Date(Date.now() + 330 * 60_000);
  const pad = x => String(x).padStart(2, '0');
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const feedTime = `${pad(indiaNow.getUTCDate())}-${months[indiaNow.getUTCMonth()]}-${indiaNow.getUTCFullYear()} ${pad(indiaNow.getUTCHours())}:${pad(indiaNow.getUTCMinutes())}:${pad(indiaNow.getUTCSeconds())}`;
  try {
    globalThis.fetch = async url => {
      const path = String(url);
      if (path.includes('api.ipify.org')) return new Response('{"ip":"74.220.52.132"}');
      if (path.includes('OpenAPIScripMaster.json')) return new Response(JSON.stringify(master), { status: 200 });
      if (path.includes('/market/v1/quote/')) return new Response(JSON.stringify({ status: true,
        data: { fetched: [{ symbolToken: '99919000', ltp: 55_100, exchFeedTime: feedTime },
          ...master.slice(1).map(row => ({ symbolToken: row.token, ltp: 80,
            opnInterest: row.symbol.endsWith('PE') ? 120 : 100, exchFeedTime: feedTime }))] } }), { status: 200 });
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
      assert.equal(result.optionChain.expiry, '31DEC2030');
      assert.equal(result.optionChain.atm, 55100);
      assert.equal(result.optionChain.nearAtmPcr, 1.2);
      assert.equal(result.optionChain.pcrCoverage, '3/3 paired strikes');
      assert.equal(result.optionChain.contracts.length, 6);
      assert.equal(result.suggestedContract, null);
    }
  } finally {
    globalThis.fetch = previousFetch;
  }
});
