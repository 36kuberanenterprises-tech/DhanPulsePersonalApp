import test from 'node:test';
import assert from 'node:assert/strict';
import { parseAngelLtpPacket, streamInstrument } from '../src/live-stream.js';

function packet({ token = '99926000', exchange = 1, price = 2500150, time = Date.now() } = {}) {
  const bytes = Buffer.alloc(51);
  bytes.writeUInt8(1, 0);
  bytes.writeUInt8(exchange, 1);
  bytes.write(token, 2, 'utf8');
  bytes.writeBigInt64LE(1n, 27);
  bytes.writeBigInt64LE(BigInt(time), 35);
  bytes.writeBigInt64LE(BigInt(price), 43);
  return bytes;
}

test('Angel binary ticks decode price and exchange time without using arrival time as a substitute', () => {
  const time = Date.now() - 1000;
  assert.deepEqual(parseAngelLtpPacket(packet({ time })), {
    exchangeType: 1, token: '99926000', price: 25001.5, exchangeTimestamp: time
  });
  assert.equal(parseAngelLtpPacket(packet({ time: 0 })), null);
  assert.equal(parseAngelLtpPacket(packet({ price: 0 })), null);
  assert.equal(parseAngelLtpPacket(Buffer.alloc(20)), null);
});

test('stream subscription accepts only a broker market token and its actual exchange', () => {
  assert.deepEqual(streamInstrument({ exch_seg: 'BSE', token: '99919000' }), { exchangeType: 3, token: '99919000' });
  assert.deepEqual(streamInstrument({ exch_seg: 'MCX', token: '23456' }), { exchangeType: 5, token: '23456' });
  assert.throws(() => streamInstrument({ exch_seg: 'NSE', token: '../../bad' }));
});
