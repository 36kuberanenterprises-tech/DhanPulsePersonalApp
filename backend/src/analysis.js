import { ema, rsi, macd, supertrend, vwap, atr } from './indicators.js';
import { instrumentMaster, resolveUnderlying, resolveNearestFuture, resolveOptionWindow, marketData, candleData, parseCandles, parseFetched, quoteLtp, quoteOi } from './angel.js';

const round = (n, d = 2) => Number.isFinite(n) ? Number(n.toFixed(d)) : null;
const IST_OFFSET_MS = 330 * 60 * 1000;
const istParts = d => {
  const x = new Date(d.getTime() + IST_OFFSET_MS);
  return { y: x.getUTCFullYear(), m: x.getUTCMonth(), day: x.getUTCDate(), h: x.getUTCHours(), min: x.getUTCMinutes() };
};
const fmtDate = d => {
  const p = istParts(d);
  const pad = n => String(n).padStart(2, '0');
  return `${p.y}-${pad(p.m+1)}-${pad(p.day)} ${pad(p.h)}:${pad(p.min)}`;
};
const marketOpenFor = now => {
  const p = istParts(now);
  const utc = Date.UTC(p.y, p.m, p.day, 9, 15) - IST_OFFSET_MS;
  return new Date(utc);
};

function exchangeOf(row) { return row.exch_seg || row.exchange || 'NSE'; }

function signalEngine({ spot, ema9, ema15, vwapValue, rsiValue, macdValue, st, pcr }) {
  const rules = [];
  let bull = 0, bear = 0;
  const add = (name, state, detail) => {
    rules.push({ name, state, detail });
    if (state === 'BULLISH') bull++; if (state === 'BEARISH') bear++;
  };
  add('Price vs EMA 9', spot > ema9 ? 'BULLISH' : 'BEARISH', `${round(spot)} vs ${round(ema9)}`);
  add('EMA 9 vs EMA 15', ema9 > ema15 ? 'BULLISH' : 'BEARISH', `${round(ema9)} vs ${round(ema15)}`);
  if (vwapValue != null) add('Price vs futures VWAP', spot > vwapValue ? 'BULLISH' : 'BEARISH', `${round(spot)} vs ${round(vwapValue)}`);
  else rules.push({ name: 'Price vs futures VWAP', state: 'UNAVAILABLE', detail: 'No usable futures volume data' });
  add('RSI', rsiValue >= 55 ? 'BULLISH' : rsiValue <= 45 ? 'BEARISH' : 'NEUTRAL', `${round(rsiValue)}`);
  add('MACD histogram', macdValue?.histogram > 0 ? 'BULLISH' : macdValue?.histogram < 0 ? 'BEARISH' : 'NEUTRAL', `${round(macdValue?.histogram ?? 0, 4)}`);
  add('Supertrend', st?.direction || 'NEUTRAL', st ? `${round(st.value)}` : 'Unavailable');
  if (pcr != null) add('Near ATM PCR', pcr >= 1.1 ? 'BULLISH' : pcr <= 0.9 ? 'BEARISH' : 'NEUTRAL', `${round(pcr)}`);
  else rules.push({ name: 'Near ATM PCR', state: 'UNAVAILABLE', detail: 'OI unavailable in quote response' });

  const considered = bull + bear + rules.filter(r => r.state === 'NEUTRAL').length;
  let signal = 'WAIT';
  if (bull >= 5 && bull >= bear + 3) signal = 'CE';
  if (bear >= 5 && bear >= bull + 3) signal = 'PE';
  return { signal, bullRules: bull, bearRules: bear, consideredRules: considered, rules };
}

function pickSupportResistance(chain, spot) {
  const ce = chain.filter(x => x.optionType === 'CE' && x.oi > 0);
  const pe = chain.filter(x => x.optionType === 'PE' && x.oi > 0);
  const maxByOi = arr => arr.slice().sort((a,b) => b.oi - a.oi)[0] || null;
  const resistance = maxByOi(ce);
  const support = maxByOi(pe);
  return {
    support: support ? support.strike : null,
    resistance: resistance ? resistance.strike : null,
    spot: round(spot)
  };
}

export async function analyse(session, symbol = 'NIFTY', interval = 'FIVE_MINUTE') {
  symbol = symbol.toUpperCase();
  if (!['NIFTY','BANKNIFTY','SENSEX'].includes(symbol)) throw new Error('Supported symbols: NIFTY, BANKNIFTY, SENSEX');
  const rows = await instrumentMaster();
  const underlying = resolveUnderlying(rows, symbol);
  const uExchange = exchangeOf(underlying);
  const q = await marketData(session, { [uExchange]: [String(underlying.token)] }, 'FULL');
  const uq = parseFetched(q)[0] || {};
  let spot = quoteLtp(uq);

  const now = new Date();
  let from = marketOpenFor(now);
  if (now.getTime() < from.getTime()) from = new Date(from.getTime() - 24 * 60 * 60 * 1000);
  const cRaw = await candleData(session, { exchange: uExchange, symboltoken: String(underlying.token), interval, fromdate: fmtDate(from), todate: fmtDate(now) });
  const candles = parseCandles(cRaw);
  if (candles.length < 35) throw new Error(`Only ${candles.length} candles available. Need at least 35 for analysis.`);
  if (!spot) spot = candles[candles.length - 1].close;
  const closes = candles.map(c => c.close);

  const e9 = ema(closes, 9), e15 = ema(closes, 15), rv = rsi(closes, 14), mv = macd(closes), st = supertrend(candles, 10, 3), a = atr(candles, 14);

  let vw = null, vwapSource = 'Unavailable';
  const future = resolveNearestFuture(rows, symbol);
  if (future) {
    try {
      const fRaw = await candleData(session, { exchange: exchangeOf(future), symboltoken: String(future.token), interval, fromdate: fmtDate(from), todate: fmtDate(now) });
      const fc = parseCandles(fRaw);
      vw = vwap(fc);
      if (vw != null) vwapSource = `Nearest futures ${future.symbol || future.name}`;
    } catch {}
  }

  const window = resolveOptionWindow(rows, symbol, spot, 5);
  const byEx = {};
  for (const c of window.contracts) (byEx[c.exch_seg] ||= []).push(String(c.token));
  let chain = [];
  if (Object.keys(byEx).length) {
    try {
      const m = await marketData(session, byEx, 'FULL');
      const fetched = parseFetched(m);
      const byToken = new Map(fetched.map(x => [String(x.symbolToken ?? x.symboltoken ?? x.token), x]));
      chain = window.contracts.map(c => {
        const z = byToken.get(String(c.token)) || {};
        const sym = String(c.symbol || '');
        const optionType = /PE$/i.test(sym) ? 'PE' : /CE$/i.test(sym) ? 'CE' : (String(c.instrumenttype).toUpperCase().includes('PE') ? 'PE' : 'CE');
        return { token: String(c.token), tradingSymbol: c.symbol, strike: c.strikeN, optionType, ltp: round(quoteLtp(z)), oi: quoteOi(z), lotSize: Number(c.lotsize || 0) };
      }).sort((a,b) => a.strike - b.strike || a.optionType.localeCompare(b.optionType));
    } catch {}
  }
  const ceOi = chain.filter(x => x.optionType === 'CE').reduce((s,x)=>s+x.oi,0);
  const peOi = chain.filter(x => x.optionType === 'PE').reduce((s,x)=>s+x.oi,0);
  const pcr = ceOi > 0 ? peOi / ceOi : null;

  const engine = signalEngine({ spot, ema9: e9, ema15: e15, vwapValue: vw, rsiValue: rv, macdValue: mv, st, pcr });
  const sr = pickSupportResistance(chain, spot);
  const atm = window.atm || null;
  const optionType = engine.signal === 'CE' ? 'CE' : engine.signal === 'PE' ? 'PE' : null;
  const suggested = optionType ? chain.filter(x => x.optionType === optionType).sort((x,y)=>Math.abs(x.strike-spot)-Math.abs(y.strike-spot))[0] || null : null;

  const levels = a ? {
    underlyingEntry: round(spot),
    stop: round(engine.signal === 'CE' ? spot - a : engine.signal === 'PE' ? spot + a : spot),
    target1: round(engine.signal === 'CE' ? spot + 1.5*a : engine.signal === 'PE' ? spot - 1.5*a : spot),
    target2: round(engine.signal === 'CE' ? spot + 2*a : engine.signal === 'PE' ? spot - 2*a : spot),
    basis: 'ATR based reference levels on underlying index'
  } : null;

  return {
    symbol, timestamp: new Date().toISOString(), timeframe: interval,
    signal: engine.signal,
    ruleScore: { bullish: engine.bullRules, bearish: engine.bearRules, considered: engine.consideredRules },
    market: { ltp: round(spot), ema9: round(e9), ema15: round(e15), vwap: round(vw), vwapSource, rsi: round(rv), macdHistogram: round(mv?.histogram, 4), supertrend: st ? { direction: st.direction, value: round(st.value) } : null, atr: round(a) },
    optionChain: { expiry: window.expiry, atm, nearAtmPcr: round(pcr), totalCeOi: ceOi || null, totalPeOi: peOi || null, support: sr.support, resistance: sr.resistance, contracts: chain },
    suggestedContract: suggested,
    levels,
    rules: engine.rules,
    notes: [
      'Signal is a rule based market view, not a probability or guarantee.',
      'VWAP uses the nearest futures contract because index historical candles do not provide usable volume.',
      'PCR shown here is calculated from the selected near ATM option window, not the full exchange chain.',
      'This build does not place orders.'
    ]
  };
}
