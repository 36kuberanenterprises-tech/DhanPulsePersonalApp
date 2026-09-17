export function ema(values, period) {
  if (!Array.isArray(values) || values.length < period) return null;
  const k = 2 / (period + 1);
  let current = values.slice(0, period).reduce((a, b) => a + b, 0) / period;
  for (let i = period; i < values.length; i++) current = values[i] * k + current * (1 - k);
  return current;
}

export function emaSeries(values, period) {
  const out = Array(values.length).fill(null);
  if (values.length < period) return out;
  const k = 2 / (period + 1);
  let current = values.slice(0, period).reduce((a, b) => a + b, 0) / period;
  out[period - 1] = current;
  for (let i = period; i < values.length; i++) {
    current = values[i] * k + current * (1 - k);
    out[i] = current;
  }
  return out;
}

export function rsi(values, period = 14) {
  if (!Array.isArray(values) || values.length <= period) return null;
  let gains = 0;
  let losses = 0;
  for (let i = 1; i <= period; i++) {
    const d = values[i] - values[i - 1];
    if (d >= 0) gains += d; else losses -= d;
  }
  let avgGain = gains / period;
  let avgLoss = losses / period;
  for (let i = period + 1; i < values.length; i++) {
    const d = values[i] - values[i - 1];
    const gain = Math.max(d, 0);
    const loss = Math.max(-d, 0);
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
  }
  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - 100 / (1 + rs);
}

export function macd(values, fast = 12, slow = 26, signalPeriod = 9) {
  if (values.length < slow + signalPeriod) return null;
  const fastS = emaSeries(values, fast);
  const slowS = emaSeries(values, slow);
  const line = values.map((_, i) => (fastS[i] != null && slowS[i] != null ? fastS[i] - slowS[i] : null));
  const valid = line.filter(v => v != null);
  if (valid.length < signalPeriod) return null;
  const signal = ema(valid, signalPeriod);
  const last = valid[valid.length - 1];
  return { line: last, signal, histogram: last - signal };
}

export function atr(candles, period = 14) {
  if (!Array.isArray(candles) || candles.length <= period) return null;
  const trs = [];
  for (let i = 1; i < candles.length; i++) {
    const c = candles[i];
    const p = candles[i - 1];
    trs.push(Math.max(c.high - c.low, Math.abs(c.high - p.close), Math.abs(c.low - p.close)));
  }
  let current = trs.slice(0, period).reduce((a, b) => a + b, 0) / period;
  for (let i = period; i < trs.length; i++) current = (current * (period - 1) + trs[i]) / period;
  return current;
}

export function supertrend(candles, period = 10, multiplier = 3) {
  if (!Array.isArray(candles) || candles.length < period + 2) return null;
  const tr = [0];
  for (let i = 1; i < candles.length; i++) {
    const c = candles[i], p = candles[i - 1];
    tr.push(Math.max(c.high - c.low, Math.abs(c.high - p.close), Math.abs(c.low - p.close)));
  }
  const atrs = Array(candles.length).fill(null);
  let a = tr.slice(1, period + 1).reduce((x, y) => x + y, 0) / period;
  atrs[period] = a;
  for (let i = period + 1; i < candles.length; i++) {
    a = (a * (period - 1) + tr[i]) / period;
    atrs[i] = a;
  }
  const upper = Array(candles.length).fill(null);
  const lower = Array(candles.length).fill(null);
  const finalUpper = Array(candles.length).fill(null);
  const finalLower = Array(candles.length).fill(null);
  const st = Array(candles.length).fill(null);
  const dir = Array(candles.length).fill(null);

  for (let i = period; i < candles.length; i++) {
    const hl2 = (candles[i].high + candles[i].low) / 2;
    upper[i] = hl2 + multiplier * atrs[i];
    lower[i] = hl2 - multiplier * atrs[i];
    if (i === period) {
      finalUpper[i] = upper[i];
      finalLower[i] = lower[i];
      st[i] = candles[i].close <= finalUpper[i] ? finalUpper[i] : finalLower[i];
      dir[i] = candles[i].close > st[i] ? 1 : -1;
      continue;
    }
    finalUpper[i] = (upper[i] < finalUpper[i - 1] || candles[i - 1].close > finalUpper[i - 1]) ? upper[i] : finalUpper[i - 1];
    finalLower[i] = (lower[i] > finalLower[i - 1] || candles[i - 1].close < finalLower[i - 1]) ? lower[i] : finalLower[i - 1];
    if (st[i - 1] === finalUpper[i - 1]) {
      st[i] = candles[i].close <= finalUpper[i] ? finalUpper[i] : finalLower[i];
    } else {
      st[i] = candles[i].close >= finalLower[i] ? finalLower[i] : finalUpper[i];
    }
    dir[i] = candles[i].close > st[i] ? 1 : -1;
  }
  const i = candles.length - 1;
  return { value: st[i], direction: dir[i] === 1 ? 'BULLISH' : 'BEARISH' };
}

export function vwap(candles) {
  if (!Array.isArray(candles) || candles.length === 0) return null;
  let pv = 0, vol = 0;
  for (const c of candles) {
    const v = Number(c.volume || 0);
    if (v <= 0) continue;
    const typical = (c.high + c.low + c.close) / 3;
    pv += typical * v;
    vol += v;
  }
  return vol > 0 ? pv / vol : null;
}
