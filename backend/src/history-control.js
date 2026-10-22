// One shared history budget per client code, independent of app login/session.
// This controls this backend only; another application's traffic is not observable.
export const HISTORY_LIMITS = { gap: 1100, minute: 150, hour: 5000 };
export function isRateError(error) {
  return error?.status === 429 || error?.rateLimited === true ||
    /exceeding access rate|rate limit|too many requests|AB1021|\b429\b/i.test(error?.message || '');
}
export function cooldownError(until, now = Date.now()) {
  const seconds = Math.max(1, Math.ceil((until - now) / 1000));
  return Object.assign(new Error(`Candle data: historical request cooldown after exceeding access rate. Retry in ${seconds} seconds.`),
    { rateLimited: true, retryAt: until, retryAfterMs: seconds * 1000 });
}
export class HistoryBudget {
  constructor({ now = () => Date.now(), sleep = ms => new Promise(r => setTimeout(r, ms)), limits = HISTORY_LIMITS } = {}) {
    this.now = now; this.sleep = sleep; this.limits = limits; this.clients = new Map();
  }
  state(key) {
    if (!this.clients.has(key)) this.clients.set(key, { starts: [], blockedUntil: 0, failures: 0, queue: Promise.resolve() });
    return this.clients.get(key);
  }
  async run(key, prepare, request) {
    const state = this.state(key);
    const pending = state.queue.then(async () => {
      if (state.blockedUntil > this.now()) throw cooldownError(state.blockedUntil, this.now());
      // Reserve the general broker-read slot first so it cannot bunch the
      // actual history starts after the history permit has been granted.
      await prepare();
      state.starts = state.starts.filter(t => t > this.now() - 3_600_000);
      const minute = state.starts.filter(t => t > this.now() - 60_000);
      const due = Math.max(this.now(), (state.starts.at(-1) ?? -Infinity) + this.limits.gap,
        minute.length >= this.limits.minute ? minute[minute.length - this.limits.minute] + 60_000 : 0,
        state.starts.length >= this.limits.hour ? state.starts[state.starts.length - this.limits.hour] + 3_600_000 : 0);
      if (due - this.now() > 5000) throw cooldownError(due, this.now());
      if (due > this.now()) await this.sleep(due - this.now());
      if (state.blockedUntil > this.now()) throw cooldownError(state.blockedUntil, this.now());
      state.starts.push(this.now());
      try {
        const result = await request();
        state.failures = 0;
        return result;
      } catch (error) {
        if (isRateError(error)) {
          const backoff = Math.min(900_000, 60_000 * 2 ** Math.min(state.failures++, 4));
          state.blockedUntil = this.now() + Math.max(backoff, error.retryAfterMs || 0);
          error.retryAt = state.blockedUntil;
          error.retryAfterMs = state.blockedUntil - this.now();
        }
        throw error;
      }
    });
    state.queue = pending.catch(() => {});
    return pending;
  }
}

const MAX_DAYS = { ONE_MINUTE:30, THREE_MINUTE:60, FIVE_MINUTE:100, TEN_MINUTE:100,
  FIFTEEN_MINUTE:200, THIRTY_MINUTE:200, ONE_HOUR:400, ONE_DAY:2000 };
export function validateCandlePayload(payload) {
  const date = value => {
    if (!/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(value || '')) return NaN;
    const time = Date.parse(value.replace(' ', 'T') + ':00+05:30');
    if (!Number.isFinite(time)) return NaN;
    const canonical = new Date(time + 330 * 60_000).toISOString().slice(0,16).replace('T',' ');
    return canonical === value ? time : NaN;
  };
  const start = date(payload?.fromdate), end = date(payload?.todate);
  if (!['NSE','BSE','NFO','BFO','MCX','CDS'].includes(payload?.exchange) ||
      !/^[A-Za-z0-9_-]{1,64}$/.test(String(payload?.symboltoken || '')) || !MAX_DAYS[payload?.interval] ||
      !Number.isFinite(start) || !Number.isFinite(end) || end <= start ||
      end - start > MAX_DAYS[payload.interval] * 86_400_000) {
    throw Object.assign(new Error('Candle data: invalid exchange, token, interval or historical date range'), { status: 400 });
  }
}
