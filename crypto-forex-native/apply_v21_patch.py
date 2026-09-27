from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
SERVICE = ROOT / "app/src/main/java/com/dhanpulse/cryptofxnative/BackgroundService.java"
ACTIVITY = ROOT / "app/src/main/java/com/dhanpulse/cryptofxnative/MainActivity.java"
GRADLE = ROOT / "app/build.gradle.kts"
INDEX = ROOT / "app/src/main/assets/index.html"


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
    in_str = None
    esc = False
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


def replace_js_function(text, name, new_func):
    sig = f"function {name}("
    return replace_method(text, sig, new_func)


# -----------------------------------------------------------------------------
# Native service: clean V2.1 storage and richer rolling microstructure context.
# -----------------------------------------------------------------------------
s = SERVICE.read_text(encoding="utf-8")

s = replace_once(s,
    '    private static final String TRADES_KEY = "native_trades_json";',
    '    private static final String TRADES_KEY = "native_trades_v21_json";',
    "clean v2.1 trade store")

s = replace_once(s,
    '''    private volatile long lastEnsembleSignalAt = 0L;\n    private volatile String lastEnsembleKey = "";''',
    '''    private volatile long lastEnsembleSignalAt = 0L;
    private volatile String lastEnsembleKey = "";

    // V2.1 clean algorithm context. Raw aggTrade flow remains short lived for the
    // turning detector, while compact one second buckets retain three minutes of
    // directional flow without keeping every tick in memory.
    private final ArrayDeque<FlowBucket> flowBuckets = new ArrayDeque<>();
    private final ArrayDeque<DepthSample> depthSamples = new ArrayDeque<>();
    private final ArrayDeque<OiSample> oiSamples = new ArrayDeque<>();
    private volatile double flow3s = 0.0, flow10s = 0.0, flow30s = 0.0, flow60s = 0.0, flow180s = 0.0;
    private volatile double depth1s = 0.0, depth3s = 0.0, depth10s = 0.0;
    private volatile double oi1m = 0.0, oi5m = 0.0, oi15m = 0.0;
    private volatile long lastDepthReceived = 0L;

    // Two stage setup confirmation. A strategy must remain valid across several
    // live trade events before an entry is recorded.
    private String armedSetupKey = "";
    private long armedSetupAt = 0L;
    private int armedSetupCount = 0;
    private double armedSetupPrice = Double.NaN;
    private int armedSetupDir = 0;''',
    "v2.1 context fields")

# Use depth20 instead of one level bookTicker.
s = replace_once(s,
    '''        String streams = lower + "@aggTrade/" + lower + "@bookTicker/" + lower + "@markPrice@1s/" + lower + "@kline_1m/" + lower + "@kline_15m/" + lower + "@kline_1h";''',
    '''        String streams = lower + "@aggTrade/" + lower + "@depth20@100ms/" + lower + "@markPrice@1s/" + lower + "@kline_1m/" + lower + "@kline_15m/" + lower + "@kline_1h";''',
    "depth20 stream")

old_depth_branch = '''            } else if (stream.endsWith("@bookTicker")) {
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
            } else if (stream.contains("@markPrice")) {'''
new_depth_branch = '''            } else if (stream.contains("@depth20")) {
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
            } else if (stream.contains("@markPrice")) {'''
s = replace_once(s, old_depth_branch, new_depth_branch, "depth20 processing")

# Add compact flow buckets whenever an aggregate trade arrives.
s = replace_once(s,
    '''        if (buy) flowBuy += qty; else flowSell += qty;
        trimFlow(System.currentTimeMillis());''',
    '''        if (buy) flowBuy += qty; else flowSell += qty;
        updateFlowBucket(ts, qty, buy);
        trimFlow(System.currentTimeMillis());''',
    "flow buckets")

# Replace OI fetch with rolling 1m/5m/15m changes rather than comparing only two
# nearby samples.
new_oi = r'''    private void fetchOpenInterest() {
        Request req = new Request.Builder().url("https://fapi.binance.com/fapi/v1/openInterest?symbol=" + symbol).build();
        client.newCall(req).enqueue(new Callback() {
            @Override public void onFailure(Call call, IOException e) {}
            @Override public void onResponse(Call call, Response response) throws IOException {
                try (Response r = response) {
                    String body = r.body() != null ? r.body().string() : "{}";
                    JSONObject j = new JSONObject(body);
                    double oi = j.optDouble("openInterest", Double.NaN);
                    if (Double.isFinite(oi) && oi > 0) engine.execute(() -> {
                        previousOpenInterest = openInterest;
                        openInterest = oi;
                        long now = System.currentTimeMillis();
                        oiSamples.addLast(new OiSample(now, oi));
                        while (!oiSamples.isEmpty() && now - oiSamples.peekFirst().time > 20 * 60_000L) oiSamples.removeFirst();
                        oi1m = oiChangeFor(60_000L);
                        oi5m = oiChangeFor(5 * 60_000L);
                        oi15m = oiChangeFor(15 * 60_000L);
                        oiChangePct = oiComposite();
                    });
                } catch (Exception ignored) {}
            }
        });
    }'''
s = replace_method(s, "    private void fetchOpenInterest()", new_oi)

# Helper functions for persistent flow/depth and OI context.
helper_anchor = "    private double flowImbalance() {"
helpers = r'''    private void updateFlowBucket(long ts, double qty, boolean buy) {
        long sec = (ts > 0 ? ts : System.currentTimeMillis()) / 1000L;
        FlowBucket last = flowBuckets.peekLast();
        if (last == null || last.second != sec) {
            last = new FlowBucket(sec);
            flowBuckets.addLast(last);
        }
        if (buy) last.buy += Math.max(0.0, qty); else last.sell += Math.max(0.0, qty);
        long cut = sec - 185L;
        while (!flowBuckets.isEmpty() && flowBuckets.peekFirst().second < cut) flowBuckets.removeFirst();
        flow3s = flowWindow(3);
        flow10s = flowWindow(10);
        flow30s = flowWindow(30);
        flow60s = flowWindow(60);
        flow180s = flowWindow(180);
    }

    private double flowWindow(int seconds) {
        if (flowBuckets.isEmpty()) return 0.0;
        long cut = System.currentTimeMillis() / 1000L - seconds;
        double b = 0.0, s = 0.0;
        Iterator<FlowBucket> it = flowBuckets.descendingIterator();
        while (it.hasNext()) {
            FlowBucket x = it.next();
            if (x.second < cut) break;
            b += x.buy; s += x.sell;
        }
        double total = b + s;
        return total > 0 ? (b - s) / total : 0.0;
    }

    private double ensembleFlow() {
        double x = flow3s * 0.22 + flow10s * 0.28 + flow30s * 0.22 + flow60s * 0.16 + flow180s * 0.12;
        // Opposing horizons usually mean transition/noise. Dampen the apparent edge.
        if (flow3s * flow30s < -0.01) x *= 0.55;
        if (flow10s * flow60s < -0.01) x *= 0.70;
        return Math.max(-1.0, Math.min(1.0, x));
    }

    private void addDepthSample(long now, double imbalance) {
        depthSamples.addLast(new DepthSample(now, Math.max(-1.0, Math.min(1.0, imbalance))));
        while (!depthSamples.isEmpty() && now - depthSamples.peekFirst().time > 11_000L) depthSamples.removeFirst();
        depth1s = depthAverage(1_000L);
        depth3s = depthAverage(3_000L);
        depth10s = depthAverage(10_000L);
    }

    private double depthAverage(long ms) {
        if (depthSamples.isEmpty()) return 0.0;
        long cut = System.currentTimeMillis() - ms;
        double sum = 0.0; int count = 0;
        Iterator<DepthSample> it = depthSamples.descendingIterator();
        while (it.hasNext()) {
            DepthSample d = it.next();
            if (d.time < cut) break;
            sum += d.value; count++;
        }
        return count > 0 ? sum / count : 0.0;
    }

    private double depthComposite() {
        double x = depth1s * 0.45 + depth3s * 0.35 + depth10s * 0.20;
        if (depth1s * depth3s < -0.01) x *= 0.45;
        if (depth3s * depth10s < -0.01) x *= 0.65;
        return Math.max(-1.0, Math.min(1.0, x));
    }

    private double oiChangeFor(long ms) {
        if (!Double.isFinite(openInterest) || openInterest <= 0 || oiSamples.isEmpty()) return 0.0;
        long now = System.currentTimeMillis();
        OiSample base = null;
        for (OiSample x : oiSamples) {
            if (now - x.time >= ms) base = x;
            else break;
        }
        if (base == null || base.value <= 0) return 0.0;
        return (openInterest - base.value) / base.value * 100.0;
    }

    private double oiComposite() {
        double w = 0.0, sum = 0.0;
        if (Math.abs(oi1m) > 0.000001) { sum += oi1m * 0.35; w += 0.35; }
        if (Math.abs(oi5m) > 0.000001) { sum += oi5m * 0.40; w += 0.40; }
        if (Math.abs(oi15m) > 0.000001) { sum += oi15m * 0.25; w += 0.25; }
        return w > 0 ? sum / w : 0.0;
    }

    private void resetArmedSetup() {
        armedSetupKey = "";
        armedSetupAt = 0L;
        armedSetupCount = 0;
        armedSetupPrice = Double.NaN;
        armedSetupDir = 0;
    }

'''
s = replace_once(s, helper_anchor, helpers + helper_anchor, "v2.1 helpers")

# V2.1: REST is allowed to keep existing signals updated but cannot create a new
# trade. Only genuine aggregate-trade WebSocket events may run the entry engine.
old_process = '''        checkTrades(price, exchangeTs);
        Turning turn = detectTurningFast(price);
        signalState = turn.state;
        considerFastTurning(turn, price);
        if (now - lastMainSignalAt > 150) {
            lastMainSignalAt = now;
            analyseMainAndMaybeRecord();
        }
        lastEngineMs = (System.nanoTime() - startNs) / 1_000_000.0;'''
new_process = '''        checkTrades(price, exchangeTs);
        Turning turn = detectTurningFast(price);
        signalState = turn.state;
        considerFastTurning(turn, price);
        if ("WS TRADE".equals(source) && now - lastMainSignalAt > 150) {
            lastMainSignalAt = now;
            analyseMainAndMaybeRecord();
        } else if (!"WS TRADE".equals(source)) {
            signalState = "MONITOR ONLY · " + source;
        }
        lastEngineMs = (System.nanoTime() - startNs) / 1_000_000.0;'''
s = replace_once(s, old_process, new_process, "WS only entries")

# One clean V2.1 adaptive authority, persistent flow/depth context, and a two
# stage ARMED -> TRIGGER confirmation.
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

        marketRegime = result.regime;
        activeStrategy = result.strategy;
        ensembleConfidence = result.confidence;
        ensembleReason = result.reason + String.format(Locale.US,
                " · F3 %.2f F30 %.2f F180 %.2f · D1 %.2f D10 %.2f · OI1 %.3f OI5 %.3f OI15 %.3f",
                flow3s, flow30s, flow180s, depth1s, depth10s, oi1m, oi5m, oi15m);

        boolean wsHealthy = "WS TRADE".equals(feedMode) && lastTickReceived > 0 && now - lastTickReceived <= 1500;
        boolean depthHealthy = lastDepthReceived > 0 && now - lastDepthReceived <= 1800;
        if (!wsHealthy) {
            resetArmedSetup();
            signalState = "MONITOR ONLY · LIVE TRADE FEED REQUIRED";
            return;
        }
        if (!depthHealthy) {
            resetArmedSetup();
            signalState = "WAIT · DEPTH20 WARMING";
            return;
        }
        if (!result.trade) {
            resetArmedSetup();
            signalState = result.regime + " · WAIT";
            return;
        }

        String side = result.dir > 0 ? "BUY" : "SELL";
        int performanceAdj = strategyPerformanceAdjustment(result.strategy, side);
        int effectiveConfidence = Math.max(0, Math.min(99, result.confidence + performanceAdj));
        ensembleConfidence = effectiveConfidence;
        if (performanceAdj <= -4 && effectiveConfidence < 76) {
            resetArmedSetup();
            signalState = result.strategy + " · PERFORMANCE VETO";
            return;
        }

        // Strong disagreement from persistent flow or depth vetoes the setup even
        // if lagging indicators are still aligned.
        if (result.dir * stableFlow < -0.12 || result.dir * stableDepth < -0.14) {
            resetArmedSetup();
            signalState = result.strategy + " · ORDER FLOW VETO";
            return;
        }

        double av = atrLast(mainCandles, 14);
        if (!Double.isFinite(av) || av <= 0) av = Math.abs(px) * 0.004;
        String armKey = symbol + "|" + tf + "|" + result.strategy + "|" + side;
        if (!armKey.equals(armedSetupKey)) {
            armedSetupKey = armKey;
            armedSetupAt = now;
            armedSetupCount = 1;
            armedSetupPrice = px;
            armedSetupDir = result.dir;
            signalState = "ARMED " + result.strategy + " " + side + " · Q" + effectiveConfidence;
            return;
        }

        // Cancel a setup that deteriorates before confirmation.
        if (now - armedSetupAt > 5_000L ||
                (armedSetupDir > 0 && px < armedSetupPrice - av * 0.22) ||
                (armedSetupDir < 0 && px > armedSetupPrice + av * 0.22)) {
            resetArmedSetup();
            signalState = "WAIT · SETUP INVALIDATED";
            return;
        }

        armedSetupCount++;
        if (armedSetupCount < 4 || now - armedSetupAt < 650L) {
            signalState = "ARMED " + result.strategy + " " + side + " · " + armedSetupCount + "/4 · Q" + effectiveConfidence;
            return;
        }

        long candleTime = mainCandles.get(n - 1).t;
        String key = symbol + "|" + tf + "|" + result.strategy + "|" + side + "|" + candleTime;
        if (key.equals(lastEnsembleKey) && now - lastEnsembleSignalAt < 60_000L) {
            resetArmedSetup();
            return;
        }
        if (now - lastEnsembleSignalAt < 20_000L) {
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
        if (recordSignal(side, stage, effectiveConfidence, plan, "native clean adaptive ensemble v2.1")) {
            lastEnsembleKey = key;
            lastEnsembleSignalAt = now;
            signalState = "TRIGGERED " + stage + " · Q" + effectiveConfidence;
            notifySignal(side, result.strategy + " Q" + effectiveConfidence, px);
        }
        resetArmedSetup();
    }'''
s = replace_method(s, "    private void analyseMainAndMaybeRecord()", new_analyse)

# Only one open algorithm position per symbol/timeframe. This prevents opposite
# BUY and SELL records from two rapidly changing states at the same time.
s = replace_once(s,
    '''            if ("OPEN".equals(t.optString("status")) && symbol.equals(t.optString("symbol")) && tf.equals(t.optString("tf")) && side.equals(t.optString("side"))) return false;''',
    '''            if ("OPEN".equals(t.optString("status")) && symbol.equals(t.optString("symbol")) && tf.equals(t.optString("tf"))) return false;''',
    "single open algorithm position")

s = replace_once(s,
    '''            t.put("source", source);
            t.put("stage", stage);''',
    '''            t.put("source", source);
            t.put("engineVersion", "2.1.0");
            t.put("entryFeed", feedMode);
            t.put("flow3s", flow3s);
            t.put("flow30s", flow30s);
            t.put("flow180s", flow180s);
            t.put("depth1s", depth1s);
            t.put("depth10s", depth10s);
            t.put("oi1m", oi1m);
            t.put("oi5m", oi5m);
            t.put("oi15m", oi15m);
            t.put("stage", stage);''',
    "v2.1 trade metadata")

# Add clean-engine state to heartbeat.
s = replace_once(s,
    '''                .putString("spread_bps", Double.isFinite(spreadBps) ? String.format(Locale.US, "%.3f", spreadBps) : "");''',
    '''                .putString("spread_bps", Double.isFinite(spreadBps) ? String.format(Locale.US, "%.3f", spreadBps) : "")
                .putString("flow_3s", String.format(Locale.US, "%.3f", flow3s))
                .putString("flow_30s", String.format(Locale.US, "%.3f", flow30s))
                .putString("flow_180s", String.format(Locale.US, "%.3f", flow180s))
                .putString("depth_1s", String.format(Locale.US, "%.3f", depth1s))
                .putString("depth_10s", String.format(Locale.US, "%.3f", depth10s))
                .putString("oi_1m", String.format(Locale.US, "%.4f", oi1m))
                .putString("oi_5m", String.format(Locale.US, "%.4f", oi5m))
                .putString("oi_15m", String.format(Locale.US, "%.4f", oi15m));''',
    "v2.1 heartbeat context")

# Add compact helper data classes.
class_anchor = "    private static final class Turning {"
classes = r'''    private static final class FlowBucket {
        final long second;
        double buy = 0.0, sell = 0.0;
        FlowBucket(long second) { this.second = second; }
    }

    private static final class DepthSample {
        final long time;
        final double value;
        DepthSample(long time, double value) { this.time = time; this.value = value; }
    }

    private static final class OiSample {
        final long time;
        final double value;
        OiSample(long time, double value) { this.time = time; this.value = value; }
    }

'''
s = replace_once(s, class_anchor, classes + class_anchor, "v2.1 helper classes")
SERVICE.write_text(s, encoding="utf-8")


# -----------------------------------------------------------------------------
# Android bridge: the native V2.1 store is authoritative. A different key means
# previous V1/V2 records cannot contaminate the clean forward test.
# -----------------------------------------------------------------------------
a = ACTIVITY.read_text(encoding="utf-8")
a = a.replace('private static final String TRADES = "native_trades_json";',
              'private static final String TRADES = "native_trades_v21_json";')
a = a.replace("var K='dhanpulse_cf_android_trades_v1';", "var K='dhanpulse_cf_android_trades_v21';")
a = a.replace('setInterval(sync,1000);sync();})();', 'setInterval(sync,500);sync();})();')

# Native state exposes the stable context so the UI can confirm the real engine
# rather than the browser-only calculations.
a = replace_once(a,
    '''                o.put("spreadBps", prefs.getString("spread_bps", ""));
                return o.toString();''',
    '''                o.put("spreadBps", prefs.getString("spread_bps", ""));
                o.put("flow3s", prefs.getString("flow_3s", ""));
                o.put("flow30s", prefs.getString("flow_30s", ""));
                o.put("flow180s", prefs.getString("flow_180s", ""));
                o.put("depth1s", prefs.getString("depth_1s", ""));
                o.put("depth10s", prefs.getString("depth_10s", ""));
                o.put("oi1m", prefs.getString("oi_1m", ""));
                o.put("oi5m", prefs.getString("oi_5m", ""));
                o.put("oi15m", prefs.getString("oi_15m", ""));
                return o.toString();''',
    "v2.1 native state")

# Update the visible background status with the native signal/feed state.
a = replace_once(a,
    '''e=document.getElementById('bgHeartbeat');if(e)e.textContent=(st.tickAgeMs!=null?('tick age '+st.tickAgeMs+' ms · '):'')+(st.feedMode||'STARTING')+' · '+(st.marketRegime||'')+' · '+(st.activeStrategy||'WAIT')+' · Q'+(st.ensembleConfidence||0);''',
    '''e=document.getElementById('bgHeartbeat');if(e)e.textContent=(st.tickAgeMs!=null?('tick age '+st.tickAgeMs+' ms · '):'')+(st.feedMode||'STARTING')+' · '+(st.signalState||'MONITORING')+' · '+(st.marketRegime||'')+' · '+(st.activeStrategy||'WAIT')+' · Q'+(st.ensembleConfidence||0);var tl=document.getElementById('tradeLogState');if(tl)tl.textContent='Native V2.1 performance: '+(st.feedMode||'STARTING')+' · tick age '+(st.tickAgeMs>=0?st.tickAgeMs:'NA')+' ms';''',
    "native UI feed status")
ACTIVITY.write_text(a, encoding="utf-8")


# -----------------------------------------------------------------------------
# Web UI: display only. Browser calculations can still draw the chart, but they
# are forbidden from creating or mutating V2.1 trade records.
# -----------------------------------------------------------------------------
h = INDEX.read_text(encoding="utf-8")
h = h.replace('var TRKEY="dhanpulse_cf_android_trades_v1", KEY=',
              'var TRKEY="dhanpulse_cf_android_trades_v21", KEY=')

h = replace_js_function(h, "considerFastTurning",
    '''function considerFastTurning(){return}''')
h = replace_js_function(h, "recordFast",
    '''function recordFast(src){return}''')
h = replace_js_function(h, "record",
    '''function record(src){return}''')
h = replace_js_function(h, "autoRecord",
    '''function autoRecord(){return}''')
h = replace_js_function(h, "updateTradesWithTick",
    '''function updateTradesWithTick(price,evt,source){S.lastTradeLogAt=Date.now();S.lastTradeLogSource="NATIVE V2.1";renderTradeLogState(false)}''')
h = replace_js_function(h, "updateAllTrades",
    '''function updateAllTrades(){return}''')
h = replace_js_function(h, "updateWithCandle",
    '''function updateWithCandle(c){return}''')

new_render = r'''function renderTrades(){renderTradeLogState(true);var ts=trades().slice().reverse(),tot=ts.length,closed=ts.filter(function(t){return t.status==="CLOSED"}),wins=closed.filter(function(t){return t.result==="T3"}).length,losses=closed.filter(function(t){return t.result==="SL"}).length,open=ts.filter(function(t){return t.status==="OPEN"}).length,h1=ts.filter(function(t){return t.h1}).length,h2=ts.filter(function(t){return t.h2}).length,h3=ts.filter(function(t){return t.h3}).length,pc=function(n,d){return d?((n/d)*100).toFixed(1)+"%":"0.0%"};q("perf").innerHTML='<div><span>V2.1 Signals</span><b>'+tot+'</b></div><div><span>Closed Trades</span><b>'+closed.length+'</b></div><div><span>Closed Win Rate</span><b>'+pc(wins,closed.length)+'</b></div><div><span>SL Rate Closed</span><b>'+pc(losses,closed.length)+'</b></div><div><span>T1 Touch Rate</span><b>'+pc(h1,tot)+'</b></div><div><span>T2 Touch Rate</span><b>'+pc(h2,tot)+'</b></div><div><span>T3 Hit Rate</span><b>'+pc(h3,tot)+'</b></div><div><span>Open Signals</span><b>'+open+'</b></div>';q("trades").innerHTML=ts.slice(0,100).map(function(t){var d=dec(t.entry),label=(t.strategy||t.stage||"V2.1");return'<tr><td>'+new Date(t.createdAt).toLocaleString("en-IN")+'</td><td>'+t.market+'</td><td>'+t.symbol+'</td><td>'+t.tf+'</td><td>'+t.side+'<br><small>'+label+'</small></td><td>'+fmt(t.entry,d)+'</td><td>'+fmt(t.sl,d)+'</td><td>'+fmt(t.t1,d)+'</td><td>'+fmt(t.t2,d)+'</td><td>'+fmt(t.t3,d)+'</td><td>'+t.status+'</td><td>'+t.result+'</td></tr>'}).join("")||'<tr><td colspan="12">No V2.1 signals recorded yet.</td></tr>'}'''
h = replace_js_function(h, "renderTrades", new_render)

h = h.replace('q("refresh").onclick=load;q("record").onclick=function(){if(effectiveSignal())recordFast("manual-fast");else record("manual")};',
              'q("refresh").onclick=load;q("record").disabled=true;q("record").textContent="Native V2.1 Auto";q("record").onclick=function(){};')
h = h.replace('Version 2.0.0 Adaptive Ensemble', 'Version 2.1.0 Clean Algorithm')
INDEX.write_text(h, encoding="utf-8")


# App version.
g = GRADLE.read_text(encoding="utf-8")
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 21', g)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.1.0"', g)
GRADLE.write_text(g, encoding="utf-8")

print("DhanPulse V2.1 clean native algorithm patch applied")
