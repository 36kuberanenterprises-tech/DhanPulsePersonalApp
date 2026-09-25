import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveNearestFuture, resolveOptionWindow, quoteFeedAgeMs } from '../src/angel.js';
import { signalEngine, nearAtmOi } from '../src/analysis.js';

const expiryRows = [
  { token: '100', name: 'NIFTY', symbol: 'NIFTY24SEP26FUT', exch_seg: 'NFO', instrumenttype: 'FUTIDX', expiry: '24SEP2026' },
  { token: '101', name: 'NIFTY', symbol: 'NIFTY29SEP26FUT', exch_seg: 'NFO', instrumenttype: 'FUTIDX', expiry: '29SEP2026' },
  { token: '102', name: 'NIFTY', symbol: 'NIFTY24SEP2623200CE', exch_seg: 'NFO', instrumenttype: 'OPTIDX', strike: '2320000', expiry: '24SEP2026' },
  { token: '103', name: 'NIFTY', symbol: 'NIFTY29SEP2623200CE', exch_seg: 'NFO', instrumenttype: 'OPTIDX', strike: '2320000', expiry: '29SEP2026' }
];

test('expired contracts are not selected on the following trading day', () => {
  const now = Date.parse('2026-09-25T04:30:00Z');
  assert.equal(resolveNearestFuture(expiryRows, 'NIFTY', now)?.token, '101');
  assert.equal(resolveOptionWindow(expiryRows, 'NIFTY', 23200, 5, now)?.expiry, '29SEP2026');
});

test('expiry changes at 15:30 IST on its trading date', () => {
  assert.equal(resolveNearestFuture(expiryRows, 'NIFTY', Date.parse('2026-09-24T09:59:00Z'))?.token, '100');
  assert.equal(resolveNearestFuture(expiryRows, 'NIFTY', Date.parse('2026-09-24T10:01:00Z'))?.token, '101');
});

test('broker feed time is read as India time, not UTC', () => {
  const now = Date.parse('2026-09-25T04:30:45Z');
  assert.equal(quoteFeedAgeMs({ exchFeedTime: '25-Sep-2026 10:00:05' }, now), 40_000);
  assert.equal(quoteFeedAgeMs({}, now), null);
});

test('futures rule compares the futures price against its own traded average', () => {
  const inputs = {
    spot: 23250, ema9: 23200, ema15: 23150,
    futuresPrice: 23260, vwapValue: 23280, vwapSource: 'broker',
    rsiValue: 63, macdValue: { histogram: 10 },
    st: { direction: 'BULLISH', value: 23100 }, pcr: 1.2
  };
  const answer = signalEngine(inputs);
  assert.equal(answer.rules[2].state, 'BEARISH');
  assert.equal(answer.signal, 'CE');
  const withoutAverage = signalEngine({ ...inputs, vwapValue: null });
  assert.equal(withoutAverage.rules[2].state, 'UNAVAILABLE');
  assert.equal(withoutAverage.signal, 'CE');
});

test('PCR excludes unpaired strikes and pauses its vote with too little coverage', () => {
  const paired = [23150, 23200, 23250].flatMap(strike => [
    { strike, optionType: 'CE', oi: 100, ltp: 80 },
    { strike, optionType: 'PE', oi: 120, ltp: 75 }
  ]);
  assert.equal(nearAtmOi(paired, 23200).pcr, 1.2);
  const missingPut = paired.map(x => x.strike === 23250 && x.optionType === 'PE' ? { ...x, ltp: null } : x);
  assert.equal(nearAtmOi(missingPut, 23200).pcr, null);
  assert.equal(nearAtmOi(missingPut, 23200).coverage, '2/3 paired strikes');
});
