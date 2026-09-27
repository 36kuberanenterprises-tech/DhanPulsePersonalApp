from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
SERVICE = ROOT / "app/src/main/java/com/dhanpulse/cryptofxnative/BackgroundService.java"
ACTIVITY = ROOT / "app/src/main/java/com/dhanpulse/cryptofxnative/MainActivity.java"
GRADLE = ROOT / "app/build.gradle.kts"
INDEX = ROOT / "app/src/main/assets/index.html"
MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"

def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"Patch target not found: {label}")
    return text.replace(old, new, 1)

# Native engine fixes: same-direction strategy changes no longer reset the
# armed trigger, and a tightly filtered 1-minute continuation bridge catches
# fast moves before the selected 5-minute indicators fully catch up.
s = SERVICE.read_text(encoding="utf-8")

s = replace_once(
    s,
    '        String armKey = symbol + "|" + tf + "|" + result.strategy + "|" + side;',
    '        String armKey = symbol + "|" + tf + "|" + side;',
    "same-side arming"
)

needle = '''        marketRegime = result.regime;
        activeStrategy = result.strategy;'''
replacement = '''        if (!result.trade) {
            AdaptiveEnsemble.Result micro = microContinuationResult(px, b15, b60, stableFlow, stableDepth);
            if (micro != null) result = micro;
        }

        marketRegime = result.regime;
        activeStrategy = result.strategy;'''
s = replace_once(s, needle, replacement, "micro continuation hook")

helper_anchor = "    private void resetArmedSetup() {"
micro_helper = r'''    private AdaptiveEnsemble.Result microContinuationResult(
            double px, int bias15, int bias60, double stableFlow, double stableDepth) {
        if (microCandles == null || microCandles.size() < 30 || !Double.isFinite(px)) return null;
        int n = microCandles.size();
        double[] close = new double[n];
        for (int i = 0; i < n; i++) close[i] = microCandles.get(i).c;

        double[] e5 = ema(close, 5);
        double[] e9 = ema(close, 9);
        double[] e21 = ema(close, 21);
        int i = n - 1;
        if (!Double.isFinite(e5[i]) || !Double.isFinite(e9[i]) || !Double.isFinite(e21[i])) return null;

        double av = atrLast(microCandles, 14);
        if (!Double.isFinite(av) || av <= 0) return null;

        double mom3 = (px - close[Math.max(0, n - 4)]) / av;
        double priorHi = maxHigh(microCandles, Math.max(0, n - 9), n - 1);
        double priorLo = minLow(microCandles, Math.max(0, n - 9), n - 1);

        boolean longShape = e5[i] > e9[i] && e9[i] > e21[i] && px > e9[i] && mom3 > 0.22;
        boolean shortShape = e5[i] < e9[i] && e9[i] < e21[i] && px < e9[i] && mom3 < -0.22;
        if (!longShape && !shortShape) return null;

        int dir = longShape ? 1 : -1;
        if (bias15 == -dir && bias60 == -dir) return null;

        int score = 64;
        double dm = mom3 * dir;
        double df = stableFlow * dir;
        double dd = stableDepth * dir;

        if (dm > 0.35) score += 4;
        if (dm > 0.55) score += 4;
        if (df > 0.03) score += 4;
        if (df > 0.10) score += 3;
        if (dd > 0.03) score += 3;
        if (dd > 0.10) score += 2;
        if (bias15 == dir) score += 4; else if (bias15 == -dir) score -= 4;
        if (bias60 == dir) score += 4; else if (bias60 == -dir) score -= 5;
        if (dir > 0 && px > priorHi) score += 5;
        if (dir < 0 && px < priorLo) score += 5;

        if (df < -0.12 && dd < -0.10) score -= 10;
        if (Double.isFinite(spreadBps) && spreadBps > 6.0) score -= 8;

        if (score < 72) return null;
        String side = dir > 0 ? "BUY" : "SELL";
        String reason = String.format(Locale.US,
                "1m continuation %s · mom %.2f · flow %.2f · depth %.2f · 15m %d · 1h %d",
                side, mom3, stableFlow, stableDepth, bias15, bias60);
        return new AdaptiveEnsemble.Result(true, dir, "MICRO TREND", "MICRO CONTINUATION",
                Math.min(94, score), 0.90, reason);
    }

'''
s = replace_once(s, helper_anchor, micro_helper + helper_anchor, "micro helper insertion")

s = s.replace('signalState = result.regime + " · WAIT · " + result.reason;',
              'signalState = "WAIT · " + result.regime + " · Q" + result.confidence + " · " + result.reason;')

SERVICE.write_text(s, encoding="utf-8")

# In-app diagnostics and version label.
a = ACTIVITY.read_text(encoding="utf-8")
a = a.replace("Native V2.1 performance: ", "Native V2.1.2 · ")
a = a.replace(
    "+(st.feedMode||'STARTING')+' · tick age '+(st.tickAgeMs>=0?st.tickAgeMs:'NA')+' ms';",
    "+(st.feedMode||'STARTING')+' · '+(st.signalState||'MONITORING')+' · '+(st.marketRegime||'')+' · '+(st.activeStrategy||'WAIT')+' Q'+(st.ensembleConfidence||0)+' · tick age '+(st.tickAgeMs>=0?st.tickAgeMs:'NA')+' ms';"
)
ACTIVITY.write_text(a, encoding="utf-8")

h = INDEX.read_text(encoding="utf-8")
h = h.replace("Version 2.1.1 Balanced Trigger", "Version 2.1.2 Active Signal")
h = h.replace("V2.1.1 Signals", "V2.1.2 Signals")
h = h.replace("No V2.1.1 signals recorded yet.", "No V2.1.2 signals recorded yet.")
h = h.replace("NATIVE V2.1", "NATIVE V2.1.2")

if 'id="dhanpulseBrandLogo"' not in h:
    h = h.replace(
        "<body>",
        '<body><div id="dhanpulseBrandLogo" style="text-align:center;padding:12px 12px 2px">'
        '<img src="dhanpulse_logo.jpg" alt="DhanPulse" '
        'style="width:132px;max-width:38vw;border-radius:18px;display:inline-block"></div>',
        1
    )

INDEX.write_text(h, encoding="utf-8")

g = GRADLE.read_text(encoding="utf-8")
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 23', g)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.1.2"', g)
GRADLE.write_text(g, encoding="utf-8")

m = MANIFEST.read_text(encoding="utf-8")
if 'android:icon="@drawable/dhanpulse_logo"' not in m:
    m = m.replace(
        '<application\n        android:allowBackup="true"',
        '<application\n        android:allowBackup="true"\n'
        '        android:icon="@drawable/dhanpulse_logo"\n'
        '        android:roundIcon="@drawable/dhanpulse_logo"',
        1
    )
MANIFEST.write_text(m, encoding="utf-8")

print("DhanPulse V2.1.2 active signal + logo patch applied")
