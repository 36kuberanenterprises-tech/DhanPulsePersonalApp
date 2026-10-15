from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.7.3 Secure API Vault','Version 2.7.4 Backend Variables')
s=s.replace('DhanPulse Delta Exchange India Version 2.7.3 Secure API Vault.',
            'DhanPulse Delta Exchange India Version 2.7.4 Backend Variables.')
s=s.replace('DhanPulse Delta Exchange India Version 2.7.3 Secure API Vault',
            'DhanPulse Delta Exchange India Version 2.7.4 Backend Variables')

css=r'''
/* V2.7.4 backend variables account mode */
.backend-mode-card{
  margin:10px 0 12px;padding:13px;border:1px solid rgba(47,111,237,.42);
  border-radius:12px;background:linear-gradient(145deg,rgba(47,111,237,.10),rgba(18,21,26,.98))
}
.backend-mode-head{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:8px}
.backend-mode-head b{font-size:12px;color:#e8eef8}.backend-mode-head span{font-size:9px;padding:5px 8px;border-radius:999px;border:1px solid #394453;color:#9ba7b4}
.backend-mode-card p{font-size:10px;line-height:1.45;color:#94a0ad;margin:5px 0 10px}
.backend-actions{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:end}
.backend-actions button{min-height:42px!important;white-space:nowrap}
.backend-status-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:9px}
.backend-status-grid div{padding:8px;border:1px solid #2b333d;border-radius:9px;background:#14181d}
.backend-status-grid span{display:block;font-size:8px;color:#78838f;text-transform:uppercase;letter-spacing:.06em}
.backend-status-grid b{display:block;font-size:10px;margin-top:4px}
#deltaDirectToggle{width:100%;margin-top:9px;background:transparent!important;color:#8fa0b2!important;border-color:#2f3741!important}
.delta-direct-hidden{display:none!important}
@media(max-width:680px){.backend-actions{grid-template-columns:1fr}.backend-status-grid{grid-template-columns:1fr 1fr 1fr}}
'''
if 'V2.7.4 backend variables account mode' not in s:
    s=s.replace('</style>',css+'\n</style>',1)

js=r'''
/* V2.7.4 Backend Variables.
   Recommended mode keeps Delta API key and secret only in DhanPulse backend environment variables.
   The phone stores only a separate backend access token in Android encrypted preferences. */
var V274={version:'2.7.4',directVisible:false};
if(typeof V273!=='undefined')V273.version='2.7.4';
if(typeof V272!=='undefined')V272.version='2.7.4';
if(typeof V271!=='undefined')V271.version='2.7.4';
if(typeof V270!=='undefined')V270.version='2.7.4';
if(typeof V268!=='undefined')V268.version='2.7.4';

function v274Bridge(){return window.DhanPulseNative||null}
function v274Set(id,v,cl){var e=q(id);if(e){e.textContent=v;if(cl)e.className=cl}}
function v274TokenSaved(){
  try{var b=v274Bridge();return !!(b&&b.deltaBackendTokenStatus&&String(b.deltaBackendTokenStatus())==='SAVED')}catch(e){return false}
}
function v274SaveToken(){
  var el=q('deltaBackendToken'),v=el?el.value.trim():'',b=v274Bridge();
  if(!v){v268Set('deltaAuthMessage','Enter the Backend Access Token first.');return}
  try{b.saveDeltaBackendToken(v);el.value='';v274Set('deltaBackendTokenState','SAVED','bull');v268Set('deltaAuthMessage','Backend access token saved securely on this phone.')}catch(e){v268Set('deltaAuthMessage','Unable to save backend access token.')}
}
function v274ConnectBackend(){
  var el=q('deltaBackendToken'),v=el?el.value.trim():'',b=v274Bridge();
  try{
    if(v&&b.saveDeltaBackendToken){b.saveDeltaBackendToken(v);el.value=''}
    if(!b||!b.verifyDeltaBackendAccount){v268Set('deltaAuthMessage','Backend account bridge unavailable.');return}
    if(!v274TokenSaved()){v268Set('deltaAuthMessage','Save the Backend Access Token first.');return}
    v268Set('deltaAuthState','VERIFYING','neutral');
    v268Set('deltaAuthMessage','Connecting to Delta through DhanPulse backend variables...');
    b.verifyDeltaBackendAccount();
  }catch(e){v268Set('deltaAuthMessage','Unable to connect through backend variables.')}
}
function v274CheckBackend(){
  try{var b=v274Bridge();if(b&&b.checkDeltaBackendStatus)b.checkDeltaBackendStatus()}catch(e){}
}
window.__deltaBackendStatus=function(payload){
  var d=payload;try{if(typeof d==='string')d=JSON.parse(d)}catch(e){d={}}
  v274Set('deltaBackendKeyState',d.apiKey?'READY':'MISSING',d.apiKey?'bull':'neutral');
  v274Set('deltaBackendSecretState',d.apiSecret?'READY':'MISSING',d.apiSecret?'bull':'neutral');
  v274Set('deltaBackendTokenState',v274TokenSaved()?'SAVED':'NOT SAVED',v274TokenSaved()?'bull':'neutral');
  v274Set('deltaBackendOverall',(d.configured&&v274TokenSaved())?'READY':'SETUP NEEDED',(d.configured&&v274TokenSaved())?'bull':'neutral');
};
function v274ToggleDirect(){
  V274.directVisible=!V274.directVisible;
  var c=q('deltaAccountPanel')&&q('deltaAccountPanel').querySelector('.controls');
  if(c)c.classList.toggle('delta-direct-hidden',!V274.directVisible);
  var st=q('deltaCredentialPartState');if(st)st.classList.toggle('delta-direct-hidden',!V274.directVisible);
  var b=q('deltaDirectToggle');if(b)b.textContent=V274.directVisible?'Hide phone API fields':'Use phone credentials instead';
}
function v274Layout(){
  var panel=q('deltaAccountPanel');if(!panel)return;
  if(!q('deltaBackendCard')){
    var card=document.createElement('div');card.id='deltaBackendCard';card.className='backend-mode-card';
    card.innerHTML=
      '<div class="backend-mode-head"><b>Recommended · Backend Variables</b><span id="deltaBackendOverall">CHECKING</span></div>'+
      '<p>Keep DELTA_API_KEY and DELTA_API_SECRET in the DhanPulse backend variables. The APK never needs those two credentials. Enter only your separate Backend Access Token below.</p>'+
      '<div class="backend-actions"><label>Backend Access Token<input id="deltaBackendToken" type="password" autocomplete="off" placeholder="Enter your backend access token"></label><button id="deltaBackendSave">Save Token</button></div>'+
      '<button id="deltaBackendConnect" class="pro-api-toggle" style="width:100%;margin-top:8px">Connect Using Backend Variables</button>'+
      '<div class="backend-status-grid"><div><span>API Key</span><b id="deltaBackendKeyState">CHECKING</b></div><div><span>API Secret</span><b id="deltaBackendSecretState">CHECKING</b></div><div><span>Phone Token</span><b id="deltaBackendTokenState">CHECKING</b></div></div>'+
      '<button id="deltaDirectToggle">Use phone credentials instead</button>';
    var controls=panel.querySelector('.controls');
    if(controls)controls.parentNode.insertBefore(card,controls);
    else panel.appendChild(card);
    q('deltaBackendSave').onclick=v274SaveToken;
    q('deltaBackendConnect').onclick=v274ConnectBackend;
    q('deltaDirectToggle').onclick=v274ToggleDirect;
  }
  var controls2=panel.querySelector('.controls');if(controls2)controls2.classList.add('delta-direct-hidden');
  var parts=q('deltaCredentialPartState');if(parts)parts.classList.add('delta-direct-hidden');
  v274Set('deltaBackendTokenState',v274TokenSaved()?'SAVED':'NOT SAVED',v274TokenSaved()?'bull':'neutral');
  v274CheckBackend();
  if(v274TokenSaved())setTimeout(v274ConnectBackend,450);
}
var __v274AccountResult=window.__deltaAccountResult;
window.__deltaAccountResult=function(payload){
  if(__v274AccountResult)__v274AccountResult(payload);
  var d=payload;try{if(typeof d==='string')d=JSON.parse(d)}catch(e){d={}}
  if(d&&d.success&&d.backendMode){
    v274Set('deltaPrivateState','BACKEND','bull');
    v268Set('deltaAuthMessage','Connected securely through DhanPulse backend variables. API key and secret remain on the server.');
  }
};
setTimeout(v274Layout,260);
'''
if 'V2.7.4 Backend Variables.' not in s:
    s=s.replace('\n})();\n</script>',js+'\n})();\n</script>',1)
idx.write_text(s)

mgr=root/'app/src/main/java/com/dhanpulse/cryptofxv11/DeltaAccountManager.java'
m=mgr.read_text()
if 'KEY_BACKEND_TOKEN' not in m:
    m=m.replace('private static final String KEY_SECRET = "delta_api_secret";',
                'private static final String KEY_SECRET = "delta_api_secret";\n    private static final String KEY_BACKEND_TOKEN = "delta_backend_access_token";',1)
    anchor='''    static boolean hasSecret(Context c) {
        try { return !prefs(c).getString(KEY_SECRET, "").isEmpty(); } catch (Exception e) { return false; }
    }
'''
    extra=anchor+'''\n    static void saveBackendToken(Context c, String token) throws Exception {
        if (token == null || token.trim().isEmpty()) throw new IllegalArgumentException("Empty backend token");
        prefs(c).edit().putString(KEY_BACKEND_TOKEN, token.trim()).apply();
    }

    static String backendToken(Context c) {
        try { return prefs(c).getString(KEY_BACKEND_TOKEN, ""); } catch (Exception e) { return ""; }
    }

    static boolean hasBackendToken(Context c) {
        return !backendToken(c).isEmpty();
    }
'''
    if anchor not in m: raise SystemExit('hasSecret anchor missing')
    m=m.replace(anchor,extra,1)
m=m.replace('DhanPulse-Android/2.7.3','DhanPulse-Android/2.7.4')
mgr.write_text(m)

backend=root/'app/src/main/java/com/dhanpulse/cryptofxv11/DeltaBackendAccount.java'
backend.write_text(r'''package com.dhanpulse.cryptofxv11;

import android.content.Context;

import org.json.JSONObject;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

final class DeltaBackendAccount {
    interface Callback { void onResult(String json); }
    private static final String BASE = "https://dhanpulse-personal-api.onrender.com";
    private static final OkHttpClient HTTP = new OkHttpClient();
    private static final ExecutorService EXEC = Executors.newSingleThreadExecutor();
    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");

    private DeltaBackendAccount() {}

    static void statusAsync(Callback cb) {
        EXEC.execute(() -> {
            try {
                Request req = new Request.Builder().url(BASE + "/api/delta/status")
                        .header("Accept", "application/json")
                        .header("User-Agent", "DhanPulse-Android/2.7.4").get().build();
                try (Response r = HTTP.newCall(req).execute()) {
                    String body = r.body() == null ? "{}" : r.body().string();
                    cb.onResult(body);
                }
            } catch (Exception e) {
                cb.onResult("{\"configured\":false,\"apiKey\":false,\"apiSecret\":false,\"accessToken\":false}");
            }
        });
    }

    static void verifyAsync(Context context, Callback cb) {
        String token = DeltaAccountManager.backendToken(context);
        if (token == null || token.isEmpty()) {
            cb.onResult("{\"success\":false,\"error\":\"Backend Access Token is not saved\"}");
            return;
        }
        EXEC.execute(() -> {
            try {
                RequestBody body = RequestBody.create("{}", JSON);
                Request req = new Request.Builder().url(BASE + "/api/delta/account")
                        .header("Accept", "application/json")
                        .header("Content-Type", "application/json")
                        .header("X-Delta-Access-Token", token)
                        .header("User-Agent", "DhanPulse-Android/2.7.4")
                        .post(body).build();
                try (Response r = HTTP.newCall(req).execute()) {
                    String text = r.body() == null ? "{}" : r.body().string();
                    JSONObject j;
                    try { j = new JSONObject(text); }
                    catch (Exception x) { j = new JSONObject().put("success", false).put("error", "Backend returned invalid response"); }
                    if (!r.isSuccessful() && !j.has("success")) j.put("success", false);
                    cb.onResult(j.toString());
                }
            } catch (Exception e) {
                try {
                    cb.onResult(new JSONObject().put("success", false)
                            .put("error", e.getMessage() == null ? "Backend connection failed" : e.getMessage()).toString());
                } catch (Exception ignored) {}
            }
        });
    }
}
''')

ma=root/'app/src/main/java/com/dhanpulse/cryptofxv11/MainActivity.java'
a=ma.read_text()
anchor='''        @JavascriptInterface
        public void saveDeltaApiKey(String apiKey) {
'''
if anchor not in a: raise SystemExit('NativeBridge API key anchor missing')
if 'public void saveDeltaBackendToken(String token)' not in a:
    methods=r'''        @JavascriptInterface
        public void saveDeltaBackendToken(String token) {
            try { DeltaAccountManager.saveBackendToken(MainActivity.this, token); } catch (Exception ignored) {}
        }

        @JavascriptInterface
        public String deltaBackendTokenStatus() {
            return DeltaAccountManager.hasBackendToken(MainActivity.this) ? "SAVED" : "NONE";
        }

        @JavascriptInterface
        public void verifyDeltaBackendAccount() {
            DeltaBackendAccount.verifyAsync(MainActivity.this, MainActivity.this::deliverDeltaAccountResult);
        }

        @JavascriptInterface
        public void checkDeltaBackendStatus() {
            DeltaBackendAccount.statusAsync(MainActivity.this::deliverDeltaBackendStatus);
        }

'''
    a=a.replace(anchor,methods+anchor,1)

if 'private void deliverDeltaBackendStatus(String json)' not in a:
    method_anchor='''    private void deliverDeltaAccountResult(String json) {
'''
    helper=r'''    private void deliverDeltaBackendStatus(String json) {
        if (webView == null || json == null) return;
        webView.post(() -> {
            try {
                String js = "window.__deltaBackendStatus&&window.__deltaBackendStatus(" + JSONObject.quote(json) + ");";
                webView.evaluateJavascript(js, null);
            } catch (Exception ignored) {}
        });
    }

'''
    if method_anchor not in a: raise SystemExit('deliverDeltaAccountResult anchor missing')
    a=a.replace(method_anchor,helper+method_anchor,1)

ma.write_text(a)

b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 45',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.7.4"',bs,count=1)
b.write_text(bs)
