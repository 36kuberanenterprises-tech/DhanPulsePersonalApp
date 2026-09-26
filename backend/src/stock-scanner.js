import { candleData, instrumentMaster, marketData, parseCandles, parseFetched, quoteFeedAgeMs, quoteLtp, resolveUnderlying, rmsLimit } from './angel.js';
import { atr, ema } from './indicators.js';

const IST = 330 * 60_000;
const FIVE_MINUTES = 300_000;
const NIFTY_CSV = 'https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv';
// Used only when the official constituent file cannot be reached. Never
// describe this fallback as a current Nifty 50 constituent list.
const FALLBACK = {
  RELIANCE: 'Energy', HDFCBANK: 'Financial Services', ICICIBANK: 'Financial Services',
  SBIN: 'Financial Services', AXISBANK: 'Financial Services', KOTAKBANK: 'Financial Services',
  BAJFINANCE: 'Financial Services', INFY: 'Information Technology',
  TCS: 'Information Technology', HCLTECH: 'Information Technology',
  WIPRO: 'Information Technology', TECHM: 'Information Technology',
  BHARTIARTL: 'Telecommunication', ITC: 'Consumer Goods',
  HINDUNILVR: 'Consumer Goods', NESTLEIND: 'Consumer Goods',
  LT: 'Construction', MARUTI: 'Automobile', 'M&M': 'Automobile',
  TATAMOTORS: 'Automobile', SUNPHARMA: 'Healthcare',
  DRREDDY: 'Healthcare', TATASTEEL: 'Metals', JSWSTEEL: 'Metals',
  ADANIPORTS: 'Services', NTPC: 'Power', POWERGRID: 'Power'
};
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const round = (x, decimals = 2) => Number.isFinite(x) ? Number(x.toFixed(decimals)) : null;
const median = values => {
  const sorted = values.filter(Number.isFinite).sort((a, b) => a - b);
  if (!sorted.length) return null;
  const n = sorted.length;
  return n % 2 ? sorted[(n - 1) / 2] : (sorted[n / 2 - 1] + sorted[n / 2]) / 2;
};
const ist = date => new Date(date.getTime() + IST);
const dayKey = date => ist(date).toISOString().slice(0, 10);
const minuteOfDay = date => {
  const d = ist(date);
  return d.getUTCHours() * 60 + d.getUTCMinutes();
};
const candleDate = candle => {
  const ms = Date.parse(candle.timestamp);
  return Number.isFinite(ms) ? new Date(ms) : null;
};
const direction = (a, b) => a > b ? 'BUY' : a < b ? 'SELL' : 'WAIT';

export function scannerSession(now = new Date()) {
  const d = ist(now);
  const weekday = d.getUTCDay();
  const minute = minuteOfDay(now);
  if (weekday === 0 || weekday === 6 || minute < 555 || minute >= 930) return 'MARKET_CLOSED';
  if (minute < 575) return 'OPENING_RANGE';
  if (minute >= 885) return 'NO_NEW_ENTRIES';
  return 'SCANNING';
}

function csvFields(line) {
  const fields = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < line.length; i++) {
    if (line[i] === '"' && quoted && line[i + 1] === '"') { field += '"'; i++; }
    else if (line[i] === '"') quoted = !quoted;
    else if (line[i] === ',' && !quoted) { fields.push(field.trim()); field = ''; }
    else field += line[i];
  }
  fields.push(field.trim());
  return fields;
}

export function parseNiftyConstituents(csv) {
  const lines = String(csv || '').replace(/^\uFEFF/, '').split(/\r?\n/).filter(Boolean);
  const head = csvFields(lines.shift() || '').map(x => x.toLowerCase());
  const symbol = head.indexOf('symbol');
  const industry = head.indexOf('industry');
  if (symbol < 0 || industry < 0) throw new Error('NSE constituent columns missing');
  const items = lines.map(csvFields).map(row => ({
    symbol: String(row[symbol] || '').toUpperCase(), sector: String(row[industry] || 'Other')
  })).filter(row => /^[A-Z0-9&-]+$/.test(row.symbol));
  if (items.length < 40 || items.length > 60) throw new Error('NSE constituent list incomplete');
  return items;
}

let universeCache = { at: 0, items: [], source: '' };
async function universe() {
  if (universeCache.items.length && Date.now() - universeCache.at < 6 * 60 * 60_000) return universeCache;
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    let response;
    try { response = await fetch(NIFTY_CSV, { signal: controller.signal }); }
    finally { clearTimeout(timeout); }
    if (!response.ok) throw new Error('NSE constituent file unavailable');
    universeCache = { at: Date.now(), items: parseNiftyConstituents(await response.text()), source: 'NSE Nifty 50 constituent file' };
  } catch {
    universeCache = { at: Date.now(), items: Object.entries(FALLBACK).map(([symbol, sector]) => ({ symbol, sector })), source: 'Fallback stock watchlist, membership unverified' };
  }
  return universeCache;
}

export async function stockWatchlist() {
  return universe();
}

export function quoteSpread(quote) {
  const bid = Number(quote?.depth?.buy?.[0]?.price);
  const ask = Number(quote?.depth?.sell?.[0]?.price);
  return bid > 0 && ask >= bid ? ask - bid : null;
}

export function completedCandles(candles, now = new Date()) {
  return candles.filter(c => {
    const t = candleDate(c);
    return t && t.getTime() + FIVE_MINUTES + 20_000 <= now.getTime() &&
      [c.open, c.high, c.low, c.close, c.volume].every(Number.isFinite) && c.volume >= 0;
  }).sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
}

export function sessionVwap(candles, now = new Date()) {
  const today = dayKey(now);
  const current = candles.filter(c => {
    const t = candleDate(c);
    const m = t ? minuteOfDay(t) : 0;
    return t && dayKey(t) === today && m >= 555 && m < 930;
  });
  const volume = current.reduce((sum, c) => sum + c.volume, 0);
  if (current.length < 3 || current.some(c => c.volume <= 0) || volume <= 0) return null;
  return current.reduce((sum, c) => sum + (c.high + c.low + c.close) / 3 * c.volume, 0) / volume;
}

function fifteenMinuteTrend(candles) {
  const groups = new Map();
  for (const c of candles) {
    const t = candleDate(c);
    if (!t) continue;
    const slot = Math.floor(t.getTime() / 900_000);
    const rows = groups.get(slot) || [];
    rows.push(c);
    groups.set(slot, rows);
  }
  const closes = [...groups.values()].filter(rows => rows.length === 3)
    .map(rows => rows[2].close);
  if (closes.length < 20) return 'WAIT';
  return direction(ema(closes, 9), ema(closes, 15));
}

function relativeVolume(candles, now, latest) {
  const currentDate = dayKey(now);
  const minute = minuteOfDay(candleDate(latest));
  const days = new Map();
  for (const c of candles) {
    const t = candleDate(c);
    if (!t || minuteOfDay(t) > minute || minuteOfDay(t) < 555) continue;
    const key = dayKey(t);
    days.set(key, (days.get(key) || 0) + c.volume);
  }
  const prior = [...days.entries()].filter(([key]) => key !== currentDate).slice(-20).map(([, volume]) => volume);
  const typical = prior.length >= 5 ? median(prior) : null;
  return typical > 0 ? (days.get(currentDate) || 0) / typical : null;
}

export function estimatedRoundTrip(entry, quantity, spread = 0) {
  const turnover = entry * quantity;
  const brokerage = Math.min(20, Math.max(5, turnover * 0.001));
  // Explicit estimate, not an exact broker contract note. The extra allowance
  // covers statutory charges, spread and some execution friction.
  return 2 * brokerage + 2 * turnover * 0.0005 + quantity * Math.max(0, spread);
}

export function sizeStockTrade({ cash, entry, stop, spread = 0 }) {
  if (![cash, entry, stop].every(x => Number.isFinite(x) && x > 0)) return null;
  const distance = Math.abs(entry - stop);
  if (distance <= 0) return null;
  const budget = Math.min(cash, 20_000) * 0.005;
  let low = 0;
  let high = Math.min(Math.floor(cash * 0.9 / entry), Math.floor(budget / distance));
  while (low < high) {
    const mid = Math.ceil((low + high) / 2);
    if (mid * distance + estimatedRoundTrip(entry, mid, spread) <= budget) low = mid;
    else high = mid - 1;
  }
  if (low < 1) return null;
  const fees = estimatedRoundTrip(entry, low, spread);
  return { quantity: low, riskBudget: round(budget), estimatedCosts: round(fees), estimatedLoss: round(low * distance + fees), estimatedProfitAtTwoR: round(low * distance * 2 - fees) };
}

function priorDayHighLow(candles, now) {
  const today = dayKey(now);
  const days = [...new Set(candles.map(c => candleDate(c)).filter(Boolean).map(dayKey))].filter(d => d < today);
  const previous = days[days.length - 1];
  if (!previous) return null;
  const rows = candles.filter(c => {
    const t = candleDate(c);
    return t && dayKey(t) === previous;
  });
  return { high: Math.max(...rows.map(c => c.high)), low: Math.min(...rows.map(c => c.low)) };
}

export function evaluateStock({ symbol, sector, quote, candles, now, cash, niftyReturn, sectorReturn, sectorCount }) {
  const price = quoteLtp(quote);
  const base = { symbol, sector, token: String(quote?.symbolToken || quote?.symboltoken || quote?.token || ''), price: round(price),
    quoteTime: quote?.exchFeedTime || null, status: 'WAIT', side: 'WAIT', setup: null, reason: '', plan: null };
  const refuse = reason => ({ ...base, reason });
  const state = scannerSession(now);
  if (state !== 'SCANNING') return refuse(state === 'MARKET_CLOSED' ? 'Market closed' : state === 'OPENING_RANGE' ? 'Waiting until 9:35 after opening range' : 'New intraday entries stopped at 2:45 pm');
  const age = quoteFeedAgeMs(quote, now.getTime());
  if (age == null || age < -30_000 || age > 45_000 || price <= 0) return refuse('Live stock quote is missing or delayed');
  const spread = quoteSpread(quote);
  if (spread == null || spread / price > 0.002) return refuse('Bid and ask spread is missing or too wide');
  const verified = completedCandles(candles, now);
  const current = verified.filter(c => {
    const t = candleDate(c);
    return t && dayKey(t) === dayKey(now) && minuteOfDay(t) >= 555;
  });
  if (current.length < 4 || current.slice(0, 3).some(c => c.volume <= 0)) return refuse('Completed stock candles with traded volume are still preparing');
  const last = current[current.length - 1];
  const prior = current[current.length - 2];
  if (now.getTime() - candleDate(last).getTime() > 7 * 60_000) return refuse('Latest completed five minute candle is delayed');
  const vwap = sessionVwap(verified, now);
  const a = atr(verified.slice(-80), 14);
  const trend = fifteenMinuteTrend(verified);
  const volumeRatio = relativeVolume(verified, now, last);
  if (!vwap || !a || trend === 'WAIT' || volumeRatio == null) return refuse('VWAP, trend, ATR or comparable past volume is missing');
  if (cash <= 0) return refuse('Available broker cash is unavailable for risk sizing');
  const previousClose = Number(quote?.close);
  if (!Number.isFinite(previousClose) || previousClose <= 0) return refuse('Previous close is unavailable for relative strength');
  if (sectorCount < 2 || !Number.isFinite(sectorReturn) || !Number.isFinite(niftyReturn)) return refuse('Sector comparison is unavailable');
  const opening = current.slice(0, 3);
  const openingHigh = Math.max(...opening.map(c => c.high));
  const openingLow = Math.min(...opening.map(c => c.low));
  const moves = [
    { side: 'BUY', aligned: trend === 'BUY' && price > vwap && sectorReturn >= niftyReturn && price / previousClose - 1 > niftyReturn / 100,
      breakout: prior.close <= openingHigh && last.close > openingHigh && last.close - openingHigh <= a * 0.35,
      pullback: current.length >= 6 && prior.low <= Math.max(vwap, ema(verified.slice(-20).map(c => c.close), 9) || vwap) &&
        prior.close >= vwap && last.close > prior.high,
      stop: Math.min(last.low, prior.low) - a * 0.08 },
    { side: 'SELL', aligned: trend === 'SELL' && price < vwap && sectorReturn <= niftyReturn && price / previousClose - 1 < niftyReturn / 100,
      breakout: prior.close >= openingLow && last.close < openingLow && openingLow - last.close <= a * 0.35,
      pullback: current.length >= 6 && prior.high >= Math.min(vwap, ema(verified.slice(-20).map(c => c.close), 9) || vwap) &&
        prior.close <= vwap && last.close < prior.low,
      stop: Math.max(last.high, prior.high) + a * 0.08 }
  ];
  for (const move of moves) {
    if (!move.aligned) continue;
    const setup = move.breakout ? 'OPENING_RANGE' : move.pullback ? 'FIRST_PULLBACK' : null;
    if (!setup) continue;
    if (volumeRatio < (setup === 'OPENING_RANGE' ? 1.2 : 1.0)) return refuse('Traded volume is below the same time comparison');
    const distance = Math.abs(price - move.stop);
    if ((move.side === 'BUY' && price <= move.stop) || (move.side === 'SELL' && price >= move.stop) ||
        distance < Math.max(spread * 3, a * 0.2) || distance > a * 1.5 ||
        Math.abs(price - last.close) > a * 0.25) return refuse('Entry is too far from the trigger or the stop is unsuitable');
    const previousDay = priorDayHighLow(verified, now);
    const obstacle = move.side === 'BUY' ? previousDay?.high : previousDay?.low;
    if (obstacle != null && (move.side === 'BUY' ? obstacle > price && obstacle - price < distance * 1.5 : obstacle < price && price - obstacle < distance * 1.5)) return refuse('Previous day level leaves too little room for the target');
    const sizing = sizeStockTrade({ cash, entry: price, stop: move.stop, spread });
    if (!sizing || sizing.estimatedProfitAtTwoR <= sizing.estimatedLoss * 1.25) return refuse('Estimated charges leave insufficient net reward within the risk limit');
    const sign = move.side === 'BUY' ? 1 : -1;
    return { ...base, status: 'READY', side: move.side, setup, reason: setup === 'OPENING_RANGE'
      ? 'Opening range close, sector trend and comparable volume agree'
      : 'First trend pullback confirmed with sector and VWAP',
      vwap: round(vwap), volumeRatio: round(volumeRatio), trend,
      plan: { entry: round(price), stop: round(move.stop), target1: round(price + sign * distance),
        target2: round(price + sign * distance * 2), target3: round(price + sign * distance * 3),
        ...sizing, estimated: true } };
  }
  return refuse('No completed breakout or first pullback aligned with the market and sector');
}

const historyCache = new Map();
const scanCache = new Map();
const scanLocks = new Map();
async function stockHistory(session, token, now) {
  const key = session.clientCode + ':' + token;
  const entry = historyCache.get(key);
  const slot = Math.floor(now.getTime() / FIVE_MINUTES);
  if (entry && entry.slot === slot) return entry.candles;
  const from = new Date(now.getTime() - 45 * 86_400_000);
  const format = date => {
    const d = ist(date);
    return d.toISOString().slice(0, 10) + ' ' + d.toISOString().slice(11, 16);
  };
  const raw = await candleData(session, { exchange: 'NSE', symboltoken: token, interval: 'FIVE_MINUTE',
    fromdate: format(from), todate: format(now) });
  const candles = parseCandles(raw);
  historyCache.set(key, { slot, candles });
  return candles;
}

export async function scanStocks(session, trackedToken = null, now = new Date()) {
  const key = session.clientCode + ':' + (trackedToken || '');
  const cached = scanCache.get(key);
  if (cached && Date.now() - cached.at < 30_000) return cached.data;
  if (scanLocks.has(key)) return scanLocks.get(key);
  const pending = (async () => {
    const list = await universe();
    const master = await instrumentMaster();
    const bySymbol = new Map(master.filter(r => r.exch_seg === 'NSE' && String(r.symbol || '').endsWith('-EQ'))
      .map(r => [String(r.symbol).slice(0, -3), r]));
    const stocks = list.items.map(x => ({ ...x, instrument: bySymbol.get(x.symbol) })).filter(x => x.instrument);
    const nifty = resolveUnderlying(master, 'NIFTY');
    const tokens = stocks.map(x => String(x.instrument.token));
    if (trackedToken && /^\d{1,12}$/.test(trackedToken) &&
        master.some(r => r.exch_seg === 'NSE' && String(r.symbol || '').endsWith('-EQ') && String(r.token) === trackedToken) &&
        !tokens.includes(trackedToken)) tokens.push(trackedToken);
    const batches = [];
    for (let i = 0; i < tokens.length; i += 50) batches.push(tokens.slice(i, i + 50));
    const quotes = [];
    for (let i = 0; i < batches.length; i++) {
      if (i) await wait(1100);
      quotes.push(...parseFetched(await marketData(session, { NSE: batches[i] }, 'FULL')));
    }
    await wait(1100);
    const indexQuote = parseFetched(await marketData(session, { NSE: [String(nifty.token)] }, 'FULL'))[0];
    const quoteByToken = new Map(quotes.map(q => [String(q.symbolToken ?? q.symboltoken ?? q.token), q]));
    const market = scannerSession(now);
    const indexAge = quoteFeedAgeMs(indexQuote, now.getTime());
    const niftyReturn = Number(indexQuote?.percentChange);
    const indexFresh = indexAge != null && indexAge >= -30_000 && indexAge <= 45_000 && Number.isFinite(niftyReturn);
    const ranked = stocks.map(stock => {
      const quote = quoteByToken.get(String(stock.instrument.token));
      const price = quoteLtp(quote);
      const age = quoteFeedAgeMs(quote, now.getTime());
      const pct = Number(quote?.percentChange);
      return { ...stock, quote, price, pct,
        turnover: price * Number(quote?.tradeVolume || 0),
        fresh: age != null && age >= -30_000 && age <= 45_000 && price > 0 && Number.isFinite(pct) };
    });
    const groups = new Map();
    for (const stock of ranked.filter(x => x.fresh)) {
      const values = groups.get(stock.sector) || [];
      values.push(stock.pct);
      groups.set(stock.sector, values);
    }
    const sectorRows = [...groups.entries()].filter(([, values]) => values.length >= 2)
      .map(([name, values]) => ({ name, changePct: round(median(values)), count: values.length }))
      .sort((a, b) => b.changePct - a.changePct);
    const sectorMap = new Map(sectorRows.map(x => [x.name, x]));
    const selected = ranked.filter(x => x.fresh && x.turnover >= 10_000_000 && quoteSpread(x.quote) != null)
      .sort((a, b) => b.turnover * Math.abs(b.pct) - a.turnover * Math.abs(a.pct))
      .slice(0, market === 'SCANNING' && indexFresh ? 8 : 0);
    let cash = 0;
    if (selected.length) {
      try { cash = Number((await rmsLimit(session))?.data?.availablecash || 0); } catch {}
    }
    const analysed = [];
    for (const stock of selected) {
      try {
        const candles = await stockHistory(session, String(stock.instrument.token), now);
        analysed.push(evaluateStock({ symbol: stock.symbol, sector: stock.sector, quote: stock.quote,
          candles, now, cash, niftyReturn,
          sectorReturn: sectorMap.get(stock.sector)?.changePct,
          sectorCount: sectorMap.get(stock.sector)?.count || 0 }));
      } catch {
        analysed.push({ symbol: stock.symbol, sector: stock.sector, token: String(stock.instrument.token),
          price: round(stock.price), quoteTime: stock.quote?.exchFeedTime || null, status: 'WAIT', side: 'WAIT',
          reason: 'Broker five minute history unavailable; retrying later', setup: null, plan: null });
      }
      await wait(1200);
    }
    const sideRank = side => analysed.filter(x => x.side === side && x.status === 'READY')
      .sort((a, b) => (b.plan?.estimatedProfitAtTwoR / b.plan?.estimatedLoss) -
        (a.plan?.estimatedProfitAtTwoR / a.plan?.estimatedLoss))[0] || null;
    const tracked = trackedToken ? quoteByToken.get(trackedToken) : null;
    const trackedAge = quoteFeedAgeMs(tracked, now.getTime());
    const result = {
      marketStatus: market === 'SCANNING' && !indexFresh ? 'DATA_STALE' : market,
      timestamp: now.toISOString(), universeSource: list.source,
      scanned: stocks.length, evaluated: analysed.length, niftyChangePct: Number.isFinite(niftyReturn) ? round(niftyReturn) : null,
      strongestSector: sectorRows[0] || null, weakestSector: sectorRows[sectorRows.length - 1] || null,
      bestBuy: sideRank('BUY'), bestSell: sideRank('SELL'),
      candidates: analysed.sort((a, b) => (b.status === 'READY') - (a.status === 'READY')).slice(0, 12),
      trackedQuote: tracked && trackedAge != null && trackedAge >= -30_000 && trackedAge <= 45_000
        ? { token: trackedToken, price: round(quoteLtp(tracked)), quoteTime: tracked.exchFeedTime, fresh: true }
        : null,
      note: market !== 'SCANNING' ? 'No new stock calls outside the scanner window. Market snapshots are informational.'
        : !indexFresh ? 'Nifty quote is delayed; stock entries are paused.'
        : analysed.some(x => x.status === 'READY') ? 'Research signal only. Live stock orders are disabled.'
        : 'No confirmed stock entry. See each candidate for its WAIT reason.'
    };
    scanCache.set(key, { at: Date.now(), data: result });
    return result;
  })().finally(() => scanLocks.delete(key));
  scanLocks.set(key, pending);
  return pending;
}
