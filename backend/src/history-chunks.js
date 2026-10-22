// Retain successful research chunks when a later broker request fails. Errors
// are never cached here: the shared broker limiter still owns the cooldown.
export class HistoryChunks {
  constructor({ now = () => Date.now(), maxRows = 200_000 } = {}) {
    this.now = now; this.maxRows = maxRows; this.rows = 0;
    this.cache = new Map(); this.pending = new Map();
  }
  async get(client, payload, load) {
    const key = JSON.stringify([client, payload.exchange, payload.symboltoken,
      payload.interval, payload.fromdate, payload.todate]);
    const hit = this.cache.get(key);
    if (hit && hit.until > this.now()) return hit.value;
    if (hit) { this.rows -= hit.value.length; this.cache.delete(key); }
    if (this.pending.has(key)) return this.pending.get(key);
    const pending = Promise.resolve().then(load).then(value => {
      if (!Array.isArray(value) || !value.length) return value;
      const end = Date.parse(payload.todate.replace(' ', 'T') + ':00+05:30');
      // A current-day chunk can contain an unfinished candle. Refresh it soon.
      const today = new Date(this.now() + 330 * 60_000).toISOString().slice(0, 10);
      const ttl = payload.todate.slice(0, 10) < today ? 6 * 3_600_000 : 15_000;
      if (Number.isFinite(end) && value.length <= this.maxRows) {
        while (this.rows + value.length > this.maxRows || this.cache.size >= 500) {
          const oldest = this.cache.keys().next().value;
          this.rows -= this.cache.get(oldest).value.length; this.cache.delete(oldest);
        }
        this.cache.set(key, { value, until: this.now() + ttl });
        this.rows += value.length;
      }
      return value;
    }).finally(() => this.pending.delete(key));
    this.pending.set(key, pending);
    return pending;
  }
}
