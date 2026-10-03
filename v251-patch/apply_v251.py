from pathlib import Path
import re

root = Path('crypto-forex-app/buildsrc')
idx = root / 'app/src/main/assets/index.html'
s = idx.read_text()

# Version and fresh records
s = s.replace('Version 2.5 News Intelligence Lab', 'Version 2.5.1 Continuous Background')
s = s.replace('DhanPulse Crypto and Forex Version 2.5 News Intelligence Lab.', 'DhanPulse Crypto and Forex Version 2.5.1 Continuous Background.')
s = s.replace('var TRKEY="dhanpulse_cf_android_trades_v25"', 'var TRKEY="dhanpulse_cf_android_trades_v251"')
s = s.replace('V2.5 Signals', 'V2.5.1 Signals')
s = s.replace('No V2.5 signals recorded yet.', 'No V2.5.1 signals recorded yet.')

js = r'''
/* V2.5.1 continuous background reliability and opportunity recovery.
   Keeps the V2.5 news risk layer, forces background analysis from native ticks,
   and gradually relaxes only precision thresholds after long signal silence.
   Hard regime, feed, spread, higher timeframe, flow, conflict, news and loss brakes remain. */
var V251={lastCtxAt:0,ctxBusy:false,version:'2.5.1'};
function v251ResultLabel(t){
  if(!t)return '';
  if(t.status==='OPEN'){
    if(t.h2)return 'TARGET 2 HIT · RUNNING';
    if(t.h1)return 'TARGET 1 HIT · RUNNING';
    return 'RUNNING';
  }
  var r=String(t.result||'').toUpperCase();
  if(r==='SL')return 'SL HIT';
  if(r==='T3')return 'TARGET 3 HIT';
  if(r==='T2 PROTECTED')return 'TARGET 2 HIT · PROFIT PROTECTED';
  if(r==='T1 PROTECTED')return 'TARGET 1 HIT · PROFIT PROTECTED';
  if(r==='TIME EXIT')return finite(t.pnlR)&&t.pnlR>0?'TIME EXIT · PROFIT':'TIME EXIT';
  if(r==='AMBIGUOUS')return 'AMBIGUOUS';
  if(t.h3)return 'TARGET 3 HIT';
  if(t.h2)return 'TARGET 2 HIT';
  if(t.h1)return 'TARGET 1 HIT';
  return t.result||'';
}
var __v251CloseTrade=v23closeTrade;
v23closeTrade=function(t,res,px,evt){var ok=__v251CloseTrade(t,res,px,evt);try{t.resultDisplay=v251ResultLabel(t)}catch(e){}return ok};

function v251LastSignalAge(){
  var x=trades().filter(function(t){return t.symbol===S.symbol&&t.tf===S.tf}).sort(function(a,b){return a.createdAt-b.createdAt});
  if(!x.length)return 999999999;
  return Date.now()-x[x.length-1].createdAt;
}

/* Slightly higher activity ceiling. Quality gates still decide whether a trade exists. */
v24tradeLimit=function(){
  var now=Date.now(),list=trades().filter(function(t){return t.symbol===S.symbol&&t.tf===S.tf&&now-t.createdAt<21600000});
  var hour=list.filter(function(t){return now-t.createdAt<3600000}).length;
  return hour>=3||list.length>=8;
};

/* Keep strong SL cooldown, but do not suppress a new valid setup for too long after a completed profitable trade. */
v24cooldownBlocked=function(c){
  var list=v23closed().filter(function(t){return t.symbol===S.symbol&&t.tf===S.tf&&t.result!=="AMBIGUOUS"});
  if(!list.length)return false;
  var last=list[list.length-1],age=Date.now()-(last.closedAt||last.createdAt);
  if(last.result==="SL"&&age<v23tfCooldown(2.2))return true;
  if(age<v23tfCooldown(.35))return true;
  var same=list.filter(function(t){return t.strategy===c.strategy}).slice(-1)[0];
  if(same&&finite(same.pnlR)&&same.pnlR<0&&Date.now()-(same.closedAt||same.createdAt)<v23tfCooldown(3.2))return true;
  return false;
};

var __v251BaseSelect=v24select;
v24select=function(){
  var primary=__v251BaseSelect();
  if(primary&&primary.candidate)return primary;
  var reason=String(primary&&primary.reason||'');
  if(/NEWS RISK|existing signal|loss|drawdown|frequency|cooldown|conflict|opposite setup|feed|spread|extreme|analysis unavailable/i.test(reason))return primary;
  var age=v251LastSignalAge();
  if(age<3*3600000)return primary;
  var reg=v23regime(),fg=v24feedGate(reg);
  if(!fg.ok||v24activeTrade())return primary;
  var brake=v24lossBrake();if(brake||v24tradeLimit())return primary;
  var relax=age>=8*3600000?6:age>=5*3600000?4:2;
  var all=v23families().map(function(c){
    var t=v24threshold(c.strategy),hc=v24hardContext(c,reg);
    c.threshold=Math.max(88,t.threshold-relax);c.paused=t.pause;c.hardOK=hc.ok;c.hardReason=hc.reason;return c;
  }).filter(function(c){return !c.paused&&c.hardOK});
  var qualified=all.filter(function(c){return c.score>=c.threshold});
  if(!qualified.length)return primary;
  var qb=qualified.filter(function(c){return c.side==='BUY'}).sort(function(a,b){return b.score-a.score});
  var qs=qualified.filter(function(c){return c.side==='SELL'}).sort(function(a,b){return b.score-a.score});
  var bestB=qb[0],bestS=qs[0];
  if(bestB&&bestS&&Math.abs(bestB.score-bestS.score)<18)return primary;
  var best=!bestS||(bestB&&bestB.score>bestS.score)?bestB:bestS;
  var opp=all.filter(function(c){return c.side!==best.side}).sort(function(a,b){return b.score-a.score})[0];
  if(opp&&opp.score>=opp.threshold-4&&best.score-opp.score<16)return primary;
  var support=all.filter(function(c){return c.side===best.side&&c.strategy!==best.strategy&&c.score>=c.threshold-5}).length;
  if(support<1&&best.score<best.threshold+3)return primary;
  if(v24cooldownBlocked(best))return primary;
  var nc=typeof v25newsContext==='function'?v25newsContext(best.side):null;
  if(nc&&nc.block)return{candidate:null,reason:'WAIT: NEWS RISK · '+nc.reason,regime:reg};
  if(nc&&nc.aligned){support++;best.reasons=(best.reasons||[]).concat(['news plus candle aligned'])}
  best.support=support;
  best.fast=(best.score>=best.threshold+4&&support>=1);
  best.reasons=(best.reasons||[]).concat(['opportunity recovery after '+Math.floor(age/3600000)+'h without signal']);
  best.newsContext=nc;
  return{candidate:best,reason:'',regime:reg};
};

window.__dhanpulseBackgroundPulse=function(){
  try{
    if(typeof v24confirmStep==='function')v24confirmStep();
    if(finite(S.livePrice)){
      if(typeof updateTradesWithTick==='function')updateTradesWithTick(S.livePrice,Date.now(),'BACKGROUND NATIVE');
      if(typeof v25shadowUpdate==='function')v25shadowUpdate(S.livePrice);
    }
    var now=Date.now();
    if(now-V251.lastCtxAt>5000&&!V251.ctxBusy&&typeof refreshContext==='function'){
      V251.lastCtxAt=now;V251.ctxBusy=true;
      Promise.resolve(refreshContext()).catch(function(){}).then(function(){V251.ctxBusy=false});
    }
    if(typeof nativeHeartbeat==='function'&&(!V251.lastHb||now-V251.lastHb>1800)){V251.lastHb=now;nativeHeartbeat()}
  }catch(e){}
};
if(typeof BACKGROUND_MODE!=='undefined'&&BACKGROUND_MODE){setInterval(window.__dhanpulseBackgroundPulse,700);setTimeout(window.__dhanpulseBackgroundPulse,900)}
'''

if 'V2.5.1 continuous background reliability' not in s:
    s = s.replace('</script>', js + '\n</script>', 1)

# Make the Result column human readable without changing raw result codes used by risk logic.
s = s.replace("<td>'+t.status+'</td><td>'+t.result+'</td>", "<td>'+t.status+'</td><td>'+v251ResultLabel(t)+'</td>")
idx.write_text(s)

# Android package/version. Use robust regex because older V2.5 regex was over-escaped.
b = root / 'app/build.gradle.kts'
bs = b.read_text()
bs = re.sub(r'applicationId\s*=\s*"[^"]+"', 'applicationId = "com.dhanpulse.cryptofxresearchv251"', bs, count=1)
bs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 30', bs, count=1)
bs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.5.1"', bs, count=1)
b.write_text(bs)

# Strengthen the native foreground service so the headless decision engine is actively pumped
# while the Activity is stopped or the screen is locked. This avoids relying on throttled WebView timers.
sv = root / 'app/src/main/java/com/dhanpulse/cryptofxv11/DhanPulseMonitorService.java'
v = sv.read_text()

field_anchor = '    private Runnable nativeWatchdogRunnable;\n'
if 'backgroundEngineWatchdogRunnable' not in v:
    if field_anchor not in v:
        raise SystemExit('native watchdog field anchor missing')
    v = v.replace(field_anchor, field_anchor + '    private Runnable backgroundEngineWatchdogRunnable;\n    private long lastHeadlessHeartbeatAt = 0L;\n    private long lastHeadlessReloadAt = 0L;\n', 1)

# Stop the headless pump when UI becomes foreground.
v = v.replace('            uiForeground = true;\n            destroyHeadlessWebView();',
              '            uiForeground = true;\n            stopBackgroundEngineWatchdog();\n            destroyHeadlessWebView();', 1)

# Start the pump whenever service enters background mode.
bg_anchor = '            prefs.edit().putBoolean("background_ran", true).apply();\n            ensureHeadlessWebView();'
if bg_anchor in v:
    v = v.replace(bg_anchor, bg_anchor + '\n            startBackgroundEngineWatchdog();')

# Sticky process restart path should also keep the background engine alive.
v = v.replace('            if (!uiForeground) ensureHeadlessWebView();',
              '            if (!uiForeground) { ensureHeadlessWebView(); startBackgroundEngineWatchdog(); }')

# Native tick injection now explicitly asks the headless page to run one decision pulse.
old_js = 'String js = "window.__nativeMarketTick&&window.__nativeMarketTick("\n                                + JSONObject.quote(json) + ");";'
new_js = 'String js = "window.__nativeMarketTick&&window.__nativeMarketTick("\n                                + JSONObject.quote(json) + ");window.__dhanpulseBackgroundPulse&&window.__dhanpulseBackgroundPulse();";'
if old_js in v:
    v = v.replace(old_js, new_js, 1)

# Headless heartbeat proves the background WebView is alive.
old_hb = '        public void onHeartbeat(String json) {\n            handleHeartbeat(json);\n        }'
new_hb = '        public void onHeartbeat(String json) {\n            lastHeadlessHeartbeatAt = System.currentTimeMillis();\n            handleHeartbeat(json);\n        }'
if old_hb in v:
    v = v.replace(old_hb, new_hb, 1)

# Show readable result text in trade notifications too, when available.
v = v.replace('String result = t.optString("result", "UPDATE");',
              'String result = t.optString("resultDisplay", t.optString("result", "UPDATE"));')

watchdog = r'''
    private void startBackgroundEngineWatchdog() {
        if (mainHandler == null || backgroundEngineWatchdogRunnable != null) return;
        lastHeadlessReloadAt = System.currentTimeMillis();
        backgroundEngineWatchdogRunnable = new Runnable() {
            @Override
            public void run() {
                if (backgroundEngineWatchdogRunnable != this) return;
                if (!prefs.getBoolean("monitor_enabled", true)) {
                    stopBackgroundEngineWatchdog();
                    return;
                }
                if (!uiForeground) {
                    long now = System.currentTimeMillis();
                    WebView w = headlessWebView;
                    if (w == null) {
                        lastHeadlessReloadAt = now;
                        ensureHeadlessWebView();
                    } else {
                        try {
                            w.evaluateJavascript("window.__dhanpulseBackgroundPulse&&window.__dhanpulseBackgroundPulse();", null);
                        } catch (Throwable ignored) {
                        }
                        boolean neverReady = lastHeadlessHeartbeatAt == 0L && now - lastHeadlessReloadAt > 15000L;
                        boolean stalled = lastHeadlessHeartbeatAt > 0L && now - lastHeadlessHeartbeatAt > 20000L;
                        if ((neverReady || stalled) && now - lastHeadlessReloadAt > 12000L) {
                            lastHeadlessReloadAt = now;
                            lastHeadlessHeartbeatAt = 0L;
                            destroyHeadlessWebView();
                            ensureHeadlessWebView();
                        }
                    }
                }
                if (mainHandler != null && backgroundEngineWatchdogRunnable == this) {
                    mainHandler.postDelayed(this, 750L);
                }
            }
        };
        mainHandler.post(backgroundEngineWatchdogRunnable);
    }

    private void stopBackgroundEngineWatchdog() {
        if (mainHandler != null && backgroundEngineWatchdogRunnable != null) {
            mainHandler.removeCallbacks(backgroundEngineWatchdogRunnable);
        }
        backgroundEngineWatchdogRunnable = null;
    }

'''
if 'private void startBackgroundEngineWatchdog()' not in v:
    anchor = '    private void acquireLocks() {'
    if anchor not in v:
        raise SystemExit('acquireLocks anchor missing')
    v = v.replace(anchor, watchdog + anchor, 1)

# Always stop the watchdog with the service.
v = v.replace('    public void onDestroy() {\n        destroyHeadlessWebView();',
              '    public void onDestroy() {\n        stopBackgroundEngineWatchdog();\n        destroyHeadlessWebView();', 1)

# Keep service alive when the task is swiped away if the manifest supports the attribute.
manifest = root / 'app/src/main/AndroidManifest.xml'
if manifest.exists():
    ms = manifest.read_text()
    if 'DhanPulseMonitorService' in ms and 'android:stopWithTask' not in ms:
        ms = re.sub(r'(<service\b[^>]*android:name="[^"]*DhanPulseMonitorService")', r'\1 android:stopWithTask="false"', ms, count=1)
    manifest.write_text(ms)

sv.write_text(v)
