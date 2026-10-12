# DhanPulse static IP relay

The active entry point is `src/server.js` (`npm start`). Run it only on a
server that actually sends broker traffic from the registered static IP.

Required environment variables:
- `ORDER_RELAY_SECRET`: a long random shared secret
- `CLIENT_PUBLIC_IP`: the public IP registered with Angel One
- `PORT`: listener port (defaults to 8080)

Expose the relay to the backend through HTTPS. Before configuring it, check
`GET /health`: `ready` must be true and `actualPublicIp` must match
`expectedPublicIp`. The relay checks its outbound IP again before forwarding
an order or historical candle request.

On the Render backend, set `ORDER_RELAY_URL` to that HTTPS endpoint and set
the same `ORDER_RELAY_SECRET`. Both order and candle requests then use the
relay. `HISTORY_RELAY_URL` and `HISTORY_RELAY_SECRET` can override the history
route if a separate static host is used. Do not configure a relay URL until
the static host, TLS and health check are ready.

A verified IP route is necessary for the configured route; it does not
guarantee Angel One will accept historical candles. If the broker returns 403,
new calls stay paused and the broker error remains visible.
