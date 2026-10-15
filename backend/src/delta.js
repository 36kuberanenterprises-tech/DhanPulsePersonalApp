import crypto from 'crypto';

const BASE = 'https://api.india.delta.exchange';

function env(name) {
  return String(process.env[name] || '').trim();
}

function hmac(secret, message) {
  return crypto.createHmac('sha256', secret).update(message).digest('hex');
}

async function signedGet(path, apiKey, apiSecret) {
  const timestamp = String(Math.floor(Date.now() / 1000));
  const signature = hmac(apiSecret, 'GET' + timestamp + path);
  const r = await fetch(BASE + path, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      'api-key': apiKey,
      signature,
      timestamp,
      'User-Agent': 'DhanPulse-Backend/2.7.4'
    }
  });
  const text = await r.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; }
  catch { throw new Error(`Delta returned non-JSON response (${r.status})`); }
  if (!r.ok || data?.success === false) {
    const e = data?.error || {};
    const message = [e.code, e.context, data?.message].filter(Boolean).join(': ');
    throw new Error(message || `Delta request failed (${r.status})`);
  }
  return data;
}

function sameSecret(a, b) {
  const aa = Buffer.from(String(a || ''));
  const bb = Buffer.from(String(b || ''));
  return aa.length === bb.length && aa.length > 0 && crypto.timingSafeEqual(aa, bb);
}

export function deltaBackendConfigured() {
  return {
    apiKey: !!env('DELTA_API_KEY'),
    apiSecret: !!env('DELTA_API_SECRET'),
    accessToken: !!env('DELTA_APP_ACCESS_TOKEN')
  };
}

export function verifyDeltaAccessToken(token) {
  return sameSecret(String(token || '').trim(), env('DELTA_APP_ACCESS_TOKEN'));
}

export async function deltaAccountSummary() {
  const apiKey = env('DELTA_API_KEY');
  const apiSecret = env('DELTA_API_SECRET');
  if (!apiKey || !apiSecret) throw new Error('Delta backend variables are not configured');

  const pref = await signedGet('/v2/users/trading_preferences', apiKey, apiSecret);
  const pr = pref?.result || {};
  let userId = pr?.user_id == null ? '' : String(pr.user_id);

  const wallets = await signedGet('/v2/wallet/balances', apiKey, apiSecret);
  const rows = Array.isArray(wallets?.result) ? wallets.result : [];
  const meta = wallets?.meta || {};

  let accountName = '';
  let holderName = '';
  try {
    const subs = await signedGet('/v2/sub_accounts', apiKey, apiSecret);
    const list = Array.isArray(subs?.result) ? subs.result : [];
    let selected = list.find(x => userId && String(x?.id) === userId)
      || list.find(x => x && x.is_sub_account === false)
      || (list.length === 1 ? list[0] : null);
    if (selected) {
      if (!userId && selected.id != null) userId = String(selected.id);
      accountName = String(selected.account_name || '');
      holderName = [selected.first_name, selected.last_name].filter(Boolean).join(' ').trim();
    }
  } catch {}

  let primary = null;
  const nonzero = [];
  for (const w of rows) {
    const asset = String(w?.asset_symbol || '');
    const balance = String(w?.balance ?? '0');
    const available = String(w?.available_balance ?? '0');
    const score = Math.abs(Number(balance) || 0);
    if (score > 0) nonzero.push({ asset, balance, available });
    if (!primary || score > primary.score) primary = { asset, balance, available, score };
    if (!userId && w?.user_id != null) userId = String(w.user_id);
  }

  return {
    success: true,
    source: 'DhanPulse backend variables',
    provider: 'Delta Exchange India',
    userId,
    accountName,
    holderName,
    displayName: holderName,
    netEquity: String(meta?.net_equity ?? ''),
    primaryAvailable: primary ? `${primary.asset} ${primary.available}` : '',
    primaryBalance: primary ? `${primary.asset} ${primary.balance}` : '',
    wallets: nonzero.slice(0, 12),
    keyMask: apiKey.length > 8 ? apiKey.slice(0, 4) + '••••••••' + apiKey.slice(-4) : 'SERVER SAVED',
    backendMode: true,
    privateFeed: 'BACKEND'
  };
}
