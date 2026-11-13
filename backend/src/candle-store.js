// A local, durable store for broker-confirmed OHLCV. Never store SmartAPI keys,
// client IDs, session tokens, or guessed candles in this directory.
import { createHash, randomUUID } from 'node:crypto';
import { readFile, writeFile, mkdir, rename, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { homedir } from 'node:os';

const VERSION = 1;
const MAX_ROWS = 1200;
const MAX_FILE_BYTES = 512_000;

export function candleStorageDirectory() {
  if (process.env.DHANPULSE_CANDLE_CACHE_DIR?.trim()) {
    return process.env.DHANPULSE_CANDLE_CACHE_DIR.trim();
  }
  // The signed-in Windows user has a private LocalAppData folder.
  return process.env.LOCALAPPDATA
    ? join(process.env.LOCALAPPDATA, 'DhanPulse', 'candles')
    : join(homedir(), '.local', 'state', 'dhanpulse', 'candles');
}

export function candleCachePath(cacheKey, directory = candleStorageDirectory()) {
  // Including the client code in the cache key separates accounts, but only
  // its SHA-256 digest appears on disk. No credentials are saved in the file.
  const digest = createHash('sha256').update(String(cacheKey)).digest('hex');
  return join(directory, digest + '.json');
}

function validBar(row) {
  const timestamp = typeof row?.timestamp === 'string' ? row.timestamp : '';
  const time = Date.parse(timestamp);
  const open = Number(row?.open), high = Number(row?.high),
    low = Number(row?.low), close = Number(row?.close),
    volume = Number(row?.volume);
  if (!timestamp || !Number.isFinite(time) || !Number.isFinite(open) ||
      !Number.isFinite(high) || !Number.isFinite(low) || !Number.isFinite(close) ||
      !Number.isFinite(volume) || open <= 0 || close <= 0 || low <= 0 ||
      high < Math.max(open,close,low) || low > Math.min(open,close) || volume < 0) return null;
  return { timestamp: new Date(time).toISOString(), open, high, low, close, volume };
}

function cleanBars(rows) {
  if (!Array.isArray(rows)) return [];
  const unique = new Map();
  for (const row of rows.slice(-MAX_ROWS)) {
    const valid = validBar(row);
    if (valid) unique.set(Date.parse(valid.timestamp), valid);
  }
  return [...unique.entries()]
    .sort(([a], [b]) => a-b)
    .map(([,row]) => row)
    .slice(-MAX_ROWS);
}

export async function readSavedCandles(cacheKey, { directory = candleStorageDirectory() } = {}) {
  let contents;
  try {
    contents = await readFile(candleCachePath(cacheKey, directory), 'utf8');
  } catch (e) {
    if (e.code === 'ENOENT') return null;
    throw e;
  }
  if (Buffer.byteLength(contents) > MAX_FILE_BYTES) return null;
  let record;
  try { record = JSON.parse(contents); } catch { return null; }
  if (record?.version !== VERSION || !Array.isArray(record.candles)) return null;
  const candles = cleanBars(record.candles);
  return candles.length >= 35
    ? { candles, savedAt: Number(record.savedAt) || null }
    : null;
}

export async function saveBrokerCandles(cacheKey, candles, { directory = candleStorageDirectory() } = {}) {
  const clean = cleanBars(candles);
  if (clean.length < 35) return false;
  await mkdir(directory, { recursive: true, mode: 0o700 });
  const filepath = candleCachePath(cacheKey, directory);
  const temporary = filepath + '.' + process.pid + '.' + randomUUID() + '.tmp';
  try {
    // Fixed schema: data on disk contains only OHLCV and timestamps.
    await writeFile(temporary, JSON.stringify({ version: VERSION,
      savedAt: Date.now(), candles: clean }), { encoding: 'utf8', mode: 0o600 });
    try {
      await rename(temporary, filepath);
    } catch (e) {
      // Windows can prevent rename over an existing file. There is a short
      // replacement window only on this platform; data remains in memory.
      if (process.platform !== 'win32' || !['EPERM','EEXIST'].includes(e.code)) throw e;
      await rm(filepath, { force: true });
      await rename(temporary, filepath);
    }
    return true;
  } finally {
    await rm(temporary, { force: true }).catch(() => {});
  }
}
