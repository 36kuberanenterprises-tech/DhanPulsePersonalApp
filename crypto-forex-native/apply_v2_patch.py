from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVICE = ROOT / "app/src/main/java/com/dhanpulse/cryptofxnative/BackgroundService.java"
ACTIVITY = ROOT / "app/src/main/java/com/dhanpulse/cryptofxnative/MainActivity.java"
GRADLE = ROOT / "app/build.gradle.kts"


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"Patch target not found: {label}")
    return text.replace(old, new, 1)


def replace_method(text, signature, new_method):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f"Method not found: {signature}")
    brace = text.find("{", start)
    if brace < 0:
        raise SystemExit(f"Opening brace not found: {signature}")
    depth = 0
    end = None
    for i in range(brace, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise SystemExit(f"Closing brace not found: {signature}")
    return text[:start] + new_method.rstrip() + text[end:]


s = SERVICE.read_text(encoding="utf-8")

s = replace_once(
    s,
    '    private final ArrayList<Candle> microCandles = new ArrayList<>();\n    private final ArrayList<Candle> mainCandles = new ArrayList<>();',
    '''    private final ArrayList<Candle> microCandles = new ArrayList<>();
    private final ArrayList<Candle> mainCandles = new ArrayList<>();
    private final ArrayList<Candle> context15Candles = new ArrayList<>();
    private final ArrayList<Candle> context60Candles = new ArrayList<>();
    private volatile double fundingRate = 0.0;
    private volatile double openInterest = Double.NaN;
    private volatile double previousOpenInterest = Double.NaN;
    private volatile double oiChangePct = 0.0;
    private volatile double bestBid = Double.NaN;
    private volatile double bestAsk = Double.NaN;
    private volatile double spreadBps = Double.NaN;
    private volatile long lastOiSync = 0L;
    private volatile long lastHtfSync = 0L;
    private volatile String marketRegime = "WARMING UP";
    private volatile String activeStrategy = "WAIT";
    private volatile int ensembleConfidence = 0;
    private volatile String ensembleReason = "Collecting market context";
    private volatile long lastEnsembleSignalAt = 0L;
    private volatile String lastEnsembleKey = "";''',
    "ensemble fields")

s = replace_once(
    s,
    '''        fetchHistory("1m", true);
        if (!"1m".equals(tf)) fetchHistory(tf, false); else fetchHistory("1m", false);
        openSocket(gen);''',
    '''        fetchHistory("1m", true);
        if (!"1m".equals(tf)) fetchHistory(tf, false); else fetchHistory("1m", false);
        fetchAuxHistory("15m", context15Candles);
        fetchAuxHistory("1h", context60Candles);
        fetchOpenInterest();
        openSocket(gen);''',
    "reconnect context")

s = replace_once(
    s,
    '''        String lower = symbol.toLowerCase(Locale.US);
        String streams = lower + "@aggTrade/" + lower + "@bookTicker/" + lower + "@kline_1m";
        if (!"1m".equals(tf)) streams += "/" + lower + "@kline_" + tf;''',
    '''        String lower = symbol.toLowerCase(Locale.US);
        String streams = lower + "@aggTrade/" + lower + "@bookTicker/" + lower + "@markPrice@1s/" + lower + "@kline_1m/" + lower + "@kline_15m/" + lower + "@kline_1h";
        if (!"1m".equals(tf) && !"15m".equals(tf) && !"1h".equals(tf)) streams += "/" + lower + "@kline_" + tf;''',
    "websocket streams")

s = replace_once(
    s,
    '''            } else if (stream.endsWith("@bookTicker")) {
                double bidQty = data.optDouble("B", 0.0);
                double askQty = data.optDouble("A", 0.0);
                double total = bidQty + askQty;
                orderBookImbalance = total > 0 ? (bidQty - askQty) / total : 0.0;
            } else if (stream.contains("@kline_")) {''',
    '''            } else if (stream.endsWith("@bookTicker")) {
                double bidQty = data.optDouble("B", 0.0);
                double askQty = data.optDouble("A", 0.0);
                bestBid = data.optDouble("b", Double.NaN);
                bestAsk = data.optDouble("a", Double.NaN);
                double total = bidQty + askQty;
                orderBookImbalance = total > 0 ? (bidQty - askQty) / total : 0.0;
                if (Double.isFinite(bestBid) && Double.isFinite(bestAsk) && bestBid > 0 && bestAsk >= bestBid) {
                    double mid = (bestBid + bestAsk) / 2.0;
                    spreadBps = mid > 0 ? (bestAsk - bestBid) / mid * 10000.0 : Double.NaN;
                }
            } else if (stream.contains("@markPrice")) {
                fundingRate = data.optDouble("r", fundingRate);
                double mark = data.optDouble("p", Double.NaN);
                if (Double.isFinite(mark) && !Double.isFinite(lastPrice)) lastPrice = mark;
            } else if (stream.contains("@kline_")) {''',
    "book and funding context")

s = replace_once(
    s,
    '''            if ("1m".equals(interval)) upsertCandle(microCandles, c);
            if (tf.equals(interval)) upsertCandle(mainCandles, c.copy());
            if ("1m".equals(tf) && "1m".equals(interval)) upsertCandle(mainCandles, c.copy());''',
    '''            if ("1m".equals(interval)) upsertCandle(microCandles, c);
            if ("15m".equals(interval)) upsertCandle(context15Candles, c.copy());
            if ("1h".equals(interval)) upsertCandle(context60Candles, c.copy());
            if (tf.equals(interval)) upsertCandle(mainCandles, c.copy());
            if ("1m".equals(tf) && "1m".equals(interval)) upsertCandle(mainCandles, c.copy());''',
    "context klines")

s = replace_once(
    s,
    '''            if (now - lastRestSync > 30000) {
                lastRestSync = now;
                fetchHistory("1m", true);
                if (!"1m".equals(tf)) fetchHistory(tf, false); else fetchHistory("1m", false);
            }
            if (now - lastNotificationUpdate > 5000) {''',
    '''            if (now - lastRestSync > 30000) {
                lastRestSync = now;
                fetchHistory("1m", true);
                if (!"1m".equals(tf)) fetchHistory(tf, false); else fetchHistory("1m", false);
            }
            if (now - lastOiSync > 10000) {
                lastOiSync = now;
                fetchOpenInterest();
            }
            if (now - lastHtfSync > 60000) {
                lastHtfSync = now;
                fetchAuxHistory("15m", context15Candles);
                fetchAuxHistory("1h", context60Candles);
            }
            if (now - lastNotificationUpdate > 5000) {''',
    "watchdog context refresh")

s = replace_once(
    s,
    '''                .putInt("reconnects", reconnects)
                .putString("engine_ms", String.format(Locale.US, "%.3f", lastEngineMs));''',
    '''                .putInt("reconnects", reconnects)
                .putString("engine_ms", String.format(Locale.US, "%.3f", lastEngineMs))
                .putString("market_regime", marketRegime)
                .putString("active_strategy", activeStrategy)
                .putInt("ensemble_confidence", ensembleConfidence)
                .putString("ensemble_reason", ensembleReason)
                .putString("funding_rate", String.format(Locale.US, "%.6f", fundingRate))
                .putString("oi_change_pct", String.format(Locale.US, "%.4f", oiChangePct))
                .putString("spread_bps", Double.isFinite(spreadBps) ? String.format(Locale.US, "%.3f", spreadBps) : "");''',
    "heartbeat ensemble state")

new_consider = r'''    private void considerFastTurning(Turning turn, double price) {
        // V2: top/bottom detection is now one input to the adaptive ensemble.
        // It no longer independently opens a trade, which prevents a single
        // reversal detector from overruling trend, breakout, volatility and
        // higher-timeframe context.
        if (turn != null && turn.trigger) signalState = turn.state + " · ENSEMBLE CHECK";
    }'''
s = replace_method(s, "    private void considerFastTurning(Turning turn, double price)", new_consider)

new_analyse = r'''    private void analyseMainAndMaybeRecord() {
        if (mainCandles.size() < 60) return;
        int n = mainCandles.size();
        double[] o = new double[n], h = new double[n], l = new double[n], c = new double[n], v = new double[n], tb = new double[n];
        for (int j = 0; j < n; j++) {
            Candle z = mainCandles.get(j);
            o[j] = z.o; h[j] = z.h; l[j] = z.l; c[j] = z.c; v[j] = z.v; tb[j] = z.tb;
        }
        double px = Double.isFinite(lastPrice) ? lastPrice : c[n - 1];
        Turning turn = detectTurningFast(px);
        int b15 = trendBias(context15Candles);
        int b60 = trendBias(context60Candles);
        AdaptiveEnsemble.Result result = AdaptiveEnsemble.evaluate(
                o, h, l, c, v, tb,
                flowImbalance(), orderBookImbalance, fundingRate, oiChangePct, spreadBps,
                b15, b60,
                turn == null ? 0 : turn.dir,
                turn == null ? 0 : turn.score,
                turn != null && turn.trigger
        );

        marketRegime = result.regime;
        activeStrategy = result.strategy;
        ensembleConfidence = result.confidence;
        ensembleReason = result.reason;
        if (!result.trade) {
            if (turn != null && turn.trigger) signalState = turn.state + " · WAIT";
            else signalState = result.regime + " · WAIT";
            return;
        }

        String side = result.dir > 0 ? "BUY" : "SELL";
        int performanceAdj = strategyPerformanceAdjustment(result.strategy, side);
        int effectiveConfidence = Math.max(0, Math.min(99, result.confidence + performanceAdj));
        ensembleConfidence = effectiveConfidence;
        if (performanceAdj <= -4 && effectiveConfidence < 76) {
            signalState = result.strategy + " · PERFORMANCE VETO";
            return;
        }

        long now = System.currentTimeMillis();
        long candleTime = mainCandles.get(n - 1).t;
        String key = symbol + "|" + tf + "|" + result.strategy + "|" + side + "|" + candleTime;
        if (key.equals(lastEnsembleKey) && now - lastEnsembleSignalAt < 60000) return;

        double av = atrLast(mainCandles, 14);
        if (!Double.isFinite(av) || av <= 0) av = Math.abs(px) * 0.004;
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
        if (recordSignal(side, stage, effectiveConfidence, plan, "native adaptive ensemble v2")) {
            lastEnsembleKey = key;
            lastEnsembleSignalAt = now;
            signalState = stage + " · Q" + effectiveConfidence;
            notifySignal(side, result.strategy + " Q" + effectiveConfidence, px);
        }
    }'''
s = replace_method(s, "    private void analyseMainAndMaybeRecord()", new_analyse)

helper_anchor = "    private int smcScore(List<Candle> c, double[] atr) {"
helpers = r'''    private void fetchAuxHistory(String interval, ArrayList<Candle> target) {
        Request req = new Request.Builder().url("https://fapi.binance.com/fapi/v1/klines?symbol=" + symbol + "&interval=" + interval + "&limit=300").build();
        client.newCall(req).enqueue(new Callback() {
            @Override public void onFailure(Call call, IOException e) {}
            @Override public void onResponse(Call call, Response response) throws IOException {
                try (Response r = response) {
                    String body = r.body() != null ? r.body().string() : "[]";
                    JSONArray arr = new JSONArray(body);
                    ArrayList<Candle> parsed = new ArrayList<>();
                    for (int i = 0; i < arr.length(); i++) {
                        JSONArray row = arr.optJSONArray(i);
                        if (row == null || row.length() < 10) continue;
                        parsed.add(new Candle(row.optLong(0, 0L), row.optDouble(1, 0.0), row.optDouble(2, 0.0),
                                row.optDouble(3, 0.0), row.optDouble(4, 0.0), row.optDouble(5, 0.0),
                                row.optDouble(9, 0.0), true));
                    }
                    engine.execute(() -> {
                        target.clear(); target.addAll(parsed); trimCandles(target);
                    });
                } catch (Exception ignored) {}
            }
        });
    }

    private void fetchOpenInterest() {
        Request req = new Request.Builder().url("https://fapi.binance.com/fapi/v1/openInterest?symbol=" + symbol).build();
        client.newCall(req).enqueue(new Callback() {
            @Override public void onFailure(Call call, IOException e) {}
            @Override public void onResponse(Call call, Response response) throws IOException {
                try (Response r = response) {
                    String body = r.body() != null ? r.body().string() : "{}";
                    JSONObject j = new JSONObject(body);
                    double oi = j.optDouble("openInterest", Double.NaN);
                    if (Double.isFinite(oi) && oi > 0) engine.execute(() -> {
                        if (Double.isFinite(openInterest) && openInterest > 0) previousOpenInterest = openInterest;
                        openInterest = oi;
                        if (Double.isFinite(previousOpenInterest) && previousOpenInterest > 0) {
                            oiChangePct = (openInterest - previousOpenInterest) / previousOpenInterest * 100.0;
                        }
                    });
                } catch (Exception ignored) {}
            }
        });
    }

    private int trendBias(List<Candle> list) {
        if (list == null || list.size() < 30) return 0;
        int n = list.size();
        double[] close = new double[n];
        for (int i = 0; i < n; i++) close[i] = list.get(i).c;
        double[] e9 = ema(close, 9), e21 = ema(close, 21);
        int i = n - 1;
        if (!Double.isFinite(e9[i]) || !Double.isFinite(e21[i])) return 0;
        double slope = e21[i] - e21[Math.max(20, i - 2)];
        if (e9[i] > e21[i] && close[i] > e21[i] && slope > 0) return 1;
        if (e9[i] < e21[i] && close[i] < e21[i] && slope < 0) return -1;
        return 0;
    }

    private int strategyPerformanceAdjustment(String strategy, String side) {
        int samples = 0, wins = 0;
        for (int i = trades.size() - 1; i >= 0 && samples < 40; i--) {
            JSONObject t = trades.get(i);
            if (!"CLOSED".equals(t.optString("status"))) continue;
            if (!symbol.equals(t.optString("symbol"))) continue;
            if (!side.equals(t.optString("side"))) continue;
            if (!t.optString("stage", "").startsWith(strategy)) continue;
            samples++;
            if (t.optBoolean("h1", false)) wins++;
        }
        if (samples < 20) return 0;
        double hit = wins / (double) samples;
        if (hit >= 0.65) return 4;
        if (hit >= 0.58) return 2;
        if (hit <= 0.40) return -4;
        if (hit <= 0.48) return -2;
        return 0;
    }

'''
s = replace_once(s, helper_anchor, helpers + helper_anchor, "ensemble helper insertion")

s = replace_once(
    s,
    '''            t.put("stage", stage);
            t.put("score", score);''',
    '''            t.put("stage", stage);
            t.put("strategy", activeStrategy);
            t.put("regime", marketRegime);
            t.put("confidence", ensembleConfidence);
            t.put("ensembleReason", ensembleReason);
            t.put("score", score);''',
    "trade metadata")

SERVICE.write_text(s, encoding="utf-8")

# UI bridge: expose native regime/strategy/confidence to the existing background panel.
a = ACTIVITY.read_text(encoding="utf-8")
a = replace_once(
    a,
    '''                o.put("engineMs", prefs.getString("engine_ms", ""));
                return o.toString();''',
    '''                o.put("engineMs", prefs.getString("engine_ms", ""));
                o.put("marketRegime", prefs.getString("market_regime", "WARMING UP"));
                o.put("activeStrategy", prefs.getString("active_strategy", "WAIT"));
                o.put("ensembleConfidence", prefs.getInt("ensemble_confidence", 0));
                o.put("ensembleReason", prefs.getString("ensemble_reason", ""));
                o.put("fundingRate", prefs.getString("funding_rate", ""));
                o.put("oiChangePct", prefs.getString("oi_change_pct", ""));
                o.put("spreadBps", prefs.getString("spread_bps", ""));
                return o.toString();''',
    "native state bridge")
a = replace_once(
    a,
    '''e=document.getElementById('bgHeartbeat');if(e)e.textContent=(st.tickAgeMs!=null?('tick age '+st.tickAgeMs+' ms · '):'')+(st.feedMode||'STARTING');''',
    '''e=document.getElementById('bgHeartbeat');if(e)e.textContent=(st.tickAgeMs!=null?('tick age '+st.tickAgeMs+' ms · '):'')+(st.feedMode||'STARTING')+' · '+(st.marketRegime||'')+' · '+(st.activeStrategy||'WAIT')+' · Q'+(st.ensembleConfidence||0);''',
    "UI regime line")
ACTIVITY.write_text(a, encoding="utf-8")

# App version.
g = GRADLE.read_text(encoding="utf-8")
g = g.replace('versionCode = 19', 'versionCode = 20')
g = g.replace('versionName = "1.9.0"', 'versionName = "2.0.0"')
GRADLE.write_text(g, encoding="utf-8")

print("DhanPulse Adaptive Ensemble V2 patch applied")
