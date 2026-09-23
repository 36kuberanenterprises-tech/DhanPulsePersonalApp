import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import crypto from 'crypto';
import { login, profile, rmsLimit, positions, placeOrder, instrumentMaster } from './angel.js';
import { analyse } from './analysis.js';
import { runBacktest } from './backtest.js';

const app = express();
app.use(cors());
app.use(express.json({ limit: '256kb' }));

const sessions = new Map();
const analysisCache = new Map();
const sessionTtl = 14 * 60 * 60 * 1000;

app.get('/', (_, res) => res.json({ ok: true, service: 'DhanPulse Personal API', status: 'live', mode: 'analysis-manual-auto-backtest', registeredPublicIp: process.env.CLIENT_PUBLIC_IP || '34.70.199.153' }));
app.get('/health', (_, res) => res.json({ ok: true, service: 'DhanPulse Personal API', status: 'live', mode: 'analysis-manual-auto-backtest', registeredPublicIp: process.env.CLIENT_PUBLIC_IP || '34.70.199.153' }));

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
  const interval = String(req.query.interval || 'FIVE_MINUTE').toUpperCase();
  const allowed = ['ONE_MINUTE','THREE_MINUTE','FIVE_MINUTE','TEN_MINUTE','FIFTEEN_MINUTE'];
  if (!allowed.includes(interval)) return res.status(400).json({ error: 'Unsupported interval' });

  const sessionId = req.header('X-Session-Id');
  const key = sessionId + '|' + String(req.params.symbol || '').toUpperCase() + '|' + interval;

  try {
    const result = await analyse(req.smartSession, req.params.symbol, interval);
    analysisCache.set(key, { at: Date.now(), value: result });
    res.json(result);
  } catch (e) {
    console.error('Analysis refresh failed:', e?.message || e);
    const cached = analysisCache.get(key);
    if (cached && Date.now() - cached.at <= 2 * 60 * 1000) {
      const value = {
        ...cached.value,
        timestamp: new Date().toISOString(),
        notes: [
          ...(cached.value.notes || []),
          'Latest broker refresh was temporarily unavailable. Showing the most recent successful analysis.'
        ]
      };
      return res.json(value);
    }
    res.status(503).json({ error: e.message || 'Live analysis temporarily unavailable. Please retry.' });
  }
});


function n(value) {
  const x = Number(value ?? 0);
  return Number.isFinite(x) ? x : 0;
}

function summarizeAccount(rmsRaw, posRaw) {
  const rms = rmsRaw?.data || {};
  const rows = Array.isArray(posRaw?.data) ? posRaw.data : [];

  const positionRows = rows.map(p => {
    const buyQty = n(p.buyqty);
    const sellQty = n(p.sellqty);
    const netQty = n(p.netqty ?? p.netquantity ?? (buyQty - sellQty));
    const realized = n(p.realised ?? p.realized);
    const unrealized = n(p.unrealised ?? p.unrealized);
    const pnl = Number.isFinite(Number(p.pnl)) ? Number(p.pnl) : realized + unrealized;
    return {
      exchange: p.exchange || null,
      token: String(p.symboltoken || p.token || ''),
      tradingSymbol: p.tradingsymbol || null,
      productType: p.producttype || null,
      netQty,
      buyQty,
      sellQty,
      buyAvgPrice: n(p.buyavgprice),
      sellAvgPrice: n(p.sellavgprice),
      ltp: n(p.ltp),
      realizedPnl: realized,
      unrealizedPnl: unrealized,
      pnl
    };
  });

  const realizedPnl = positionRows.reduce((s, p) => s + p.realizedPnl, 0);
  const unrealizedPnl = positionRows.reduce((s, p) => s + p.unrealizedPnl, 0);
  const totalPnl = positionRows.reduce((s, p) => s + p.pnl, 0);

  return {
    availableCash: n(rms.availablecash),
    net: n(rms.net),
    utilizedDebits: n(rms.utiliseddebits),
    availableLimitMargin: n(rms.availablelimitmargin),
    realizedPnl,
    unrealizedPnl,
    totalPnl,
    positions: positionRows.filter(p => p.netQty !== 0 || Math.abs(p.pnl) > 0.0001)
  };
}

app.post('/api/backtest', requireSession, async (req, res) => {
  try {
    const body = req.body || {};
    const allowedIntervals = ['ONE_MINUTE','THREE_MINUTE','FIVE_MINUTE','TEN_MINUTE','FIFTEEN_MINUTE'];
    const symbol = String(body.symbol || 'NIFTY').toUpperCase();
    const interval = String(body.interval || 'FIVE_MINUTE').toUpperCase();
    const years = Number(body.years || 3);
    const capital = Number(body.capital || 20000);

    if (!['NIFTY','BANKNIFTY','SENSEX'].includes(symbol)) return res.status(400).json({ error: 'Unsupported symbol' });
    if (!allowedIntervals.includes(interval)) return res.status(400).json({ error: 'Unsupported interval' });
    if (![1,3,5].includes(years)) return res.status(400).json({ error: 'Backtest period must be 1, 3 or 5 years' });

    const result = await runBacktest(req.smartSession, { symbol, interval, years, capital });
    res.json(result);
  } catch (e) {
    console.error('Backtest failed:', e?.message || e);
    res.status(503).json({ error: e.message || 'Backtest failed' });
  }
});

app.get('/api/account', requireSession, async (req, res) => {
  try {
    const [rms, pos] = await Promise.all([
      rmsLimit(req.smartSession),
      positions(req.smartSession)
    ]);
    res.json(summarizeAccount(rms, pos));
  } catch (e) {
    console.error('Account refresh failed:', e?.message || e);
    res.status(503).json({ error: e.message || 'Account data temporarily unavailable' });
  }
});

app.post('/api/order', requireSession, async (req, res) => {
  try {
    const body = req.body || {};
    const side = String(body.side || '').toUpperCase();
    const token = String(body.token || '').trim();
    const tradingSymbol = String(body.tradingSymbol || '').trim();
    const exchange = String(body.exchange || '').trim().toUpperCase();
    const lots = Math.max(1, Math.min(20, Math.floor(Number(body.lots || 1))));

    if (!['BUY', 'SELL'].includes(side)) return res.status(400).json({ error: 'side must be BUY or SELL' });
    if (!token || !tradingSymbol || !exchange) return res.status(400).json({ error: 'Option contract is incomplete' });

    const rows = await instrumentMaster();
    const contract = rows.find(r =>
      String(r.token) === token &&
      String(r.symbol || '').toUpperCase() === tradingSymbol.toUpperCase() &&
      String(r.exch_seg || '').toUpperCase() === exchange &&
      /OPT/i.test(String(r.instrumenttype || ''))
    );
    if (!contract) return res.status(400).json({ error: 'Selected option contract is not valid in the instrument master' });

    const lotSize = Math.max(1, Math.floor(Number(contract.lotsize || 1)));
    const quantity = lotSize * lots;

    if (side === 'SELL') {
      const pos = await positions(req.smartSession);
      const current = (Array.isArray(pos?.data) ? pos.data : []).find(p => String(p.symboltoken || p.token) === token);
      const buyQty = n(current?.buyqty);
      const sellQty = n(current?.sellqty);
      const netQty = n(current?.netqty ?? current?.netquantity ?? (buyQty - sellQty));
      if (netQty <= 0) return res.status(400).json({ error: 'SELL is enabled only to exit an existing long option position. No long position found.' });
      if (quantity > netQty) return res.status(400).json({ error: `Exit quantity ${quantity} is higher than current long quantity ${netQty}` });
    }

    const orderPayload = {
      variety: 'NORMAL',
      tradingsymbol: tradingSymbol,
      symboltoken: token,
      transactiontype: side,
      exchange,
      ordertype: 'MARKET',
      producttype: 'INTRADAY',
      duration: 'DAY',
      price: '0',
      squareoff: '0',
      stoploss: '0',
      quantity: String(quantity)
    };

    const order = await placeOrder(req.smartSession, orderPayload);
    let account = null;
    try {
      const [rms, pos] = await Promise.all([rmsLimit(req.smartSession), positions(req.smartSession)]);
      account = summarizeAccount(rms, pos);
    } catch {}

    res.json({
      ok: true,
      side,
      lots,
      quantity,
      lotSize,
      tradingSymbol,
      orderId: order?.data?.orderid || null,
      uniqueOrderId: order?.data?.uniqueorderid || null,
      message: order?.message || 'Order submitted',
      account
    });
  } catch (e) {
    console.error('Order failed:', e?.message || e);
    res.status(400).json({ error: e.message || 'Order failed' });
  }
});

app.post('/api/auth/logout', requireSession, (req, res) => {
  const id = req.header('X-Session-Id');
  sessions.delete(id);
  for (const key of analysisCache.keys()) if (key.startsWith(id + '|')) analysisCache.delete(key);
  res.json({ ok: true });
});

setInterval(() => {
  for (const [id, s] of sessions) if (Date.now() - s.createdAt > sessionTtl) sessions.delete(id);
}, 30 * 60 * 1000).unref();

const port = Number(process.env.PORT || 8787);
app.listen(port, () => console.log(`DhanPulse Personal API running on :${port}`));
