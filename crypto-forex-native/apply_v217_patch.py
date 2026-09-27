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
    if brace < 0:
        raise SystemExit(f"Opening brace not found: {signature}")
    depth = 0
    in_str = None
    esc = False
    end = None
    for i in range(brace, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == in_str:
                in_str = None
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


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"Patch target not found: {label}")
    return text.replace(old, new, 1)


s = SERVICE.read_text(encoding="utf-8")

# Dedicated trade socket and explicit candidate/feed diagnostics.  The auxiliary
# socket can carry depth/mark/klines, while the direct single-stream socket is
# responsible only for aggTrade.  This avoids an OPEN websocket being mistaken
# for a healthy trade feed when no aggTrade frames are actually arriving.
field_anchor = '    private volatile String nativeTurnFlow = "NA";\n'
field_block = '''    private volatile String nativeTurnFlow = "NA";\n    private volatile WebSocket tradeSocket;\n    private volatile long dedicatedTradeOpenedAt = 0L;\n    private volatile long lastDedicatedTradeReceived = 0L;\n    private volatile long dedicatedTradeMessages = 0L;\n    private volatile long lastDedicatedReconnectAttempt = 0L;\n    private volatile String dedicatedTradeStatus = "STARTING";\n    private volatile String restMicroError = "";\n    private volatile int restAggHttpCode = 0;\n    private volatile int restDepthHttpCode = 0;\n    private volatile boolean entryFeedAllowedNow = false;\n    private volatile boolean degradedEntryFeedNow = false;\n    private volatile String candidateSide = "WAIT";\n    private volatile int candidateQuality = 0;\n    private volatile String candidateStrategy = "WAIT";\n    private volatile String candidateReason = "Waiting for candidate";\n    private volatile String feedBlockReason = "STARTING";\n'''
s = replace_once(s, field_anchor, field_block, "V2.1.7 diagnostic fields")

reset_anchor = '''        lastRestAggTradeId = -1L;\n        lastRestMicroReceived = 0L;\n        lastRestDepthReceived = 0L;'''
reset_block = '''        lastRestAggTradeId = -1L;
        lastRestMicroReceived = 0L;
        lastRestDepthReceived = 0L;
        dedicatedTradeOpenedAt = 0L;
        lastDedicatedTradeReceived = 0L;
        dedicatedTradeMessages = 0L;
        dedicatedTradeStatus = "CONNECTING";
        restMicroError = "";
        feedBlockReason = "BUILDING LIVE FEED";
        candidateSide = "WAIT";
        candidateQuality = 0;
        candidateStrategy = "WAIT";'''
s = replace_once(s, reset_anchor, reset_block, "V2.1.7 reset state")

# Auxiliary market context socket.  aggTrade is intentionally removed here and
# handled by a dedicated direct socket below.
new_open = r'''    private void openSocket(int gen) {
        String lower = symbol.toLowerCase(Locale.US);
        ArrayList<String> params = new ArrayList<>();
        params.add(lower + "@depth20@100ms");
        params.add(lower + "@markPrice@1s");
        params.add(lower + "@kline_1m");
        params.add(lower + "@kline_15m");
        params.add(lower + "@kline_1h");
        String selected = lower + "@kline_" + tf;
        if (!params.contains(selected)) params.add(selected);

        boolean rawMode = (reconnects % 2 == 0);
        wsEndpointMode = rawMode ? "AUX RAW" : "AUX COMBINED";
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
            @Override public void onOpen(WebSocket webSocket, Response response) {
                if (gen != generation.get()) return;
                lastSocketOpenedAt = System.currentTimeMillis();
                if (rawMode) {
                    try {
                        JSONObject sub = new JSONObject();
                        sub.put("method", "SUBSCRIBE");
                        JSONArray arr = new JSONArray();
                        for (String p : params) arr.put(p);
                        sub.put("params", arr);
                        sub.put("id", 217);
                        webSocket.send(sub.toString());
                    } catch (Exception ignored) {}
                }
                writeHeartbeat();
            }

            @Override public void onMessage(WebSocket webSocket, String text) {
                if (gen != generation.get()) return;
                engine.execute(() -> processSocketMessage(text));
            }

            @Override public void onFailure(WebSocket webSocket, Throwable t, Response response) {
                if (gen != generation.get()) return;
                reconnects++;
                handler.postDelayed(() -> engine.execute(() -> {
                    if (gen == generation.get()) reconnectNow("aux websocket failure");
                }), Math.min(15000L, 1400L * Math.max(1, Math.min(8, reconnects))));
            }

            @Override public void onClosed(WebSocket webSocket, int code, String reason) {
                if (gen != generation.get()) return;
                reconnects++;
                handler.postDelayed(() -> engine.execute(() -> {
                    if (gen == generation.get()) reconnectNow("aux websocket closed");
                }), 1800L);
            }
        });
        openDedicatedTradeSocket(gen);
    }'''
s = replace_method(s, '    private void openSocket(int gen)', new_open)

trade_socket_method = r'''    private void openDedicatedTradeSocket(int gen) {
        try {
            if (tradeSocket != null) tradeSocket.cancel();
        } catch (Exception ignored) {}
        String lower = symbol.toLowerCase(Locale.US);
        String url = "wss://fstream.binance.com/ws/" + lower + "@aggTrade";
        dedicatedTradeStatus = "CONNECTING";
        lastDedicatedReconnectAttempt = System.currentTimeMillis();
        Request req = new Request.Builder().url(url).build();
        tradeSocket = client.newWebSocket(req, new WebSocketListener() {
            @Override public void onOpen(WebSocket webSocket, Response response) {
                if (gen != generation.get()) return;
                dedicatedTradeOpenedAt = System.currentTimeMillis();
                dedicatedTradeStatus = "OPEN · WAITING AGGTRADE";
                writeHeartbeat();
            }

            @Override public void onMessage(WebSocket webSocket, String text) {
                if (gen != generation.get()) return;
                engine.execute(() -> {
                    try {
                        JSONObject d = new JSONObject(text);
                        if (!"aggTrade".equals(d.optString("e", ""))) return;
                        double price = d.optDouble("p", Double.NaN);
                        double qty = d.optDouble("q", 0.0);
                        long ts = d.optLong("T", d.optLong("E", System.currentTimeMillis()));
                        boolean aggressiveBuy = !d.optBoolean("m", false);
                        if (!Double.isFinite(price)) return;
                        dedicatedTradeMessages++;
                        lastDedicatedTradeReceived = System.currentTimeMillis();
                        lastWsTradeReceived = lastDedicatedTradeReceived;
                        dedicatedTradeStatus = "LIVE · " + dedicatedTradeMessages + " msgs";
                        processTick(price, qty, aggressiveBuy, ts, "WS TRADE");
                    } catch (Exception e) {
                        dedicatedTradeStatus = "MESSAGE ERROR";
                    }
                });
            }

            @Override public void onFailure(WebSocket webSocket, Throwable t, Response response) {
                if (gen != generation.get()) return;
                String msg = t == null ? "unknown" : t.getClass().getSimpleName();
                dedicatedTradeStatus = "FAILED · " + msg;
            }

            @Override public void onClosed(WebSocket webSocket, int code, String reason) {
                if (gen != generation.get()) return;
                dedicatedTradeStatus = "CLOSED · " + code;
            }
        });
    }

'''
anchor = '    private void processSocketMessage(String text) {'
if anchor not in s:
    raise SystemExit('processSocketMessage anchor not found')
s = s.replace(anchor, trade_socket_method + anchor, 1)

# Main socket should not double-process aggTrade when the dedicated stream is
# healthy.  It remains a fallback only if an old combined subscription happens
# to deliver aggTrade.
old_agg = '''            if (stream.endsWith("@aggTrade")) {
                double price = data.optDouble("p", Double.NaN);'''
new_agg = '''            if (stream.endsWith("@aggTrade")) {
                if (lastDedicatedTradeReceived > 0L && System.currentTimeMillis() - lastDedicatedTradeReceived < 2500L) return;
                double price = data.optDouble("p", Double.NaN);'''
s = replace_once(s, old_agg, new_agg, "dedicated aggTrade preference")

# Watch actual trade frames, not socket-open state.  Reopen the direct trade
# socket independently, while REST microstructure provides continuity.
old_watch = '''            long wsRef = lastWsTradeReceived > 0 ? lastWsTradeReceived : lastSocketOpenedAt;
            long wsAge = wsRef > 0 ? now - wsRef : Long.MAX_VALUE;
            if (wsAge > 1800L) {
                fetchRestMicrostructure();
                if (lastRestMicroReceived == 0L || now - lastRestMicroReceived > 3000L) fetchRestPrice();
            }
            if (wsAge > 7000L && now - lastReconnectAttempt > 6000L) {
                lastReconnectAttempt = now;
                engine.execute(() -> reconnectNow("watchdog stale WS trade feed"));
            }'''
new_watch = '''            long tradeRef = Math.max(lastDedicatedTradeReceived, lastWsTradeReceived);
            long tradeAge = tradeRef > 0 ? now - tradeRef : Long.MAX_VALUE;
            if (tradeAge > 1600L) {
                fetchRestMicrostructure();
                if (lastRestMicroReceived == 0L || now - lastRestMicroReceived > 2800L) fetchRestPrice();
            }
            if (tradeAge > 3500L && now - lastDedicatedReconnectAttempt > 4000L) {
                lastDedicatedReconnectAttempt = now;
                engine.execute(() -> openDedicatedTradeSocket(generation.get()));
            }
            if (tradeAge > 12000L && now - lastReconnectAttempt > 10000L) {
                lastReconnectAttempt = now;
                engine.execute(() -> reconnectNow("watchdog no genuine trade frames"));
            }'''
s = replace_once(s, old_watch, new_watch, "trade-frame watchdog")

# REST fallback now reports real HTTP/network failures and rotates between
# Binance futures API hosts.  This makes a blocked fallback visible instead of
# silently leaving the app in REST BACKUP forever.
rest_base = r'''    private String futuresRestBase() {
        long slot = (System.currentTimeMillis() / 10_000L) % 3L;
        if (slot == 1L) return "https://fapi1.binance.com";
        if (slot == 2L) return "https://fapi2.binance.com";
        return "https://fapi.binance.com";
    }

'''
anchor = '    private void fetchRestMicrostructure() {'
if anchor not in s:
    raise SystemExit('fetchRestMicrostructure anchor not found')
s = s.replace(anchor, rest_base + anchor, 1)

new_fetch_micro = r'''    private void fetchRestMicrostructure() {
        long now = System.currentTimeMillis();
        if (restMicroBusy || now - lastRestMicroPoll < 800L) return;
        restMicroBusy = true;
        lastRestMicroPoll = now;
        fetchRestDepth();
        String base = futuresRestBase();
        Request req = new Request.Builder()
                .url(base + "/fapi/v1/aggTrades?symbol=" + symbol + "&limit=120")
                .build();
        client.newCall(req).enqueue(new Callback() {
            @Override public void onFailure(Call call, IOException e) {
                restMicroError = "aggTrades network " + e.getClass().getSimpleName();
                restAggHttpCode = 0;
                restMicroBusy = false;
            }
            @Override public void onResponse(Call call, Response response) throws IOException {
                String body = "[]";
                int code;
                boolean ok;
                try (Response r = response) {
                    code = r.code(); ok = r.isSuccessful();
                    if (r.body() != null) body = r.body().string();
                }
                restAggHttpCode = code;
                if (!ok) {
                    restMicroError = "aggTrades HTTP " + code;
                    restMicroBusy = false;
                    return;
                }
                final String payload = body;
                engine.execute(() -> {
                    try {
                        ingestRestAggTrades(payload);
                        restMicroError = "";
                    } finally {
                        restMicroBusy = false;
                    }
                });
            }
        });
    }'''
s = replace_method(s, '    private void fetchRestMicrostructure()', new_fetch_micro)

new_fetch_depth = r'''    private void fetchRestDepth() {
        String base = futuresRestBase();
        Request req = new Request.Builder()
                .url(base + "/fapi/v1/depth?symbol=" + symbol + "&limit=20")
                .build();
        client.newCall(req).enqueue(new Callback() {
            @Override public void onFailure(Call call, IOException e) {
                restDepthHttpCode = 0;
                if (restMicroError.isEmpty()) restMicroError = "depth network " + e.getClass().getSimpleName();
            }
            @Override public void onResponse(Call call, Response response) throws IOException {
                String body = "{}";
                int code; boolean ok;
                try (Response r = response) {
                    code = r.code(); ok = r.isSuccessful();
                    if (r.body() != null) body = r.body().string();
                }
                restDepthHttpCode = code;
                if (!ok) {
                    if (restMicroError.isEmpty()) restMicroError = "depth HTTP " + code;
                    return;
                }
                final String payload = body;
                engine.execute(() -> ingestRestDepth(payload));
            }
        });
    }'''
s = replace_method(s, '    private void fetchRestDepth()', new_fetch_depth)

# The price pipeline always evaluates a candidate. Recording is enabled only when
# genuine trade microstructure is available.  A live WS trade feed can continue
# with missing depth, but then only a higher-quality candidate may be recorded.
new_process_tick = r'''    private void processTick(double price, double qty, boolean aggressiveBuy, long exchangeTs, String source) {
        long startNs = System.nanoTime();
        long now = System.currentTimeMillis();
        lastPrice = price;
        lastTickReceived = now;
        lastExchangeEvent = exchangeTs;

        boolean wsTrade = "WS TRADE".equals(source);
        boolean restMicro = "REST MICRO".equals(source);
        if (wsTrade) {
            lastWsTradeReceived = now;
            feedMode = "WS TRADE";
        } else if (restMicro) {
            lastRestMicroReceived = now;
            if (lastWsTradeReceived == 0L || now - lastWsTradeReceived > 1600L) feedMode = "REST MICRO";
        } else if (lastWsTradeReceived == 0L || now - lastWsTradeReceived > 2200L) {
            if (lastRestMicroReceived > 0L && now - lastRestMicroReceived < 2400L) feedMode = "REST MICRO";
            else feedMode = source;
        }

        if (qty > 0) addFlow(exchangeTs, qty, aggressiveBuy);
        updateSynthetic(microCandles, price, exchangeTs, 60_000L, qty, aggressiveBuy);
        updateSynthetic(mainCandles, price, exchangeTs, tfMillis(tf), qty, aggressiveBuy);
        checkTrades(price, exchangeTs);

        boolean depthFresh = lastDepthReceived > 0L && now - lastDepthReceived < 4000L;
        boolean microFresh = lastRestMicroReceived > 0L && now - lastRestMicroReceived < 2600L;
        boolean flowReady = flowBuckets.size() >= 3;
        entryFeedAllowedNow = wsTrade || (restMicro && microFresh && (depthFresh || flowReady));
        degradedEntryFeedNow = entryFeedAllowedNow && !depthFresh;

        Turning turn = detectTurningFast(price);
        nativeTurnState = turn.state;
        nativeTurnLocation = turn.location;
        nativeTurnReason = turn.reason;
        nativeTurnFlow = String.format(Locale.US, "%.1f%%", turn.flow * 100.0);

        if (entryFeedAllowedNow) {
            considerFastTurning(turn, price);
        }
        if (now - lastMainSignalAt > 220L) {
            lastMainSignalAt = now;
            analyseMainAndMaybeRecord();
        }
        lastEngineMs = (System.nanoTime() - startNs) / 1_000_000.0;
    }'''
s = replace_method(s, '    private void processTick(double price, double qty, boolean aggressiveBuy, long exchangeTs, String source)', new_process_tick)

# Candidate selection is now independent from entry-feed permission.  The screen
# can therefore say SELL SETUP Q78 / BLOCKED BY FEED instead of simply WAIT.
new_analyse = r'''    private void analyseMainAndMaybeRecord() {
        if (mainCandles.size() < 60) return;
        int n = mainCandles.size();
        double[] o = new double[n], h = new double[n], l = new double[n], c = new double[n], v = new double[n], tb = new double[n];
        for (int j = 0; j < n; j++) {
            Candle z = mainCandles.get(j);
            o[j] = z.o; h[j] = z.h; l[j] = z.l; c[j] = z.c; v[j] = z.v; tb[j] = z.tb;
        }
        long now = System.currentTimeMillis();
        double px = Double.isFinite(lastPrice) ? lastPrice : c[n - 1];

        Candle liveBar = mainCandles.get(n - 1);
        long tfMs = tfMillis(tf);
        double progress = tfMs > 0 ? (now - liveBar.t) / (double) tfMs : 1.0;
        progress = Math.max(0.20, Math.min(1.0, progress));
        if (!liveBar.closed && progress < 0.98) {
            double scale = Math.min(3.0, 1.0 / progress);
            v[n - 1] *= scale;
            tb[n - 1] *= scale;
        }

        Turning turn = detectTurningFast(px);
        int b15 = trendBias(context15Candles);
        int b60 = trendBias(context60Candles);
        double stableFlow = ensembleFlow();
        double stableDepth = depthComposite();
        double stableOi = oiComposite();

        AdaptiveEnsemble.Result result = AdaptiveEnsemble.evaluate(
                o, h, l, c, v, tb,
                stableFlow, stableDepth, fundingRate, stableOi, spreadBps,
                b15, b60,
                turn == null ? 0 : turn.dir,
                turn == null ? 0 : turn.score,
                turn != null && turn.trigger
        );
        if (!result.trade) {
            AdaptiveEnsemble.Result micro = microContinuationResult(px, b15, b60, stableFlow, stableDepth);
            if (micro != null) result = micro;
        }

        marketRegime = result.regime;
        activeStrategy = result.strategy;
        ensembleConfidence = result.confidence;
        ensembleReason = result.reason + String.format(Locale.US,
                " · F3 %.2f F30 %.2f F180 %.2f · D1 %.2f D10 %.2f · OI1 %.3f OI5 %.3f OI15 %.3f · bar %.0f%%",
                flow3s, flow30s, flow180s, depth1s, depth10s, oi1m, oi5m, oi15m, progress * 100.0);

        if (!result.trade) {
            candidateSide = "WAIT";
            candidateQuality = result.confidence;
            candidateStrategy = result.strategy;
            candidateReason = result.reason;
            feedBlockReason = entryFeedAllowedNow ? "" : currentFeedBlockReason(now);
            if (!armedSetupKey.isEmpty() && now - armedSetupAt <= 2_500L && entryFeedAllowedNow) {
                signalState = "ARMED HOLD · " + armedSetupKey.replace('|', ' ') + " · " + result.regime;
                return;
            }
            resetArmedSetup();
            signalState = "WAIT · " + result.regime + " · " + result.reason;
            return;
        }

        String side = result.dir > 0 ? "BUY" : "SELL";
        int performanceAdj = strategyPerformanceAdjustment(result.strategy, side);
        int effectiveConfidence = Math.max(0, Math.min(99, result.confidence + performanceAdj));
        ensembleConfidence = effectiveConfidence;
        candidateSide = side;
        candidateQuality = effectiveConfidence;
        candidateStrategy = result.strategy;
        candidateReason = result.reason;

        if (!entryFeedAllowedNow) {
            resetArmedSetup();
            feedBlockReason = currentFeedBlockReason(now);
            signalState = "CANDIDATE " + side + " Q" + effectiveConfidence + " · BLOCKED · " + feedBlockReason;
            return;
        }

        if (degradedEntryFeedNow && effectiveConfidence < 82) {
            resetArmedSetup();
            feedBlockReason = "DEPTH DEGRADED · Q82 REQUIRED";
            signalState = "CANDIDATE " + side + " Q" + effectiveConfidence + " · BLOCKED · " + feedBlockReason;
            return;
        }
        feedBlockReason = "";

        if (performanceAdj <= -4 && effectiveConfidence < 76) {
            resetArmedSetup();
            signalState = result.strategy + " " + side + " · PERFORMANCE VETO";
            return;
        }

        double dirFlow = result.dir * stableFlow;
        double dirDepth = result.dir * stableDepth;
        boolean hardFlowVeto = (dirFlow < -0.18 && dirDepth < -0.16) || dirFlow < -0.38 || dirDepth < -0.35;
        if (hardFlowVeto) {
            if (!armedSetupKey.isEmpty() && now - armedSetupAt <= 1_400L) {
                signalState = "ARMED FLOW CHECK · " + side + " Q" + effectiveConfidence;
                return;
            }
            resetArmedSetup();
            signalState = result.strategy + " " + side + " · ORDER FLOW VETO";
            return;
        }

        double av = atrLast(mainCandles, 14);
        if (!Double.isFinite(av) || av <= 0) av = Math.abs(px) * 0.004;
        String armKey = symbol + "|" + tf + "|" + side;
        if (!armKey.equals(armedSetupKey)) {
            armedSetupKey = armKey;
            armedSetupAt = now;
            armedSetupCount = 1;
            armedSetupPrice = px;
            armedSetupDir = result.dir;
            signalState = "ARMED " + side + " · " + result.strategy + " · 1/3 · Q" + effectiveConfidence;
            return;
        }

        if (now - armedSetupAt > 4_500L ||
                (armedSetupDir > 0 && px < armedSetupPrice - av * 0.30) ||
                (armedSetupDir < 0 && px > armedSetupPrice + av * 0.30)) {
            resetArmedSetup();
            signalState = "WAIT · SETUP INVALIDATED";
            return;
        }

        armedSetupCount++;
        int requiredCount = effectiveConfidence >= 86 ? 2 : 3;
        long requiredMs = effectiveConfidence >= 86 ? 180L : 320L;
        if (armedSetupCount < requiredCount || now - armedSetupAt < requiredMs) {
            signalState = "ARMED " + side + " · " + result.strategy + " · " + armedSetupCount + "/" + requiredCount + " · Q" + effectiveConfidence;
            return;
        }

        long candleTime = mainCandles.get(n - 1).t;
        String key = symbol + "|" + tf + "|" + side + "|" + candleTime;
        if (key.equals(lastEnsembleKey) && now - lastEnsembleSignalAt < 60_000L) {
            resetArmedSetup();
            return;
        }
        if (now - lastEnsembleSignalAt < 15_000L) {
            signalState = "WAIT · SIGNAL COOLDOWN";
            resetArmedSetup();
            return;
        }

        double baseRisk = av * result.riskAtrMult;
        double structureLow = minLow(mainCandles, Math.max(0, n - 7), n);
        double structureHigh = maxHigh(mainCandles, Math.max(0, n - 7), n);
        Plan plan;
        if (result.dir > 0) {
            double structureStop = structureLow - av * 0.08;
            double sl = Math.min(px - baseRisk, structureStop);
            double risk = px - sl;
            if (risk > av * 2.20) { risk = av * 2.20; sl = px - risk; }
            plan = new Plan(px, sl, px + risk, px + risk * 1.60, px + risk * 2.35);
        } else {
            double structureStop = structureHigh + av * 0.08;
            double sl = Math.max(px + baseRisk, structureStop);
            double risk = sl - px;
            if (risk > av * 2.20) { risk = av * 2.20; sl = px + risk; }
            plan = new Plan(px, sl, px - risk, px - risk * 1.60, px - risk * 2.35);
        }

        String stage = result.strategy + " " + side;
        if (recordSignal(side, stage, effectiveConfidence, plan, "native feed authority v2.1.7 · " + feedMode)) {
            lastEnsembleKey = key;
            lastEnsembleSignalAt = now;
            signalState = "TRIGGERED " + stage + " · Q" + effectiveConfidence;
            feedBlockReason = "";
            notifySignal(side, result.strategy + " Q" + effectiveConfidence, px);
        }
        resetArmedSetup();
    }

    private String currentFeedBlockReason(long now) {
        long tradeAge = lastDedicatedTradeReceived > 0 ? now - lastDedicatedTradeReceived : Long.MAX_VALUE;
        long restAge = lastRestMicroReceived > 0 ? now - lastRestMicroReceived : Long.MAX_VALUE;
        if (tradeAge == Long.MAX_VALUE && dedicatedTradeOpenedAt > 0)
            return "TRADE WS OPEN · NO AGGTRADE FRAMES";
        if (tradeAge > 3000L && dedicatedTradeStatus.startsWith("FAILED"))
            return dedicatedTradeStatus;
        if (restAge > 3000L && !restMicroError.isEmpty())
            return restMicroError + " · agg " + restAggHttpCode + " · depth " + restDepthHttpCode;
        if (restAge > 3000L)
            return "REST MICRO STALE · agg " + restAggHttpCode + " · depth " + restDepthHttpCode;
        return "BUILDING TRADE MICROSTRUCTURE";
    }'''
s = replace_method(s, '    private void analyseMainAndMaybeRecord()', new_analyse)

# Persist explicit candidate and feed diagnostics.
heartbeat_anchor = '                .putString("native_turn_flow", nativeTurnFlow)\n'
heartbeat_block = '''                .putString("native_turn_flow", nativeTurnFlow)\n                .putString("candidate_side", candidateSide)\n                .putInt("candidate_quality", candidateQuality)\n                .putString("candidate_strategy", candidateStrategy)\n                .putString("candidate_reason", candidateReason)\n                .putString("feed_block_reason", feedBlockReason)\n                .putString("dedicated_trade_status", dedicatedTradeStatus)\n                .putLong("dedicated_trade_opened_at", dedicatedTradeOpenedAt)\n                .putLong("last_dedicated_trade_received", lastDedicatedTradeReceived)\n                .putLong("dedicated_trade_messages", dedicatedTradeMessages)\n                .putInt("rest_agg_http_code", restAggHttpCode)\n                .putInt("rest_depth_http_code", restDepthHttpCode)\n                .putString("rest_micro_error", restMicroError)\n'''
s = replace_once(s, heartbeat_anchor, heartbeat_block, "V2.1.7 heartbeat diagnostics")
s = s.replace('t.put("engineVersion", "2.1.6");', 't.put("engineVersion", "2.1.7");')
SERVICE.write_text(s, encoding="utf-8")


# Android bridge exposes feed diagnostics and separates candidate direction from
# a recorded trade.  A blocked candidate is shown as BUY SETUP / SELL SETUP, not
# as a published BUY/SELL order and not as an unexplained WAIT.
a = ACTIVITY.read_text(encoding="utf-8")
a = a.replace(
    '                o.put("turnFlow", prefs.getString("native_turn_flow", "NA"));',
    '                o.put("turnFlow", prefs.getString("native_turn_flow", "NA"));\n'
    '                o.put("candidateSide", prefs.getString("candidate_side", "WAIT"));\n'
    '                o.put("candidateQuality", prefs.getInt("candidate_quality", 0));\n'
    '                o.put("candidateStrategy", prefs.getString("candidate_strategy", "WAIT"));\n'
    '                o.put("candidateReason", prefs.getString("candidate_reason", ""));\n'
    '                o.put("feedBlockReason", prefs.getString("feed_block_reason", ""));\n'
    '                o.put("tradeWsStatus", prefs.getString("dedicated_trade_status", "STARTING"));\n'
    '                long dtr = prefs.getLong("last_dedicated_trade_received", 0);\n'
    '                o.put("tradeWsAgeMs", dtr > 0 ? Math.max(0, now - dtr) : -1);\n'
    '                o.put("tradeWsMessages", prefs.getLong("dedicated_trade_messages", 0));\n'
    '                o.put("restAggHttp", prefs.getInt("rest_agg_http_code", 0));\n'
    '                o.put("restDepthHttp", prefs.getInt("rest_depth_http_code", 0));\n'
    '                o.put("restMicroError", prefs.getString("rest_micro_error", ""));',
    1
)

js = r'''(function(){
if(window.__dhanpulseNativeBridgeV217)return;
window.__dhanpulseNativeBridgeV217=true;
window.__nativeDecisionAuthority=true;
var K='dhanpulse_cf_android_trades_v21',lastNative='',lastState={};
function el(id){return document.getElementById(id)}
function num(v){var n=Number(v);return isFinite(n)?n:null}
function fmt(v){var n=num(v);if(n===null)return 'NA';return Math.abs(n)>=1000?n.toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2}):n.toFixed(4)}
function nativeTrades(){try{var a=JSON.parse(AndroidNative.getNativeTrades()||'[]');return Array.isArray(a)?a:[]}catch(e){return []}}
function latestOpen(st,a){var best=null;(a||[]).forEach(function(t){if(t.status==='OPEN'&&t.symbol===(st.symbol||'')&&t.tf===(st.tf||'')){if(!best||(t.createdAt||0)>(best.createdAt||0))best=t}});return best}
function copyNativeTrades(){try{var raw=AndroidNative.getNativeTrades()||'[]';if(raw!==lastNative){lastNative=raw;var a=JSON.parse(raw);if(!Array.isArray(a))a=[];localStorage.setItem(K,JSON.stringify(a));if(window.S)S.tradeCache=a;if(window.renderTrades)renderTrades()}}catch(e){}}
function paint(st){
 lastState=st||{};
 var fm=String(st.feedMode||'STARTING'),ss=String(st.signalState||'MONITORING');
 var ws=fm.indexOf('WS TRADE')===0,rm=fm.indexOf('REST MICRO')===0,entryFeed=ws||rm;
 var cand=String(st.candidateSide||'WAIT'),cq=Number(st.candidateQuality||0),cs=String(st.candidateStrategy||'WAIT');
 var c=el('conn');if(c){c.textContent='NATIVE '+fm;c.className='badge '+(entryFeed?'live':'')}
 var bg=el('bgState');if(bg){bg.textContent=st.active?'NATIVE ACTIVE':'STARTING';bg.className=st.active?'bull':'neutral'}
 var bh=el('bgHeartbeat');if(bh)bh.textContent='trade WS '+(st.tradeWsStatus||'STARTING')+' · msg '+(st.tradeWsMessages||0)+' · feed '+fm+' · '+ss;
 var bs=el('bgSymbol');if(bs)bs.textContent=st.symbol||'';var bt=el('bgTf');if(bt)bt.textContent=st.tf||'';
 var tl=el('tradeLogState');if(tl)tl.textContent='Native V2.1.7 · '+fm+' · TradeWS '+(st.tradeWsStatus||'')+' · candidate '+cand+' Q'+cq+' · '+ss;
 var lp=num(st.lastPrice),pe=el('price');if(pe&&lp!==null)pe.textContent=fmt(lp);
 var ts=el('turnState');if(ts)ts.textContent=st.turnState||'MONITORING';
 var tloc=el('turnLocation');if(tloc)tloc.textContent=st.turnLocation||'NA';
 var tf=el('turnFlow');if(tf)tf.textContent=st.turnFlow||'NA';
 var tr=el('turnReason');if(tr)tr.textContent=st.turnReason||'Waiting for native microstructure';
 var em=el('engineMs');if(em&&st.engineMs)em.textContent=st.engineMs+' ms';
 var ev=el('eventType');if(ev)ev.textContent=fm+' · WS '+(st.tradeWsStatus||'');
 var a=nativeTrades(),open=latestOpen(st,a),side='',stage='',reason='',q=Number(st.ensembleConfidence||0),published=false;
 if(open){side=String(open.side||'');published=true;stage='RECORDED · '+String(open.stage||'NATIVE SIGNAL');reason='Native signal recorded and being tracked';}
 else if(ss.indexOf('TRIGGERED')>=0){side=ss.indexOf('BUY')>=0?'BUY':ss.indexOf('SELL')>=0?'SELL':'';published=!!side;stage=ss;reason='Native trigger fired. Recording sync in progress';}
 else if(ss.indexOf('ARMED')>=0){stage=ss;reason='Candidate '+cand+' Q'+cq+' is armed for final confirmation';}
 else if(cand==='BUY'||cand==='SELL'){stage=ss;reason=(st.feedBlockReason?'BLOCKED: '+st.feedBlockReason:(st.candidateReason||'Candidate detected'));}
 else if(!entryFeed){stage='FEED RECOVERY · '+fm;reason=st.feedBlockReason||'Building trade microstructure';}
 else {stage=ss;reason='Native engine is monitoring. No qualified candidate yet';}
 var d=el('decision'),card=el('decisionCard'),sc=el('score'),sg=el('stage'),rs=el('reason'),pd=el('pdir');
 var display=published?side:((cand==='BUY'||cand==='SELL')?(cand+' SETUP'):'WAIT');
 if(d)d.textContent=display;
 if(card)card.className='panel decision '+(published?side.toLowerCase():'wait');
 if(sc)sc.textContent=(published?'Native Q '+q:'Candidate Q '+cq)+' | '+(published?(st.activeStrategy||'WAIT'):cs);
 if(sg)sg.textContent='Stage: '+(stage||'WAIT');
 if(rs)rs.textContent=reason;
 if(pd)pd.textContent=published?side:'WAIT';
 ['entry','sl','t1','t2','t3'].forEach(function(id){var x=el(id);if(x)x.textContent=open?fmt(open[id]):'NA'});
 window.__nativeChartPlan=open?{direction:side,entry:Number(open.entry),sl:Number(open.sl),t1:Number(open.t1),t2:Number(open.t2),t3:Number(open.t3)}:null;
 var r=el('record');if(r){r.disabled=true;r.textContent='Native Auto Record'}
 try{if(window.draw)draw()}catch(e){}
}
window.__renderNativeDecision=function(){paint(lastState||{})};
function sync(){try{var s=el('symbol'),tf=el('tf');if(s&&tf)AndroidNative.setMonitoringConfig(s.value,tf.value);var st=JSON.parse(AndroidNative.getNativeState()||'{}');paint(st);copyNativeTrades();AndroidNative.ensureService()}catch(e){}}
['symbol','tf'].forEach(function(id){var x=el(id);if(x)x.addEventListener('change',function(){setTimeout(sync,40)})});
var clr=el('clear');if(clr)clr.addEventListener('click',function(){setTimeout(function(){AndroidNative.clearNativeTrades();localStorage.removeItem(K);if(window.S)S.tradeCache=[];copyNativeTrades()},250)});
var anchor=el('bgState');if(anchor){var p=anchor.closest('.panel');if(p&&!el('nativeBatteryBtn')){var b=document.createElement('button');b.id='nativeBatteryBtn';b.textContent='Allow 24/7 Background';b.style.marginTop='12px';b.style.width='100%';b.onclick=function(){AndroidNative.openBatterySettings()};p.appendChild(b)}}
setInterval(sync,250);sync();
})();'''
java_method = '''    private void injectNativeBridge() {\n        String js = %s;\n        webView.evaluateJavascript(js, null);\n    }''' % json.dumps(js)
a = replace_method(a, '    private void injectNativeBridge()', java_method)
a = a.replace('Native V2.1.6 · ', 'Native V2.1.7 · ')
ACTIVITY.write_text(a, encoding="utf-8")

h = INDEX.read_text(encoding="utf-8")
h = h.replace('Version 2.1.6 Hybrid Micro Feed', 'Version 2.1.7 Feed Authority Fix')
h = h.replace('V2.1.6 Signals', 'V2.1.7 Signals')
h = h.replace('No V2.1.6 signals recorded yet.', 'No V2.1.7 signals recorded yet.')
h = h.replace('NATIVE V2.1.6', 'NATIVE V2.1.7')
INDEX.write_text(h, encoding="utf-8")

g = GRADLE.read_text(encoding="utf-8")
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 28', g)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.1.7"', g)
GRADLE.write_text(g, encoding="utf-8")

print('DhanPulse V2.1.7 dedicated trade feed authority, candidate diagnostics and recording pipeline applied')
