import test from 'node:test';
import assert from 'node:assert/strict';
import { scannerCheckSummary, stockDecisionState, shortlistStocks } from '../src/stock-scanner.js';

test('scanner counts missing historical data separately from analysed setups', () => {
  const rows = [
    { status: 'WAIT', reason: 'Broker candle history is loading; checking shortly' },
    { status: 'WAIT', reason: 'Angel One denied five minute history (HTTP 403)' },
    { status: 'WAIT', reason: 'VWAP, trend, ATR or comparable past volume is missing' },
    { status: 'WAIT', reason: 'No completed breakout or first pullback aligned with the market and sector' },
    { status: 'READY', plan: { entry: 100 }, reason: 'Completed setup' }
  ];
  const s = scannerCheckSummary(rows);
  assert.deepEqual([s.evaluated, s.dataUnavailable, s.loading], [2, 2, 1]);
  assert.match(s.note, /Research signal/);
  assert.equal(stockDecisionState(rows[1]), 'DATA_UNAVAILABLE');
  assert.equal(stockDecisionState(rows[3]), 'WAITING_SETUP');
});

test('a scanner with no completed candles must not imply checks finished', () => {
  const status = scannerCheckSummary([
    { status: 'WAIT', reason: 'Broker restricted five minute history; retrying later' },
    { status: 'WAIT', reason: 'Candle data: historical request cooldown' }
  ]);
  assert.equal(status.evaluated, 0);
  assert.equal(status.dataUnavailable, 2);
  assert.equal(status.loading, 0);
  assert.match(status.note, /0 stocks analysed; 2 need data/);
});
