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
        if ch in ('\"', "'"):
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


# -----------------------------------------------------------------------------
# Native service: make trade persistence authoritative and immediately visible.
# V2.1.7 could successfully trigger a notification while the UI still read an
# empty trade store. V2.1.8 mirrors one canonical JSON payload to all legacy keys
# and commits synchronously on the engine thread so a trigger and a table record
# cannot diverge.
# -----------------------------------------------------------------------------
s = SERVICE.read_text(encoding="utf-8")
s = re.sub(
    r'private static final String TRADES_KEY = "[^"]+";',
    'private static final String TRADES_KEY = "native_trades_v21_json";',
    s,
    count=1,
)

new_persist = r'''    private void persistTrades() {
        JSONArray arr = new JSONArray();
        for (JSONObject t : trades) arr.put(t);
        String raw = arr.toString();
        lastTradesRaw = raw;
        long now = System.currentTimeMillis();
        String lastId = "";
        if (!trades.isEmpty()) lastId = trades.get(trades.size() - 1).optString("id", "");
        // commit() is intentional here. This runs on the single native engine
        // thread and guarantees the Android bridge sees the signal immediately.
        prefs.edit()
                .putString(TRADES_KEY, raw)
                .putString("native_trades_v21_json", raw)
                .putString("native_trades_json", raw)
                .putInt("native_trade_count", trades.size())
                .putLong("native_trades_updated_at", now)
                .putString("last_recorded_trade_id", lastId)
                .commit();
    }'''
s = replace_method(s, '    private void persistTrades()', new_persist)

# Faster decision cadence without removing quality filters.
s = s.replace('if (now - lastMainSignalAt > 220L)', 'if (now - lastMainSignalAt > 90L)', 1)
s = s.replace('now - lastRestMicroPoll < 800L', 'now - lastRestMicroPoll < 500L', 1)
s = s.replace('int requiredCount = effectiveConfidence >= 86 ? 2 : 3;',
              'int requiredCount = effectiveConfidence >= 94 ? 2 : (effectiveConfidence >= 86 ? 2 : 3);', 1)
s = s.replace('long requiredMs = effectiveConfidence >= 86 ? 180L : 320L;',
              'long requiredMs = effectiveConfidence >= 94 ? 90L : (effectiveConfidence >= 86 ? 130L : 260L);', 1)

# Store an explicit record heartbeat when a new trade is added. This is separate
# from normal market heartbeat so UI diagnostics can prove recording occurred.
needle = '''            trades.add(t);\n            while (trades.size() > 1500) trades.remove(0);\n            persistTrades();\n            return true;'''
replacement = '''            trades.add(t);
            while (trades.size() > 1500) trades.remove(0);
            persistTrades();
            prefs.edit()
                    .putLong("last_signal_recorded_at", now)
                    .putString("last_signal_recorded_id", t.optString("id", ""))
                    .putString("last_signal_recorded_side", side)
                    .putString("last_signal_recorded_stage", stage)
                    .apply();
            return true;'''
if needle not in s:
    raise SystemExit('recordSignal persistence target not found')
s = s.replace(needle, replacement, 1)

# Expose record state in the native heartbeat preferences.
hb_anchor = '                .putString("feed_block_reason", feedBlockReason)\n'
if hb_anchor in s:
    s = s.replace(hb_anchor,
        hb_anchor +
        '                .putInt("native_trade_count", trades.size())\n'
        '                .putString("last_recorded_trade_id", trades.isEmpty() ? "" : trades.get(trades.size() - 1).optString("id", ""))\n',
        1)

s = s.replace('t.put("engineVersion", "2.1.7");', 't.put("engineVersion", "2.1.8");')
SERVICE.write_text(s, encoding="utf-8")


# -----------------------------------------------------------------------------
# Android bridge: read the canonical native store directly, with legacy fallback.
# Also align the WebView local key with the HTML TRKEY used by renderTrades().
# -----------------------------------------------------------------------------
a = ACTIVITY.read_text(encoding="utf-8")
a = re.sub(
    r'private static final String TRADES = "[^"]+";',
    'private static final String TRADES = "native_trades_v21_json";',
    a,
    count=1,
)

new_get_trades = r'''        @JavascriptInterface
        public String getNativeTrades() {
            String raw = prefs.getString("native_trades_v21_json", "[]");
            if (raw == null || raw.trim().isEmpty() || "[]".equals(raw.trim())) {
                String legacy = prefs.getString("native_trades_json", "[]");
                if (legacy != null && !legacy.trim().isEmpty() && !"[]".equals(legacy.trim())) raw = legacy;
            }
            return raw == null ? "[]" : raw;
        }'''
a = replace_method(a, '        public String getNativeTrades()', new_get_trades)

new_clear = r'''        @JavascriptInterface
        public void clearNativeTrades() {
            prefs.edit()
                    .putString("native_trades_v21_json", "[]")
                    .putString("native_trades_json", "[]")
                    .putInt("native_trade_count", 0)
                    .remove("last_signal_recorded_at")
                    .remove("last_signal_recorded_id")
                    .remove("last_signal_recorded_side")
                    .remove("last_signal_recorded_stage")
                    .commit();
            Intent i = new Intent(MainActivity.this, BackgroundService.class);
            i.setAction(BackgroundService.ACTION_CLEAR);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(i); else startService(i);
        }'''
a = replace_method(a, '        public void clearNativeTrades()', new_clear)

# The HTML generated by V2.1.1 uses dhanpulse_cf_android_trades_v211.
# Keep bridge and HTML on exactly the same local key and sync more quickly.
a = a.replace("var K='dhanpulse_cf_android_trades_v21'", "var K='dhanpulse_cf_android_trades_v211'")
a = a.replace('setInterval(sync,250);sync();', 'setInterval(sync,100);sync();')

# Always refresh S.tradeCache from the native source, even if the JSON string is
# unchanged, because the WebView can recreate/reset its JS state on resume.
old_copy = "function copyNativeTrades(){try{var raw=AndroidNative.getNativeTrades()||'[]';if(raw!==lastNative){lastNative=raw;var a=JSON.parse(raw);if(!Array.isArray(a))a=[];localStorage.setItem(K,JSON.stringify(a));if(window.S)S.tradeCache=a;if(window.renderTrades)renderTrades()}}catch(e){}}"
new_copy = "function copyNativeTrades(){try{var raw=AndroidNative.getNativeTrades()||'[]';var a=JSON.parse(raw);if(!Array.isArray(a))a=[];lastNative=raw;localStorage.setItem(K,JSON.stringify(a));if(window.S)S.tradeCache=a;if(window.renderTrades)renderTrades()}catch(e){}}"
if old_copy not in a:
    raise SystemExit('V2.1.8 native trade bridge target not found')
a = a.replace(old_copy, new_copy, 1)

# Expose trade-count diagnostics to the WebView state object.
state_anchor = '                o.put("feedBlockReason", prefs.getString("feed_block_reason", ""));'
if state_anchor in a:
    a = a.replace(state_anchor,
        state_anchor + '\n'
        '                o.put("nativeTradeCount", prefs.getInt("native_trade_count", 0));\n'
        '                o.put("lastRecordedTradeId", prefs.getString("last_signal_recorded_id", prefs.getString("last_recorded_trade_id", "")));\n'
        '                o.put("lastRecordedAt", prefs.getLong("last_signal_recorded_at", 0));',
        1)

a = a.replace('Native V2.1.7 · ', 'Native V2.1.8 · ')
ACTIVITY.write_text(a, encoding="utf-8")


# -----------------------------------------------------------------------------
# HTML labels and single local trade key.
# -----------------------------------------------------------------------------
h = INDEX.read_text(encoding="utf-8")
h = h.replace('var TRKEY="dhanpulse_cf_android_trades_v211"', 'var TRKEY="dhanpulse_cf_android_trades_v211"')
h = h.replace('Version 2.1.7 Feed Authority Fix', 'Version 2.1.8 Signal Sync Fast')
h = h.replace('V2.1.7 Signals', 'V2.1.8 Signals')
h = h.replace('No V2.1.7 signals recorded yet.', 'No V2.1.8 signals recorded yet.')
h = h.replace('NATIVE V2.1.7', 'NATIVE V2.1.8')
INDEX.write_text(h, encoding="utf-8")


g = GRADLE.read_text(encoding="utf-8")
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 29', g)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.1.8"', g)
GRADLE.write_text(g, encoding="utf-8")

print('DhanPulse V2.1.8 signal persistence sync and faster decision cadence applied')
