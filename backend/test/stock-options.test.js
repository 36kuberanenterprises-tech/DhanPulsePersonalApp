import test from 'node:test';
import assert from 'node:assert/strict';
import { stockOptionCatalog, stockOptionWindow, stockOptionBuyWindow } from '../src/stock-options.js';

const now = Date.parse('2026-10-06T04:40:00Z');
const rows = [
  { exch_seg: 'NSE', symbol: 'RELIANCE-EQ', token: '2885' },
  { exch_seg: 'NFO', instrumenttype: 'OPTSTK', name: 'RELIANCE', symbol: 'RELIANCE29OCT261400CE', token: '101', strike: '140000', expiry: '29OCT2026', lotsize: '500' },
  { exch_seg: 'NFO', instrumenttype: 'OPTSTK', name: 'RELIANCE', symbol: 'RELIANCE29OCT261400PE', token: '102', strike: '140000', expiry: '29OCT2026', lotsize: '500' },
  { exch_seg: 'NFO', instrumenttype: 'OPTSTK', name: 'RELIANCE', symbol: 'RELIANCE26NOV261400CE', token: '103', strike: '140000', expiry: '26NOV2026', lotsize: '500' },
  { exch_seg: 'NFO', instrumenttype: 'OPTIDX', name: 'NIFTY', symbol: 'NIFTY29OCT261400CE', token: '104', strike: '140000', expiry: '29OCT2026' }
];

test('catalog and near ATM window contain only valid stock options of nearest expiry', () => {
  assert.deepEqual(stockOptionCatalog(rows, now), ['RELIANCE']);
  const window = stockOptionWindow(rows, 'RELIANCE', 1398, now);
  assert.equal(window.expiry, '29OCT2026');
  assert.equal(window.atm, 1400);
  assert.deepEqual(window.contracts.map(r => r.token), ['101', '102']);
});

test('stock option entry closes ahead of physical settlement expiry', () => {
  assert.equal(stockOptionBuyWindow(rows[1], now).allowed, true);
  assert.equal(stockOptionBuyWindow(rows[1], Date.parse('2026-10-27T04:40:00Z')).allowed, false);
  assert.equal(stockOptionBuyWindow(rows[1], Date.parse('2026-10-06T12:00:00Z')).allowed, false);
});
