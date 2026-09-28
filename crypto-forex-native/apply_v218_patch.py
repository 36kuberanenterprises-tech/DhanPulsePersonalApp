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

# Durable signal replication state. A notification must never exist without a
# recoverable trade record. The service writes the full array synchronously and
# also stores the most recent signal independently for UI self-healing.
anchor = '    private volatile String feedBlockReason = "STARTING";\n'
fields = '''    private volatile String feedBlockReason = "STARTING";\n    private volatile long tradeRevision = 0L;\n    private volatile String lastRecordedSignalJson = "";\n    private volatile long lastRecordedSignalAt = 0L;\n'''
s = replace_once(s, anchor, fields, "record replication fields")

new_persist = r'''    private void persistTrades() {
        JSONArray arr = new JSONArray();
        for (JSONObject t : trades) arr.put(t);
        String raw = arr.toString();
        lastTradesRaw = raw;
        tradeRevision++;
        // commit() is intentional here. Signal creation is infrequent and the
        // UI must see the record before/at the same time as the notification.
        prefs.edit()
                .putString(TRADES_KEY, raw)
                .putLong("trade_revision", tradeRevision)
                .commit();
    }'''
s = replace_method(s, '    private void persistTrades()', new_persist)

# Replace recordSignal so every accepted signal is synchronously committed and
# mirrored as last_signal_json before the notification is allowed to fire.
new_record = r'''    private boolean recordSignal(String side, String stage, int score, Plan plan, String source) {
        reloadTradesFromPrefs();
        for (JSONObject t : trades) {
            if ("OPEN".equals(t.optString("status")) && symbol.equals(t.optString("symbol")) && tf.equals(t.optString("tf"))) return false;
        }
        long now = System.currentTimeMillis();
        try {
            JSONObject t = new JSONObject();
            String slot = "crypto|" + symbol + "|" + tf + "|" + (now / 2500L) + "|" + side;
            t.put("id", "native-" + now + "-" + Math.abs(slot.hashCode()));
            t.put("slot", slot);
            t.put("key", slot);
            t.put("source", source);
            t.put("engineVersion", "2.1.8");
            t.put("entryFeed", feedMode);
            t.put("strategy", activeStrategy);
            t.put("regime", marketRegime);
            t.put("stage", stage);
            t.put("score", score);
            t.put("shiftScore", 0);
            t.put("createdAt", now);
            t.put("signalCandleTime", now);
            t.put("market", "crypto");
            t.put("symbol", symbol);
            t.put("tf", tf);
            t.put("side", side);
            t.put("entry", plan.entry);
            t.put("sl", plan.sl);
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
            t.put("flow3s", flow3s);
            t.put("flow30s", flow30s);
            t.put("flow180s", flow180s);
            t.put("depth1s", depth1s);
            t.put("depth10s", depth10s);
            t.put("oi1m", oi1m);
            t.put("oi5m", oi5m);
            t.put("oi15m", oi15m);
            trades.add(t);
            while (trades.size() > 1500) trades.remove(0);

            JSONArray arr = new JSONArray();
            for (JSONObject x : trades) arr.put(x);
            String raw = arr.toString();
            lastTradesRaw = raw;
            lastRecordedSignalJson = t.toString();
            lastRecordedSignalAt = now;
            tradeRevision++;
            boolean ok = prefs.edit()
                    .putString(TRADES_KEY, raw)
                    .putString("last_signal_json", lastRecordedSignalJson)
                    .putLong("last_signal_at", now)
                    .putLong("trade_revision", tradeRevision)
                    .commit();
            if (!ok) {
                trades.remove(t);
                return false;
            }
            return true;
        } catch (Exception e) {
            return false;
        }
    }'''
s = replace_method(s, '    private boolean recordSignal(String side, String stage, int score, Plan plan, String source)', new_record)

# Faster evaluation cadence. Price/order-flow updates remain event driven. This
# only reduces the throttle around full ensemble evaluation; it does not bypass
# confirmation, feed quality, flow veto or risk logic.
s = s.replace('if (now - lastMainSignalAt > 220L) {', 'if (now - lastMainSignalAt > (wsTrade ? 90L : 180L)) {', 1)

# Faster confirmation for strong candidates while preserving 3-check confirmation
# for ordinary setups.
s = s.replace('int requiredCount = effectiveConfidence >= 86 ? 2 : 3;\n        long requiredMs = effectiveConfidence >= 86 ? 180L : 320L;',
              'int requiredCount = effectiveConfidence >= 84 ? 2 : 3;\n        long requiredMs = effectiveConfidence >= 84 ? 100L : 220L;', 1)

# Persist record diagnostics in heartbeat.
hb = '                .putString("rest_micro_error", restMicroError)\n'
hb_new = '''                .putString("rest_micro_error", restMicroError)\n                .putLong("trade_revision", tradeRevision)\n                .putString("last_signal_json", lastRecordedSignalJson)\n                .putLong("last_signal_at", lastRecordedSignalAt)\n'''
s = replace_once(s, hb, hb_new, "heartbeat record diagnostics")
s = s.replace('t.put("engineVersion", "2.1.7");', 't.put("engineVersion", "2.1.8");')
SERVICE.write_text(s, encoding="utf-8")


# Android bridge: expose durable revision and last signal. The Java bridge also
# repairs the array if the service notification exists but the array was lost or
# stale for any reason.
a = ACTIVITY.read_text(encoding="utf-8")
a = a.replace(
    '                o.put("restMicroError", prefs.getString("rest_micro_error", ""));',
    '                o.put("restMicroError", prefs.getString("rest_micro_error", ""));\n'
    '                o.put("tradeRevision", prefs.getLong("trade_revision", 0));\n'
    '                o.put("lastSignalAt", prefs.getLong("last_signal_at", 0));',
    1
)

# Replace getNativeTrades with a self-healing read path.
old_get = '''        @JavascriptInterface
        public String getNativeTrades() {
            return prefs.getString(TRADES, "[]");
        }'''
new_get = '''        @JavascriptInterface
        public String getNativeTrades() {
            try {
                String raw = prefs.getString(TRADES, "[]");
                JSONArray arr = new JSONArray(raw == null ? "[]" : raw);
                String last = prefs.getString("last_signal_json", "");
                if (last != null && !last.isEmpty()) {
                    JSONObject sig = new JSONObject(last);
                    String id = sig.optString("id", "");
                    boolean found = false;
                    for (int i = 0; i < arr.length(); i++) {
                        JSONObject x = arr.optJSONObject(i);
                        if (x != null && id.equals(x.optString("id", ""))) { found = true; break; }
                    }
                    if (!found) {
                        arr.put(sig);
                        prefs.edit().putString(TRADES, arr.toString()).commit();
                    }
                }
                return arr.toString();
            } catch (Exception e) {
                return prefs.getString(TRADES, "[]");
            }
        }'''
a = replace_once(a, old_get, new_get, "self healing getNativeTrades")

# Clear both the array and independent recovery record, and notify the running
# service through ACTION_CLEAR so memory and SharedPreferences cannot diverge.
old_clear = '''        @JavascriptInterface
        public void clearNativeTrades() {
            prefs.edit().putString(TRADES, "[]").apply();
        }'''
new_clear = '''        @JavascriptInterface
        public void clearNativeTrades() {
            prefs.edit().putString(TRADES, "[]").putString("last_signal_json", "").putLong("last_signal_at", 0L).commit();
            Intent i = new Intent(MainActivity.this, BackgroundService.class);
            i.setAction(BackgroundService.ACTION_CLEAR);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(i); else startService(i);
        }'''
a = replace_once(a, old_clear, new_clear, "clear sync")

# Stronger UI sync: always parse the native array, not only when the raw string
# changes, because renderTrades may have been rebuilt/reloaded by WebView.
start = a.find("js = r'''(function(){")
if start < 0:
    raise SystemExit("V2.1.7 bridge block not found")
end = a.find("'''\njava_method", start)
if end < 0:
    raise SystemExit("V2.1.7 bridge end not found")
old_js_block = a[start:end+3]
js = r'''(function(){
if(window.__dhanpulseNativeBridgeV218)return;
window.__dhanpulseNativeBridgeV218=true;
window.__nativeDecisionAuthority=true;
var K='dhanpulse_cf_android_trades_v21',lastState={},lastRevision=-1;
function el(id){return document.getElementById(id)}
function num(v){var n=Number(v);return isFinite(n)?n:null}
function fmt(v){var n=num(v);if(n===null)return 'NA';return Math.abs(n)>=1000?n.toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2}):n.toFixed(4)}
function nativeTrades(){try{var a=JSON.parse(AndroidNative.getNativeTrades()||'[]');return Array.isArray(a)?a:[]}catch(e){return []}}
function latestOpen(st,a){var best=null;(a||[]).forEach(function(t){if(t.status==='OPEN'&&t.symbol===(st.symbol||'')&&t.tf===(st.tf||'')){if(!best||(t.createdAt||0)>(best.createdAt||0))best=t}});return best}
function copyNativeTrades(force){try{var a=nativeTrades();localStorage.setItem(K,JSON.stringify(a));if(window.S)S.tradeCache=a;if(window.renderTrades)renderTrades();return a}catch(e){return []}}
function paint(st){
 lastState=st||{};
 var fm=String(st.feedMode||'STARTING'),ss=String(st.signalState||'MONITORING');
 var ws=fm.indexOf('WS TRADE')===0,rm=fm.indexOf('REST MICRO')===0,entryFeed=ws||rm;
 var cand=String(st.candidateSide||'WAIT'),cq=Number(st.candidateQuality||0),cs=String(st.candidateStrategy||'WAIT');
 var c=el('conn');if(c){c.textContent='NATIVE '+fm;c.className='badge '+(entryFeed?'live':'')}
 var bg=el('bgState');if(bg){bg.textContent=st.active?'NATIVE ACTIVE':'STARTING';bg.className=st.active?'bull':'neutral'}
 var bh=el('bgHeartbeat');if(bh)bh.textContent='trade WS '+(st.tradeWsStatus||'STARTING')+' · msg '+(st.tradeWsMessages||0)+' · feed '+fm+' · '+ss;
 var bs=el('bgSymbol');if(bs)bs.textContent=st.symbol||'';var bt=el('bgTf');if(bt)bt.textContent=st.tf||'';
 var lp=num(st.lastPrice),pe=el('price');if(pe&&lp!==null)pe.textContent=fmt(lp);
 var ts=el('turnState');if(ts)ts.textContent=st.turnState||'MONITORING';
 var tloc=el('turnLocation');if(tloc)tloc.textContent=st.turnLocation||'NA';
 var tf=el('turnFlow');if(tf)tf.textContent=st.turnFlow||'NA';
 var tr=el('turnReason');if(tr)tr.textContent=st.turnReason||'Waiting for native microstructure';
 var em=el('engineMs');if(em&&st.engineMs)em.textContent=st.engineMs+' ms';
 var ev=el('eventType');if(ev)ev.textContent=fm+' · WS '+(st.tradeWsStatus||'');
 var a=copyNativeTrades(false),open=latestOpen(st,a),side='',stage='',reason='',q=Number(st.ensembleConfidence||0),published=false;
 if(open){side=String(open.side||'');published=true;stage='RECORDED · '+String(open.stage||'NATIVE SIGNAL');reason='Native signal recorded and tracking T1 T2 T3 SL';}
 else if(ss.indexOf('TRIGGERED')>=0){side=ss.indexOf('BUY')>=0?'BUY':ss.indexOf('SELL')>=0?'SELL':'';published=!!side;stage=ss;reason='Signal triggered. Durable record sync active.';}
 else if(ss.indexOf('ARMED')>=0){stage=ss;reason='Candidate '+cand+' Q'+cq+' is armed for final confirmation';}
 else if(cand==='BUY'||cand==='SELL'){stage=ss;reason=(st.feedBlockReason?'BLOCKED: '+st.feedBlockReason:(st.candidateReason||'Candidate detected'));}
 else if(!entryFeed){stage='FEED RECOVERY · '+fm;reason=st.feedBlockReason||'Building trade microstructure';}
 else {stage=ss;reason='Native engine is monitoring. No qualified candidate yet';}
 var tl=el('tradeLogState');if(tl)tl.textContent='Native V2.1.8 · '+fm+' · rev '+(st.tradeRevision||0)+' · '+a.length+' records · '+ss;
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
 try{if(window.draw)draw()}catch(e){}
}
window.__renderNativeDecision=function(){paint(lastState||{})};
function sync(){try{var s=el('symbol'),tf=el('tf');if(s&&tf)AndroidNative.setMonitoringConfig(s.value,tf.value);var st=JSON.parse(AndroidNative.getNativeState()||'{}');paint(st);AndroidNative.ensureService()}catch(e){}}
['symbol','tf'].forEach(function(id){var x=el(id);if(x)x.addEventListener('change',function(){setTimeout(sync,25)})});
var clr=el('clear');if(clr)clr.addEventListener('click',function(){setTimeout(function(){AndroidNative.clearNativeTrades();localStorage.removeItem(K);if(window.S)S.tradeCache=[];copyNativeTrades(true)},150)});
setInterval(sync,150);sync();
})();'''
new_js_block = "js = r'''" + js + "'''"
a = a[:start] + new_js_block + a[end+3:]
a = a.replace('Native V2.1.7 · ', 'Native V2.1.8 · ')
ACTIVITY.write_text(a, encoding="utf-8")

h = INDEX.read_text(encoding="utf-8")
h = h.replace('Version 2.1.7 Feed Authority Fix', 'Version 2.1.8 Fast Record Sync')
h = h.replace('V2.1.7 Signals', 'V2.1.8 Signals')
h = h.replace('No V2.1.7 signals recorded yet.', 'No V2.1.8 signals recorded yet.')
h = h.replace('NATIVE V2.1.7', 'NATIVE V2.1.8')
INDEX.write_text(h, encoding="utf-8")

g = GRADLE.read_text(encoding="utf-8")
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 29', g)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.1.8"', g)
GRADLE.write_text(g, encoding="utf-8")

print('DhanPulse V2.1.8 durable signal recording and fast decision patch applied')