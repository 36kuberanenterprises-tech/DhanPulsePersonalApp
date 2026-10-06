import test from 'node:test';
import assert from 'node:assert/strict';
import { chooseStockSetup, chooseStockOption } from '../src/stock-opportunities.js';

const now = Date.parse('2026-10-06T05:00:00Z');
const stock = { status: 'READY', side: 'SELL', symbol: 'RELIANCE', token: '2885',
  reason: 'Confirmed', plan: { estimatedProfitAtTwoR: 300, estimatedLoss: 100 } };

test('a missing or delayed scanner never becomes an order candidate', () => {
  assert.equal(chooseStockSetup({ marketStatus: 'SCANNING', timestamp: new Date(now).toISOString(), evaluated: 0 }, now).status, 'WAIT');
  assert.equal(chooseStockSetup({ marketStatus: 'SCANNING', timestamp: new Date(now - 31_000).toISOString(), evaluated: 8, bestSell: stock }, now).status, 'WAIT');
  assert.equal(chooseStockSetup({ marketStatus: 'DATA_STALE', timestamp: new Date(now).toISOString(), evaluated: 8, bestSell: stock }, now).status, 'WAIT');
});

test('confirmed bearish stock setup remains bearish for a put recommendation', () => {
  const choice = chooseStockSetup({ marketStatus: 'SCANNING', timestamp: new Date(now).toISOString(), evaluated: 8, bestSell: stock }, now);
  assert.equal(choice.status, 'READY');
  assert.equal(choice.stock.side, 'SELL');
});

test('a liquid put is selected only with current depth and expiry clearance', () => {
  const row = { exch_seg: 'NFO', instrumenttype: 'OPTSTK', name: 'RELIANCE',
    symbol: 'RELIANCE29OCT261400PE', token: '101', strike: '140000', expiry: '29OCT2026', lotsize: '500' };
  const quote = { symbolToken: '101', exchFeedTime: '06-Oct-2026 10:30:00',
    opnInterest: '1000', depth: { buy: [{ price: 19.8, quantity: 600 }], sell: [{ price: 20, quantity: 600 }] } };
  const candidate = chooseStockOption([row], [quote], stock, 1402, 1_000_000, now);
  assert.equal(candidate?.optionType, 'PE');
  assert.equal(candidate?.strike, 1400);
  assert.equal(chooseStockOption([row], [{ ...quote, opnInterest: '0' }], stock, 1402, 1_000_000, now), null);
  assert.equal(chooseStockOption([row], [quote], stock, 1402, 20_000, now), null);
});
