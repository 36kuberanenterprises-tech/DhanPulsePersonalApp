import { WebSocket } from 'undici';

const BROKER_STREAM = 'wss://smartapisocket.angelone.in/smart-stream';
const EXCHANGE_TYPES = { NSE: 1, NFO: 2, BSE: 3, BFO: 4, MCX: 5 };

export function parseAngelLtpPacket(data) {
  const packet = Buffer.from(data);
  if (packet.length < 51 || ![1, 2, 3].includes(packet.readUInt8(0))) return null;
  const exchangeType = packet.readUInt8(1);
  const token = packet.subarray(2, 27).toString('utf8').split('\0')[0];
  const exchangeTimestamp = Number(packet.readBigInt64LE(35));
  const price = Number(packet.readBigInt64LE(43)) / 100;
  if (!/^\d{1,12}$/.test(token) || !Number.isFinite(price) || price <= 0 ||
      !Number.isSafeInteger(exchangeTimestamp) || exchangeTimestamp < Date.UTC(2020, 0, 1) ||
      exchangeTimestamp > Date.now() + 30_000) return null;
  return { exchangeType, token, price, exchangeTimestamp };
}

export function streamInstrument(row) {
  const exchange = row.exch_seg || row.exchange;
  const exchangeType = EXCHANGE_TYPES[exchange];
  const token = String(row.token || '');
  if (!exchangeType || !/^\d{1,12}$/.test(token)) throw new Error('Broker streaming token unavailable');
  return { exchangeType, token };
}

// One authenticated broker socket is opened for the active screen. The stream
// only updates a display price. It never produces signals or places orders.
export function openAngelPriceStream(session, instrument, onTick, onDone) {
  if (![session.jwt, session.apiKey, session.clientCode, session.feedToken].every(Boolean)) {
    throw new Error('Broker feed token unavailable. Login again to start the price stream.');
  }
  const ws = new WebSocket(BROKER_STREAM, {
    headers: {
      Authorization: session.jwt.replace(/^Bearer\s+/i, ''),
      'x-api-key': session.apiKey,
      'x-client-code': session.clientCode,
      'x-feed-token': session.feedToken
    }
  });
  ws.binaryType = 'arraybuffer';
  let closed = false;
  const heartbeat = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) ws.send('ping');
  }, 10_000);
  heartbeat.unref?.();
  ws.addEventListener('open', () => {
    ws.send(JSON.stringify({
      correlationID: 'dhanpulse1', action: 1,
      params: { mode: 1, tokenList: [{ exchangeType: instrument.exchangeType, tokens: [instrument.token] }] }
    }));
  });
  ws.addEventListener('message', event => {
    if (closed || typeof event.data === 'string') return;
    const deliver = data => {
      const tick = parseAngelLtpPacket(data);
      if (tick?.token === instrument.token && tick.exchangeType === instrument.exchangeType) onTick(tick);
    };
    if (event.data instanceof ArrayBuffer) deliver(event.data);
    else if (event.data?.arrayBuffer) event.data.arrayBuffer().then(deliver).catch(() => {});
  });
  const finish = () => {
    if (closed) return;
    closed = true;
    clearInterval(heartbeat);
    onDone();
  };
  ws.addEventListener('error', finish);
  ws.addEventListener('close', finish);
  return () => {
    if (closed) return;
    closed = true;
    clearInterval(heartbeat);
    ws.close();
  };
}
