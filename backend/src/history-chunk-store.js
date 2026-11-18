// Retain only verified broker OHLCV historical chunks across backend restarts.
// Files use a SHA256 key, never credentials or raw client codes in their names.
// A failed/empty/current-day fetch is not persisted.
import { createHash, randomUUID } from 'node:crypto';
import { mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { candleStorageDirectory } from './candle-store.js';

const VERSION = 1;
const MAX_BYTES = 2_000_000;
const MAX_BARS = 15_000;
const MAX_AGE_MS = 7 * 24 * 3_600_000;

const valid = row => {
  if (!row || typeof row.timestamp !== 'string') return false;
  const time = Date.parse(row.timestamp);
  return Number.isFinite(time) && [row.open, row.high, row.low, row.close, row.volume]
    .every(x => typeof x === 'number' && Number.isFinite(x)) &&
    row.open > 0 && row.close > 0 && row.low > 0 && row.volume >= 0 &&
    row.high >= Math.max(row.open, row.close, row.low) &&
    row.low <= Math.min(row.open, row.close);
};

export function chunkDiskPath(cacheKey, directory = join(candleStorageDirectory(), 'research-chunks')) {
  return join(directory, createHash('sha256').update(cacheKey).digest('hex') + '.json');
}

export async function readHistoryChunk(cacheKey, { directory, now = Date.now() } = {}) {
  const path = chunkDiskPath(cacheKey, directory);
  let raw;
  try { raw = await readFile(path, 'utf8'); }
  catch (e) { if (e.code === 'ENOENT') return null; throw e; }
  if (Buffer.byteLength(raw, 'utf8') > MAX_BYTES) return null;
  let record;
  try { record = JSON.parse(raw); } catch { return null; }
  if (record?.version !== VERSION || !Array.isArray(record.bars) ||
      record.bars.length < 1 || record.bars.length > MAX_BARS ||
      !Number.isFinite(record.savedAt) ||
      now < record.savedAt || now - record.savedAt > MAX_AGE_MS ||
      !record.bars.every(valid)) return null;
  return record.bars;
}

export async function saveHistoryChunk(cacheKey, payload, bars, { directory, now = Date.now() } = {}) {
  if (!Array.isArray(bars) || !bars.length || bars.length > MAX_BARS || !bars.every(valid)) return false;
  const end = Date.parse(String(payload?.todate || '').replace(' ', 'T') + ':00+05:30');
  // Historical chunks that overlap the current day may contain unfinished bars.
  const currentDayStart = Math.floor((now + 330 * 60_000) / 86_400_000) * 86_400_000 - 330 * 60_000;
  if (!Number.isFinite(end) || end >= currentDayStart) return false;
  const contents = JSON.stringify({ version: VERSION, savedAt: now, bars });
  if (Buffer.byteLength(contents, 'utf8') > MAX_BYTES) return false;
  const path = chunkDiskPath(cacheKey, directory);
  await mkdir(dirname(path), { recursive: true, mode: 0o700 });
  const temporary = path + '.' + process.pid + '.' + randomUUID() + '.tmp';
  try {
    await writeFile(temporary, contents, { encoding: 'utf8', mode: 0o600 });
    try { await rename(temporary, path); }
    catch (e) {
      if (process.platform !== 'win32' || !['EPERM', 'EEXIST'].includes(e.code)) throw e;
      await rm(path, { force: true });
      await rename(temporary, path);
    }
    return true;
  } finally { await rm(temporary, { force: true }).catch(() => {}); }
}
