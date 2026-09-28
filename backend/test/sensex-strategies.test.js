import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluateSensexFamilies, sensexClosedCandles, buildSensexDecision } from '../src/sensex-strategies.js';

const now = new Date('2026-09-28T09:21:00Z'); // 14:51 IST

function candles(count, latest, minutes, slope) {
  const end = Date.parse(latest);
  return Array.from({ length: count }, (_, i) => {
    const close = 55_000 + (i - count + 1) * slope;
    return { timestamp: new Date(end - (count - i - 1) * minutes * 60_000).toISOString(),
      open: close - 5, high: close + 10, low: close - 10, close, volume: 100 };
  });
}

function trendingFamily() {
  return evaluateSensexFamilies({
    candles: candles(80, '2026-09-28T09:15:00Z', 5, 3),
    higherCandles: candles(50, '2026-09-28T09:00:00Z', 15, 7),
    interval: 'FIVE_MINUTE', spot: 55_000, now
  });
}

const liquidCall = { contract: { token: '123', ltp: 100, oi: 5000, lotSize: 20,
  bid: 99.5, ask: 100.5, bidQty: 100, askQty: 80 }, reason: 'liquid', score: 93 };

function decide(family, changes = {}) {
  return buildSensexDecision({ family, pcr: 1.02, oiCoverage: '5/5 paired strikes',
    support: 54_800, resistance: 55_300, spot: 55_000, futurePrice: 55_035,
    selected: liquidCall, now, ...changes });
}

test('only broker completed bars enter the SENSEX signal and all six families are reported', () => {
  const family = trendingFamily();
  assert.equal(family.direction, 'CE');
  assert.equal(family.regime.name, 'TREND');
  assert.equal(family.votes.length, 6);
  assert.deepEqual(family.active.map(v => v.name), ['Trend continuation']);

  const complete = candles(80, '2026-09-28T09:15:00Z', 5, 3);
  const unfinished = { ...complete.at(-1), timestamp: '2026-09-28T09:20:00Z',
    open: 55_000, high: 55_400, low: 54_600, close: 54_600 };
  assert.equal(sensexClosedCandles([...complete, unfinished], 'FIVE_MINUTE', now).at(-1).close, 55_000);
  const withPartial = evaluateSensexFamilies({ candles: [...complete, unfinished],
    higherCandles: candles(50, '2026-09-28T09:00:00Z', 15, 7),
    interval: 'FIVE_MINUTE', spot: 55_000, now });
  assert.deepEqual(withPartial.votes, family.votes);
});

test('a supported SENSEX setup stays manual even when all market checks pass', () => {
  const result = decide(trendingFamily());
  assert.equal(result.direction, 'CE');
  assert.equal(result.status, 'FAMILY_CONFIRMED');
  assert.equal(result.setupAllowed, true);
  assert.equal(result.autoEntryAllowed, false);
  assert.equal(result.contextChecks.length, 7);
  assert.ok(result.contextChecks.every(x => x.vote === 'OK'));
});

test('independent opposing families and opposite OI veto a call', () => {
  const family = trendingFamily();
  const opposing = { ...family, direction: 'WAIT', conflict: true,
    active: [...family.active, { name: 'Liquidity reversal', vote: 'PE' }],
    votes: [...family.votes.slice(0, 3), { name: 'Liquidity reversal', vote: 'PE' }, ...family.votes.slice(4)] };
  const disagreement = decide(opposing);
  assert.equal(disagreement.direction, 'WAIT');
  assert.equal(disagreement.status, 'REJECTED_CONFLICT');
  assert.equal(disagreement.setupAllowed, false);
  assert.match(disagreement.message, /families disagree/i);

  const oiOpposite = decide(family, { pcr: 0.82 });
  assert.equal(oiOpposite.direction, 'WAIT');
  assert.equal(oiOpposite.status, 'REJECTED_CONFLICT');
  assert.match(oiOpposite.message, /PCR.*opposite/i);
});

test('unknown OI, stale higher candle, missing futures basis and illiquid option cause WAIT', () => {
  const family = trendingFamily();
  for (const change of [
    { pcr: null, oiCoverage: '2/5 paired strikes' },
    { futurePrice: null },
    { selected: { contract: { ...liquidCall.contract, ask: 105 } } },
    { selected: { contract: { ...liquidCall.contract, bidQty: 3 } } },
    { now: new Date('2026-09-28T09:47:00Z') }
  ]) {
    const result = decide(family, change);
    assert.equal(result.direction, 'WAIT');
    assert.equal(result.setupAllowed, false);
    assert.equal(result.autoEntryAllowed, false);
  }
  const delayed = evaluateSensexFamilies({
    candles: candles(80, '2026-09-28T09:05:00Z', 5, 3),
    higherCandles: candles(50, '2026-09-28T09:00:00Z', 15, 7),
    interval: 'FIVE_MINUTE', spot: 55_000, now
  });
  assert.equal(delayed.direction, 'WAIT');
  assert.match(delayed.reason, /delayed/);
});
