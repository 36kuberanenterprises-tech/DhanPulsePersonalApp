import express from 'express';

const app = express();
app.use(express.json({ limit: '100kb' }));

const PORT = Number(process.env.PORT || 8787);
const RELAY_SECRET = String(process.env.ORDER_RELAY_SECRET || '').trim();
const REGISTERED_IP = String(process.env.CLIENT_PUBLIC_IP || '34.70.199.153').trim();
const ROOT = 'https://apiconnect.angelone.in';

if (!RELAY_SECRET) {
  console.error('ORDER_RELAY_SECRET is required');
  process.exit(1);
}

function headers(apiKey, jwt) {
  return {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-PrivateKey': apiKey,
    'X-UserType': 'USER',
    'X-SourceID': 'WEB',
    'X-ClientLocalIP': '127.0.0.1',
    'X-ClientPublicIP': REGISTERED_IP,
    'X-MACAddress': '00:00:00:00:00:00',
    'Authorization': 'Bearer ' + jwt
  };
}

async function externalIp() {
  try {
    const r = await fetch('https://api.ipify.org?format=json');
    if (!r.ok) return null;
    return (await r.json())?.ip || null;
  } catch {
    return null;
  }
}

app.get('/health', async (_req, res) => {
  const ip = await externalIp();
  res.json({
    ok: true,
    service: 'DhanPulse Order Relay',
    registeredIp: REGISTERED_IP,
    actualEgressIp: ip,
    ready: ip === REGISTERED_IP
  });
});

app.post('/api/angel/order', async (req, res) => {
  if (String(req.headers['x-relay-secret'] || '') !== RELAY_SECRET) {
    return res.status(401).json({ ok:false, error:'Unauthorized relay request' });
  }

  const { apiKey, jwt, order } = req.body || {};
  if (!apiKey || !jwt || !order) {
    return res.status(400).json({ ok:false, error:'Missing apiKey, jwt or order payload' });
  }

  const actualIp = await externalIp();
  if (actualIp !== REGISTERED_IP) {
    return res.status(503).json({
      ok:false,
      error:`Relay egress IP ${actualIp || 'unknown'} does not match registered IP ${REGISTERED_IP}`
    });
  }

  try {
    const r = await fetch(ROOT + '/rest/secure/angelbroking/order/v1/placeOrder', {
      method:'POST',
      headers:headers(apiKey, jwt),
      body:JSON.stringify(order)
    });
    const text = await r.text();
    let data;
    try { data = JSON.parse(text); }
    catch { return res.status(502).json({ ok:false, error:`Angel returned non-JSON response (${r.status})` }); }

    if (!r.ok || data?.status === false) {
      return res.status(400).json({ ok:false, error:data?.message || data?.error || 'Angel order failed', angel:data });
    }
    return res.json({ ok:true, angel:data, actualEgressIp:actualIp });
  } catch (e) {
    return res.status(502).json({ ok:false, error:e.message || 'Relay order failed' });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`DhanPulse Order Relay listening on ${PORT}`);
});
