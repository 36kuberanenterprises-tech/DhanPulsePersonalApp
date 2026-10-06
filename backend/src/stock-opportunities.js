import { quoteFeedAgeMs, normalizeStrike } from './angel.js';
import { stockOptionBuyWindow } from './stock-options.js';

// An opportunity is a recommendation, never an authorization to send an order.
export function chooseStockSetup(scan, now = Date.now()) {
  if (scan?.marketStatus !== 'SCANNING') return { status: 'WAIT', reason: scan?.note || 'Scanner is outside its entry window' };
  const age = now - Date.parse(scan.timestamp);
  if (!Number.isFinite(age) || age < 0 || age > 30_000) return { status: 'WAIT', reason: 'Scanner result is delayed' };
  if (scan.evaluated < 1) return { status: 'WAIT', reason: 'Broker candle history has not completed' };
  const ready = [scan.bestBuy, scan.bestSell].filter(x => x?.status === 'READY' &&
    x.plan && x.token && ['BUY', 'SELL'].includes(x.side));
  if (!ready.length) return { status: 'WAIT', reason: 'No stock passed completed candle, VWAP, volume and market checks' };
  ready.sort((a, b) =>
    (b.plan.estimatedProfitAtTwoR / b.plan.estimatedLoss) -
    (a.plan.estimatedProfitAtTwoR / a.plan.estimatedLoss));
  return { status: 'READY', stock: ready[0], reason: ready[0].reason };
}

export function chooseStockOption(rows, quotes, stock, spot, cash, now = Date.now()) {
  if (!stock || !(spot > 0) || !(cash > 0)) return null;
  const type = stock.side === 'BUY' ? 'CE' : stock.side === 'SELL' ? 'PE' : null;
  if (!type) return null;
  const eligible = rows.filter(row => row.instrumenttype === 'OPTSTK' && row.exch_seg === 'NFO' &&
    String(row.name).toUpperCase() === stock.symbol && String(row.symbol).endsWith(type));
  const byToken = new Map(quotes.map(q => [String(q.symbolToken ?? q.symboltoken ?? q.token), q]));
  const options = eligible.flatMap(row => {
    const q = byToken.get(String(row.token));
    const age = quoteFeedAgeMs(q, now);
    const bid = Number(q?.depth?.buy?.[0]?.price || 0);
    const ask = Number(q?.depth?.sell?.[0]?.price || 0);
    const lot = Number(row.lotsize || 0);
    const bidQty = Number(q?.depth?.buy?.[0]?.quantity || 0);
    const askQty = Number(q?.depth?.sell?.[0]?.quantity || 0);
    const oi = Number(q?.opnInterest ?? q?.openInterest ?? q?.oi ?? 0);
    // One lot, 20% premium stop, 0.5% cash risk budget; no expiry proximity.
    if (!stockOptionBuyWindow(row, now).allowed || age == null || age < -30_000 || age > 45_000 ||
        !(bid > 0 && ask >= bid && ask >= 15 && (ask - bid) / ask <= 0.03) ||
        !(lot > 0 && bidQty >= lot && askQty >= lot && oi > 0) ||
        ask * lot > cash * 0.25 || ask * lot * 0.2 > cash * 0.005) return [];
    return [{ token: String(row.token), tradingSymbol: row.symbol, exchange: 'NFO',
      optionType: type, strike: normalizeStrike(row.strike), lotSize: lot, bid, ask, expiry: row.expiry,
      estimatedPremium: ask * lot, estimatedRiskAt20PctStop: ask * lot * 0.2,
      distance: Math.abs(normalizeStrike(row.strike) - spot) }];
  });
  return options.sort((a, b) => a.distance - b.distance || a.ask - b.ask)[0] || null;
}
