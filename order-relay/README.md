# DhanPulse Order Relay

Run this only on the server that actually owns public IP 34.70.199.153.

Required environment variables:
- ORDER_RELAY_SECRET=<long random secret>
- CLIENT_PUBLIC_IP=34.70.199.153
- PORT=8787

Start:
npm install
npm start

Verify:
GET /health must return actualEgressIp = 34.70.199.153 and ready = true.

Then point the Render backend to this relay with ORDER_RELAY_URL and the same ORDER_RELAY_SECRET.
