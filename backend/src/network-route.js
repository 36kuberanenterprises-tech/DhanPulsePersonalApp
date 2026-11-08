import { isIP } from 'node:net';
import { ProxyAgent, request as undiciRequest } from 'undici';

// These probes make read-only requests. They never submit broker orders,
// change registered IPs, or treat a declared X-ClientPublicIP header as proof.
export function ipMatchesRegistered(observed, primary, secondary = null) {
  return isIP(String(observed || '')) === 4 &&
    [primary, secondary].filter(Boolean).includes(observed);
}

export async function probeRelayHealth(relayUrl, primary, secondary, fetcher = fetch) {
  let healthUrl;
  try {
    const origin = new URL(relayUrl);
    if (origin.protocol !== 'https:') return { status: 'RELAY_URL_NOT_HTTPS', ip: null };
    healthUrl = new URL('/health', origin).toString();
  } catch { return { status: 'INVALID_RELAY_URL', ip: null }; }
  try {
    const response = await fetcher(healthUrl, {
      method: 'GET', headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(4500)
    });
    const payload = await response.json();
    const ip = String(payload?.actualPublicIp || '');
    if (response.ok && payload?.ok === true && payload?.ready === true &&
      ipMatchesRegistered(ip, primary, secondary) && payload.expectedPublicIp === ip) {
      return { status: 'RELAY_IP_VERIFIED', ip };
    }
    return { status: 'RELAY_IP_NOT_VERIFIED', ip: isIP(ip) === 4 ? ip : null };
  } catch { return { status: 'RELAY_UNREACHABLE', ip: null }; }
}

export async function probeProxyEgress(proxyUrl) {
  let dispatcher;
  try {
    dispatcher = new ProxyAgent(proxyUrl);
    const r = await undiciRequest('https://api.ipify.org?format=json', {
      method: 'GET', dispatcher, headersTimeout: 4500, bodyTimeout: 4500,
      signal: AbortSignal.timeout(5000)
    });
    if (r.statusCode !== 200) {
      await r.body.text();
      return null;
    }
    const body = await r.body.json();
    const ip = String(body?.ip || '');
    return isIP(ip) === 4 ? ip : null;
  } catch { return null; }
  finally { if (dispatcher) await dispatcher.close().catch(() => {}); }
}
