import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import crypto from 'crypto';
import { login, profile } from './angel.js';
import { analyse } from './analysis.js';

const app = express();
app.use(cors());
app.use(express.json({ limit: '256kb' }));

const sessions = new Map();
const sessionTtl = 14 * 60 * 60 * 1000;

app.get('/health', (_, res) => res.json({ ok: true, service: 'DhanPulse Personal API', mode: 'analysis-only' }));

app.post('/api/auth/login', async (req, res) => {
  try {
    const { apiKey, clientCode, pin, totp } = req.body || {};
    const resolvedApiKey = String(process.env.ANGEL_API_KEY || apiKey || '').trim();
    const resolvedClientCode = String(process.env.ANGEL_CLIENT_CODE || clientCode || '').trim();
    if (![resolvedApiKey, resolvedClientCode, pin, totp].every(x => String(x || '').trim())) {
      return res.status(400).json({ error: 'SmartAPI setup missing. Configure ANGEL_API_KEY and ANGEL_CLIENT_CODE on the server, then enter PIN and TOTP.' });
    }
    const r = await login({ apiKey: resolvedApiKey, clientCode: resolvedClientCode, pin: String(pin), totp: String(totp).trim() });
    const data = r.data || {};
    const session = { apiKey: resolvedApiKey, clientCode: resolvedClientCode, jwt: data.jwtToken, refreshToken: data.refreshToken, feedToken: data.feedToken, createdAt: Date.now() };
    const id = crypto.randomUUID();
    sessions.set(id, session);
    let p = null;
    try { p = await profile(session); } catch {}
    res.json({ sessionId: id, expiresAt: new Date(Date.now() + sessionTtl).toISOString(), profile: p?.data || { clientcode: resolvedClientCode } });
  } catch (e) { res.status(401).json({ error: e.message }); }
});

function requireSession(req, res, next) {
  const id = req.header('X-Session-Id');
  const s = sessions.get(id);
  if (!s) return res.status(401).json({ error: 'Login required' });
  if (Date.now() - s.createdAt > sessionTtl) { sessions.delete(id); return res.status(401).json({ error: 'Session expired. Login again.' }); }
  req.smartSession = s; next();
}

app.get('/api/analysis/:symbol', requireSession, async (req, res) => {
  try {
    const interval = String(req.query.interval || 'FIVE_MINUTE').toUpperCase();
    const allowed = ['ONE_MINUTE','THREE_MINUTE','FIVE_MINUTE','TEN_MINUTE','FIFTEEN_MINUTE'];
    if (!allowed.includes(interval)) return res.status(400).json({ error: 'Unsupported interval' });
    res.json(await analyse(req.smartSession, req.params.symbol, interval));
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/auth/logout', requireSession, (req, res) => {
  const id = req.header('X-Session-Id'); sessions.delete(id); res.json({ ok: true });
});

setInterval(() => {
  for (const [id, s] of sessions) if (Date.now() - s.createdAt > sessionTtl) sessions.delete(id);
}, 30 * 60 * 1000).unref();

const port = Number(process.env.PORT || 8787);
app.listen(port, () => console.log(`DhanPulse Personal API running on :${port}`));
