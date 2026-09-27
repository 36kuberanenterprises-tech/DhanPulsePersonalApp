from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
SERVICE = ROOT / "app/src/main/java/com/dhanpulse/cryptofxnative/BackgroundService.java"
ENSEMBLE = ROOT / "app/src/main/java/com/dhanpulse/cryptofxnative/AdaptiveEnsemble.java"
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
        raise SystemExit(f"Closing brace not found: {signature}")
    return text[:start] + new_method.rstrip() + text[end:]


# -----------------------------------------------------------------------------
# Ensemble tuning: keep quality filters, but remove the specific over-filtering
# that prevented valid intrabar trend and momentum moves from ever becoming a
# candidate.
# -----------------------------------------------------------------------------
e = ENSEMBLE.read_text(encoding="utf-8")

e = replace_once(
    e,
    '''        boolean trendUp = ema5 >= ema9 && ema9 > ema21 && ema21 > ema50 && slope21 > 0 && price > ema21;\n        boolean trendDown = ema5 <= ema9 && ema9 < ema21 && ema21 < ema50 && slope21 < 0 && price < ema21;''',
    '''        boolean trendUp = ema5 >= ema9 && ema9 > ema21 && ema21 > ema50 && slope21 > 0 && price > ema21;
        boolean trendDown = ema5 <= ema9 && ema9 < ema21 && ema21 < ema50 && slope21 < 0 && price < ema21;
        // A fresh directional move should not have to wait for EMA50 to catch up.
        // Soft trend is used only for the transition-continuation setup below.
        boolean softTrendUp = ema5 > ema9 && ema9 > ema21 && slope21 > 0 && price > ema9;
        boolean softTrendDown = ema5 < ema9 && ema9 < ema21 && slope21 < 0 && price < ema9;''',
    "soft trend definition")

# Slightly relax only the quality thresholds that were demonstrably too strict
# after persistent flow/depth confirmation is already required by the service.
e = e.replace('new Candidate(1, "TREND PULLBACK", s, 74, 1.00,', 'new Candidate(1, "TREND PULLBACK", s, 72, 1.00,')
e = e.replace('new Candidate(-1, "TREND PULLBACK", s, 74, 1.00,', 'new Candidate(-1, "TREND PULLBACK", s, 72, 1.00,')
e = e.replace('new Candidate(1, "BREAKOUT", s, 78, 1.25,', 'new Candidate(1, "BREAKOUT", s, 74, 1.25,')
e = e.replace('new Candidate(-1, "BREAKOUT", s, 78, 1.25,', 'new Candidate(-1, "BREAKOUT", s, 74, 1.25,')
e = e.replace('new Candidate(1, "MEAN REVERSION", s, 80, 0.95,', 'new Candidate(1, "MEAN REVERSION", s, 78, 0.95,')
e = e.replace('new Candidate(-1, "MEAN REVERSION", s, 80, 0.95,', 'new Candidate(-1, "MEAN REVERSION", s, 78, 0.95,')
e = e.replace('new Candidate(turningDir, "LIQUIDITY REVERSAL", s, 82, 1.10,', 'new Candidate(turningDir, "LIQUIDITY REVERSAL", s, 79, 1.10,')

e = e.replace('momentum3 > 0.72 && volumeRatio > 1.08 && (flow > 0.08 || takerRatio > 0.54)',
              'momentum3 > 0.45 && volumeRatio > 0.82 && (flow > 0.05 || takerRatio > 0.52)')
e = e.replace('momentum3 < -0.72 && volumeRatio > 1.08 && (flow < -0.08 || takerRatio < 0.46)',
              'momentum3 < -0.45 && volumeRatio > 0.82 && (flow < -0.05 || takerRatio < 0.48)')
e = e.replace('new Candidate(1, "MOMENTUM IGNITION", s, 78, 1.15,', 'new Candidate(1, "MOMENTUM IGNITION", s, 73, 1.15,')
e = e.replace('new Candidate(-1, "MOMENTUM IGNITION", s, 78, 1.15,', 'new Candidate(-1, "MOMENTUM IGNITION", s, 73, 1.15,')

transition_block = r'''
        // 1B. Fresh trend continuation. This catches a real move while EMA50 is
        // still lagging after a range/transition. Higher timeframe and live
        // order flow still have to support the direction.
        if (!trendUp && softTrendUp && adx >= 15.0 && momentum3 > 0.16) {
            int s = 54;
            if (adx >= 18.0) s += 5;
            if (momentum3 > 0.35) s += 6;
            if (volumeRatio > 0.85) s += 4;
            if (rsi >= 51 && rsi <= 73) s += 4;
            if (finite(vwap) && price > vwap) s += 3;
            s += flowScore(flow, 1, 7) + bookScore(book, 1, 4) + htfScore(bias15, bias60, 1);
            if (takerRatio > 0.52) s += 4;
            if (bias15 == -1 && bias60 == -1) s -= 12;
            bestLong = choose(bestLong, new Candidate(1, "TREND CONTINUATION", s, 70, 1.05,
                    metrics("fresh trend", adx, volumeRatio, flow, book, bias15, bias60)));
        }
        if (!trendDown && softTrendDown && adx >= 15.0 && momentum3 < -0.16) {
            int s = 54;
            if (adx >= 18.0) s += 5;
            if (momentum3 < -0.35) s += 6;
            if (volumeRatio > 0.85) s += 4;
            if (rsi >= 27 && rsi <= 49) s += 4;
            if (finite(vwap) && price < vwap) s += 3;
            s += flowScore(flow, -1, 7) + bookScore(book, -1, 4) + htfScore(bias15, bias60, -1);
            if (takerRatio < 0.48) s += 4;
            if (bias15 == 1 && bias60 == 1) s -= 12;
            bestShort = choose(bestShort, new Candidate(-1, "TREND CONTINUATION", s, 70, 1.05,
                    metrics("fresh trend", adx, volumeRatio, flow, book, bias15, bias60)));
        }

'''
e = replace_once(e, '        // 2. Breakout with participation confirmation\n', transition_block + '        // 2. Breakout with participation confirmation\n', "transition continuation insertion")
ENSEMBLE.write_text(e, encoding="utf-8")


# -----------------------------------------------------------------------------
# Service: normalize live partial-candle volume and use setup hysteresis instead
# of requiring four perfectly identical 150 ms snapshots in a row.
# -----------------------------------------------------------------------------
s = SERVICE.read_text(encoding="utf-8")

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

        // The live candle is incomplete. Comparing its raw volume with complete
        // historical candles systematically understates participation until late
        // in the bar. Project it conservatively by elapsed candle time, capped at
        // 3x so the first seconds cannot create an unrealistic volume spike.
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

        // Do not throw away an already valid setup because of one noisy 100 ms
        // depth/flow snapshot. Give it a short grace period, then require the
        // strategy to become valid again before the timer expires.
        if (!result.trade) {
            if (!armedSetupKey.isEmpty() && now - armedSetupAt <= 2_500L) {
                signalState = "ARMED HOLD · " + armedSetupKey.replace('|', ' ') + " · " + result.regime;
                return;
            }
            resetArmedSetup();
            signalState = result.regime + " · WAIT · " + result.reason;
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

        // A single mildly opposite flow measurement is normal during pullbacks.
        // Veto only when both persistent flow and depth disagree, or when one is
        // extremely adverse.
        double dirFlow = result.dir * stableFlow;
        double dirDepth = result.dir * stableDepth;
        boolean hardFlowVeto = (dirFlow < -0.16 && dirDepth < -0.14) || dirFlow < -0.35 || dirDepth < -0.32;
        if (hardFlowVeto) {
            if (!armedSetupKey.isEmpty() && now - armedSetupAt <= 1_500L) {
                signalState = result.strategy + " · ARMED FLOW CHECK";
                return;
            }
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
            signalState = "ARMED " + result.strategy + " " + side + " · 1/3 · Q" + effectiveConfidence;
            return;
        }

        // Cancel only when the market truly invalidates the setup, not just when
        // a micro reading flickers. Stronger Q setups confirm faster.
        if (now - armedSetupAt > 4_000L ||
                (armedSetupDir > 0 && px < armedSetupPrice - av * 0.28) ||
                (armedSetupDir < 0 && px > armedSetupPrice + av * 0.28)) {
            resetArmedSetup();
            signalState = "WAIT · SETUP INVALIDATED";
            return;
        }

        armedSetupCount++;
        int requiredCount = effectiveConfidence >= 88 ? 2 : 3;
        long requiredMs = effectiveConfidence >= 88 ? 220L : 380L;
        if (armedSetupCount < requiredCount || now - armedSetupAt < requiredMs) {
            signalState = "ARMED " + result.strategy + " " + side + " · " + armedSetupCount + "/" + requiredCount + " · Q" + effectiveConfidence;
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
        if (recordSignal(side, stage, effectiveConfidence, plan, "native clean adaptive ensemble v2.1.1")) {
            lastEnsembleKey = key;
            lastEnsembleSignalAt = now;
            signalState = "TRIGGERED " + stage + " · Q" + effectiveConfidence;
            notifySignal(side, result.strategy + " Q" + effectiveConfidence, px);
        }
        resetArmedSetup();
    }'''
s = replace_method(s, "    private void analyseMainAndMaybeRecord()", new_analyse)

# Isolate V2.1.1 statistics from the over-filtered V2.1 run.
s = s.replace('private static final String TRADES_KEY = "native_trades_v21_json";',
              'private static final String TRADES_KEY = "native_trades_v211_json";')
s = s.replace('t.put("engineVersion", "2.1.0");', 't.put("engineVersion", "2.1.1");')
SERVICE.write_text(s, encoding="utf-8")


# -----------------------------------------------------------------------------
# Android bridge and visible diagnostics. Show WHY the engine is waiting/armed,
# not only whether the background service is alive.
# -----------------------------------------------------------------------------
a = ACTIVITY.read_text(encoding="utf-8")
a = a.replace('private static final String TRADES = "native_trades_v21_json";',
              'private static final String TRADES = "native_trades_v211_json";')
a = a.replace("var K='dhanpulse_cf_android_trades_v21';", "var K='dhanpulse_cf_android_trades_v211';")
a = a.replace(
    "var tl=document.getElementById('tradeLogState');if(tl)tl.textContent='Native V2.1 performance: '+(st.feedMode||'STARTING')+' · tick age '+(st.tickAgeMs>=0?st.tickAgeMs:'NA')+' ms';",
    "var tl=document.getElementById('tradeLogState');if(tl)tl.textContent='Native V2.1.1 · '+(st.feedMode||'STARTING')+' · '+(st.signalState||'MONITORING')+' · '+(st.marketRegime||'')+' · '+(st.activeStrategy||'WAIT')+' Q'+(st.ensembleConfidence||0)+' · tick '+(st.tickAgeMs>=0?st.tickAgeMs:'NA')+' ms';")
ACTIVITY.write_text(a, encoding="utf-8")


# -----------------------------------------------------------------------------
# Web display store and version label.
# -----------------------------------------------------------------------------
h = INDEX.read_text(encoding="utf-8")
h = h.replace('var TRKEY="dhanpulse_cf_android_trades_v21", KEY=',
              'var TRKEY="dhanpulse_cf_android_trades_v211", KEY=')
h = h.replace('V2.1 Signals', 'V2.1.1 Signals')
h = h.replace('No V2.1 signals recorded yet.', 'No V2.1.1 signals recorded yet.')
h = h.replace('Version 2.1.0 Clean Algorithm', 'Version 2.1.1 Balanced Trigger')
INDEX.write_text(h, encoding="utf-8")

# App version.
g = GRADLE.read_text(encoding="utf-8")
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 22', g)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.1.1"', g)
GRADLE.write_text(g, encoding="utf-8")

print("DhanPulse V2.1.1 balanced trigger patch applied")
