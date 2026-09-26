import { instrumentMaster, mcxIndexCatalog, mcxEnergyCatalog, resolveUnderlying } from './angel.js';
import { stockWatchlist } from './stock-scanner.js';

const isIndex = r => /IDX|INDEX/i.test(String(r.instrumenttype || '')) || String(r.token || '').startsWith('999');
const validToken = r => /^\d{1,12}$/.test(String(r?.token || ''));

export function buildBacktestCatalog(rows, stockList = { items: [], source: '' }) {
  const indexRows = rows.filter(r => ['NSE', 'BSE'].includes(r.exch_seg) && isIndex(r) && validToken(r));
  const indices = [];
  const used = new Set();
  for (const name of ['NIFTY', 'BANKNIFTY', 'SENSEX']) {
    let row;
    try { row = resolveUnderlying(rows, name); } catch { continue; }
    const key = row.exch_seg + ':' + row.token;
    if (used.has(key)) continue;
    used.add(key);
    indices.push({ symbol: name, label: name === 'BANKNIFTY' ? 'BANK NIFTY' : name,
      exchange: row.exch_seg, kind: 'INDEX', token: String(row.token) });
  }
  for (const row of indexRows.sort((a,b) => String(a.symbol).localeCompare(String(b.symbol)))) {
    const key = row.exch_seg + ':' + row.token;
    if (used.has(key)) continue;
    const symbol = String(row.symbol || '').toUpperCase().trim();
    if (!symbol || symbol.length > 40) continue;
    used.add(key);
    indices.push({ symbol, label: symbol, exchange: row.exch_seg, kind: 'INDEX', token: String(row.token) });
  }
  const mcx = mcxIndexCatalog(rows).map(x => {
    const row = rows.find(r => r.exch_seg === 'MCX' && r.instrumenttype === 'AMXIDX' &&
      String(r.symbol || '').toUpperCase() === x.symbol && validToken(r));
    return row && { symbol: x.symbol, label: x.symbol, exchange: 'MCX', kind: 'MCX_INDEX',
      token: String(row.token), hasOptions: x.hasOptions };
  }).filter(Boolean);
  const byStock = new Map(rows.filter(r => r.exch_seg === 'NSE' &&
    String(r.symbol || '').endsWith('-EQ') && validToken(r))
    .map(r => [String(r.symbol).slice(0, -3).toUpperCase(), r]));
  const stocks = stockList.items.map(x => {
    const row = byStock.get(x.symbol);
    return row && { symbol: x.symbol, label: x.symbol, exchange: 'NSE', kind: 'STOCK',
      token: String(row.token), sector: x.sector };
  }).filter(Boolean);
  const energy = mcxEnergyCatalog(rows).map(x => ({ symbol: x.symbol, label: x.symbol, exchange: 'MCX',
    kind: 'ENERGY', enabled: false, reason: 'Archived expiry by expiry futures data is required for a continuous backtest.' }));
  return { indices, mcx, stocks, energy, source: 'Angel One instrument master; stocks: ' + stockList.source };
}

export async function backtestCatalog() {
  const [rows, watchlist] = await Promise.all([instrumentMaster(), stockWatchlist()]);
  return buildBacktestCatalog(rows, watchlist);
}

export function findBacktestChoice(catalog, { symbol, exchange, kind }) {
  const all = [...catalog.indices, ...catalog.mcx, ...catalog.stocks];
  const choice = all.find(x => x.symbol === String(symbol || '').toUpperCase() &&
    x.exchange === String(exchange || '').toUpperCase() && x.kind === String(kind || '').toUpperCase());
  if (!choice) throw new Error('This instrument is not in the current backtest catalogue. Refresh the list.');
  return choice;
}
