import test from 'node:test';
import assert from 'node:assert/strict';
import { analyse } from '../src/analysis.js';

test('a live SENSEX quote with old broker candles is DATA_STALE and cannot issue a call', async () => {
  const previousFetch = globalThis.fetch;
  const previousNow = Date.now;
  const now = Date.parse('2026-10-12T04:01:00Z'); // Monday 09:31 IST
  Date.now = () => now;
  const pad = x => String(x).padStart(2, '0');
  const local = new Date(now + 330 * 60_000);
  const feedTime = `${pad(local.getUTCDate())}-Oct-${local.getUTCFullYear()} ${pad(local.getUTCHours())}:${pad(local.getUTCMinutes())}:${pad(local.getUTCSeconds())}`;
  const master = [
    { token: '99919000', symbol: 'SENSEX', name: 'SENSEX', exch_seg: 'BSE', instrumenttype: 'AMXIDX' },
    ...[72400, 72500, 72600].flatMap((strike, i) => ['CE', 'PE'].map((side, j) => ({
      token: String(9200 + i * 2 + j), symbol: `SENSEX31DEC30${strike}${side}`,
      name: 'SENSEX', exch_seg: 'BFO', instrumenttype: 'OPTIDX',
      strike: String(strike * 100), expiry: '31DEC2030', lotsize: '20'
    })))
  ];
  const bars = [8, 9].flatMap(day => Array.from({ length: 75 }, (_, i) => [
    new Date(Date.parse(`2026-10-${String(day).padStart(2, '0')}T03:45:00Z`) + i * 300_000).toISOString(),
    72_500, 72_510, 72_490, 72_500, 0
  ]));
  try {
    globalThis.fetch = async url => {
      const path = String(url);
      if (path.includes('OpenAPIScripMaster.json')) return new Response(JSON.stringify(master), { status: 200 });
      if (path.includes('/market/v1/quote/')) return new Response(JSON.stringify({ status: true, data: {
        fetched: master.map(row => ({ symbolToken: row.token, ltp: row.token === '99919000' ? 72_565 : 100,
          opnInterest: 100, exchFeedTime: feedTime }))
      } }), { status: 200 });
      if (path.includes('/historical/v1/getCandleData')) return new Response(JSON.stringify({ status: true, data: bars }), { status: 200 });
      throw new Error(`Unexpected request: ${path}`);
    };
    const result = await analyse({ apiKey: 'test', jwt: 'test' }, 'SENSEX', 'FIVE_MINUTE', null, 'sensex-families-v1');
    assert.equal(result.tradeDecision.status, 'DATA_STALE');
    assert.equal(result.dataFresh, false);
    assert.equal(result.signal, 'WAIT');
    assert.equal(result.tradeDecision.setupAllowed, false);
    assert.equal(result.tradeDecision.autoEntryAllowed, false);
    assert.equal(result.suggestedContract, null);
    assert.deepEqual(result.tradeDecision.strategyVotes, []);
    assert.deepEqual(result.tradeDecision.contextChecks, []);
    assert.deepEqual(result.rules, []);
    assert.equal(result.ruleScore.considered, 0);
    assert.match(result.tradeDecision.message, /quote is live.*candle is delayed/i);
  } finally {
    globalThis.fetch = previousFetch;
    Date.now = previousNow;
  }
});
