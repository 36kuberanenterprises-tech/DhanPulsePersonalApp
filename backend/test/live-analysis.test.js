import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveNearestFuture, resolveOptionWindow, resolveUnderlying, quoteFeedAgeMs, mcxIndexCatalog, mcxEnergyCatalog, futureForEnergyOption, normalizeStrike, mcxOptionEntryWindow } from '../src/angel.js';
import { signalEngine, nearAtmOi, marketDataState } from '../src/analysis.js';

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

test('an old quote after trading hours is a closed market snapshot, not a live call', () => {
  const now = new Date('2026-09-25T12:40:00Z'); // 18:10 IST
  assert.equal(marketDataState(now, 2 * 60 * 60 * 1000), 'MARKET_CLOSED');
  assert.equal(marketDataState(now, null, false), 'MARKET_CLOSED');
  assert.equal(marketDataState(new Date('2026-09-26T04:30:00Z'), 0), 'MARKET_CLOSED');
  const tradingHour = new Date('2026-09-25T04:30:00Z');
  assert.equal(marketDataState(tradingHour, 40_000), 'LIVE');
  assert.equal(marketDataState(tradingHour, 120_000), 'DATA_STALE');
  assert.equal(marketDataState(tradingHour, null), 'DATA_STALE');
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

const mcxRows = [
  { token: '99920005', name: 'MCXBULLDEX', symbol: 'MCXBULLDEX', instrumenttype: 'AMXIDX', exch_seg: 'MCX' },
  { token: '99920004', name: 'MCXMETLDEX', symbol: 'MCXMETLDEX', instrumenttype: 'AMXIDX', exch_seg: 'MCX' },
  { token: '210', name: 'MCXBULLDEX', symbol: 'MCXBULLDEX25SEP26FUT', instrumenttype: 'FUTIDX', exch_seg: 'MCX', expiry: '25SEP2026' },
  { token: '211', name: 'MCXBULLDEX', symbol: 'MCXBULLDEX28OCT26FUT', instrumenttype: 'FUTIDX', exch_seg: 'MCX', expiry: '28OCT2026' },
  ...['25SEP2026', '28OCT2026'].flatMap((expiry, i) => [32000, 32100, 32200].flatMap(strike => ['CE', 'PE'].map(side => ({
    token: String(300 + i * 100 + strike - 32000 + (side === 'PE' ? 1 : 0)),
    name: 'MCXBULLDEX', symbol: `MCXBULLDEX${expiry}${strike}${side}`,
    exch_seg: 'MCX', instrumenttype: 'OPTIDX', expiry, strike: String(strike * 100), lotsize: '30'
  }))))
];

test('MCX catalogue lists every broker index but marks only indexes with active options tradable', () => {
  const catalog = mcxIndexCatalog(mcxRows, Date.parse('2026-09-25T11:00:00Z'));
  assert.deepEqual(catalog.map(x => [x.symbol, x.hasOptions]), [['MCXBULLDEX', true], ['MCXMETLDEX', false]]);
  assert.equal(resolveUnderlying(mcxRows, 'MCXMETLDEX').token, '99920004');
  assert.equal(resolveOptionWindow(mcxRows, 'MCXMETLDEX', 32050).contracts.length, 0);
});

test('MCX index options roll after 17:00 IST on expiry day, while equity expiry is unchanged', () => {
  const before = Date.parse('2026-09-25T11:29:00Z');
  const after = Date.parse('2026-09-25T11:31:00Z');
  assert.equal(resolveOptionWindow(mcxRows, 'MCXBULLDEX', 32100, 5, before).expiry, '25SEP2026');
  assert.equal(resolveOptionWindow(mcxRows, 'MCXBULLDEX', 32100, 5, after).expiry, '28OCT2026');
  assert.equal(resolveNearestFuture(mcxRows, 'MCXBULLDEX', after).token, '211');
  assert.equal(mcxOptionEntryWindow(mcxRows[4], before).allowed, false); // no new buys after 16:30 on expiry
  assert.equal(mcxOptionEntryWindow(mcxRows[4], after).allowed, false);
  assert.equal(mcxOptionEntryWindow(mcxRows[10], after).allowed, true);
});

test('MCX session remains available in the evening while equity index is closed', () => {
  const evening = new Date('2026-09-25T13:25:00Z'); // 18:55 IST
  assert.equal(marketDataState(evening, 35_000, true, 'MCX'), 'LIVE');
  assert.equal(marketDataState(evening, 35_000, true), 'MARKET_CLOSED');
  assert.equal(marketDataState(new Date('2026-09-25T18:01:00Z'), 35_000, true, 'MCX'), 'MARKET_CLOSED');
  assert.equal(marketDataState(new Date('2026-11-06T18:10:00Z'), 35_000, true, 'MCX'), 'LIVE');
});

test('MCX option buying core can use four aligned checks but equity stays at five', () => {
  const inputs = {
    spot: 32100, ema9: 32090, ema15: 32080, futuresPrice: null, vwapValue: null, vwapSource: 'No future',
    rsiValue: 56, macdValue: { histogram: 0.3 }, st: { direction: 'BEARISH', value: 32200 }, pcr: null
  };
  assert.equal(signalEngine(inputs, 'MCX').signal, 'CE');
  assert.equal(signalEngine(inputs).signal, 'WAIT');
});

const energyRows = [
  { token:'600', name:'NATGASMINI', symbol:'NATGASMINI25SEP26FUT', instrumenttype:'FUTCOM', exch_seg:'MCX', expiry:'25SEP2026' },
  { token:'601', name:'NATGASMINI', symbol:'NATGASMINI27OCT26FUT', instrumenttype:'FUTCOM', exch_seg:'MCX', expiry:'27OCT2026' },
  { token:'602', name:'NATGASMINI', symbol:'NATGASMINI24NOV26FUT', instrumenttype:'FUTCOM', exch_seg:'MCX', expiry:'24NOV2026' },
  ...[300,305,310].flatMap((strike,i)=>['CE','PE'].map((side,j)=>({
    token:String(700+i*2+j), name:'NATGASMINI', symbol:`NATGASMINI23OCT26${strike}${side}`,
    instrumenttype:'OPTFUT', exch_seg:'MCX', expiry:'23OCT2026', strike:String(strike*100), lotsize:'250'
  }))),
  { token:'800', name:'NATGASMINI', symbol:'NATGASMINI20NOV26305CE', instrumenttype:'OPTFUT', exch_seg:'MCX', expiry:'20NOV2026', strike:'30500', lotsize:'250' }
];

test('energy options use the next matching futures month and correctly scale natural gas strikes', () => {
  const now = Date.parse('2026-09-25T05:00:00Z');
  assert.equal(normalizeStrike('30500.000000'), 305);
  assert.equal(mcxEnergyCatalog(energyRows, now)[0].symbol, 'NATGASMINI');
  assert.equal(mcxEnergyCatalog(energyRows, now)[0].hasOptions, true);
  assert.equal(resolveNearestFuture(energyRows, 'NATGASMINI', now).token, '601');
  const chain = resolveOptionWindow(energyRows, 'NATGASMINI', 305, 5, now);
  assert.equal(chain.expiry, '23OCT2026');
  assert.equal(chain.atm, 305);
  assert.equal(chain.contracts.length, 6);
  assert.equal(futureForEnergyOption(energyRows, energyRows[4], now).token, '601');
});

test('energy entries stop ahead of expiry and roll to the next eligible option month', () => {
  const before = Date.parse('2026-10-19T05:00:00Z');
  const near = energyRows[3];
  assert.equal(mcxOptionEntryWindow(near, before).allowed, true);
  const cutoff = Date.parse('2026-10-20T05:00:00Z');
  assert.equal(mcxOptionEntryWindow(near, cutoff).allowed, false);
  assert.equal(resolveOptionWindow(energyRows, 'NATGASMINI', 305, 5, cutoff).expiry, '20NOV2026');
  assert.equal(resolveNearestFuture(energyRows, 'NATGASMINI', cutoff).token, '602');
  assert.equal(mcxOptionEntryWindow(near, Date.parse('2026-10-26T05:00:00Z')).allowed, false);
});
