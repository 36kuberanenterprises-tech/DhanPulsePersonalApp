const relayEndpoint = (rawUrl, path) => {
  const url = new URL(String(rawUrl || '').trim());
  if (url.protocol !== 'https:') throw new Error('Broker relay requires HTTPS.');
  return url.href.replace(/\/$/, '') + path;
};

export async function probeOrderRelay(relayUrl, secret, registeredIps, fetcher = fetch) {
  if (!secret) return { ready: false, status: 'RELAY_SECRET_MISSING', message: 'Order relay secret is missing.', host: null, ip: null };
  let endpoint;
  try { endpoint = relayEndpoint(relayUrl, '/health'); }
  catch { return { ready: false, status: 'RELAY_URL_INVALID', message: 'Order relay must have a valid HTTPS URL.', host: null, ip: null }; }
  const host = new URL(endpoint).host;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 4000);
  try {
    const response = await fetcher(endpoint, { signal: controller.signal });
    const data = await response.json();
    const ip = String(data?.actualPublicIp || data?.actualEgressIp || '').trim();
    const expected = String(data?.expectedPublicIp || data?.registeredIp || '').trim();
    const ready = response.ok && data?.ready === true && ip && ip === expected && registeredIps.includes(ip);
    return ready
      ? { ready: true, status: 'READY', message: 'Verified static-IP order relay is ready.', host, ip }
      : { ready: false, status: 'RELAY_IP_UNVERIFIED',
          message: 'Order relay health did not verify an Angel One registered outbound IP.', host, ip: ip || null };
  } catch {
    return { ready: false, status: 'RELAY_UNAVAILABLE',
      message: 'Order relay health is unavailable. Live orders remain blocked.', host, ip: null };
  } finally { clearTimeout(timer); }
}

export async function requestCandleViaRelay(relayUrl, secret, session, payload, fetcher = fetch) {
  if (!secret) throw new Error('Candle data: broker relay secret is missing.');
  const url = relayEndpoint(relayUrl, '/api/angel/candles');
  const response = await fetcher(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Relay-Secret': secret },
    body: JSON.stringify({ apiKey: session.apiKey, jwt: session.jwt, payload })
  });
  const raw = await response.text();
  let data;
  try { data = JSON.parse(raw); }
  catch { throw new Error(`Candle data: relay returned a non-JSON response (${response.status}).`); }
  if (!response.ok || data?.ok !== true || data?.candles?.status === false) {
    throw new Error(`Candle data: ${String(data?.error || data?.candles?.message || 'relay request failed').slice(0, 160)} (HTTP ${response.status}).`);
  }
  return data.candles;
}
