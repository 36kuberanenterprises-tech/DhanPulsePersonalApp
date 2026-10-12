import express from 'express';

const app = express();
app.use(express.json({ limit: '64kb' }));

const PORT = Number(process.env.PORT || 8080);
const RELAY_SECRET = String(process.env.ORDER_RELAY_SECRET || process.env.RELAY_SECRET || '').trim();
const EXPECTED_PUBLIC_IP = String(process.env.CLIENT_PUBLIC_IP || process.env.EXPECTED_PUBLIC_IP || '34.70.199.153').trim();

let ipCache = { at: 0, ip: null };

async function actualPublicIp(force = false) {
  if (!force && ipCache.ip && Date.now() - ipCache.at < 5 * 60 * 1000) return ipCache.ip;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 4000);
  try {
    const r = await fetch('https://api.ipify.org?format=json', { signal: controller.signal });
    if (!r.ok) return null;
    const data = await r.json();
    const ip = String(data?.ip || '').trim() || null;
    if (ip) ipCache = { at: Date.now(), ip };
    return ip;
  } finally {
    clearTimeout(timer);
  }
}

function baseHeaders(apiKey, jwt, registeredPublicIp) {
  return {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': `Bearer ${jwt}`,
    'X-PrivateKey': apiKey,
    'X-UserType': 'USER',
    'X-SourceID': 'WEB',
    'X-ClientLocalIP': '127.0.0.1',
    'X-ClientPublicIP': registeredPublicIp,
    'X-MACAddress': '00:00:00:00:00:00'
  };
}

app.get('/health', async (_, res) => {
  const ip = await actualPublicIp(true).catch(() => null);
  res.status(ip === EXPECTED_PUBLIC_IP ? 200 : 503).json({
    ok: ip === EXPECTED_PUBLIC_IP,
    service: 'DhanPulse Angel Order Relay',
    expectedPublicIp: EXPECTED_PUBLIC_IP,
    actualPublicIp: ip,
    ready: ip === EXPECTED_PUBLIC_IP
  });
});

app.post('/api/angel/order', async (req, res) => {
  try {
    if (!RELAY_SECRET || req.get('X-Relay-Secret') !== RELAY_SECRET) {
      return res.status(401).json({ ok: false, error: 'Relay authentication failed' });
    }

    const ip = await actualPublicIp(true);
    if (ip !== EXPECTED_PUBLIC_IP) {
      return res.status(503).json({
        ok: false,
        error: `Relay egress IP ${ip || 'unknown'} does not match expected ${EXPECTED_PUBLIC_IP}`
      });
    }

    const { apiKey, jwt, registeredPublicIp, order } = req.body || {};
    if (registeredPublicIp && registeredPublicIp !== EXPECTED_PUBLIC_IP) {
      return res.status(400).json({ ok: false, error: 'Registered IP does not match the relay outbound IP.' });
    }
    if (!apiKey || !jwt || !order) {
      return res.status(400).json({ ok: false, error: 'Incomplete relay order request' });
    }

    const r = await fetch('https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/placeOrder', {
      method: 'POST',
      headers: baseHeaders(apiKey, jwt, registeredPublicIp || EXPECTED_PUBLIC_IP),
      body: JSON.stringify(order)
    });

    const raw = await r.text();
    let data;
    try { data = JSON.parse(raw); }
    catch { return res.status(502).json({ ok: false, error: `Angel returned non-JSON (${r.status})` }); }

    if (!r.ok || data?.status === false) {
      return res.status(r.ok ? 400 : r.status).json({ ok: false, error: data?.message || data?.error || 'Angel order failed', angel: data });
    }

    res.json({ ok: true, angel: data });
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message || 'Relay failed' });
  }
});

app.post('/api/angel/candles', async (req, res) => {
  try {
    if (!RELAY_SECRET || req.get('X-Relay-Secret') !== RELAY_SECRET) {
      return res.status(401).json({ ok: false, error: 'Relay authentication failed' });
    }
    const ip = await actualPublicIp(true);
    if (ip !== EXPECTED_PUBLIC_IP) {
      return res.status(503).json({ ok: false, error: 'Relay outbound IP is not the registered IP.' });
    }
    const { apiKey, jwt, payload } = req.body || {};
    const valid = apiKey && jwt && payload &&
      ['NSE', 'BSE', 'NFO', 'BFO', 'MCX'].includes(payload.exchange) &&
      /^\d+$/.test(String(payload.symboltoken || '')) &&
      ['ONE_MINUTE', 'THREE_MINUTE', 'FIVE_MINUTE', 'TEN_MINUTE', 'FIFTEEN_MINUTE', 'ONE_DAY'].includes(payload.interval) &&
      /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(String(payload.fromdate || '')) &&
      /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(String(payload.todate || ''));
    if (!valid) return res.status(400).json({ ok: false, error: 'Invalid candle request.' });

    const response = await fetch('https://apiconnect.angelone.in/rest/secure/angelbroking/historical/v1/getCandleData', {
      method: 'POST', headers: baseHeaders(apiKey, jwt, EXPECTED_PUBLIC_IP),
      body: JSON.stringify(payload)
    });
    const raw = await response.text();
    let candles;
    try { candles = JSON.parse(raw); }
    catch {
      const reason = raw.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 160);
      return res.status(response.status === 403 ? 403 : 502).json({
        ok: false, error: `Broker returned HTTP ${response.status}${reason ? ': ' + reason : ''}`
      });
    }
    if (!response.ok || candles?.status === false) {
      return res.status(response.ok ? 502 : response.status).json({
        ok: false, error: String(candles?.message || 'Broker candle request failed').slice(0, 160)
      });
    }
    res.json({ ok: true, candles });
  } catch {
    res.status(502).json({ ok: false, error: 'Broker candle relay unavailable.' });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`DhanPulse order relay listening on ${PORT}; expected egress ${EXPECTED_PUBLIC_IP}`);
});
