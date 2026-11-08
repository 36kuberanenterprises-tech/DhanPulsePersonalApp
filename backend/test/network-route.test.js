import test from 'node:test';
import assert from 'node:assert/strict';
import { ipMatchesRegistered, probeRelayHealth } from '../src/network-route.js';

test('verified backend IP matches primary or secondary, not a claimed header', () => {
  assert.equal(ipMatchesRegistered('34.70.199.153', '34.70.199.153', '74.220.52.132'), true);
  assert.equal(ipMatchesRegistered('74.220.52.132', '34.70.199.153', '74.220.52.132'), true);
  assert.equal(ipMatchesRegistered('216.24.60.99', '34.70.199.153', '74.220.52.132'), false);
  assert.equal(ipMatchesRegistered(null, '34.70.199.153', null), false);
});

test('relay must prove a registered actual source IP from its health check', async () => {
  const f = async () => new Response(JSON.stringify({
    ok: true, ready: true, expectedPublicIp: '34.70.199.153',
    actualPublicIp: '34.70.199.153'
  }), { status: 200, headers: { 'content-type': 'application/json' } });
  const result = await probeRelayHealth('https://relay.example.org/', '34.70.199.153', null, f);
  assert.equal(result.status, 'RELAY_IP_VERIFIED');
  assert.equal(result.ip, '34.70.199.153');
});

test('relay mismatch and malformed URLs fail closed', async () => {
  const mismatched = async () => new Response(JSON.stringify({
    ok: true, ready: true, expectedPublicIp: '34.70.199.153',
    actualPublicIp: '216.24.60.99'
  }), { status: 200 });
  const x = await probeRelayHealth('https://relay.example.org', '34.70.199.153', null, mismatched);
  assert.equal(x.status, 'RELAY_IP_NOT_VERIFIED');
  const y = await probeRelayHealth('http://relay.example.org', '34.70.199.153', null);
  assert.equal(y.status, 'RELAY_URL_NOT_HTTPS');
  const unavailable = await probeRelayHealth('https://relay.example.org', '34.70.199.153', null,
    async () => { throw new Error('unavailable'); });
  assert.equal(unavailable.status, 'RELAY_UNREACHABLE');
});
