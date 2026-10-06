import { contractActive, normalizeStrike } from './angel.js';

export function stockOptionCatalog(rows, now = Date.now()) {
  const cash = new Set(rows.filter(r => r.exch_seg === 'NSE' && String(r.symbol || '').endsWith('-EQ'))
    .map(r => String(r.symbol).slice(0, -3).toUpperCase()));
  const names = new Set(rows.filter(r => r.exch_seg === 'NFO' && r.instrumenttype === 'OPTSTK' &&
    contractActive(r, now)).map(r => String(r.name || '').toUpperCase().trim()).filter(n => cash.has(n)));
  return [...names].sort();
}

export function stockOptionWindow(rows, symbol, spot, now = Date.now()) {
  const name = String(symbol || '').toUpperCase().trim();
  const valid = rows.filter(r => r.exch_seg === 'NFO' && r.instrumenttype === 'OPTSTK' &&
    String(r.name || '').toUpperCase().trim() === name && contractActive(r, now) &&
    /(?:CE|PE)$/i.test(String(r.symbol || '')) && normalizeStrike(r.strike) > 0);
  const expiries = [...new Set(valid.map(r => String(r.expiry || '').toUpperCase()))]
    .sort((a, b) => expiryDay(a) - expiryDay(b));
  const expiry = expiries[0] || null;
  const strikes = [...new Set(valid.filter(r => r.expiry?.toUpperCase() === expiry)
    .map(r => normalizeStrike(r.strike)))].sort((a, b) => a - b);
  const atm = strikes.reduce((best, strike) => Math.abs(strike - spot) < Math.abs(best - spot) ? strike : best, strikes[0]);
  const center = strikes.indexOf(atm);
  const selected = new Set(strikes.slice(Math.max(0, center - 3), center + 4));
  return { expiry, expiries, atm: atm || null,
    contracts: valid.filter(r => r.expiry?.toUpperCase() === expiry && selected.has(normalizeStrike(r.strike)))
      .sort((a, b) => normalizeStrike(a.strike) - normalizeStrike(b.strike) || a.symbol.localeCompare(b.symbol)) };
}

function expiryDay(raw) {
  const m = String(raw || '').toUpperCase().match(/^(\d{1,2})([A-Z]{3})(\d{4})$/);
  if (!m) return NaN;
  const month = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'].indexOf(m[2]);
  return month < 0 ? NaN : Date.UTC(Number(m[3]), month, Number(m[1]));
}

export function stockOptionBuyWindow(row, now = Date.now()) {
  if (row?.exch_seg !== 'NFO' || row?.instrumenttype !== 'OPTSTK' || !contractActive(row, now))
    return { allowed: false, reason: 'Stock option contract is invalid or expired.' };
  const india = new Date(now + 330 * 60_000);
  const day = india.getUTCDay();
  const minutes = india.getUTCHours() * 60 + india.getUTCMinutes();
  if (day === 0 || day === 6 || minutes < 9 * 60 + 15 || minutes >= 15 * 60 + 20)
    return { allowed: false, reason: 'New stock option buys are available from 09:15 to 15:20 IST on trading days.' };
  const expiry = expiryDay(row.expiry);
  if (!Number.isFinite(expiry)) return { allowed: false, reason: 'Stock option expiry is unknown.' };
  const today = Date.UTC(india.getUTCFullYear(), india.getUTCMonth(), india.getUTCDate());
  let remaining = 0;
  for (let date = today + 86_400_000; date <= expiry; date += 86_400_000) {
    const weekday = new Date(date).getUTCDay();
    if (weekday !== 0 && weekday !== 6) remaining++;
  }
  if (remaining <= 2) return { allowed: false, reason: 'New stock option buys stop ahead of expiry because physical settlement can apply. Exit open positions before expiry.' };
  return { allowed: true, reason: null };
}
