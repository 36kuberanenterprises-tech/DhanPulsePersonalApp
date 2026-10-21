from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.7.6 DeltaPulse Connected','Version 2.8.0 Multi Market')
s=s.replace('DhanPulse Delta Exchange India Version 2.7.6 DeltaPulse Connected.',
            'DhanPulse Version 2.8.0 Multi Market.')
s=s.replace('DhanPulse Delta Exchange India Version 2.7.6 DeltaPulse Connected',
            'DhanPulse Version 2.8.0 Multi Market')

css=r'''
/* V2.8.0 multi market switch + Flattrade India */
.market-switch{
  display:grid;grid-template-columns:1fr 1fr;gap:4px;padding:4px;margin:0 0 10px;
  border:1px solid var(--ios-line,#2a3038);background:var(--ios-surface,#12151a);
  border-radius:13px
}
.market-switch button{
  min-height:38px!important;border:none!important;background:transparent!important;color:#7f8b97!important;
  font-size:10px!important;font-weight:760!important;letter-spacing:.05em!important
}
.market-switch button.active{
  background:#20262e!important;color:#f2f6fb!important;box-shadow:inset 0 0 0 1px #36404b!important
}
#flattradePanel{
  display:none;background:var(--ios-surface,#12151a)!important;border:1px solid rgba(47,111,237,.48)!important;
  border-radius:14px!important;padding:14px!important;margin-bottom:10px!important
}
body.india-mode #flattradePanel{display:block!important}
body.india-mode .v280-crypto-section{display:none!important}
.ft-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
.ft-title{font-size:15px;font-weight:760}.ft-sub{font-size:9px;color:#8593a0;margin-top:3px;line-height:1.45}
.ft-badge{font-size:9px;font-weight:760;padding:6px 9px;border-radius:999px;border:1px solid #3b4550;color:#9aa6b3;white-space:nowrap}
.ft-badge.ok{color:#36d399;border-color:rgba(54,211,153,.35);background:rgba(54,211,153,.07)}
.ft-badge.warn{color:#f2b84b;border-color:rgba(242,184,75,.35);background:rgba(242,184,75,.07)}
.ft-state{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:11px}
.ft-state>div{padding:9px;border:1px solid var(--ios-line,#2a3038);border-radius:10px;background:#15191e}
.ft-state span{display:block;font-size:8px;color:#798590;text-transform:uppercase;letter-spacing:.06em}
.ft-state b{display:block;font-size:10px;margin-top:4px}
.ft-actions{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:10px}
.ft-actions button{min-height:42px!important}
.ft-account{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:10px}
.ft-account>div{padding:10px;border:1px solid var(--ios-line,#2a3038);border-radius:10px;background:#15191e}
.ft-account span{display:block;font-size:8px;color:#798590;text-transform:uppercase;letter-spacing:.05em}
.ft-account b{display:block;font-size:11px;margin-top:4px;overflow-wrap:anywhere}
.ft-note{font-size:9px;color:#8996a2;line-height:1.5;margin-top:10px;padding:9px;border-left:2px solid #e3aa46;background:rgba(227,170,70,.05)}
.ft-token-row{display:grid;grid-template-columns:1fr auto;gap:7px;align-items:end;margin-top:10px}
.ft-token-row button{min-height:42px!important}
@media(max-width:680px){
  .ft-state{grid-template-columns:1fr 1fr}
  .ft-account{grid-template-columns:1fr 1fr}
  .ft-actions{grid-template-columns:1fr}
  .ft-token-row{grid-template-columns:1fr auto}
}
'''
if 'V2.8.0 multi market switch + Flattrade India' not in s:
    s=s.replace('</style>',css+'\n</style>',1)

js=r'''
/* V2.8.0 Multi Market: Delta crypto + Flattrade India */
var V280={version:'2.8.0',mode:'crypto'};

function v280Bridge(){return window.DhanPulseNative||null}
function v280Text(id,val,cl){
  var e=q(id);if(!e)return;e.textContent=(val==null||val==='')?'NA':String(val);if(cl)e.className=cl
}
function v280MarkCrypto(){
  var app=document.querySelector('.app');if(!app)return;
  Array.from(app.children).forEach(function(el){
    if(!el||!el.classList)return;
    if(el.id==='flattradePanel'||el.id==='marketSwitch'||el.tagName==='HEADER'||el.id==='proNav'||el.id==='iosAccountStrip')return;
    if(el.classList.contains('market-switch'))return;
    el.classList.add('v280-crypto-section');
  });
}
function v280Mode(mode){
  V280.mode=mode==='india'?'india':'crypto';
  document.body.classList.toggle('india-mode',V280.mode==='india');
  var c=q('marketCrypto'),i=q('marketIndia');if(c)c.classList.toggle('active',V280.mode==='crypto');if(i)i.classList.toggle('active',V280.mode==='india');
  if(V280.mode==='india'){
    var p=q('flattradePanel');if(p)p.scrollIntoView({behavior:'smooth',block:'start'});
    v280FlattradeStatus();
  }else{
    window.scrollTo({top:0,behavior:'smooth'});
  }
}
function v280SaveAppToken(){
  var b=v280Bridge(),el=q('ftAppToken'),v=el?el.value.trim():'';
  if(!v){v280Text('ftMessage','Enter APP_ACCESS_TOKEN first.');return}
  try{
    if(b&&b.saveDeltaBackendToken)b.saveDeltaBackendToken(v);
    el.value='';
    v280Text('ftMessage','APP token saved securely on this phone.');
    v280FlattradeStatus();
  }catch(e){v280Text('ftMessage','Unable to save APP token.')}
}
function v280FlattradeStatus(){
  var b=v280Bridge();
  try{
    if(!b||!b.flattradeStatus){v280Text('ftMessage','Flattrade native bridge unavailable.');return}
    b.flattradeStatus();
  }catch(e){v280Text('ftMessage','Unable to check Flattrade status.')}
}
function v280FlattradeAuthorize(){
  var b=v280Bridge();
  try{
    v280Text('ftMessage','Opening Flattrade authorization in your browser...');
    if(b&&b.startFlattradeAuthorization)b.startFlattradeAuthorization();
  }catch(e){v280Text('ftMessage','Unable to open Flattrade authorization.')}
}
function v280FlattradeAccount(){
  var b=v280Bridge();
  try{
    v280Text('ftMessage','Refreshing Flattrade account...');
    if(b&&b.refreshFlattradeAccount)b.refreshFlattradeAccount();
  }catch(e){v280Text('ftMessage','Unable to refresh Flattrade account.')}
}
window.__flattradeStatus=function(payload){
  var d=payload;try{if(typeof d==='string')d=JSON.parse(d)}catch(e){d={}}
  v280Text('ftApiKey',d.api_key?'READY':'MISSING',d.api_key?'bull':'neutral');
  v280Text('ftApiSecret',d.api_secret?'READY':'MISSING',d.api_secret?'bull':'neutral');
  v280Text('ftStaticIp',d.static_ip_required?'REQUIRED':'NA',d.static_ip_required?'neutral':'bull');
  v280Text('ftSession',d.session_connected?'CONNECTED':'LOGIN NEEDED',d.session_connected?'bull':'neutral');
  var badge=q('ftStatusBadge');
  if(badge){
    var ok=!!d.session_connected;badge.textContent=ok?'CONNECTED':(d.configured?'READY TO AUTHORIZE':'SETUP NEEDED');
    badge.className='ft-badge '+(ok?'ok':'warn');
  }
  if(d.session_connected){v280Text('ftMessage','Flattrade session is connected. Refresh account to load cash, positions and holdings.')}
  else if(d.configured){v280Text('ftMessage','API key and secret are ready on Render. Authorize Flattrade to create today\'s session.')}
  else{v280Text('ftMessage','Add FLATTRADE_API_KEY and FLATTRADE_API_SECRET in Render first.')}
};
window.__flattradeAccount=function(payload){
  var d=payload;try{if(typeof d==='string')d=JSON.parse(d)}catch(e){d={}}
  if(!d||!d.success){v280Text('ftMessage',(d&&d.error)||'Flattrade account request failed.');return}
  v280Text('ftClientId',d.clientId||'NA');
  v280Text('ftAccountId',d.accountId||'NA');
  v280Text('ftCash',d.cash||'NA');
  v280Text('ftMargin',d.marginUsed||'0');
  v280Text('ftPositions',d.activePositions==null?'0':d.activePositions);
  v280Text('ftHoldings',d.holdingsCount==null?'0':d.holdingsCount);
  v280Text('ftExchanges',Array.isArray(d.enabledExchanges)?d.enabledExchanges.join(', '):'NA');
  v280Text('ftMessage','Authenticated account data loaded from Flattrade API V2.');
  var badge=q('ftStatusBadge');if(badge){badge.textContent='CONNECTED';badge.className='ft-badge ok'}
  v280Text('ftSession','CONNECTED','bull');
};
window.__flattradeAuthError=function(message){
  v280Text('ftMessage',message||'Unable to start Flattrade authorization.');
};
window.__flattradeResume=function(){
  if(V280.mode==='india'){setTimeout(v280FlattradeStatus,250);setTimeout(v280FlattradeAccount,700)}
};
function v280Layout(){
  var app=document.querySelector('.app'),strip=q('iosAccountStrip')||q('proNav');if(!app||!strip)return;
  if(!q('marketSwitch')){
    var sw=document.createElement('div');sw.id='marketSwitch';sw.className='market-switch';
    sw.innerHTML='<button id="marketCrypto" class="active">CRYPTO · DELTA</button><button id="marketIndia">INDIA · FLATTRADE</button>';
    strip.insertAdjacentElement('afterend',sw);
    q('marketCrypto').onclick=function(){v280Mode('crypto')};
    q('marketIndia').onclick=function(){v280Mode('india')};
  }
  if(!q('flattradePanel')){
    var p=document.createElement('section');p.id='flattradePanel';p.className='panel';
    p.innerHTML=
      '<div class="ft-head"><div><div class="ft-title">India Market · Flattrade API V2</div><div class="ft-sub">NSE · BSE · NFO · BFO · MCX · CDS · read only account and market connection</div></div><span id="ftStatusBadge" class="ft-badge warn">CHECKING</span></div>'+
      '<div class="ft-state"><div><span>API Key</span><b id="ftApiKey">CHECKING</b></div><div><span>API Secret</span><b id="ftApiSecret">CHECKING</b></div><div><span>Static IP</span><b id="ftStaticIp">REQUIRED</b></div><div><span>Session</span><b id="ftSession">CHECKING</b></div></div>'+
      '<div class="ft-token-row"><label>APP Access Token<input id="ftAppToken" type="password" autocomplete="off" placeholder="Same APP_ACCESS_TOKEN used for DeltaPulse"></label><button id="ftSaveToken">Save Token</button></div>'+
      '<div class="ft-actions"><button id="ftAuthorize" class="pro-api-toggle">Authorize Flattrade</button><button id="ftRefresh">Refresh Flattrade Account</button></div>'+
      '<div class="ft-account"><div><span>Client ID</span><b id="ftClientId">NA</b></div><div><span>Account ID</span><b id="ftAccountId">NA</b></div><div><span>Cash Available</span><b id="ftCash">NA</b></div><div><span>Margin Used</span><b id="ftMargin">NA</b></div><div><span>Open Positions</span><b id="ftPositions">NA</b></div><div><span>Holdings</span><b id="ftHoldings">NA</b></div><div style="grid-column:1/-1"><span>Enabled Exchanges</span><b id="ftExchanges">NA</b></div></div>'+
      '<div id="ftMessage" class="ft-note">Checking Flattrade backend setup...</div>'+
      '<div class="ft-note">Flattrade access tokens are normally regenerated daily and cleared around 5–6 AM. Token exchange must originate from the private static IP registered for the Flattrade API key.</div>';
    sw.insertAdjacentElement('afterend',p);
    q('ftSaveToken').onclick=v280SaveAppToken;
    q('ftAuthorize').onclick=v280FlattradeAuthorize;
    q('ftRefresh').onclick=v280FlattradeAccount;
  }
  v280MarkCrypto();
  v280Mode('crypto');
  v280FlattradeStatus();
}
setTimeout(v280Layout,450);
'''
if 'V2.8.0 Multi Market: Delta crypto + Flattrade India' not in s:
    s=s.replace('\n})();\n</script>',js+'\n})();\n</script>',1)
idx.write_text(s)

java_dir=root/'app/src/main/java/com/dhanpulse/cryptofxv11'
ft=java_dir/'FlattradeBackend.java'
ft.write_text(r'''package com.dhanpulse.cryptofxv11;

import android.content.Context;

import org.json.JSONObject;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;

final class FlattradeBackend {
    interface Callback { void onResult(String json); }
    private static final String BASE = "https://deltapulse-personal-api.onrender.com";
    private static final OkHttpClient HTTP = new OkHttpClient();
    private static final ExecutorService EXEC = Executors.newSingleThreadExecutor();

    private FlattradeBackend() {}

    private static String token(Context c) {
        return DeltaAccountManager.backendToken(c);
    }

    static void statusAsync(Context c, Callback cb) {
        getAsync(c, "/api/india/status", cb);
    }

    static void accountAsync(Context c, Callback cb) {
        getAsync(c, "/api/india/account", cb);
    }

    static void authUrlAsync(Context c, Callback cb) {
        getAsync(c, "/api/india/auth-url", cb);
    }

    private static void getAsync(Context c, String path, Callback cb) {
        String appToken = token(c);
        if (appToken == null || appToken.isEmpty()) {
            cb.onResult("{\"success\":false,\"error\":\"APP_ACCESS_TOKEN is not saved on this phone\"}");
            return;
        }
        EXEC.execute(() -> {
            try {
                Request req = new Request.Builder()
                        .url(BASE + path)
                        .header("Accept", "application/json")
                        .header("X-App-Token", appToken)
                        .header("User-Agent", "DhanPulse-Android/2.8.0")
                        .get().build();
                try (Response r = HTTP.newCall(req).execute()) {
                    String body = r.body() == null ? "{}" : r.body().string();
                    JSONObject j;
                    try { j = new JSONObject(body); }
                    catch (Exception e) { j = new JSONObject().put("success", false).put("error", "Flattrade backend returned invalid response"); }
                    if (!r.isSuccessful()) {
                        j.put("success", false);
                        if (!j.has("error")) j.put("error", j.optString("detail", "Flattrade backend request failed"));
                    }
                    cb.onResult(j.toString());
                }
            } catch (Exception e) {
                try {
                    cb.onResult(new JSONObject().put("success", false)
                            .put("error", e.getMessage() == null ? "Flattrade backend connection failed" : e.getMessage()).toString());
                } catch (Exception ignored) {}
            }
        });
    }
}
''')

ma=java_dir/'MainActivity.java'
a=ma.read_text()

anchor='''        @JavascriptInterface
        public void saveDeltaBackendToken(String token) {
'''
if anchor not in a: raise SystemExit('saveDeltaBackendToken anchor missing')
if 'public void flattradeStatus()' not in a:
    methods=r'''        @JavascriptInterface
        public void flattradeStatus() {
            FlattradeBackend.statusAsync(MainActivity.this, MainActivity.this::deliverFlattradeStatus);
        }

        @JavascriptInterface
        public void refreshFlattradeAccount() {
            FlattradeBackend.accountAsync(MainActivity.this, MainActivity.this::deliverFlattradeAccount);
        }

        @JavascriptInterface
        public void startFlattradeAuthorization() {
            FlattradeBackend.authUrlAsync(MainActivity.this, json -> {
                try {
                    JSONObject j = new JSONObject(json);
                    String url = j.optString("url", "");
                    if (!url.startsWith("https://auth.flattrade.in/")) {
                        deliverFlattradeAuthError(j.optString("error", j.optString("detail", "Flattrade authorization URL unavailable")));
                        return;
                    }
                    runOnUiThread(() -> {
                        try {
                            android.content.Intent intent = new android.content.Intent(
                                    android.content.Intent.ACTION_VIEW, android.net.Uri.parse(url));
                            startActivity(intent);
                        } catch (Exception e) {
                            deliverFlattradeAuthError("Unable to open Flattrade authorization browser.");
                        }
                    });
                } catch (Exception e) {
                    deliverFlattradeAuthError("Invalid Flattrade authorization response.");
                }
            });
        }

'''
    a=a.replace(anchor,methods+anchor,1)

deliver_anchor='''    private void deliverDeltaBackendStatus(String json) {
'''
if deliver_anchor not in a: raise SystemExit('deliverDeltaBackendStatus anchor missing')
if 'private void deliverFlattradeStatus(String json)' not in a:
    helpers=r'''    private void deliverFlattradeStatus(String json) {
        deliverJavascriptCallback("__flattradeStatus", json);
    }

    private void deliverFlattradeAccount(String json) {
        deliverJavascriptCallback("__flattradeAccount", json);
    }

    private void deliverFlattradeAuthError(String message) {
        deliverJavascriptCallback("__flattradeAuthError", message == null ? "" : message);
    }

    private void deliverJavascriptCallback(String callback, String value) {
        if (webView == null || callback == null) return;
        String safe = value == null ? "" : value;
        webView.post(() -> {
            try {
                String js = "window." + callback + "&&window." + callback + "(" + JSONObject.quote(safe) + ");";
                webView.evaluateJavascript(js, null);
            } catch (Exception ignored) {}
        });
    }

'''
    a=a.replace(deliver_anchor,helpers+deliver_anchor,1)

# Refresh Flattrade after returning from browser authorization.
resume_anchor='''        if (webView != null) {
            webView.onResume();
'''
if resume_anchor in a and 'window.__flattradeResume' not in a:
    a=a.replace(resume_anchor,'''        if (webView != null) {
            webView.onResume();
            webView.postDelayed(() -> {
                try { webView.evaluateJavascript("window.__flattradeResume&&window.__flattradeResume();", null); }
                catch (Exception ignored) {}
            }, 450);
''',1)

ma.write_text(a)

b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 48',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.8.0"',bs,count=1)
b.write_text(bs)
