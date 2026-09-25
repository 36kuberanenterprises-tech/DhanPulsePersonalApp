import { ProxyAgent, request as undiciRequest } from 'undici';
const ROOT = 'https://apiconnect.angelone.in';
const MASTER_URL = 'https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json';
const REGISTERED_PUBLIC_IP = process.env.CLIENT_PUBLIC_IP || '34.70.199.153';

function baseHeaders(apiKey, jwt) {
  const h = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-PrivateKey': apiKey,
    'X-UserType': 'USER',
    'X-SourceID': 'WEB',
    'X-ClientLocalIP': process.env.CLIENT_LOCAL_IP || '127.0.0.1',
    'X-ClientPublicIP': REGISTERED_PUBLIC_IP,
    'X-MACAddress': process.env.CLIENT_MAC || '00:00:00:00:00:00'
  };
  if (jwt) h.Authorization = `Bearer ${jwt.replace(/^Bearer\s+/i, '')}`;
  return h;
}

async function jsonFetch(url, init, label) {
  const r = await fetch(url, init);
  const text = await r.text();
  let data;
  try { data = JSON.parse(text); } catch { throw new Error(`${label}: non JSON response (${r.status})`); }
  if (!r.ok || data?.status === false) throw new Error(`${label}: ${data?.message || r.statusText} ${data?.errorcode || ''}`.trim());
  return data;
}

async function jsonFetchViaProxy(url, init, label, proxyUrl) {
  const dispatcher = new ProxyAgent(proxyUrl);
  try {
    const r = await undiciRequest(url, { ...init, dispatcher });
    const body = await r.body.text();
    let data;
    try { data = JSON.parse(body); } catch { throw new Error(`${label}: non JSON response (${r.statusCode})`); }
    if (r.statusCode < 200 || r.statusCode >= 300 || data?.status === false) {
      throw new Error(`${label}: ${data?.message || r.statusCode} ${data?.errorcode || ''}`.trim());
    }
    return data;
  } finally {
    await dispatcher.close();
  }
}

export async function login({ apiKey, clientCode, pin, totp }) {
  return jsonFetch(`${ROOT}/rest/auth/angelbroking/user/v1/loginByPassword`, {
    method: 'POST', headers: baseHeaders(apiKey),
    body: JSON.stringify({ clientcode: clientCode, password: pin, totp })
  }, 'Login');
}

export async function profile(session) {
  return jsonFetch(`${ROOT}/rest/secure/angelbroking/user/v1/getProfile`, {
    method: 'GET', headers: baseHeaders(session.apiKey, session.jwt)
  }, 'Profile');
}

export async function marketData(session, exchangeTokens, mode = 'FULL') {
  return jsonFetch(`${ROOT}/rest/secure/angelbroking/market/v1/quote/`, {
    method: 'POST', headers: baseHeaders(session.apiKey, session.jwt),
    body: JSON.stringify({ mode, exchangeTokens })
  }, 'Market data');
}

export async function candleData(session, payload) {
  return jsonFetch(`${ROOT}/rest/secure/angelbroking/historical/v1/getCandleData`, {
    method: 'POST', headers: baseHeaders(session.apiKey, session.jwt),
    body: JSON.stringify(payload)
  }, 'Candle data');
}


export async function rmsLimit(session) {
  return jsonFetch(`${ROOT}/rest/secure/angelbroking/user/v1/getRMS`, {
    method: 'GET', headers: baseHeaders(session.apiKey, session.jwt)
  }, 'RMS limit');
}

export async function positions(session) {
  return jsonFetch(`${ROOT}/rest/secure/angelbroking/order/v1/getPosition`, {
    method: 'GET', headers: baseHeaders(session.apiKey, session.jwt)
  }, 'Positions');
}

export async function placeOrder(session, payload, proxyUrl = null) {
  const url = `${ROOT}/rest/secure/angelbroking/order/v1/placeOrder`;
  const options = {
    method: 'POST', headers: baseHeaders(session.apiKey, session.jwt),
    body: JSON.stringify(payload)
  };
  return proxyUrl ? jsonFetchViaProxy(url, options, 'Place order', proxyUrl) : jsonFetch(url, options, 'Place order');
}

export async function orderBook(session) {
  return jsonFetch(`${ROOT}/rest/secure/angelbroking/order/v1/getOrderBook`, {
    method: 'GET', headers: baseHeaders(session.apiKey, session.jwt)
  }, 'Order book');
}

let masterCache = { at: 0, rows: [] };
export async function instrumentMaster(force = false) {
  const age = Date.now() - masterCache.at;
  if (!force && masterCache.rows.length && age < 6 * 60 * 60 * 1000) return masterCache.rows;
  const r = await fetch(MASTER_URL);
  if (!r.ok) throw new Error(`Instrument master: ${r.status}`);
  const rows = await r.json();
  masterCache = { at: Date.now(), rows };
  return rows;
}

export function normalizeStrike(raw) {
  const n = Number(raw || 0);
  if (!Number.isFinite(n)) return 0;
  return n > 100000 ? n / 100 : n;
}

function dateValue(s, exchange = 'NFO') {
  const raw = String(s || '').trim();
  const m = raw.match(/^(\d{1,2})([A-Za-z]{3})(\d{4})$/);
  if (m) {
    const months = { JAN:0,FEB:1,MAR:2,APR:3,MAY:4,JUN:5,JUL:6,AUG:7,SEP:8,OCT:9,NOV:10,DEC:11 };
    const month = months[m[2].toUpperCase()];
    // Index options on MCX stop trading at 17:00 IST on their expiry day.
    // Equity index options stop trading at 15:30 IST.
    if (month != null) return exchange === 'MCX'
      ? Date.UTC(Number(m[3]), month, Number(m[1]), 11, 30)
      : Date.UTC(Number(m[3]), month, Number(m[1]), 10, 0);
  }
  const d = new Date(raw);
  return Number.isNaN(d.getTime()) ? Number.MAX_SAFE_INTEGER : d.getTime();
}

export function contractActive(row, now = Date.now()) {
  return dateValue(row?.expiry, row?.exch_seg) > now;
}

export function mcxOptionEntryWindow(row, now = Date.now()) {
  if (row?.exch_seg !== 'MCX' || row?.instrumenttype !== 'OPTIDX' || !contractActive(row, now)) {
    return { allowed: false, reason: 'MCX index option contract has expired or is not valid.' };
  }
  const india = new Date(now + 330 * 60_000);
  const day = india.getUTCDay();
  const mins = india.getUTCHours() * 60 + india.getUTCMinutes();
  if (day === 0 || day === 6 || mins < 9 * 60 + 30 || mins >= 23 * 60 + 15) {
    return { allowed: false, reason: 'New MCX index option buys are available from 09:30 to 23:15 IST on trading days.' };
  }
  const expiry = String(row.expiry || '').toUpperCase();
  const date = `${String(india.getUTCDate()).padStart(2, '0')}${['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'][india.getUTCMonth()]}${india.getUTCFullYear()}`;
  if (expiry === date && mins >= 16 * 60 + 30) {
    return { allowed: false, reason: 'New buys stop at 16:30 IST on the MCX index option expiry day.' };
  }
  return { allowed: true, reason: null };
}

export function mcxIndexCatalog(rows, now = Date.now()) {
  const optionsByName = new Map();
  for (const row of rows) {
    if (row.exch_seg !== 'MCX' || row.instrumenttype !== 'OPTIDX' || !contractActive(row, now)) continue;
    const name = String(row.name || '').trim().toUpperCase();
    optionsByName.set(name, (optionsByName.get(name) || 0) + 1);
  }
  const seen = new Set();
  return rows.filter(row => row.exch_seg === 'MCX' && row.instrumenttype === 'AMXIDX').map(row => {
    const symbol = String(row.symbol || '').trim().toUpperCase();
    if (!symbol || seen.has(symbol)) return null;
    seen.add(symbol);
    const optionContracts = optionsByName.get(symbol) || 0;
    return { symbol, optionContracts, hasOptions: optionContracts > 0 };
  }).filter(Boolean).sort((a, b) => Number(b.hasOptions) - Number(a.hasOptions) || a.symbol.localeCompare(b.symbol));
}

function matchesUnderlying(row, symbol) {
  const name = String(row.name || '').toUpperCase().replace(/\s+/g, ' ').trim();
  const ts = String(row.symbol || '').toUpperCase().replace(/\s+/g, ' ').trim();
  if (symbol === 'BANKNIFTY') return name === 'BANKNIFTY' || name === 'NIFTY BANK' || ts.startsWith('BANKNIFTY');
  if (symbol === 'SENSEX') return name === 'SENSEX' || ts.startsWith('SENSEX');
  return name === 'NIFTY' || name === 'NIFTY 50' || ((ts.startsWith('NIFTY')) && !ts.startsWith('NIFTY BANK') && !ts.startsWith('BANKNIFTY'));
}

export function resolveUnderlying(rows, symbol) {
  const s = symbol.toUpperCase();
  const mcxIndex = rows.find(r => r.exch_seg === 'MCX' && r.instrumenttype === 'AMXIDX' &&
    String(r.symbol || '').trim().toUpperCase() === s);
  if (mcxIndex) return mcxIndex;
  const matchers = {
    NIFTY: r => r.exch_seg === 'NSE' && /NIFTY 50|^NIFTY$/i.test(String(r.symbol || r.name || '')),
    BANKNIFTY: r => r.exch_seg === 'NSE' && /NIFTY BANK|BANKNIFTY/i.test(String(r.symbol || r.name || '')),
    SENSEX: r => r.exch_seg === 'BSE' && /^SENSEX$/i.test(String(r.symbol || r.name || ''))
  };
  const isIndex = r => /IDX|INDEX/i.test(String(r.instrumenttype || '')) || String(r.token || '').startsWith('999');
  let found = rows.find(r => matchers[s]?.(r) && isIndex(r));
  if (!found && s === 'NIFTY') found = rows.find(r => r.token === '99926000');
  if (!found && s === 'BANKNIFTY') found = rows.find(r => r.token === '99926009');
  if (!found) throw new Error(`Unable to resolve ${symbol} index token from instrument master`);
  return found;
}

export function resolveNearestFuture(rows, symbol, now = Date.now()) {
  const mcx = rows.some(r => r.exch_seg === 'MCX' && r.instrumenttype === 'AMXIDX' && r.symbol === symbol);
  return rows
    .filter(r => mcx
      ? r.exch_seg === 'MCX' && r.instrumenttype === 'FUTIDX' && String(r.name || '').toUpperCase() === symbol
      : /FUT/i.test(String(r.instrumenttype || '')) && matchesUnderlying(r, symbol))
    .filter(r => contractActive(r, now))
    .sort((a, b) => dateValue(a.expiry, a.exch_seg) - dateValue(b.expiry, b.exch_seg))[0] || null;
}

export function resolveOptionWindow(rows, symbol, spot, wing = 5, now = Date.now()) {
  const mcx = rows.some(r => r.exch_seg === 'MCX' && r.instrumenttype === 'AMXIDX' && r.symbol === symbol);
  const targetSeg = mcx ? 'MCX' : symbol === 'SENSEX' ? 'BFO' : 'NFO';
  const opts = rows.filter(r => r.exch_seg === targetSeg && (mcx
    ? r.instrumenttype === 'OPTIDX' && String(r.name || '').toUpperCase() === symbol
    : /OPT/i.test(String(r.instrumenttype || '')) && matchesUnderlying(r, symbol)))
    .filter(r => contractActive(r, now))
    .map(r => ({ ...r, strikeN: normalizeStrike(r.strike) }))
    .filter(r => r.strikeN > 0);
  if (!opts.length) return { expiry: null, atm: null, contracts: [] };
  const expiry = opts.slice().sort((a, b) => dateValue(a.expiry, a.exch_seg) - dateValue(b.expiry, b.exch_seg))[0].expiry;
  const e = opts.filter(r => r.expiry === expiry);
  const strikes = [...new Set(e.map(r => r.strikeN))].sort((a, b) => a - b);
  const atm = strikes.reduce((best, x) => Math.abs(x - spot) < Math.abs(best - spot) ? x : best, strikes[0]);
  const idx = strikes.indexOf(atm);
  const selected = new Set(strikes.slice(Math.max(0, idx - wing), idx + wing + 1));
  const contracts = e.filter(r => selected.has(r.strikeN));
  return { expiry, atm, contracts };
}

export function parseCandles(raw) {
  return (raw?.data || []).map(x => ({ timestamp: x[0], open: Number(x[1]), high: Number(x[2]), low: Number(x[3]), close: Number(x[4]), volume: Number(x[5] || 0) }));
}

export function parseFetched(raw) {
  const fetched = raw?.data?.fetched || raw?.data?.fetchedData || raw?.data || [];
  return Array.isArray(fetched) ? fetched : [];
}

export function quoteLtp(q) {
  return Number(q?.ltp ?? q?.lastTradedPrice ?? q?.last_price ?? q?.close ?? 0);
}

export function quoteOi(q) {
  return Number(q?.opnInterest ?? q?.openInterest ?? q?.oi ?? 0);
}

export function quoteFeedAgeMs(q, now = Date.now()) {
  const raw = String(q?.exchFeedTime || '').trim();
  const m = raw.match(/^(\d{1,2})-([A-Za-z]{3})-(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})$/);
  if (!m) return null;
  const month = { JAN:0,FEB:1,MAR:2,APR:3,MAY:4,JUN:5,JUL:6,AUG:7,SEP:8,OCT:9,NOV:10,DEC:11 }[m[2].toUpperCase()];
  if (month == null) return null;
  const ms = Date.UTC(Number(m[3]), month, Number(m[1]), Number(m[4]), Number(m[5]), Number(m[6])) - 330 * 60_000;
  return now - ms;
}
