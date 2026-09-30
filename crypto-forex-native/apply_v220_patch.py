from pathlib import Path
import re

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
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise SystemExit(f"Method end not found: {signature}")
    return text[:start] + new_method.rstrip() + text[end:]


def replace_js_function(text, name, new_func):
    return replace_method(text, f"function {name}(", new_func)


s = SERVICE.read_text(encoding="utf-8")

# Start a clean V2.2 forward-test store. The old V2.1.x records remain untouched
# in their previous SharedPreferences key, but no longer contaminate V2.2 stats.
s = s.replace('private static final String TRADES_KEY = "native_trades_v21_json";',
              'private static final String TRADES_KEY = "native_trades_v22_json";')

helper_anchor = '    private boolean recordSignal(String side, String stage, int score, Plan plan, String source) {'
helpers = r'''    private int precisionMinQuality(String strategy) {
        if ("TREND CONTINUATION".equals(strategy)) return 80;
        if ("BREAKOUT".equals(strategy)) return 82;
        if ("PULLBACK".equals(strategy)) return 81;
        if ("LIQUIDITY REVERSAL".equals(strategy)) return 85;
        if ("MEAN REVERSION".equals(strategy)) return 86;
        if ("MOMENTUM IGNITION".equals(strategy)) return 82;
        return 82;
    }

    private boolean directionalFamily(String strategy) {
        return "TREND CONTINUATION".equals(strategy)
                || "BREAKOUT".equals(strategy)
                || "PULLBACK".equals(strategy)
                || "MOMENTUM IGNITION".equals(strategy);
    }

    private boolean reversalFamily(String strategy) {
        return "LIQUIDITY REVERSAL".equals(strategy) || "MEAN REVERSION".equals(strategy);
    }

    private int recentLossStreak() {
        int streak = 0;
        for (int i = trades.size() - 1; i >= 0; i--) {
            JSONObject t = trades.get(i);
            if (!symbol.equals(t.optString("symbol")) || !tf.equals(t.optString("tf"))) continue;
            if (!"CLOSED".equals(t.optString("status"))) continue;
            String r = t.optString("result", "");
            if ("SL".equals(r)) streak++; else break;
            if (streak >= 5) break;
        }
        return streak;
    }

    private int recentClosedCount(int maxN) {
        int count = 0;
        for (int i = trades.size() - 1; i >= 0 && count < maxN; i--) {
            JSONObject t = trades.get(i);
            if (symbol.equals(t.optString("symbol")) && tf.equals(t.optString("tf"))
                    && "CLOSED".equals(t.optString("status"))) count++;
        }
        return count;
    }

    private double recentClosedWinRate(int maxN) {
        int count = 0, wins = 0;
        for (int i = trades.size() - 1; i >= 0 && count < maxN; i--) {
            JSONObject t = trades.get(i);
            if (!symbol.equals(t.optString("symbol")) || !tf.equals(t.optString("tf"))) continue;
            if (!"CLOSED".equals(t.optString("status"))) continue;
            count++;
            String r = t.optString("result", "");
            if ("T3".equals(r) || "T1 LOCK".equals(r)) wins++;
        }
        return count > 0 ? wins / (double) count : -1.0;
    }

'''
if helper_anchor not in s:
    raise SystemExit('V2.2 helper anchor not found')
s = s.replace(helper_anchor, helpers + helper_anchor, 1)

new_record = r'''    private boolean recordSignal(String side, String stage, int score, Plan plan, String source) {
        reloadTradesFromPrefs();
        long now = System.currentTimeMillis();

        // One live algorithm position per symbol/timeframe. V2.1.9 could stack
        // correlated signals from different strategies and amplify one bad regime.
        for (JSONObject t : trades) {
            if ("OPEN".equals(t.optString("status"))
                    && symbol.equals(t.optString("symbol"))
                    && tf.equals(t.optString("tf"))) return false;
        }

        long duplicateWindow = Math.max(45_000L, Math.min(180_000L, tfMillis(tf) / 2L));
        long postLossPause = Math.max(60_000L, Math.min(180_000L, tfMillis(tf) / 2L));
        for (int i = trades.size() - 1; i >= 0; i--) {
            JSONObject t = trades.get(i);
            if (!symbol.equals(t.optString("symbol")) || !tf.equals(t.optString("tf"))) continue;
            long created = t.optLong("createdAt", 0L);
            String tSide = t.optString("side", "");
            String tStage = t.optString("stage", "");
            if (side.equals(tSide) && stage.equals(tStage) && created > 0 && now - created < duplicateWindow) return false;
            if ("CLOSED".equals(t.optString("status")) && "SL".equals(t.optString("result"))
                    && side.equals(tSide) && stage.equals(tStage)) {
                long closed = t.optLong("closedAt", 0L);
                if (closed > 0 && now - closed < postLossPause) return false;
                break;
            }
        }

        try {
            JSONObject t = new JSONObject();
            String slot = "crypto|" + symbol + "|" + tf + "|" + stage + "|" + (now / 1000L);
            t.put("id", "native-" + now + "-" + Math.abs(slot.hashCode()));
            t.put("slot", slot);
            t.put("key", slot);
            t.put("source", source);
            t.put("engineVersion", "2.2.0");
            t.put("entryFeed", feedMode);
            t.put("flow3s", flow3s);
            t.put("flow30s", flow30s);
            t.put("flow180s", flow180s);
            t.put("depth1s", depth1s);
            t.put("depth10s", depth10s);
            t.put("oi1m", oi1m);
            t.put("oi5m", oi5m);
            t.put("oi15m", oi15m);
            t.put("stage", stage);
            t.put("strategy", stage.replace(" BUY", "").replace(" SELL", ""));
            t.put("score", score);
            t.put("shiftScore", 0);
            t.put("createdAt", now);
            t.put("signalCandleTime", mainCandles.isEmpty() ? now : mainCandles.get(mainCandles.size() - 1).t);
            t.put("market", "crypto");
            t.put("symbol", symbol);
            t.put("tf", tf);
            t.put("side", side);
            t.put("entry", plan.entry);
            t.put("sl", plan.sl);
            t.put("protectedSl", plan.sl);
            t.put("t1", plan.t1);
            t.put("t2", plan.t2);
            t.put("t3", plan.t3);
            t.put("status", "OPEN");
            t.put("result", "OPEN");
            t.put("h1", false);
            t.put("h2", false);
            t.put("h3", false);
            t.put("closedAt", JSONObject.NULL);
            t.put("updatedAt", now);
            trades.add(t);
            while (trades.size() > 1500) trades.remove(0);
            persistTrades();
            prefs.edit()
                    .putLong("last_signal_recorded_at", now)
                    .putString("last_signal_recorded_id", t.optString("id", ""))
                    .putString("last_signal_recorded_side", side)
                    .putString("last_signal_recorded_stage", stage)
                    .apply();
            return true;
        } catch (Exception ex) {
            return false;
        }
    }'''
s = replace_method(s, '    private boolean recordSignal(String side, String stage, int score, Plan plan, String source)', new_record)

new_check = r'''    private void checkTrades(double price, long evt) {
        boolean anyChanged = false;
        for (JSONObject t : trades) {
            if (!"OPEN".equals(t.optString("status"))) continue;
            if (!symbol.equals(t.optString("symbol"))) continue;
            boolean changed = false;
            String side = t.optString("side", "");
            double entry = t.optDouble("entry", Double.NaN);
            double sl = t.optDouble("sl", Double.NaN);
            double t1 = t.optDouble("t1", Double.NaN);
            double t2 = t.optDouble("t2", Double.NaN);
            double t3 = t.optDouble("t3", Double.NaN);
            try {
                if ("BUY".equals(side)) {
                    if (Double.isFinite(t1) && price >= t1 && !t.optBoolean("h1")) {
                        t.put("h1", true); t.put("protectedSl", entry); changed = true;
                    }
                    if (Double.isFinite(t2) && price >= t2 && !t.optBoolean("h2")) {
                        t.put("h2", true); t.put("protectedSl", t1); changed = true;
                    }
                    if (Double.isFinite(t3) && price >= t3) {
                        t.put("h3", true); t.put("status", "CLOSED"); t.put("result", "T3"); t.put("closedAt", evt); changed = true;
                    } else if ("OPEN".equals(t.optString("status"))) {
                        double protectedSl = t.optBoolean("h2") && Double.isFinite(t1) ? t1
                                : t.optBoolean("h1") && Double.isFinite(entry) ? entry : sl;
                        if (Double.isFinite(protectedSl) && price <= protectedSl) {
                            t.put("status", "CLOSED");
                            t.put("result", t.optBoolean("h2") ? "T1 LOCK" : t.optBoolean("h1") ? "BE" : "SL");
                            t.put("closedAt", evt); changed = true;
                        }
                    }
                } else if ("SELL".equals(side)) {
                    if (Double.isFinite(t1) && price <= t1 && !t.optBoolean("h1")) {
                        t.put("h1", true); t.put("protectedSl", entry); changed = true;
                    }
                    if (Double.isFinite(t2) && price <= t2 && !t.optBoolean("h2")) {
                        t.put("h2", true); t.put("protectedSl", t1); changed = true;
                    }
                    if (Double.isFinite(t3) && price <= t3) {
                        t.put("h3", true); t.put("status", "CLOSED"); t.put("result", "T3"); t.put("closedAt", evt); changed = true;
                    } else if ("OPEN".equals(t.optString("status"))) {
                        double protectedSl = t.optBoolean("h2") && Double.isFinite(t1) ? t1
                                : t.optBoolean("h1") && Double.isFinite(entry) ? entry : sl;
                        if (Double.isFinite(protectedSl) && price >= protectedSl) {
                            t.put("status", "CLOSED");
                            t.put("result", t.optBoolean("h2") ? "T1 LOCK" : t.optBoolean("h1") ? "BE" : "SL");
                            t.put("closedAt", evt); changed = true;
                        }
                    }
                }
                if ("OPEN".equals(t.optString("status"))) {
                    String result = t.optBoolean("h2") ? "T2 protected" : t.optBoolean("h1") ? "T1 protected" : "OPEN";
                    if (!result.equals(t.optString("result"))) { t.put("result", result); changed = true; }
                }
                if (changed) {
                    t.put("updatedAt", System.currentTimeMillis());
                    anyChanged = true;
                }
            } catch (Exception ignored) {}
        }
        if (anyChanged) persistTrades();
    }'''
s = replace_method(s, '    private void checkTrades(double price, long evt)', new_check)

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

        double av = atrLast(mainCandles, 14);
        if (!Double.isFinite(av) || av <= 0) av = Math.abs(px) * 0.004;
        double[] e9v = ema(c, 9);
        double e9Now = e9v.length > 0 ? e9v[e9v.length - 1] : Double.NaN;
        double extension = Double.isFinite(e9Now) ? Math.abs(px - e9Now) / Math.max(av, 1e-9) : 0.0;

        int minQuality = precisionMinQuality(result.strategy);
        if (degradedEntryFeedNow) minQuality += 4;
        int lossStreak = recentLossStreak();
        if (lossStreak >= 2) minQuality += 3;
        if (lossStreak >= 3) minQuality += 3;
        int recentClosed = recentClosedCount(20);
        double recentWin = recentClosedWinRate(20);
        if (recentClosed >= 12 && recentWin >= 0 && recentWin < 0.42) minQuality += 4;
        if (recentClosed >= 12 && recentWin > 0.58) minQuality = Math.max(precisionMinQuality(result.strategy), minQuality - 1);

        boolean bothOpposite = b15 == -result.dir && b60 == -result.dir;
        if (bothOpposite && directionalFamily(result.strategy)) {
            resetArmedSetup();
            signalState = "CANDIDATE " + side + " Q" + effectiveConfidence + " · HTF VETO";
            return;
        }
        if (bothOpposite && reversalFamily(result.strategy) && effectiveConfidence < 92) {
            resetArmedSetup();
            signalState = "CANDIDATE " + side + " Q" + effectiveConfidence + " · REVERSAL HTF VETO";
            return;
        }

        if (("TREND CONTINUATION".equals(result.strategy) || "PULLBACK".equals(result.strategy)
                || "MOMENTUM IGNITION".equals(result.strategy)) && extension > 1.15) {
            resetArmedSetup();
            signalState = "CANDIDATE " + side + " Q" + effectiveConfidence + " · LATE ENTRY " + String.format(Locale.US, "%.2fATR", extension);
            return;
        }
        if ("BREAKOUT".equals(result.strategy) && extension > 1.80) {
            resetArmedSetup();
            signalState = "CANDIDATE " + side + " Q" + effectiveConfidence + " · BREAKOUT OVEREXTENDED";
            return;
        }

        if ("RANGE".equals(result.regime) && directionalFamily(result.strategy)) minQuality += 4;
        if (("TREND UP".equals(result.regime) || "TREND DOWN".equals(result.regime))
                && "MEAN REVERSION".equals(result.strategy)) minQuality += 5;
        if (!result.regime.startsWith("BREAKOUT") && "BREAKOUT".equals(result.strategy)) minQuality += 2;

        double dirFlow = result.dir * stableFlow;
        double dirDepth = result.dir * stableDepth;
        boolean hardFlowVeto = (dirFlow < -0.16 && dirDepth < -0.14) || dirFlow < -0.34 || dirDepth < -0.32;
        if (hardFlowVeto) {
            resetArmedSetup();
            signalState = result.strategy + " " + side + " · ORDER FLOW VETO";
            return;
        }
        if (directionalFamily(result.strategy)) {
            if (degradedEntryFeedNow && dirFlow < 0.12) {
                resetArmedSetup();
                signalState = "CANDIDATE " + side + " Q" + effectiveConfidence + " · DEGRADED FEED NEEDS STRONG FLOW";
                return;
            }
            if (!degradedEntryFeedNow && effectiveConfidence < 90 && dirFlow < 0.02 && dirDepth < 0.02) {
                resetArmedSetup();
                signalState = "CANDIDATE " + side + " Q" + effectiveConfidence + " · FLOW NOT CONFIRMED";
                return;
            }
        }

        if (effectiveConfidence < minQuality) {
            resetArmedSetup();
            signalState = "CANDIDATE " + side + " Q" + effectiveConfidence + " · NEED Q" + minQuality;
            return;
        }
        feedBlockReason = "";

        String armKey = symbol + "|" + tf + "|" + result.strategy + "|" + side;
        if (!armKey.equals(armedSetupKey)) {
            armedSetupKey = armKey;
            armedSetupAt = now;
            armedSetupCount = 1;
            armedSetupPrice = px;
            armedSetupDir = result.dir;
            signalState = "ARMED " + side + " · " + result.strategy + " · 1/4 · Q" + effectiveConfidence;
            return;
        }

        if (now - armedSetupAt > 5_000L ||
                (armedSetupDir > 0 && px < armedSetupPrice - av * 0.28) ||
                (armedSetupDir < 0 && px > armedSetupPrice + av * 0.28)) {
            resetArmedSetup();
            signalState = "WAIT · SETUP INVALIDATED";
            return;
        }

        armedSetupCount++;
        int requiredCount = effectiveConfidence >= 92 ? 2 : effectiveConfidence >= 86 ? 3 : 4;
        long requiredMs = effectiveConfidence >= 92 ? 300L : effectiveConfidence >= 86 ? 550L : 850L;
        if (armedSetupCount < requiredCount || now - armedSetupAt < requiredMs) {
            signalState = "ARMED " + side + " · " + result.strategy + " · " + armedSetupCount + "/" + requiredCount + " · Q" + effectiveConfidence;
            return;
        }

        long candleTime = mainCandles.get(n - 1).t;
        String key = symbol + "|" + tf + "|" + result.strategy + "|" + side + "|" + candleTime;
        if (key.equals(lastEnsembleKey) && now - lastEnsembleSignalAt < 90_000L) {
            resetArmedSetup();
            return;
        }
        if (now - lastEnsembleSignalAt < 30_000L) {
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
            if (risk > av * 2.10) { risk = av * 2.10; sl = px - risk; }
            plan = new Plan(px, sl, px + risk, px + risk * 1.55, px + risk * 2.20);
        } else {
            double structureStop = structureHigh + av * 0.08;
            double sl = Math.max(px + baseRisk, structureStop);
            double risk = sl - px;
            if (risk > av * 2.10) { risk = av * 2.10; sl = px + risk; }
            plan = new Plan(px, sl, px - risk, px - risk * 1.55, px - risk * 2.20);
        }

        String stage = result.strategy + " " + side;
        if (recordSignal(side, stage, effectiveConfidence, plan, "native precision v2.2.0 · " + feedMode)) {
            lastEnsembleKey = key;
            lastEnsembleSignalAt = now;
            signalState = "TRIGGERED " + stage + " · Q" + effectiveConfidence;
            feedBlockReason = "";
            notifySignal(side, result.strategy + " Q" + effectiveConfidence, px);
        } else {
            signalState = "WAIT · EXISTING SIGNAL / REENTRY COOLDOWN";
        }
        resetArmedSetup();
    }'''
s = replace_method(s, '    private void analyseMainAndMaybeRecord()', new_analyse)

s = re.sub(r'engineVersion", "2\.1\.\d+"', 'engineVersion", "2.2.0"', s)
s = s.replace('native multi strategy v2.1.9', 'native precision v2.2.0')
SERVICE.write_text(s, encoding="utf-8")


a = ACTIVITY.read_text(encoding="utf-8")
a = a.replace('native_trades_v21_json', 'native_trades_v22_json')
a = a.replace('dhanpulse_cf_android_trades_v211', 'dhanpulse_cf_android_trades_v220')
a = re.sub(r'Native V2\.1\.\d+', 'Native V2.2.0', a)
a = a.replace('2.1.9', '2.2.0')
ACTIVITY.write_text(a, encoding="utf-8")


h = INDEX.read_text(encoding="utf-8")
new_render = r'''function renderTrades(){renderTradeLogState(true);var ts=trades().slice().reverse(),tot=ts.length,closed=ts.filter(function(t){return t.status==="CLOSED"}),wins=closed.filter(function(t){return t.result==="T3"||t.result==="T1 LOCK"}).length,losses=closed.filter(function(t){return t.result==="SL"}).length,be=closed.filter(function(t){return t.result==="BE"}).length,open=ts.filter(function(t){return t.status==="OPEN"}).length,h1=ts.filter(function(t){return t.h1}).length,h2=ts.filter(function(t){return t.h2}).length,h3=ts.filter(function(t){return t.h3}).length,pc=function(n,d){return d?((n/d)*100).toFixed(1)+"%":"0.0%"},rSum=closed.reduce(function(s,t){return s+(t.result==="T3"?2.2:t.result==="T1 LOCK"?1.0:t.result==="BE"?0:-1)},0),exp=closed.length?(rSum/closed.length).toFixed(2)+"R":"0.00R";q("perf").innerHTML='<div><span>V2.2 Signals</span><b>'+tot+'</b></div><div><span>Closed Trades</span><b>'+closed.length+'</b></div><div><span>Closed Win Rate</span><b>'+pc(wins,closed.length)+'</b></div><div><span>SL Rate Closed</span><b>'+pc(losses,closed.length)+'</b></div><div><span>BE Rate</span><b>'+pc(be,closed.length)+'</b></div><div><span>Expectancy</span><b>'+exp+'</b></div><div><span>T1 Touch Rate</span><b>'+pc(h1,tot)+'</b></div><div><span>T2 Touch Rate</span><b>'+pc(h2,tot)+'</b></div><div><span>T3 Hit Rate</span><b>'+pc(h3,tot)+'</b></div><div><span>Open Signals</span><b>'+open+'</b></div>';q("trades").innerHTML=ts.slice(0,100).map(function(t){var d=dec(t.entry),label=(t.strategy||t.stage||"V2.2");return'<tr><td>'+new Date(t.createdAt).toLocaleString("en-IN")+'</td><td>'+t.market+'</td><td>'+t.symbol+'</td><td>'+t.tf+'</td><td>'+t.side+'<br><small>'+label+'</small></td><td>'+fmt(t.entry,d)+'</td><td>'+fmt(t.sl,d)+'</td><td>'+fmt(t.t1,d)+'</td><td>'+fmt(t.t2,d)+'</td><td>'+fmt(t.t3,d)+'</td><td>'+t.status+'</td><td>'+t.result+'</td></tr>'}).join("")||'<tr><td colspan="12">No V2.2 signals recorded yet.</td></tr>'}'''
h = replace_js_function(h, 'renderTrades', new_render)
h = h.replace('Version 2.1.9 Multi Strategy Active', 'Version 2.2.0 Precision Risk Engine')
h = h.replace('V2.1.9 Signals', 'V2.2 Signals')
h = h.replace('No V2.1.9 signals recorded yet.', 'No V2.2 signals recorded yet.')
h = re.sub(r'NATIVE V2\.1\.\d+', 'NATIVE V2.2.0', h)
h = h.replace('2.1.9', '2.2.0')
INDEX.write_text(h, encoding="utf-8")


g = GRADLE.read_text(encoding="utf-8")
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 31', g)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.2.0"', g)
GRADLE.write_text(g, encoding="utf-8")

print('DhanPulse V2.2.0 precision filters, single-position control, and protected trade management applied')
