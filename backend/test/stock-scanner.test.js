import test from 'node:test';
import assert from 'node:assert/strict';
import { completedCandles, estimatedRoundTrip, evaluateStock, scannerSession, sessionVwap, sizeStockTrade } from '../src/stock-scanner.js';

const india = (date, hour, minute) => new Date(Date.UTC(2026, 8, date, hour - 5, minute - 30));
const candle = (date, hour, minute, open, high, low, close, volume) => ({
  timestamp: india(date, hour, minute).toISOString(), open, high, low, close, volume
});

test('scanner pauses outside the confirmed NSE entry window', () => {
  assert.equal(scannerSession(india(25, 9, 30)), 'OPENING_RANGE');
  assert.equal(scannerSession(india(25, 9, 35)), 'SCANNING');
  assert.equal(scannerSession(india(25, 14, 45)), 'NO_NEW_ENTRIES');
  assert.equal(scannerSession(india(26, 11, 0)), 'MARKET_CLOSED');
});

test('VWAP needs completed traded volume and weights a heavy candle', () => {
  const rows = [
    candle(25, 9, 15, 100, 101, 99, 100, 10),
    candle(25, 9, 20, 102, 103, 101, 102, 10),
    candle(25, 9, 25, 104, 105, 103, 104, 80),
    candle(25, 9, 30, 200, 201, 199, 200, 100)
  ];
  const verified = completedCandles(rows, india(25, 9, 30));
  assert.equal(verified.length, 2);
  assert.equal(sessionVwap(rows.slice(0, 3), india(25, 9, 30)), 103.4);
  assert.equal(sessionVwap([rows[0], { ...rows[1], volume: 0 }, rows[2]], india(25, 9, 30)), null);
});

test('position risk includes costs and respects cash, including high priced shares', () => {
  const size = sizeStockTrade({ cash: 20_000, entry: 100, stop: 99, spread: 0.05 });
  assert.ok(size.quantity > 0);
  assert.ok(size.estimatedLoss <= 100);
  assert.ok(size.estimatedCosts >= estimatedRoundTrip(100, size.quantity, 0.05) - 0.01);
  assert.equal(sizeStockTrade({ cash: 20_000, entry: 30_000, stop: 29_500 }), null);
});

test('a missing stock feed or volume cannot produce a READY call', () => {
  const now = india(25, 9, 46);
  const quote = { ltp: 101, close: 99, exchFeedTime: '25-Sep-2026 09:46:00',
    depth: { buy: [{ price: 100.99 }], sell: [{ price: 101.01 }] } };
  const inputs = { symbol: 'TEST', sector: 'Financial Services', quote, candles: [], now,
    cash: 20_000, niftyReturn: 0.1, sectorReturn: 0.4, sectorCount: 2 };
  assert.equal(evaluateStock(inputs).status, 'WAIT');
  assert.match(evaluateStock(inputs).reason, /volume/);
  assert.match(evaluateStock({ ...inputs, quote: { ...quote, exchFeedTime: '25-Sep-2026 09:40:00' } }).reason, /delayed/);
});

test('an opening range break needs completed volume and a fresh quote', () => {
  const previous = [18, 21, 22, 23, 24].flatMap((day, d) =>
    Array.from({ length: 75 }, (_, i) => {
      const price = 96.5 + d * 0.35 + i * 0.012;
      return candle(day, 9 + Math.floor((15 + 5 * i) / 60), (15 + 5 * i) % 60,
        price, price + 1.0, price - 1.0, price + 0.05, 10_000);
    }));
  const today = [
    candle(25, 9, 15, 100.0, 100.5, 99.9, 100.3, 25_000),
    candle(25, 9, 20, 100.3, 100.7, 100.0, 100.5, 25_000),
    candle(25, 9, 25, 100.5, 100.85, 100.2, 100.6, 25_000),
    candle(25, 9, 30, 100.6, 100.75, 100.1, 100.6, 25_000),
    candle(25, 9, 35, 100.6, 100.75, 99.1, 100.6, 25_000),
    candle(25, 9, 40, 100.6, 101.2, 100.7, 101.0, 25_000)
  ];
  const quote = { ltp: 101, close: 99, exchFeedTime: '25-Sep-2026 09:46:00',
    depth: { buy: [{ price: 100.99 }], sell: [{ price: 101.01 }] } };
  const inputs = { symbol: 'TEST', sector: 'Financial Services', quote,
    candles: [...previous, ...today], now: india(25, 9, 46), cash: 20_000,
    niftyReturn: 0.1, sectorReturn: 0.4, sectorCount: 2 };
  const result = evaluateStock(inputs);
  assert.equal(result.status, 'READY', result.reason);
  assert.equal(result.setup, 'OPENING_RANGE');
  assert.ok(result.plan.estimatedLoss <= 100);
  const absentVolume = evaluateStock({ ...inputs, candles: [...previous, ...today.map(c => ({ ...c, volume: 0 }))] });
  assert.equal(absentVolume.status, 'WAIT');
});
