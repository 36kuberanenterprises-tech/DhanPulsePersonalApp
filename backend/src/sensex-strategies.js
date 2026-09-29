import { atr, ema, macd, rsi, supertrend } from './indicators.js';

const IST_MS = 330 * 60_000;
const SETTLE_MS = 20_000;
const MINUTES = { ONE_MINUTE: 1, THREE_MINUTE: 3, FIVE_MINUTE: 5, TEN_MINUTE: 10, FIFTEEN_MINUTE: 15 };
const round = (value, decimals = 2) => Number.isFinite(value) ? Number(value.toFixed(decimals)) : null;
const vote = (name, ce, pe, detail) => ({ name, vote: ce && !pe ? 'CE' : pe && !ce ? 'PE' : 'WAIT', detail });

function indiaMinutes(now) {
  const d = new Date(now.getTime() + IST_MS);
  return d.getUTCHours() * 60 + d.getUTCMinutes();
}

export function sensexClosedCandles(candles, interval, now = new Date()) {
  const duration = (MINUTES[interval] || 5) * 60_000;
  const byTime = new Map();
  for (const c of candles) {
    const t = Date.parse(c.timestamp);
    if (!Number.isFinite(t) || t + duration + SETTLE_MS > now.getTime() ||
        ![c.open, c.high, c.low, c.close].every(Number.isFinite)) continue;
    byTime.set(t, c);
  }
  return [...byTime.entries()].sort(([a], [b]) => a - b).map(([, c]) => c);
}

function expectedLastStart(now, interval) {
  const local = new Date(now.getTime() + IST_MS);
  const open = Date.UTC(local.getUTCFullYear(), local.getUTCMonth(), local.getUTCDate(), 9, 15) - IST_MS;
  const duration = (MINUTES[interval] || 5) * 60_000;
  return open + Math.max(0, Math.floor((now.getTime() - open - SETTLE_MS) / duration) - 1) * duration;
}

export function sensexRegime({ atrValue, spot, ema9, ema15, supertrend: st, candles }) {
  if (![atrValue, spot, ema9, ema15].every(x => Number.isFinite(x) && x > 0) || !st || candles.length < 35) {
    return { name: 'UNKNOWN', suitable: false, detail: 'Completed price history or ATR is unavailable' };
  }
  const atrPct = atrValue / spot;
  const gap = Math.abs(ema9 - ema15) / atrValue;
  const aligned = (ema9 > ema15 && st.direction === 'BULLISH') || (ema9 < ema15 && st.direction === 'BEARISH');
  if (atrPct < 0.0003) return { name: 'LOW_VOL', suitable: false, detail: `ATR is ${round(atrPct * 100, 3)}% of spot` };
  if (atrPct > 0.012) return { name: 'HIGH_VOL', suitable: false, detail: `ATR is ${round(atrPct * 100, 3)}% of spot` };
  if (aligned && gap >= 0.35) return { name: 'TREND', suitable: true, detail: `EMA gap is ${round(gap, 2)} times ATR with Supertrend alignment` };
  if (gap <= 0.18) return { name: 'RANGE', suitable: true, detail: `EMA gap is ${round(gap, 2)} times ATR` };
  return { name: 'TRANSITION', suitable: true, detail: `EMA gap is ${round(gap, 2)} times ATR` };
}

export function evaluateSensexFamilies({ candles, higherCandles, interval = 'FIVE_MINUTE', spot, now = new Date(), premiumMove = {} }) {
  const bars = sensexClosedCandles(candles || [], interval, now);
  const higher = sensexClosedCandles(higherCandles || [], 'FIFTEEN_MINUTE', now);
  const names = ['Trend continuation', 'Breakout', 'Pullback', 'Liquidity reversal', 'Short horizon mean reversion', 'Momentum ignition'];
  const waiting = reason => ({ direction: 'WAIT', conflict: false, votes: names.map(name => vote(name, false, false, reason)),
    active: [], higherVote: 'WAIT', regime: { name: 'UNKNOWN', suitable: false, detail: reason }, atrValue: null, reason });
  if (bars.length < 45 || higher.length < 25 || !Number.isFinite(spot) || spot <= 0) return waiting('Completed SENSEX and 15 minute history is preparing');
  const last = bars.at(-1), prev = bars.at(-2), prev2 = bars.at(-3);
  if (Date.parse(last.timestamp) < expectedLastStart(now, interval)) return waiting('Latest completed SENSEX candle is delayed');
  if (Date.parse(higher.at(-1).timestamp) < expectedLastStart(now, 'FIFTEEN_MINUTE')) return waiting('Latest completed 15 minute candle is delayed');
  const closes = bars.map(x => x.close);
  const hCloses = higher.map(x => x.close);
  const e9 = ema(closes, 9), e15 = ema(closes, 15), a = atr(bars, 14), st = supertrend(bars, 10, 3);
  const h9 = ema(hCloses, 9), h15 = ema(hCloses, 15), hSt = supertrend(higher, 10, 3);
  const higherVote = h9 > h15 && hSt?.direction === 'BULLISH' ? 'CE' : h9 < h15 && hSt?.direction === 'BEARISH' ? 'PE' : 'WAIT';
  const regime = sensexRegime({ atrValue: a, spot, ema9: e9, ema15: e15, supertrend: st, candles: bars });
  if (!regime.suitable) return { ...waiting(regime.detail), regime, atrValue: a, higherVote };
  const r = rsi(closes, 14), m = macd(closes);
  const high12 = Math.max(...bars.slice(-13, -1).map(x => x.high));
  const low12 = Math.min(...bars.slice(-13, -1).map(x => x.low));
  const high20 = Math.max(...bars.slice(-21, -1).map(x => x.high));
  const low20 = Math.min(...bars.slice(-21, -1).map(x => x.low));
  const high6 = Math.max(...bars.slice(-7, -1).map(x => x.high));
  const low6 = Math.min(...bars.slice(-7, -1).map(x => x.low));
  const previous20 = bars.slice(-21, -1).map(x => x.close);
  const mean = previous20.reduce((x, y) => x + y, 0) / previous20.length;
  const sd = Math.sqrt(previous20.reduce((sum, x) => sum + (x - mean) ** 2, 0) / previous20.length);
  const inside = Math.abs(spot - last.close) <= a * 0.5;
  const up = last.close > last.open, down = last.close < last.open;
  const wickDown = Math.min(last.open, last.close) - last.low;
  const wickUp = last.high - Math.max(last.open, last.close);
  const trend = regime.name === 'TREND';
  const noTrend = regime.name === 'RANGE' || regime.name === 'TRANSITION';
  const votes = [
    vote('Trend continuation', trend && higherVote === 'CE' && e9 > e15 && st.direction === 'BULLISH' &&
      last.close > e9 && last.close > prev.close && prev.close >= prev2.close && spot >= last.close - a * 0.15 && spot <= e9 + a * 1.2,
      trend && higherVote === 'PE' && e9 < e15 && st.direction === 'BEARISH' &&
      last.close < e9 && last.close < prev.close && prev.close <= prev2.close && spot <= last.close + a * 0.15 && spot >= e9 - a * 1.2,
      'Aligned EMA, Supertrend and 15 minute direction on completed candles'),
    vote('Breakout', regime.name !== 'RANGE' && higherVote === 'CE' && prev.close <= high12 &&
      last.close > high12 + a * 0.08 && last.close - high12 <= a * 0.8 && last.close - last.open >= a * 0.25 && spot >= last.close - a * 0.15,
      regime.name !== 'RANGE' && higherVote === 'PE' && prev.close >= low12 &&
      last.close < low12 - a * 0.08 && low12 - last.close <= a * 0.8 && last.open - last.close >= a * 0.25 && spot <= last.close + a * 0.15,
      'Completed close beyond the prior 12 candle range with controlled extension'),
    vote('Pullback', trend && higherVote === 'CE' && e9 > e15 && prev.low <= e9 + a * 0.15 &&
      prev.close >= e15 && up && last.close > prev.high && spot >= last.close - a * 0.15,
      trend && higherVote === 'PE' && e9 < e15 && prev.high >= e9 - a * 0.15 &&
      prev.close <= e15 && down && last.close < prev.low && spot <= last.close + a * 0.15,
      'First price recovery after a completed EMA pullback'),
    vote('Liquidity reversal', noTrend && last.low < low20 - a * 0.08 && last.close > low20 &&
      wickDown >= a * 0.3 && up && spot >= last.close - a * 0.15,
      noTrend && last.high > high20 + a * 0.08 && last.close < high20 &&
      wickUp >= a * 0.3 && down && spot <= last.close + a * 0.15,
      'Sweep of a prior 20 candle level followed by a completed reclaim'),
    vote('Short horizon mean reversion', regime.name === 'RANGE' && last.low < mean - 1.8 * sd &&
      last.close > mean - 1.8 * sd && r <= 45 && up && spot >= last.close - a * 0.15,
      regime.name === 'RANGE' && last.high > mean + 1.8 * sd &&
      last.close < mean + 1.8 * sd && r >= 55 && down && spot <= last.close + a * 0.15,
      'Range regime reversal back inside the prior 20 candle volatility band'),
    vote('Momentum ignition', regime.name !== 'RANGE' && higherVote === 'CE' && inside &&
      last.close - last.open >= a * 0.55 && last.close >= last.high - (last.high - last.low) * 0.2 &&
      last.close > high6 && m?.histogram > 0 && premiumMove.CE >= 0.02,
      regime.name !== 'RANGE' && higherVote === 'PE' && inside &&
      last.open - last.close >= a * 0.55 && last.close <= last.low + (last.high - last.low) * 0.2 &&
      last.close < low6 && m?.histogram < 0 && premiumMove.PE >= 0.02,
      'Range expansion, MACD and at least 2 percent premium movement across distinct quote samples')
  ];
  const active = votes.filter(x => x.vote !== 'WAIT');
  const conflict = active.some(x => x.vote === 'CE') && active.some(x => x.vote === 'PE');
  const direction = !active.length || conflict ? 'WAIT' : active[0].vote;
  return { direction, conflict, votes, active, higherVote, regime, atrValue: a,
    reason: conflict ? 'Independent SENSEX strategy families disagree.' : !active.length ? 'No SENSEX strategy family has a completed setup.' : `${active.map(x => x.name).join(' and ')} supports ${direction}.` };
}

export function buildSensexDecision({ family, pcr, oiCoverage, support, resistance, spot, futurePrice, selected, now = new Date() }) {
  const checks = [];
  const conflicts = [];
  const cautions = [];
  const add = (name, state, detail) => {
    checks.push({ name, vote: state, detail });
    if (state === 'BLOCK') conflicts.push(detail);
  };
  const selectedContract = selected?.contract || null;
  const basisPct = Number.isFinite(futurePrice) && futurePrice > 0 && spot > 0 ? 100 * (futurePrice / spot - 1) : null;
  const spreadPct = selectedContract?.bid > 0 && selectedContract?.ask >= selectedContract.bid && selectedContract?.ltp > 0
    ? 100 * (selectedContract.ask - selectedContract.bid) / selectedContract.ltp : null;
  const cover = Number(String(oiCoverage || '').split('/')[0]);
  const dir = family.direction;
  const htfOpposite = dir !== 'WAIT' && family.higherVote !== 'WAIT' && family.higherVote !== dir;
  add('Regime and volatility', family.regime.suitable ? 'OK' : 'BLOCK', family.regime.detail);
  add('15 minute context', htfOpposite ? 'BLOCK' : family.higherVote === 'WAIT' ? 'NEUTRAL' : 'OK',
    htfOpposite ? '15 minute direction is opposite to the active family.' : `15 minute direction: ${family.higherVote}`);
  add('Futures basis', basisPct == null || Math.abs(basisPct) > 1.5 ? 'BLOCK' : 'OK',
    basisPct == null ? 'Fresh SENSEX futures price is unavailable; funding basis cannot be checked.' :
      `SENSEX futures basis ${round(basisPct, 3)}% against spot${Math.abs(basisPct) > 1.5 ? ' is outside the filter' : ''}. This is a cost of carry proxy, not a funding rate.`);
  const extremePcr = Number.isFinite(pcr) && (pcr > 1.8 || pcr < 0.6);
  add('Open interest and PCR', !Number.isFinite(pcr) || cover < 3 ? 'BLOCK' : 'OK',
    !Number.isFinite(pcr) || cover < 3 ? 'At least three fresh paired strikes are required for OI context.' :
      `Near ATM PCR ${round(pcr)} with ${cover} paired strikes. OI counts open contracts, so this ratio alone is not a directional vote.`);
  if (extremePcr) cautions.push(`Near ATM PCR ${round(pcr)} is unusually one sided. Review option prices and the nearby OI levels before a manual entry.`);
  const barrier = dir === 'CE' && resistance != null && resistance > spot && resistance - spot <= (family.atrValue || 0) * 0.5 ||
    dir === 'PE' && support != null && support < spot && spot - support <= (family.atrValue || 0) * 0.5;
  add('OI barrier', barrier ? 'BLOCK' : 'OK', barrier ? 'Heavy OI support or resistance is too close to the proposed move.' : 'No nearby heavy OI barrier in the proposed direction.');
  const spreadReady = selectedContract && spreadPct != null && spreadPct <= 3 && selectedContract.oi > 0 &&
    selectedContract.lotSize > 0 && selectedContract.bidQty >= selectedContract.lotSize &&
    selectedContract.askQty >= selectedContract.lotSize && selectedContract.ltp >= 15;
  add('Option spread and depth', spreadReady ? 'OK' : 'BLOCK', spreadReady
    ? `Spread ${round(spreadPct)}% with bid and ask depth for at least one lot.`
    : 'Fresh option bid, ask, one lot of depth, OI and a suitable premium are required.');
  const minutes = indiaMinutes(now);
  add('Entry window', minutes >= 570 && minutes < 915 ? 'OK' : 'BLOCK',
    minutes >= 570 && minutes < 915 ? 'New SENSEX calls may be checked between 09:30 and 15:15 IST.' :
      'New SENSEX calls are available from 09:30 to 15:15 IST only.');

  if (family.conflict) conflicts.unshift('Independent SENSEX strategy families disagree.');
  const setupAllowed = dir !== 'WAIT' && !family.conflict && conflicts.length === 0;
  const direction = setupAllowed ? dir : 'WAIT';
  const totalVotes = family.votes.length;
  return {
    direction, status: setupAllowed ? 'FAMILY_CONFIRMED' : family.conflict || htfOpposite || barrier ? 'REJECTED_CONFLICT' : 'WATCHING',
    setupAllowed, autoEntryAllowed: false,
    supportingVotes: family.active.length, totalVotes, alignmentPct: totalVotes ? round(100 * family.active.length / totalVotes, 0) : 0,
    regime: family.regime.name, regimeSuitable: family.regime.suitable, regimeDetail: family.regime.detail,
    strategyFamily: setupAllowed ? family.active.map(x => x.name).join(' + ') : null,
    strategyVotes: family.votes, contextChecks: checks, conflicts, cautions,
    selectedContractReason: selected?.reason || null, selectedContractScore: selected?.score || null,
    message: setupAllowed ? `${family.reason} Context passed. Manual review only; two live scans and premium entry confirmation are still required.` :
      family.conflict ? 'WAIT: independent SENSEX strategy families disagree.' :
      dir === 'WAIT' ? `WAIT: ${family.reason}` : `WAIT: ${conflicts[0] || family.reason}`
  };
}
