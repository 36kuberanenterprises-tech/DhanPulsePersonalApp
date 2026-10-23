import { candleData, parseCandles } from './angel.js';

const MINUTES = { ONE_MINUTE: 1, THREE_MINUTE: 3, FIVE_MINUTE: 5, TEN_MINUTE: 10, FIFTEEN_MINUTE: 15 };
const IST = 330 * 60_000;
const format = ms => new Date(ms + IST).toISOString().slice(0, 16).replace('T', ' ');
const valid = c => Number.isFinite(Date.parse(c.timestamp)) &&
  [c.open,c.high,c.low,c.close,c.volume].every(Number.isFinite) && c.low > 0 &&
  c.high >= Math.max(c.open,c.close,c.low) && c.low <= Math.min(c.open,c.close) && c.volume >= 0;

// Only complete, contiguous broker minute bars can reconstruct a larger bar.
// A quote or a missing minute cannot be used to fill a hole.
export function aggregateMcxMinutes(rows, interval, now) {
  const minutes = MINUTES[interval];
  if (!minutes) throw new Error('Unsupported MCX candle interval');
  const duration = minutes * 60_000, groups = new Map();
  const unique = new Map(rows.filter(valid).map(c => [Date.parse(c.timestamp), c]));
  for (const [time,c] of unique) {
    if (time % 60_000 !== 0) continue;
    const start = Math.floor(time / duration) * duration;
    if (start + duration + 20_000 > now.getTime()) continue;
    if (!groups.has(start)) groups.set(start, []);
    groups.get(start).push([time,c]);
  }
  return [...groups.entries()].sort(([a],[b]) => a-b).flatMap(([start, group]) => {
    group.sort(([a],[b]) => a-b);
    if (group.length !== minutes || group.some(([time],i) => time !== start + i * 60_000)) return [];
    const bars = group.map(([,c]) => c);
    return [{ timestamp: new Date(start).toISOString(), open: bars[0].open,
      high: Math.max(...bars.map(c => c.high)), low: Math.min(...bars.map(c => c.low)),
      close: bars.at(-1).close, volume: bars.reduce((sum,c) => sum+c.volume,0) }];
  });
}

export function createMcxHistoryLoader(fetchHistory = candleData) {
  const cache = new Map(), locks = new Map(), failures = new Map();
  return async function mcxHistory(session, exchange, token, interval, now) {
    if (exchange !== 'MCX' || !MINUTES[interval]) throw new Error('Invalid MCX history request');
    const key = [session.clientCode || session.apiKey, token, interval].join('|');
    const duration = MINUTES[interval] * 60_000;
    const expected = Math.floor((now.getTime() - 20_000) / duration) * duration - duration;
    const previous = cache.get(key);
    const failure = failures.get(key);
    if (failure && Date.now() < failure.retryAt) {
      if (previous?.rows.length >= 35) return previous.rows;
      throw failure.error;
    }
    if (previous && previous.expected === expected && Date.now() - previous.at < 60_000) return previous.rows;
    if (previous?.rows.length >= 35 && Date.parse(previous.rows.at(-1).timestamp) >= expected) return previous.rows;
    if (locks.has(key)) return locks.get(key);
    const pending = (async () => {
      const payload = { exchange: 'MCX', symboltoken: String(token), interval,
        fromdate: format(previous?.rows.length >= 35
          ? Math.max(now.getTime() - 4*86_400_000, Date.parse(previous.rows.at(-1).timestamp) - duration)
          : now.getTime() - 4*86_400_000), todate: format(now.getTime()) };
      const raw = await fetchHistory(session, payload);
      let rows = parseCandles(raw).filter(valid);
      // A successful but empty/short selected-interval result may be recovered
      // from the same contract's ONE_MINUTE history. Never do this after 403.
      const direct = [...new Map([...(previous?.rows || []), ...rows]
        .map(c => [Date.parse(c.timestamp), c])).values()].filter(c =>
          Date.parse(c.timestamp) >= now.getTime() - 14*86_400_000 &&
          Date.parse(c.timestamp) + duration + 20_000 <= now.getTime());
      if ((direct.length < 35 || Math.max(...direct.map(c => Date.parse(c.timestamp))) < expected) && interval !== 'ONE_MINUTE') {
        const minuteRaw = await fetchHistory(session, { ...payload, interval: 'ONE_MINUTE',
          fromdate: direct.length >= 35
            ? format(Math.max(now.getTime() - 4*86_400_000,
                Math.max(...direct.map(c => Date.parse(c.timestamp))) - duration))
            : format(now.getTime() - 4*86_400_000) });
        rows = [...rows, ...aggregateMcxMinutes(parseCandles(minuteRaw), interval, now)];
      }
      const merged = new Map([...(previous?.rows || []), ...rows].map(c => [Date.parse(c.timestamp),c]));
      const completed = [...merged.entries()].filter(([time]) => time >= now.getTime()-14*86_400_000 &&
        time + duration + 20_000 <= now.getTime()).sort(([a],[b])=>a-b).map(([,c])=>c).slice(-2400);
      console.info('MCX_HISTORY', JSON.stringify({ token: String(token), interval, bars: completed.length,
        lastCandleTime: completed.at(-1)?.timestamp || null }));
      if (completed.length < 35) throw new Error(`MCX broker history returned ${completed.length} completed candles for token ${token}; 35 are required. No indicators or calls can be calculated yet.`);
      cache.set(key, { rows: completed, expected, at: Date.now() });
      failures.delete(key);
      return completed;
    })().catch(error => {
      failures.set(key, { error, retryAt: error.retryAt || Date.now() + 60_000 });
      if (previous?.rows.length >= 35) return previous.rows;
      throw error;
    }).finally(() => locks.delete(key));
    locks.set(key,pending);
    return pending;
  };
}

export const mcxHistory = createMcxHistoryLoader();
