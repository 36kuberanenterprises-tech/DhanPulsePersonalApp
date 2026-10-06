import crypto from 'crypto';

function encryptionKey() {
  const raw = process.env.SESSION_ENCRYPTION_KEY || '';
  if (!/^[0-9a-f]{64}$/i.test(raw)) throw new Error('SESSION_ENCRYPTION_KEY must be a 64 character hex secret');
  return Buffer.from(raw, 'hex');
}

export function sealSession(session) {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', encryptionKey(), iv);
  const encrypted = Buffer.concat([cipher.update(JSON.stringify(session), 'utf8'), cipher.final()]);
  return `v1.${iv.toString('base64url')}.${encrypted.toString('base64url')}.${cipher.getAuthTag().toString('base64url')}`;
}

export function openSession(token) {
  if (typeof token !== 'string' || token.length > 4096) return null;
  const parts = token.split('.');
  if (parts.length !== 4 || parts[0] !== 'v1') return null;
  try {
    const iv = Buffer.from(parts[1], 'base64url');
    const tag = Buffer.from(parts[3], 'base64url');
    if (iv.length !== 12 || tag.length !== 16) return null;
    const decipher = crypto.createDecipheriv('aes-256-gcm', encryptionKey(), iv);
    decipher.setAuthTag(tag);
    const plain = Buffer.concat([decipher.update(Buffer.from(parts[2], 'base64url')), decipher.final()]);
    const s = JSON.parse(plain.toString('utf8'));
    if (!s || !s.apiKey || !s.clientCode || !s.jwt ||
        !Number.isFinite(s.expiresAt) || !Number.isFinite(s.createdAt) ||
        s.expiresAt <= Date.now() || s.createdAt > Date.now() + 30_000 ||
        s.expiresAt - s.createdAt > 25 * 60 * 60_000) return null;
    return s;
  } catch { return null; }
}
