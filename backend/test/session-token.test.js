import test from 'node:test';
import assert from 'node:assert/strict';
import { sealSession, openSession } from '../src/session-token.js';

test('encrypted session survives an in-memory reset and rejects modification and expiry', () => {
  const previous = process.env.SESSION_ENCRYPTION_KEY;
  process.env.SESSION_ENCRYPTION_KEY = 'a'.repeat(64);
  try {
    const now = Date.now();
    const session = { apiKey: 'key', clientCode: 'client', jwt: 'broker-token', createdAt: now,
      expiresAt: now + 60_000 };
    const token = sealSession(session);
    assert.deepEqual(openSession(token), session);
    assert.ok(!token.includes('broker-token'));
    assert.equal(openSession(token.replace('v1.', 'v2.')), null);
    const parts = token.split('.');
    const alteredCiphertext = Buffer.from(parts[2], 'base64url');
    alteredCiphertext[0] ^= 1;
    assert.equal(openSession([parts[0], parts[1], alteredCiphertext.toString('base64url'), parts[3]].join('.')), null);
    assert.equal(openSession(sealSession({ ...session, expiresAt: now - 1 })), null);
  } finally {
    if (previous == null) delete process.env.SESSION_ENCRYPTION_KEY;
    else process.env.SESSION_ENCRYPTION_KEY = previous;
  }
});
