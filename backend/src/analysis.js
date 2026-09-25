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

const INTERVAL_MINUTES = {
  ONE_MINUTE: 1,
  THREE_MINUTE: 3,
  FIVE_MINUTE: 5,
  TEN_MINUTE: 10,
  FIFTEEN_MINUTE: 15
};

const liveCandleCache = new Map();
const candleLoadLocks = new Map();
const candleRetryAfter = new Map();
const optionWindowCache = new Map();

const sleep = ms => new Promise(r => setTimeout(r, ms));

function historyStartFor(now, interval) {
  const p = istParts(now);
  const lookbackDays = interval === 'FIFTEEN_MINUTE' ? 12 : 10;
  const utc = Date.UTC(p.y, p.m, p.day - lookbackDays, 9, 15) - IST_OFFSET_MS;
  return new Date(utc);
}

function bucketStartFor(now, interval) {
  const mins = INTERVAL_MINUTES[interval] || 5;
  const open = marketOpenFor(now);
  const close = new Date(open.getTime() + 375 * 60 * 1000);
  if (now < open) return open;
  if (now > close) return new Date(close.getTime() - mins * 60 * 1000);
  const elapsed = now.getTime() - open.getTime();
  const bucket = Math.floor(elapsed / (mins * 60 * 1000));
  return new Date(open.getTime() + bucket * mins * 60 * 1000);
}

async function loadHistoricalBase(session, exchange, token, interval, now, key) {
  const retryAt = candleRetryAfter.get(key) || 0;
  if (Date.now() < retryAt) throw new Error('Market history is cooling down after a broker rate-limit response. Retrying automatically.');

  const payload = {
    exchange,
    symboltoken: String(token),
    interval,
    fromdate: fmtDate(historyStartFor(now, interval)),
    todate: fmtDate(now)
  };

  let lastError;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const raw = await candleData(session, payload);
      const rows = parseCandles(raw)
        .filter(x => [x.open,x.high,x.low,x.close].every(Number.isFinite))
        .sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp));
      liveCandleCache.set(key, {
        candles: rows.slice(-1200),
        loadedAt: Date.now(),
        lastLiveAt: Date.now()
      });
      candleRetryAfter.delete(key);
      return liveCandleCache.get(key);
    } catch (e) {
      lastError = e;
      const msg = String(e?.message || '');
      if (/403|rate/i.test(msg) && attempt === 0) {
        await sleep(6500);
        continue;
      }
      if (/403|rate/i.test(msg)) candleRetryAfter.set(key, Date.now() + 45_000);
      throw e;
    }
  }
  throw lastError || new Error('Unable to load market history');
}

async function liveCandles(session, exchange, token, interval, livePrice, now) {
  const key = [exchange, token, interval].join('|');
  const mins = INTERVAL_MINUTES[interval] || 5;
  let state = liveCandleCache.get(key);

  const staleGap = state?.lastLiveAt ? Date.now() - state.lastLiveAt : Number.MAX_SAFE_INTEGER;
  const mustReload = !state || state.candles.length < 35 || staleGap > Math.max(120_000, mins * 2 * 60_000);

  if (mustReload) {
    let lock = candleLoadLocks.get(key);
    if (!lock) {
      lock = loadHistoricalBase(session, exchange, token, interval, now, key)
        .finally(() => candleLoadLocks.delete(key));
      candleLoadLocks.set(key, lock);
    }
    state = await lock;
  }

  const candles = state.candles.slice();
  const price = Number(livePrice || candles[candles.length - 1]?.close || 0);
  const bucketStart = bucketStartFor(now, interval);
  const bucketMs = bucketStart.getTime();
  const last = candles[candles.length - 1];
  const lastMs = last ? new Date(last.timestamp).getTime() : 0;

  if (price > 0) {
    if (last && Math.abs(lastMs - bucketMs) < 60_000) {
      last.high = Math.max(Number(last.high), price);
      last.low = Math.min(Number(last.low), price);
      last.close = price;
    } else if (!last || lastMs < bucketMs) {
      candles.push({
        timestamp: bucketStart.toISOString(),
        open: price,
        high: price,
        low: price,
        close: price,
        volume: 0
      });
    }
  }

  state.candles = candles.slice(-1200);
  state.lastLiveAt = Date.now();
  liveCandleCache.set(key, state);

  if (state.candles.length < 35) {
    throw new Error('Market history is still preparing. Waiting for enough prior-session candles.');
  }
  return state.candles;
}

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

function resampleCandles(candles, minutes = 15) {
  const size = minutes * 60 * 1000;
  const buckets = new Map();
  for (const row of candles) {
    const t = new Date(row.timestamp).getTime();
    if (!Number.isFinite(t)) continue;
    const key = Math.floor(t / size) * size;
    const old = buckets.get(key);
    if (!old) {
      buckets.set(key, {
        timestamp: new Date(key).toISOString(),
        open: row.open, high: row.high, low: row.low, close: row.close, volume: Number(row.volume || 0)
      });
    } else {
      old.high = Math.max(old.high, row.high);
      old.low = Math.min(old.low, row.low);
      old.close = row.close;
      old.volume += Number(row.volume || 0);
    }
  }
  return [...buckets.values()].sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp));
}

function directionFromTrend({ spot, ema9, ema15, macdValue, st, vwapValue }) {
  let bull = 0, bear = 0;
  if (spot > ema9) bull++; else bear++;
  if (ema9 > ema15) bull++; else bear++;
  if ((macdValue?.histogram ?? 0) > 0) bull++; else if ((macdValue?.histogram ?? 0) < 0) bear++;
  if (st?.direction === 'BULLISH') bull++; else if (st?.direction === 'BEARISH') bear++;
  if (vwapValue != null) {
    if (spot > vwapValue) bull++; else bear++;
  }
  if (bull >= 4 && bull >= bear + 2) return { vote: 'CE', detail: `${bull} bullish / ${bear} bearish trend checks` };
  if (bear >= 4 && bear >= bull + 2) return { vote: 'PE', detail: `${bear} bearish / ${bull} bullish trend checks` };
  return { vote: 'WAIT', detail: `${bull} bullish / ${bear} bearish trend checks` };
}

function higherTimeframeVote(candles) {
  const h = resampleCandles(candles, 15);
  if (h.length < 20) return { vote: 'WAIT', detail: '15m history not ready' };
  const closes = h.map(x => x.close);
  const e9 = ema(closes, 9), e15 = ema(closes, 15);
  const st = supertrend(h, 10, 3);
  if (e9 > e15 && st?.direction === 'BULLISH') return { vote: 'CE', detail: `15m EMA9 ${round(e9)} > EMA15 ${round(e15)} and Supertrend bullish` };
  if (e9 < e15 && st?.direction === 'BEARISH') return { vote: 'PE', detail: `15m EMA9 ${round(e9)} < EMA15 ${round(e15)} and Supertrend bearish` };
  return { vote: 'WAIT', detail: `15m trend mixed: EMA9 ${round(e9)}, EMA15 ${round(e15)}, ST ${st?.direction || 'NA'}` };
}

function oiVote(pcr, sr, spot) {
  if (pcr == null) return { vote: 'WAIT', detail: 'Near-ATM OI unavailable' };
  if (pcr >= 1.1) return { vote: 'CE', detail: `PCR ${round(pcr)} supports bullish bias; support ${round(sr.support)}` };
  if (pcr <= 0.9) return { vote: 'PE', detail: `PCR ${round(pcr)} supports bearish bias; resistance ${round(sr.resistance)}` };
  return { vote: 'WAIT', detail: `PCR ${round(pcr)} is neutral` };
}

function regimeState({ spot, ema9, ema15, atrValue, st }) {
  if (!spot || !atrValue) return { name: 'UNKNOWN', suitable: false, detail: 'ATR/regime unavailable' };
  const gap = Math.abs(ema9 - ema15);
  const ratio = gap / Math.max(atrValue, 0.01);
  const aligned = (ema9 > ema15 && st?.direction === 'BULLISH') || (ema9 < ema15 && st?.direction === 'BEARISH');
  if (ratio < 0.18) return { name: 'RANGE', suitable: false, detail: `EMA separation is only ${round(ratio,2)}x ATR` };
  if (aligned && ratio >= 0.45) return { name: 'TRENDING', suitable: true, detail: `EMA separation ${round(ratio,2)}x ATR with Supertrend alignment` };
  return { name: 'TRANSITION', suitable: true, detail: `EMA separation ${round(ratio,2)}x ATR; trend is developing` };
}

function inferStrikeStep(chain) {
  const strikes = [...new Set(chain.map(x => Number(x.strike)).filter(Number.isFinite))].sort((a,b)=>a-b);
  const diffs = [];
  for (let i=1;i<strikes.length;i++) {
    const d = strikes[i]-strikes[i-1];
    if (d > 0) diffs.push(d);
  }
  return diffs.length ? Math.min(...diffs) : 50;
}

function selectBestContract(chain, optionType, spot) {
  if (!optionType) return { contract: null, reason: 'No directional bias', score: null };
  const candidates = chain.filter(x => x.optionType === optionType && Number(x.ltp) > 0);
  if (!candidates.length) return { contract: null, reason: `No live ${optionType} premium available`, score: null };
  const step = Math.max(1, inferStrikeStep(chain));
  const maxOi = Math.max(1, ...candidates.map(x => Number(x.oi || 0)));
  const ranked = candidates.map(x => {
    const distance = Math.abs(Number(x.strike)-spot);
    const distanceScore = Math.max(0, 1 - distance / (step * 3));
    const oiScore = Math.max(0, Math.min(1, Number(x.oi || 0) / maxOi));
    const premiumScore = Number(x.ltp) >= 15 ? 1 : Math.max(0, Number(x.ltp) / 15);
    const score = 0.58 * distanceScore + 0.32 * oiScore + 0.10 * premiumScore;
    return { x, score, distance, oiScore };
  }).sort((a,b)=>b.score-a.score || a.distance-b.distance);
  const best = ranked[0];
  return {
    contract: best.x,
    score: round(best.score * 100, 1),
    reason: `${optionType} strike ${round(best.x.strike)} selected from near-ATM contracts using distance, live premium and OI liquidity; score ${round(best.score*100,1)}/100`
  };
}

function buildTradeDecision({ engine, trend, htf, oi, regime, sr, spot, atrValue, selected }) {
  const direction = engine.signal;
  const votes = [
    { name: 'Core Direction', vote: direction, detail: `${engine.bullRules} bull / ${engine.bearRules} bear confirmations` },
    { name: 'Trend Alignment', vote: trend.vote, detail: trend.detail },
    { name: '15m Higher Timeframe', vote: htf.vote, detail: htf.detail },
    { name: 'OI / PCR', vote: oi.vote, detail: oi.detail }
  ];

  if (!['CE','PE'].includes(direction)) {
    return {
      direction: 'WAIT',
      status: 'WATCHING',
      setupAllowed: false,
      supportingVotes: 0,
      totalVotes: votes.length,
      alignmentPct: 0,
      regime: regime.name,
      regimeSuitable: regime.suitable,
      strategyVotes: votes,
      conflicts: [],
      selectedContractReason: selected.reason,
      selectedContractScore: selected.score,
      message: 'No directional call. Waiting for the core confirmation threshold.'
    };
  }

  const supporting = votes.filter(v => v.vote === direction).length;
  const conflicts = [];
  if (trend.vote !== 'WAIT' && trend.vote !== direction) conflicts.push('Trend alignment is opposite to the core direction.');
  if (htf.vote !== 'WAIT' && htf.vote !== direction) conflicts.push('15-minute higher timeframe is opposite.');
  if (oi.vote !== 'WAIT' && oi.vote !== direction) conflicts.push('OI/PCR structure is opposite.');
  if (!regime.suitable) conflicts.push('Market regime is range-like; directional option buying is filtered.');

  if (atrValue) {
    if (direction === 'CE' && sr.resistance != null && sr.resistance > spot && (sr.resistance - spot) <= atrValue * 0.5) {
      conflicts.push('Heavy CE OI resistance is too close above the index.');
    }
    if (direction === 'PE' && sr.support != null && sr.support < spot && (spot - sr.support) <= atrValue * 0.5) {
      conflicts.push('Heavy PE OI support is too close below the index.');
    }
  }

  const setupAllowed = supporting >= 3 && conflicts.length === 0 && regime.suitable;
  const alignmentPct = round(100 * supporting / votes.length, 0);
  return {
    direction,
    status: setupAllowed ? 'READY_FOR_PREMIUM' : (conflicts.length ? 'REJECTED_CONFLICT' : 'CONFIRMING'),
    setupAllowed,
    supportingVotes: supporting,
    totalVotes: votes.length,
    alignmentPct,
    regime: regime.name,
    regimeSuitable: regime.suitable,
    strategyVotes: votes,
    conflicts,
    selectedContractReason: selected.reason,
    selectedContractScore: selected.score,
    message: setupAllowed
      ? `${direction} setup passed meta confirmation. Waiting for two live scans and premium breakout.`
      : (conflicts[0] || `Only ${supporting}/${votes.length} strategy layers support ${direction}; waiting for stronger agreement.`)
  };
}


export async function analyse(session, symbol = 'NIFTY', interval = 'FIVE_MINUTE') {
  symbol = symbol.toUpperCase();
  if (!['NIFTY','BANKNIFTY','SENSEX'].includes(symbol)) throw new Error('Supported symbols: NIFTY, BANKNIFTY, SENSEX');
  const rows = await instrumentMaster();
  const underlying = resolveUnderlying(rows, symbol);
  const uExchange = exchangeOf(underlying);
  const future = resolveNearestFuture(rows, symbol);
  const cachedWindow = optionWindowCache.get(symbol) || null;

  const quoteTokens = { [uExchange]: [String(underlying.token)] };
  if (future) {
    const fx = exchangeOf(future);
    (quoteTokens[fx] ||= []).push(String(future.token));
  }
  if (cachedWindow?.contracts?.length) {
    for (const c of cachedWindow.contracts) (quoteTokens[c.exch_seg] ||= []).push(String(c.token));
  }

  const q = await marketData(session, quoteTokens, 'FULL');
  let fetchedQuotes = parseFetched(q);
  let byTokenQuote = new Map(fetchedQuotes.map(x => [String(x.symbolToken ?? x.symboltoken ?? x.token), x]));
  const uq = byTokenQuote.get(String(underlying.token)) || fetchedQuotes[0] || {};
  let spot = quoteLtp(uq);

  const now = new Date();
  const candles = await liveCandles(session, uExchange, String(underlying.token), interval, spot, now);
  if (!spot) spot = candles[candles.length - 1].close;
  const closes = candles.map(c => c.close);

  const e9 = ema(closes, 9), e15 = ema(closes, 15), rv = rsi(closes, 14), mv = macd(closes), st = supertrend(candles, 10, 3), a = atr(candles, 14);

  let vw = null, vwapSource = 'Unavailable';
  if (future) {
    const fq = byTokenQuote.get(String(future.token)) || {};
    const avgPrice = Number(fq.avgPrice ?? fq.averagePrice ?? 0);
    if (Number.isFinite(avgPrice) && avgPrice > 0) {
      vw = avgPrice;
      vwapSource = `Live futures average price ${future.symbol || future.name}`;
    }
  }

  let window = cachedWindow;
  const freshWindow = resolveOptionWindow(rows, symbol, spot, 5);

  if (!window) {
    window = freshWindow;
    optionWindowCache.set(symbol, freshWindow);

    const optionTokens = {};
    for (const c of freshWindow.contracts) (optionTokens[c.exch_seg] ||= []).push(String(c.token));
    if (Object.keys(optionTokens).length) {
      await sleep(1100);
      try {
        const optionQuote = await marketData(session, optionTokens, 'FULL');
        const optionFetched = parseFetched(optionQuote);
        fetchedQuotes = fetchedQuotes.concat(optionFetched);
        byTokenQuote = new Map(fetchedQuotes.map(x => [String(x.symbolToken ?? x.symboltoken ?? x.token), x]));
      } catch {}
    }
  } else if (freshWindow?.atm != null && freshWindow.atm !== window.atm) {
    optionWindowCache.set(symbol, freshWindow);
  }

  let chain = [];
  if (window?.contracts?.length) {
    chain = window.contracts.map(c => {
      const z = byTokenQuote.get(String(c.token)) || {};
      const sym = String(c.symbol || '');
      const optionType = /PE$/i.test(sym) ? 'PE' : /CE$/i.test(sym) ? 'CE' : (String(c.instrumenttype).toUpperCase().includes('PE') ? 'PE' : 'CE');
      return { token: String(c.token), tradingSymbol: c.symbol, exchange: c.exch_seg, strike: c.strikeN, optionType, ltp: round(quoteLtp(z)), oi: quoteOi(z), lotSize: Number(c.lotsize || 0) };
    }).sort((a,b) => a.strike - b.strike || a.optionType.localeCompare(b.optionType));
  }
  const ceOi = chain.filter(x => x.optionType === 'CE').reduce((s,x)=>s+x.oi,0);
  const peOi = chain.filter(x => x.optionType === 'PE').reduce((s,x)=>s+x.oi,0);
  const pcr = ceOi > 0 ? peOi / ceOi : null;

  const engine = signalEngine({ spot, ema9: e9, ema15: e15, vwapValue: vw, rsiValue: rv, macdValue: mv, st, pcr });
  const sr = pickSupportResistance(chain, spot);
  const atm = window.atm || null;
  const optionType = engine.signal === 'CE' ? 'CE' : engine.signal === 'PE' ? 'PE' : null;

  const trend = directionFromTrend({ spot, ema9: e9, ema15: e15, macdValue: mv, st, vwapValue: vw });
  const htf = higherTimeframeVote(candles);
  const oi = oiVote(pcr, sr, spot);
  const regime = regimeState({ spot, ema9: e9, ema15: e15, atrValue: a, st });
  const selection = selectBestContract(chain, optionType, spot);
  const suggested = selection.contract;
  const tradeDecision = buildTradeDecision({
    engine, trend, htf, oi, regime, sr, spot, atrValue: a, selected: selection
  });

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
    tradeDecision,
    levels,
    rules: engine.rules,
    notes: [
      'Market bias and Trade Decision are separate: CE/PE OI are evidence, not simultaneous trade calls.',
      'The meta decision requires Core Direction plus agreement from Trend, 15m higher timeframe and OI/PCR layers, with a non-range regime.',
      'Live quotes refresh frequently while historical candles are fetched once, cached, and rolled forward locally to avoid broker historical-API rate limits.',
      'VWAP reference uses the live nearest-futures average traded price, avoiding repeated historical futures requests.',
      'PCR shown here is calculated from the selected near ATM option window, not the full exchange chain.',
      'This build does not place orders.'
    ]
  };
}
