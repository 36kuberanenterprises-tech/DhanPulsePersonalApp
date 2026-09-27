from pathlib import Path
import re, json

ROOT = Path(__file__).resolve().parent
SERVICE = ROOT / "app/src/main/java/com/dhanpulse/cryptofxnative/BackgroundService.java"
ACTIVITY = ROOT / "app/src/main/java/com/dhanpulse/cryptofxnative/MainActivity.java"
GRADLE = ROOT / "app/build.gradle.kts"
INDEX = ROOT / "app/src/main/assets/index.html"


def replace_method(text, signature, new_method):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f"Method not found: {signature}")
    brace = text.find("{", start)
    depth = 0
    in_str = None
    esc = False
    end = None
    for i in range(brace, len(text)):
        ch = text[i]
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == in_str: in_str = None
            continue
        if ch in ('"', "'"):
            in_str = ch
            continue
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise SystemExit(f"Method end not found: {signature}")
    return text[:start] + new_method.rstrip() + text[end:]

s = SERVICE.read_text(encoding="utf-8")

# Separate genuine WebSocket freshness from generic price freshness. In older builds
# REST backup refreshed lastTickReceived, which accidentally hid a dead WebSocket
# from the watchdog forever. Since new entries require WS TRADE, this could leave
# the app alive but unable to record any signal.
s = s.replace(
    '    private volatile long lastTickReceived = 0L;\n    private volatile long lastExchangeEvent = 0L;',
    '    private volatile long lastTickReceived = 0L;\n'
    '    private volatile long lastWsTradeReceived = 0L;\n'
    '    private volatile long lastSocketOpenedAt = 0L;\n'
    '    private volatile long lastReconnectAttempt = 0L;\n'
    '    private volatile String wsEndpointMode = "RAW SUBSCRIBE";\n'
    '    private volatile long lastExchangeEvent = 0L;',
    1
)

# Reset WS-specific state when a fresh connection cycle begins.
s = s.replace(
    '        feedMode = "CONNECTING";\n        signalState = "MONITORING";',
    '        feedMode = "CONNECTING";\n'
    '        signalState = "MONITORING";\n'
    '        lastWsTradeReceived = 0L;\n'
    '        lastSocketOpenedAt = 0L;',
    1
)

new_open = r'''    private void openSocket(int gen) {
        String lower = symbol.toLowerCase(Locale.US);
        ArrayList<String> params = new ArrayList<>();
        params.add(lower + "@aggTrade");
        params.add(lower + "@depth20@100ms");
        params.add(lower + "@markPrice@1s");
        params.add(lower + "@kline_1m");
        params.add(lower + "@kline_15m");
        params.add(lower + "@kline_1h");
        String selected = lower + "@kline_" + tf;
        if (!params.contains(selected)) params.add(selected);

        boolean rawMode = (reconnects % 2 == 0);
        wsEndpointMode = rawMode ? "RAW SUBSCRIBE" : "COMBINED";
        String url;
        if (rawMode) {
            url = "wss://fstream.binance.com/ws";
        } else {
            StringBuilder streams = new StringBuilder();
            for (String p : params) {
                if (streams.length() > 0) streams.append('/');
                streams.append(p);
            }
            url = "wss://fstream.binance.com/stream?streams=" + streams;
        }

        Request req = new Request.Builder().url(url).build();
        socket = client.newWebSocket(req, new WebSocketListener() {
            @Override
            public void onOpen(WebSocket webSocket, Response response) {
                if (gen != generation.get()) return;
                lastSocketOpenedAt = System.currentTimeMillis();
                feedMode = "WS OPEN · " + wsEndpointMode;
                if (rawMode) {
                    try {
                        JSONObject sub = new JSONObject();
                        sub.put("method", "SUBSCRIBE");
                        JSONArray arr = new JSONArray();
                        for (String p : params) arr.put(p);
                        sub.put("params", arr);
                        sub.put("id", 215);
                        webSocket.send(sub.toString());
                    } catch (Exception ignored) {}
                }
                writeHeartbeat();
            }

            @Override
            public void onMessage(WebSocket webSocket, String text) {
                if (gen != generation.get()) return;
                engine.execute(() -> processSocketMessage(text));
            }

            @Override
            public void onFailure(WebSocket webSocket, Throwable t, Response response) {
                if (gen != generation.get()) return;
                feedMode = "WS FAILED · " + wsEndpointMode;
                reconnects++;
                long delay = Math.min(15000, 1200L * Math.max(1, Math.min(10, reconnects)));
                handler.postDelayed(() -> engine.execute(() -> {
                    if (gen == generation.get()) reconnectNow("websocket failure");
                }), delay);
            }

            @Override
            public void onClosed(WebSocket webSocket, int code, String reason) {
                if (gen != generation.get()) return;
                feedMode = "WS CLOSED · " + wsEndpointMode;
                reconnects++;
                handler.postDelayed(() -> engine.execute(() -> {
                    if (gen == generation.get()) reconnectNow("websocket closed");
                }), 1500);
            }
        });
    }'''
s = replace_method(s, '    private void openSocket(int gen)', new_open)

new_process_socket = r'''    private void processSocketMessage(String text) {
        long startNs = System.nanoTime();
        try {
            JSONObject root = new JSONObject(text);
            // Raw subscription acknowledgements have only {result,id}.
            if (root.has("result") && root.has("id") && !root.has("e") && !root.has("stream")) return;

            String stream;
            JSONObject data;
            JSONObject wrapped = root.optJSONObject("data");
            if (root.has("stream") && wrapped != null) {
                stream = root.optString("stream", "");
                data = wrapped;
            } else {
                data = root;
                String ev = data.optString("e", "");
                String lower = symbol.toLowerCase(Locale.US);
                if ("aggTrade".equals(ev)) stream = lower + "@aggTrade";
                else if ("depthUpdate".equals(ev)) stream = lower + "@depth20@100ms";
                else if ("markPriceUpdate".equals(ev)) stream = lower + "@markPrice@1s";
                else if ("kline".equals(ev)) {
                    JSONObject k = data.optJSONObject("k");
                    if (k == null) return;
                    stream = lower + "@kline_" + k.optString("i", "1m");
                } else return;
            }

            if (stream.endsWith("@aggTrade")) {
                double price = data.optDouble("p", Double.NaN);
                double qty = data.optDouble("q", 0.0);
                long ts = data.optLong("T", data.optLong("E", System.currentTimeMillis()));
                boolean aggressiveBuy = !data.optBoolean("m", false);
                if (Double.isFinite(price)) processTick(price, qty, aggressiveBuy, ts, "WS TRADE");
            } else if (stream.contains("@depth20")) {
                JSONArray bids = data.optJSONArray("b");
                JSONArray asks = data.optJSONArray("a");
                double bidWeighted = 0.0, askWeighted = 0.0;
                if (bids != null) {
                    for (int j = 0; j < Math.min(20, bids.length()); j++) {
                        JSONArray row = bids.optJSONArray(j);
                        if (row == null || row.length() < 2) continue;
                        double p = row.optDouble(0, 0.0), q = row.optDouble(1, 0.0);
                        if (j == 0 && p > 0) bestBid = p;
                        double w = 1.0 / (1.0 + j * 0.35);
                        bidWeighted += Math.max(0.0, p * q) * w;
                    }
                }
                if (asks != null) {
                    for (int j = 0; j < Math.min(20, asks.length()); j++) {
                        JSONArray row = asks.optJSONArray(j);
                        if (row == null || row.length() < 2) continue;
                        double p = row.optDouble(0, 0.0), q = row.optDouble(1, 0.0);
                        if (j == 0 && p > 0) bestAsk = p;
                        double w = 1.0 / (1.0 + j * 0.35);
                        askWeighted += Math.max(0.0, p * q) * w;
                    }
                }
                double total = bidWeighted + askWeighted;
                if (total > 0) {
                    double rawDepth = (bidWeighted - askWeighted) / total;
                    addDepthSample(System.currentTimeMillis(), rawDepth);
                    orderBookImbalance = depthComposite();
                    lastDepthReceived = System.currentTimeMillis();
                }
                if (Double.isFinite(bestBid) && Double.isFinite(bestAsk) && bestBid > 0 && bestAsk >= bestBid) {
                    double mid = (bestBid + bestAsk) / 2.0;
                    spreadBps = mid > 0 ? (bestAsk - bestBid) / mid * 10000.0 : Double.NaN;
                }
            } else if (stream.contains("@markPrice")) {
                fundingRate = data.optDouble("r", fundingRate);
                double mark = data.optDouble("p", Double.NaN);
                if (Double.isFinite(mark) && !Double.isFinite(lastPrice)) lastPrice = mark;
            } else if (stream.contains("@kline_")) {
                JSONObject k = data.optJSONObject("k");
                if (k != null) processKline(k);
            }
        } catch (Exception ignored) {
        } finally {
            lastEngineMs = (System.nanoTime() - startNs) / 1_000_000.0;
        }
    }'''
s = replace_method(s, '    private void processSocketMessage(String text)', new_process_socket)

# REST may update price freshness, but it must not overwrite the genuine WS trade
# heartbeat. A later WS tick immediately returns the engine to WS TRADE mode.
old_tick = '''        lastPrice = price;
        lastTickReceived = now;
        lastExchangeEvent = exchangeTs;
        feedMode = source;'''
new_tick = '''        lastPrice = price;
        lastTickReceived = now;
        lastExchangeEvent = exchangeTs;
        if ("WS TRADE".equals(source)) {
            lastWsTradeReceived = now;
            feedMode = "WS TRADE";
        } else if (lastWsTradeReceived == 0L || now - lastWsTradeReceived > 2500L) {
            feedMode = source;
        }'''
if old_tick not in s:
    raise SystemExit('processTick freshness target not found')
s = s.replace(old_tick, new_tick, 1)

# Watch WebSocket age directly. Previously REST fallback kept lastTickReceived fresh,
# so the 10 second reconnect condition could never fire.
old_watch = '''            if (lastTickReceived == 0 || now - lastTickReceived > 2500) fetchRestPrice();
            if (lastTickReceived > 0 && now - lastTickReceived > 10000) {
                engine.execute(() -> reconnectNow("watchdog stale feed"));
            }'''
new_watch = '''            long wsRef = lastWsTradeReceived > 0 ? lastWsTradeReceived : lastSocketOpenedAt;
            long wsAge = wsRef > 0 ? now - wsRef : Long.MAX_VALUE;
            if (wsAge > 2500L) fetchRestPrice();
            if (wsAge > 7000L && now - lastReconnectAttempt > 6000L) {
                lastReconnectAttempt = now;
                engine.execute(() -> reconnectNow("watchdog stale WS trade feed"));
            }'''
if old_watch not in s:
    raise SystemExit('watchdog freshness target not found')
s = s.replace(old_watch, new_watch, 1)

# Persist both ages so the UI can reveal the actual reason entries are blocked.
s = s.replace(
    '                .putLong("last_tick_received", lastTickReceived)\n                .putLong("last_exchange_event", lastExchangeEvent)',
    '                .putLong("last_tick_received", lastTickReceived)\n'
    '                .putLong("last_ws_trade_received", lastWsTradeReceived)\n'
    '                .putLong("last_socket_opened_at", lastSocketOpenedAt)\n'
    '                .putString("ws_endpoint_mode", wsEndpointMode)\n'
    '                .putLong("last_exchange_event", lastExchangeEvent)',
    1
)
SERVICE.write_text(s, encoding="utf-8")

# Native state diagnostics.
a = ACTIVITY.read_text(encoding="utf-8")
a = a.replace(
    '                long tick = prefs.getLong("last_tick_received", 0);',
    '                long tick = prefs.getLong("last_tick_received", 0);\n'
    '                long wsTick = prefs.getLong("last_ws_trade_received", 0);',
    1
)
a = a.replace(
    '                o.put("tickAgeMs", tick > 0 ? Math.max(0, now - tick) : -1);',
    '                o.put("tickAgeMs", tick > 0 ? Math.max(0, now - tick) : -1);\n'
    '                o.put("wsAgeMs", wsTick > 0 ? Math.max(0, now - wsTick) : -1);\n'
    '                o.put("wsEndpointMode", prefs.getString("ws_endpoint_mode", ""));',
    1
)
a = a.replace('Native V2.1.4 · ', 'Native V2.1.5 · ')
ACTIVITY.write_text(a, encoding="utf-8")

# Visible labels and version.
h = INDEX.read_text(encoding="utf-8")
h = h.replace('Version 2.1.4 Native Authority', 'Version 2.1.5 WS Recovery')
h = h.replace('V2.1.4 Signals', 'V2.1.5 Signals')
h = h.replace('No V2.1.4 signals recorded yet.', 'No V2.1.5 signals recorded yet.')
h = h.replace('NATIVE V2.1.4', 'NATIVE V2.1.5')
INDEX.write_text(h, encoding="utf-8")

g = GRADLE.read_text(encoding="utf-8")
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 26', g)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.1.5"', g)
GRADLE.write_text(g, encoding="utf-8")

print('DhanPulse V2.1.5 genuine WebSocket recovery and trade trigger feed patch applied')
