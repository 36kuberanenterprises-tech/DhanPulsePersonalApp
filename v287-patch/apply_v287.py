from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.8.4 Full Data Recovery','Version 2.8.7 Trade Sync Integrity')
s=s.replace('DhanPulse Version 2.8.4 Full Data Recovery.','DhanPulse Version 2.8.7 Trade Sync Integrity.')
s=s.replace('DhanPulse Version 2.8.4 Full Data Recovery','DhanPulse Version 2.8.7 Trade Sync Integrity')

# User-facing terminology.
s=s.replace('<span>Profit Rate</span>','<span>Win Rate</span>')
s=s.replace('Trade performance: ','Trade result: ')

css=r'''
/* V2.8.7 trade-state integrity */
.sync-integrity{
  margin-top:8px;padding:9px 10px;border:1px solid rgba(54,211,153,.20);
  border-radius:10px;background:rgba(54,211,153,.045);font-size:9px;color:#82929f;line-height:1.45
}
.sync-integrity b{color:#36d399}
.sync-integrity.warn{border-color:rgba(242,184,75,.26);background:rgba(242,184,75,.045)}
.sync-integrity.warn b{color:#f2b84b}
'''
if 'V2.8.7 trade-state integrity' not in s:
    s=s.replace('</style>',css+'\n</style>',1)

js=r'''
/* V2.8.7 Trade Sync Integrity.
   One canonical trade record now drives notification, table, history and performance.
   Fixes stale OPEN rows caused by the preserved archive winning over a newer CLOSED copy. */
var V287={version:'2.8.7',lockKey:'dhanpulse_publish_lock_v287',lastRepair:0,lastSync:0,duplicatesRemoved:0};

function v287n(v){var n=Number(v);return Number.isFinite(n)?n:null}
function v287copy(x){try{return JSON.parse(JSON.stringify(x||{}))}catch(e){return x||{}}}
function v287time(t){return Math.max(v287n(t&&t.updatedAt)||0,v287n(t&&t.closedAt)||0,v287n(t&&t.createdAt)||0)}
function v287stateRank(t){
  if(!t)return 0;
  var r=0;
  if(String(t.status||'').toUpperCase()==='CLOSED')r+=1000;
  if(t.h3)r+=300;if(t.h2)r+=200;if(t.h1)r+=100;if(t.preProtect)r+=30;
  if(v287n(t.pnlR)!=null)r+=20;
  if(String(t.result||'').toUpperCase()!=='OPEN')r+=10;
  return r;
}
function v287near(a,b){
  a=v287n(a);b=v287n(b);if(a==null||b==null)return false;
  return Math.abs(a-b)<=Math.max(.01,Math.max(Math.abs(a),Math.abs(b))*0.0000002);
}
function v287planMatch(a,b){
  if(!a||!b)return false;
  if(String(a.market||'')!==String(b.market||''))return false;
  if(String(a.symbol||'')!==String(b.symbol||''))return false;
  if(String(a.tf||'')!==String(b.tf||''))return false;
  if(String(a.side||'')!==String(b.side||''))return false;
  if(String(a.strategy||a.stage||'')!==String(b.strategy||b.stage||''))return false;
  var ta=v287n(a.createdAt),tb=v287n(b.createdAt);
  if(ta!=null&&tb!=null&&Math.abs(ta-tb)>120000)return false;
  return v287near(a.entry,b.entry)&&v287near(a.sl,b.sl)&&v287near(a.t1,b.t1)&&v287near(a.t2,b.t2)&&v287near(a.t3,b.t3);
}
function v287mergeTrade(a,b){
  a=v287copy(a);b=v287copy(b);
  var ar=v287stateRank(a),br=v287stateRank(b),at=v287time(a),bt=v287time(b);
  var preferred=(br>ar||(br===ar&&bt>=at))?b:a,other=preferred===b?a:b;
  var out={};
  Object.keys(other||{}).forEach(function(k){out[k]=other[k]});
  Object.keys(preferred||{}).forEach(function(k){if(preferred[k]!==undefined&&preferred[k]!==null&&preferred[k]!=='')out[k]=preferred[k]});
  out.h1=!!(a.h1||b.h1);out.h2=!!(a.h2||b.h2);out.h3=!!(a.h3||b.h3);out.preProtect=!!(a.preProtect||b.preProtect);
  var ca=v287n(a.createdAt),cb=v287n(b.createdAt);
  if(ca!=null&&cb!=null)out.createdAt=Math.min(ca,cb);else out.createdAt=ca!=null?ca:cb;
  out.updatedAt=Math.max(v287time(a),v287time(b),Date.now());
  if(String(a.status||'').toUpperCase()==='CLOSED'||String(b.status||'').toUpperCase()==='CLOSED'){
    var x=String(a.status||'').toUpperCase()==='CLOSED'&&String(b.status||'').toUpperCase()==='CLOSED'
      ? ((v287n(b.closedAt)||0)>=(v287n(a.closedAt)||0)?b:a)
      : (String(b.status||'').toUpperCase()==='CLOSED'?b:a);
    out.status='CLOSED';
    ['result','resultDisplay','exitPrice','pnlR','closedAt','protect'].forEach(function(k){if(x[k]!==undefined&&x[k]!==null&&x[k]!=='')out[k]=x[k]});
  }
  if(!out.id)out.id=String((preferred&&preferred.id)||(other&&other.id)||'');
  try{if(typeof v265ResultLabel==='function')out.resultDisplay=v265ResultLabel(out)}catch(e){}
  return out;
}
function v287canonical(list){
  var src=Array.isArray(list)?list.filter(function(x){return x&&typeof x==='object'}):[],out=[];
  src.sort(function(a,b){return (v287n(a.createdAt)||0)-(v287n(b.createdAt)||0)});
  src.forEach(function(t){
    var idx=-1,id=String(t.id||'');
    if(id)idx=out.findIndex(function(x){return String(x.id||'')===id});
    if(idx<0)idx=out.findIndex(function(x){return v287planMatch(x,t)});
    if(idx>=0){out[idx]=v287mergeTrade(out[idx],t);V287.duplicatesRemoved++}
    else out.push(v287copy(t));
  });
  out.sort(function(a,b){return (v287n(a.createdAt)||0)-(v287n(b.createdAt)||0)});
  return out;
}

/* Critical archive precedence fix. The original V2.6.1 merge kept the first copy.
   Because archive was supplied first, a stale OPEN archive row could overwrite a newer
   CLOSED master row. We now merge statefully and prefer the most advanced trade state. */
if(typeof v261merge==='function'){
  v261merge=function(groups){
    var flat=[];
    (groups||[]).forEach(function(g){
      var key=g&&g.key||'',ver=(typeof v261versionFromKey==='function'?v261versionFromKey(key):'unknown');
      (g&&g.list||[]).forEach(function(raw){
        if(!raw||typeof raw!=='object')return;
        var t=v287copy(raw);if(!t.sourceVersion)t.sourceVersion=ver;flat.push(t);
      });
    });
    return v287canonical(flat);
  };
}

var __v287Save=save;
save=function(list){
  var clean=v287canonical(Array.isArray(list)?list:[]);
  return __v287Save(clean);
};

function v287rawTrades(){try{return JSON.parse(localStorage.getItem(TRKEY)||'[]')||[]}catch(e){return[]}}
function v287repairStores(){
  try{
    var master=v287rawTrades();
    var archive=(typeof V261!=='undefined'&&V261.archiveKey)?v261read(V261.archiveKey):[];
    var all=v287canonical(master.concat(archive));
    localStorage.setItem(TRKEY,JSON.stringify(all));
    if(typeof V261!=='undefined'&&V261.archiveKey)localStorage.setItem(V261.archiveKey,JSON.stringify(all));
    if(typeof S!=='undefined'&&S)S.tradeCache=null;
    V287.lastRepair=Date.now();
    return all;
  }catch(e){return []}
}

if(typeof v265LiveTrades==='function'){
  v265LiveTrades=function(){return v287canonical(v287rawTrades()).filter(function(t){return t&&!t.legacyImported})};
}
if(typeof v265LegacyTrades==='function'){
  v265LegacyTrades=function(){return v287canonical(v287rawTrades()).filter(function(t){return t&&t.legacyImported})};
}
if(typeof v23closed==='function'){
  v23closed=function(){return v287canonical(v287rawTrades()).filter(function(t){return t&&!t.legacyImported&&String(t.status||'').toUpperCase()==='CLOSED'})};
}

/* Cross-WebView publish lock: visible and background engines cannot publish the same plan twice. */
if(typeof v24publish==='function'){
  var __v287Publish=v24publish;
  v24publish=function(c,sel){
    var p=null;try{p=v24plan(c)}catch(e){}
    if(!p)return __v287Publish(c,sel);
    var probe={market:S.market,symbol:S.symbol,tf:S.tf,side:c.side,strategy:c.strategy,entry:p.entry,sl:p.sl,t1:p.t1,t2:p.t2,t3:p.t3,createdAt:Date.now()};
    var current=v287canonical(v287rawTrades());
    if(current.some(function(t){return String(t.status||'').toUpperCase()==='OPEN'&&v287planMatch(t,probe)}))return;
    var key=[probe.market,probe.symbol,probe.tf,probe.side,probe.strategy,
      Number(probe.entry).toFixed(4),Number(probe.sl).toFixed(4),Number(probe.t1).toFixed(4)].join('|');
    var now=Date.now(),lock={};
    try{lock=JSON.parse(localStorage.getItem(V287.lockKey)||'{}')}catch(e){}
    if(lock&&lock.key===key&&now-Number(lock.at||0)<20000)return;
    try{localStorage.setItem(V287.lockKey,JSON.stringify({key:key,at:now}))}catch(e){}
    var before=current.length;
    __v287Publish(c,sel);
    var after=v287canonical(v287rawTrades());
    if(after.length===before){
      try{var z=JSON.parse(localStorage.getItem(V287.lockKey)||'{}');if(z.key===key)localStorage.removeItem(V287.lockKey)}catch(e){}
    }else{
      save(after);
    }
  };
}

/* Add update timestamps to terminal changes so master/archive conflict resolution is deterministic. */
if(typeof v24closeTrade==='function'){
  var __v287Close=v24closeTrade;
  v24closeTrade=function(t,res,px,evt){
    var ok=__v287Close(t,res,px,evt);
    if(t){t.updatedAt=Date.now();try{if(typeof v265ResultLabel==='function')t.resultDisplay=v265ResultLabel(t)}catch(e){}}
    return ok;
  };
}

/* Receive a terminal/progress event from the native service and apply it to the same canonical store. */
function v287applyNativeTrade(payload){
  var d=payload;try{if(typeof d==='string')d=JSON.parse(d)}catch(e){return false}
  var t=d&&d.trade?d.trade:d;if(!t||typeof t!=='object')return false;
  var list=v287rawTrades(),matched=false;
  for(var i=0;i<list.length;i++){
    if((t.id&&String(list[i].id||'')===String(t.id))||v287planMatch(list[i],t)){
      list[i]=v287mergeTrade(list[i],t);matched=true;break;
    }
  }
  if(!matched)list.push(t);
  save(v287canonical(list));
  V287.lastSync=Date.now();
  try{if(typeof renderTrades==='function')renderTrades();if(typeof v261renderHistory==='function')v261renderHistory()}catch(e){}
  return true;
}
window.__nativeTradeSync=function(payload){v287applyNativeTrade(payload)};
window.__nativeTradeJournal=function(payload){
  var a=payload;try{if(typeof a==='string')a=JSON.parse(a)}catch(e){a=[]}
  if(!Array.isArray(a))return;
  a.forEach(v287applyNativeTrade);
};
window.__pullTradeJournal=function(){
  try{
    if(window.DhanPulseNative&&typeof DhanPulseNative.getTradeSyncJournal==='function'){
      window.__nativeTradeJournal(DhanPulseNative.getTradeSyncJournal());
    }
  }catch(e){}
};

/* Repair stale OPEN records by replaying only fully subsequent closed candles.
   This is conservative: the entry candle itself is not replayed because pre-entry movement
   cannot be distinguished inside an OHLC candle. */
function v287replayOpen(){
  try{
    if(typeof S==='undefined'||!S||!Array.isArray(S.candles)||!S.candles.length||typeof v24applyCandle!=='function')return;
    var list=v287canonical(v287rawTrades()),changed=false;
    list.forEach(function(t){
      if(t.legacyImported||String(t.status||'').toUpperCase()!=='OPEN'||t.symbol!==S.symbol||t.tf!==S.tf)return;
      for(var i=0;i<S.candles.length;i++){
        var c=S.candles[i];if(!c||!c.closed||!v287n(c.t)||c.t<v287n(t.createdAt))continue;
        if(v24applyCandle(t,c)){changed=true;t.updatedAt=Date.now();if(String(t.status||'').toUpperCase()==='CLOSED')break}
      }
    });
    if(changed)save(list);
  }catch(e){}
}

function v287integrityUi(){
  try{
    var note=q('livePerfNote');
    if(note){
      var live=v287canonical(v287rawTrades()).filter(function(t){return t&&!t.legacyImported});
      var open=live.filter(function(t){return String(t.status||'').toUpperCase()==='OPEN'}).length;
      var closed=live.filter(function(t){return String(t.status||'').toUpperCase()==='CLOSED'&&v287n(t.pnlR)!=null&&String(t.result||'').toUpperCase()!=='AMBIGUOUS'}).length;
      var wins=live.filter(function(t){return String(t.status||'').toUpperCase()==='CLOSED'&&v287n(t.pnlR)>0}).length;
      note.textContent='Performance Sync LIVE · '+closed+' resolved · '+wins+' wins · '+open+' open · notification and table share one canonical record store.';
    }
  }catch(e){}
}

setTimeout(function(){
  v287repairStores();window.__pullTradeJournal();v287replayOpen();
  try{if(typeof renderTrades==='function')renderTrades();if(typeof v261renderHistory==='function')v261renderHistory()}catch(e){}
  v287integrityUi();
},450);
setInterval(function(){
  window.__pullTradeJournal();
  if(Date.now()-V287.lastRepair>4000)v287repairStores();
  v287replayOpen();
  try{if(typeof renderTrades==='function')renderTrades()}catch(e){}
  v287integrityUi();
},2500);
'''
if 'V2.8.7 Trade Sync Integrity.' not in s:
    s=s.replace('\n})();\n</script>',js+'\n})();\n</script>',1)
idx.write_text(s)

java_dir=root/'app/src/main/java/com/dhanpulse/cryptofxv11'

# Durable native trade event journal. It is intentionally account-data free and contains only signal state.
store=java_dir/'TradeSyncStore.java'
store.write_text(r'''package com.dhanpulse.cryptofxv11;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

final class TradeSyncStore {
    private static final String PREF = "dhanpulse_trade_sync_v287";
    private static final String KEY = "events";
    private static final int MAX = 80;

    private TradeSyncStore() {}

    static synchronized void append(Context context, String json) {
        if (context == null || json == null || json.isEmpty()) return;
        try {
            JSONObject outer = new JSONObject(json);
            JSONObject trade = outer.optJSONObject("trade");
            if (trade == null) trade = outer;
            String id = trade.optString("id", "");
            SharedPreferences p = context.getSharedPreferences(PREF, Context.MODE_PRIVATE);
            JSONArray old = new JSONArray(p.getString(KEY, "[]"));
            JSONArray next = new JSONArray();
            int start = Math.max(0, old.length() - MAX + 1);
            for (int i = start; i < old.length(); i++) {
                JSONObject row = old.optJSONObject(i);
                if (row == null) continue;
                JSONObject rt = row.optJSONObject("trade");
                if (rt == null) rt = row;
                if (!id.isEmpty() && id.equals(rt.optString("id", ""))) continue;
                next.put(row);
            }
            next.put(outer);
            p.edit().putString(KEY, next.toString()).apply();
        } catch (Exception ignored) {
        }
    }

    static synchronized String read(Context context) {
        if (context == null) return "[]";
        try {
            return context.getSharedPreferences(PREF, Context.MODE_PRIVATE).getString(KEY, "[]");
        } catch (Exception e) {
            return "[]";
        }
    }
}
''')

sv=java_dir/'DhanPulseMonitorService.java'
t=sv.read_text()

# New broadcast action for authoritative trade-state updates.
if 'ACTION_TRADE_SYNC' not in t:
    anchor='public static final String ACTION_NATIVE_TICK = "com.dhanpulse.cryptofxv11.NATIVE_TICK";'
    if anchor not in t: raise SystemExit('ACTION_NATIVE_TICK anchor missing')
    t=t.replace(anchor,anchor+'\n    public static final String ACTION_TRADE_SYNC = "com.dhanpulse.cryptofxv11.TRADE_SYNC";',1)

# Persist and broadcast every trade update before notification rendering.
needle='''            JSONObject outer = new JSONObject(json);
            JSONObject t = outer.optJSONObject("trade");
'''
if 'TradeSyncStore.append(this, json);' not in t:
    if needle not in t: raise SystemExit('notifyTradeUpdate parse anchor missing')
    t=t.replace(needle,needle+'''            TradeSyncStore.append(this, json);
            try {
                Intent sync = new Intent(ACTION_TRADE_SYNC);
                sync.setPackage(getPackageName());
                sync.putExtra(EXTRA_JSON, json);
                sendBroadcast(sync);
            } catch (Exception ignored) {
            }
''',1)

# Make result notification human-readable and aligned with the trade row.
t=t.replace('String result = t.optString("result", "UPDATE");',
'''String rawResult = t.optString("result", "UPDATE");
            String result = t.optString("resultDisplay", rawResult);
            String upperResult = result.toUpperCase(Locale.US);
            if ("SL".equals(upperResult)) result = "SL HIT";
            else if ("T3".equals(upperResult)) result = "TARGET 3 HIT";
            else if ("T2 PROTECTED".equals(upperResult)) result = "TARGET 2 HIT · PROFIT PROTECTED";
            else if ("T1 PROTECTED".equals(upperResult) || "PROTECTED".equals(upperResult)) result = "PROFIT PROTECTED";''',1)
t=t.replace('if ("OPEN".equals(result) && "OPEN".equals(status)) return;',
            'if ("OPEN".equalsIgnoreCase(rawResult) && "OPEN".equalsIgnoreCase(status)) return;',1)
t=t.replace('String upper = result.toUpperCase(Locale.US);',
            'String upper = result.toUpperCase(Locale.US);',1)
t=t.replace('"Trade performance: " + result,',
'''("Trade result: " + result + (Double.isNaN(t.optDouble("pnlR", Double.NaN)) ? "" :
                            String.format(Locale.US, " · %.2fR", t.optDouble("pnlR", 0.0)))),''',1)
sv.write_text(t)

ma=java_dir/'MainActivity.java'
a=ma.read_text()

# Receiver handles both market ticks and trade-state broadcasts.
old_filter='IntentFilter filter = new IntentFilter(DhanPulseMonitorService.ACTION_NATIVE_TICK);'
new_filter='''IntentFilter filter = new IntentFilter();
            filter.addAction(DhanPulseMonitorService.ACTION_NATIVE_TICK);
            filter.addAction(DhanPulseMonitorService.ACTION_TRADE_SYNC);'''
if old_filter in a:
    a=a.replace(old_filter,new_filter,1)
elif 'filter.addAction(DhanPulseMonitorService.ACTION_TRADE_SYNC);' not in a:
    raise SystemExit('native receiver filter anchor missing')

old_js='''                    String js = "window.__nativeMarketTick&&window.__nativeMarketTick("
                            + JSONObject.quote(json) + ");";
                    webView.evaluateJavascript(js, null);'''
new_js='''                    boolean tradeSync = DhanPulseMonitorService.ACTION_TRADE_SYNC.equals(intent.getAction());
                    String callback = tradeSync ? "__nativeTradeSync" : "__nativeMarketTick";
                    String js = "window." + callback + "&&window." + callback + "("
                            + JSONObject.quote(json) + ");";
                    webView.evaluateJavascript(js, null);'''
if old_js in a:
    a=a.replace(old_js,new_js,1)
elif '__nativeTradeSync' not in a:
    raise SystemExit('native receiver JS anchor missing')

# Expose the durable journal to both foreground and headless WebViews.
bridge_anchor='''        @JavascriptInterface
        public void onTradeUpdate(String json) {
            startMonitoringService(DhanPulseMonitorService.ACTION_TRADE_EVENT, json);
        }
'''
if bridge_anchor in a and 'getTradeSyncJournal()' not in a:
    a=a.replace(bridge_anchor,bridge_anchor+'''
        @JavascriptInterface
        public String getTradeSyncJournal() {
            return TradeSyncStore.read(MainActivity.this);
        }

''',1)
elif 'getTradeSyncJournal()' not in a:
    raise SystemExit('NativeBridge onTradeUpdate anchor missing')

ma.write_text(a)

# Background WebView bridge also needs journal access so it can reconcile after process transitions.
if 'getTradeSyncJournal()' not in sv.read_text():
    z=sv.read_text()
    bridge='''        @JavascriptInterface
        public void onTradeUpdate(String json) {
            notifyTradeUpdate(json);
        }
'''
    if bridge in z:
        z=z.replace(bridge,bridge+'''
        @JavascriptInterface
        public String getTradeSyncJournal() {
            return TradeSyncStore.read(DhanPulseMonitorService.this);
        }

''',1)
    sv.write_text(z)

# Preserve the existing package identity so the user's trade history survives this update.
b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'applicationId\s*=\s*"[^"]+"','applicationId = "com.dhanpulse.cryptofxstablev263"',bs,count=1)
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 53',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.8.7"',bs,count=1)
b.write_text(bs)
