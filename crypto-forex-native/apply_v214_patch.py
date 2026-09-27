from pathlib import Path
import re, json

ROOT = Path(__file__).resolve().parent
SERVICE = ROOT / "app/src/main/java/com/dhanpulse/cryptofxnative/BackgroundService.java"
ACTIVITY = ROOT / "app/src/main/java/com/dhanpulse/cryptofxnative/MainActivity.java"
GRADLE = ROOT / "app/build.gradle.kts"
INDEX = ROOT / "app/src/main/assets/index.html"
MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"


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

# 1. Native engine authority: REST may track open trades, but only genuine WS
# trades can arm or create a new signal. This also prevents REST from firing the
# fast turning path before the later source check.
s = SERVICE.read_text(encoding="utf-8")
old = '''        checkTrades(price, exchangeTs);
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
new = '''        checkTrades(price, exchangeTs);
        if ("WS TRADE".equals(source)) {
            Turning turn = detectTurningFast(price);
            signalState = turn.state;
            considerFastTurning(turn, price);
            if (now - lastMainSignalAt > 150) {
                lastMainSignalAt = now;
                analyseMainAndMaybeRecord();
            }
        } else {
            signalState = "MONITOR ONLY · " + source + " · WAITING FOR WS";
        }
        lastEngineMs = (System.nanoTime() - startNs) / 1_000_000.0;'''
if old not in s:
    raise SystemExit("V2.1.4 processTick target not found")
s = s.replace(old, new, 1)
SERVICE.write_text(s, encoding="utf-8")

# 2. Manifest and theme. Use a new resource name to defeat launcher icon cache.
m = MANIFEST.read_text(encoding="utf-8")
m = re.sub(r'android:icon="[^"]+"', 'android:icon="@drawable/dhanpulse_launcher_v214"', m)
m = re.sub(r'android:roundIcon="[^"]+"', 'android:roundIcon="@drawable/dhanpulse_launcher_v214"', m)
m = re.sub(r'android:theme="[^"]+"', 'android:theme="@style/AppTheme"', m, count=1)
MANIFEST.write_text(m, encoding="utf-8")

# 3. Web UI: the browser may calculate indicators, but the visible BUY/SELL card
# is owned by the native 24/7 engine. Therefore a visible BUY/SELL always matches
# a recorded native signal.
h = INDEX.read_text(encoding="utf-8")
h = h.replace('dhanpulse_logo.jpg', 'dhanpulse_logo_v214.jpg')
h = h.replace('Version 2.1.3 Icon Fix', 'Version 2.1.4 Native Authority')
h = h.replace('V2.1.3 Signals', 'V2.1.4 Signals')
h = h.replace('No V2.1.3 signals recorded yet.', 'No V2.1.4 signals recorded yet.')
h = h.replace('NATIVE V2.1.3', 'NATIVE V2.1.4')
h = h.replace('>Current Decision<', '>Native Decision<')
h = h.replace('Stable live BUY and SELL signals are recorded early when price action confirms. Closed candle confirmation is also retained.',
              'Only the native 24/7 engine can publish and record BUY or SELL. Browser indicators are diagnostic only.')
if 'function renderBrowser(){' not in h:
    h = h.replace('function render(){', 'function renderBrowser(){', 1)
    anchor = 'function draw(){'
    wrapper = 'function render(){renderBrowser();try{if(window.__nativeDecisionAuthority&&window.__renderNativeDecision)window.__renderNativeDecision()}catch(e){}}\n'
    if anchor not in h:
        raise SystemExit('draw function anchor not found')
    h = h.replace(anchor, wrapper + anchor, 1)
INDEX.write_text(h, encoding="utf-8")

# 4. Replace the Android bridge so it never imports browser-generated trades and
# synchronises the top decision, feed status and plan from native state/trades.
js = r'''(function(){
if(window.__dhanpulseNativeBridgeV214)return;
window.__dhanpulseNativeBridgeV214=true;
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
 var fm=String(st.feedMode||'STARTING'),ss=String(st.signalState||'MONITORING'),ws=fm.indexOf('WS')===0;
 var c=el('conn');if(c){c.textContent=ws?'NATIVE '+fm:'NATIVE '+fm;c.className='badge '+(ws?'live':'')}
 var bg=el('bgState');if(bg){bg.textContent=st.active?'NATIVE ACTIVE':'STARTING';bg.className=st.active?'bull':'neutral'}
 var bh=el('bgHeartbeat');if(bh)bh.textContent='tick age '+(st.tickAgeMs>=0?st.tickAgeMs:'NA')+' ms · '+fm+' · '+ss;
 var bs=el('bgSymbol');if(bs)bs.textContent=st.symbol||'';var bt=el('bgTf');if(bt)bt.textContent=st.tf||'';
 var tl=el('tradeLogState');if(tl)tl.textContent='Native V2.1.4 · '+fm+' · '+ss+' · tick age '+(st.tickAgeMs>=0?st.tickAgeMs:'NA')+' ms';
 var lp=num(st.lastPrice),pe=el('price');if(pe&&lp!==null)pe.textContent=fmt(lp);
 var a=nativeTrades(),open=latestOpen(st,a),side='',stage='',reason='',q=Number(st.ensembleConfidence||0);
 if(open){side=String(open.side||'');stage='RECORDED · '+String(open.stage||'NATIVE SIGNAL');reason='Native signal recorded and now being tracked';}
 else if(ss.indexOf('TRIGGERED')>=0){side=ss.indexOf('BUY')>=0?'BUY':ss.indexOf('SELL')>=0?'SELL':'';stage=ss;reason='Native trigger fired. Recording sync in progress';}
 else if(ss.indexOf('ARMED')>=0){stage=ss;reason='Native setup is armed and waiting for final confirmation';}
 else if(!ws){stage='MONITOR ONLY · '+fm;reason='REST backup tracks price and open trades. New entries wait for the native WebSocket feed';}
 else {stage=ss;reason='Native engine is monitoring. No confirmed entry yet';}
 var d=el('decision'),card=el('decisionCard'),sc=el('score'),sg=el('stage'),rs=el('reason'),pd=el('pdir');
 var published=(side==='BUY'||side==='SELL');
 if(d)d.textContent=published?side:'WAIT';
 if(card)card.className='panel decision '+(published?side.toLowerCase():'wait');
 if(sc)sc.textContent='Native Q '+q+' | '+(st.activeStrategy||'WAIT');
 if(sg)sg.textContent='Stage: '+(stage||'WAIT');
 if(rs)rs.textContent=reason;
 if(pd)pd.textContent=published?side:'WAIT';
 ['entry','sl','t1','t2','t3'].forEach(function(id){var x=el(id);if(x)x.textContent=open?fmt(open[id]):'NA'});
 var r=el('record');if(r){r.disabled=true;r.textContent='Native Auto Record'}
}
window.__renderNativeDecision=function(){paint(lastState||{})};
function sync(){try{var s=el('symbol'),tf=el('tf');if(s&&tf)AndroidNative.setMonitoringConfig(s.value,tf.value);var st=JSON.parse(AndroidNative.getNativeState()||'{}');paint(st);copyNativeTrades();AndroidNative.ensureService()}catch(e){}}
['symbol','tf'].forEach(function(id){var x=el(id);if(x)x.addEventListener('change',function(){setTimeout(sync,40)})});
var clr=el('clear');if(clr)clr.addEventListener('click',function(){setTimeout(function(){AndroidNative.clearNativeTrades();localStorage.removeItem(K);if(window.S)S.tradeCache=[];copyNativeTrades()},250)});
var anchor=el('bgState');if(anchor){var p=anchor.closest('.panel');if(p&&!el('nativeBatteryBtn')){var b=document.createElement('button');b.id='nativeBatteryBtn';b.textContent='Allow 24/7 Background';b.style.marginTop='12px';b.style.width='100%';b.onclick=function(){AndroidNative.openBatterySettings()};p.appendChild(b)}}
setInterval(sync,300);sync();
})();'''
java_method = '''    private void injectNativeBridge() {\n        String js = %s;\n        webView.evaluateJavascript(js, null);\n    }''' % json.dumps(js)
a = ACTIVITY.read_text(encoding="utf-8")
a = replace_method(a, '    private void injectNativeBridge()', java_method)
a = a.replace('Native V2.1.3 · ', 'Native V2.1.4 · ')
ACTIVITY.write_text(a, encoding="utf-8")

# 5. Version bump.
g = GRADLE.read_text(encoding="utf-8")
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 25', g)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.1.4"', g)
GRADLE.write_text(g, encoding="utf-8")

print('DhanPulse V2.1.4 native authority, signal sync, logo and splash patch applied')
