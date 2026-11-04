import test from 'node:test';
import assert from 'node:assert/strict';
import { signalEngine, buildTradeDecision } from '../src/analysis.js';

test('missing EMA or momentum inputs cannot create a false bearish signal', () => {
  const result = signalEngine({
    spot: 23848.8, ema9: null, ema15: null,
    futuresPrice: null, vwapValue: null, vwapSource: 'Broker history denied',
    rsiValue: null, macdValue: null, st: null, pcr: null
  });
  assert.equal(result.signal, 'WAIT');
  assert.equal(result.bearRules, 0);
  assert.equal(result.bullRules, 0);
  assert.equal(result.rules.find(r => r.name === 'Price vs EMA 9').state, 'UNAVAILABLE');
  assert.equal(result.rules.find(r => r.name === 'EMA 9 vs EMA 15').state, 'UNAVAILABLE');
  assert.equal(result.rules.find(r => r.name === 'Supertrend').state, 'UNAVAILABLE');
});

test('a zero or missing futures traded average is not a directional vote', () => {
  const base = { spot: 100, ema9: 99, ema15: 98, futuresPrice: 100, vwapValue: 0,
    rsiValue: 62, macdValue: { histogram: 0.3 }, st: { direction: 'BULLISH', value: 95 }, pcr: null };
  const noAverage = signalEngine(base);
  assert.equal(noAverage.rules.find(r => r.name === 'Futures vs traded average').state, 'UNAVAILABLE');
  const withAverage = signalEngine({ ...base, vwapValue: 98 });
  assert.equal(withAverage.rules.find(r => r.name === 'Futures vs traded average').state, 'BULLISH');
});

test('missing higher timeframe or unsuitable regime prevents a call despite directional votes', () => {
  const decision = buildTradeDecision({
    engine: { signal: 'PE', bullRules: 0, bearRules: 6 },
    trend: { vote: 'PE', detail: 'down trend' },
    htf: { vote: 'WAIT', detail: 'no complete fifteen minute bars' },
    oi: { vote: 'WAIT', detail: 'open interest not verified' },
    regime: { name: 'TRENDING', suitable: true },
    sr: { support: null, resistance: null },
    spot: 23848.8, atrValue: 80,
    selected: { contract: { token: '123', ltp: 50 }, reason: 'quote available', score: 70 },
    now: new Date('2026-11-04T05:30:00Z')
  });
  assert.equal(decision.setupAllowed, false);
});
