from pathlib import Path
import re

root = Path('crypto-forex-app/buildsrc')
idx = root / 'app/src/main/assets/index.html'
s = idx.read_text()

s = s.replace('Version 2.6.7 Delta Production Only', 'Version 2.6.8 Delta Account Verify')
s = s.replace('DhanPulse Delta Exchange India Version 2.6.7 Delta Production Only.',
              'DhanPulse Delta Exchange India Version 2.6.8 Delta Account Verify.')
s = s.replace('DhanPulse Delta Exchange India Version 2.6.7 Delta Production Only',
              'DhanPulse Delta Exchange India Version 2.6.8 Delta Account Verify')

panel = r'''
<div class="panel" id="deltaAccountPanel">
  <div class="row">
    <div>
      <h2>Delta Account Verification</h2>
      <div class="muted small">Enter your Delta India production API key and API secret on this phone. They are encrypted in Android secure storage and are never written to WebView storage or GitHub.</div>
    </div>
    <b id="deltaAuthState" class="neutral">NOT CONNECTED</b>
  </div>
  <div class="controls" style="margin-top:12px">
    <label>Delta API Key
      <input id="deltaApiKey" type="password" autocomplete="off" placeholder="Enter production API key">
    </label>
    <label>Delta API Secret
      <input id="deltaApiSecret" type="password" autocomplete="off" placeholder="Enter matching API secret">
    </label>
    <button id="deltaSaveVerify">Save and Verify</button>
    <button id="deltaRefreshAccount" class="secondary">Refresh Account</button>
    <button id="deltaClearCredentials" class="secondary">Clear Credentials</button>
  </div>
  <div class="context" style="margin-top:12px">
    <div><span>Authenticated User ID</span><b id="deltaUserId">NA</b></div>
    <div><span>Account Name</span><b id="deltaAccountName">NA</b></div>
    <div><span>Net Equity</span><b id="deltaNetEquity">NA</b></div>
    <div><span>Available Balance</span><b id="deltaAvailable">NA</b></div>
    <div><span>Total Balance</span><b id="deltaTotalBalance">NA</b></div>
    <div><span>Credential</span><b id="deltaKeyMask">NOT SAVED</b></div>
  </div>
  <div id="deltaWallets" class="muted small" style="margin-top:10px">Save credentials to verify the Delta account.</div>
  <div id="deltaAuthMessage" class="muted small" style="margin-top:6px"></div>
</div>
'''

if 'id="deltaAccountPanel"' not in s:
    anchor = '<div class="panel" id="opportunityEngine">'
    if anchor not in s:
        anchor = '<div class="panel" id="historyLab">'
    if anchor not in s:
        raise SystemExit('No panel anchor found')
    s = s.replace(anchor, panel + '\n' + anchor, 1)

js = r'''
/* V2.6.8 Delta authenticated account verification.
   API key/secret are handled only by the native Android layer. */
var V268={version:'2.6.8'};
if(typeof V261!=='undefined')V261.version='2.6.8';
if(typeof V26!=='undefined')V26.version='2.6.8';
if(typeof V263!=='undefined')V263.version='2.6.8';
if(typeof V264!=='undefined')V264.version='2.6.8';
if(typeof V265!=='undefined')V265.version='2.6.8';
if(typeof V266!=='undefined')V266.version='2.6.8';
if(typeof V267!=='undefined')V267.version='2.6.8';

function v268Set(id,val,cl){var z=q(id);if(z){z.textContent=val==null?'NA':String(val);if(cl)z.className=cl}}
function v268WalletText(ws){
  if(!Array.isArray(ws)||!ws.length)return 'No nonzero wallet balances returned.';
  return ws.slice(0,8).map(function(w){
    return String(w.asset||'ASSET')+': available '+String(w.available||'0')+' · balance '+String(w.balance||'0');
  }).join(' | ');
}
window.__deltaAccountResult=function(payload){
  var d=payload;
  try{if(typeof d==='string')d=JSON.parse(d)}catch(e){d={success:false,error:'Invalid native response'}}
  if(!d||!d.success){
    v268Set('deltaAuthState','AUTH FAILED','bear');
    v268Set('deltaAuthMessage',(d&&d.error)||'Delta authentication failed');
    return;
  }
  v268Set('deltaAuthState','CONNECTED','bull');
  v268Set('deltaUserId',d.userId||'NA');
  v268Set('deltaAccountName',d.accountName||d.displayName||'Not returned by API');
  v268Set('deltaNetEquity',d.netEquity||'NA');
  v268Set('deltaAvailable',d.primaryAvailable||'NA');
  v268Set('deltaTotalBalance',d.primaryBalance||'NA');
  v268Set('deltaKeyMask',d.keyMask||'SAVED');
  v268Set('deltaWallets',v268WalletText(d.wallets));
  v268Set('deltaAuthMessage','Authenticated directly with Delta Exchange India production API.');
};
function v268Bridge(){return window.DhanPulseNative||null}
function v268SaveVerify(){
  var k=q('deltaApiKey')?q('deltaApiKey').value.trim():'';
  var sec=q('deltaApiSecret')?q('deltaApiSecret').value.trim():'';
  if(!k||!sec){v268Set('deltaAuthMessage','Enter both API key and API secret.');return}
  var b=v268Bridge();
  if(!b||!b.saveAndVerifyDeltaCredentials){v268Set('deltaAuthMessage','Native Delta credential bridge unavailable.');return}
  v268Set('deltaAuthState','VERIFYING','neutral');
  v268Set('deltaAuthMessage','Signing a read only account request to Delta production...');
  try{b.saveAndVerifyDeltaCredentials(k,sec);q('deltaApiKey').value='';q('deltaApiSecret').value=''}catch(e){v268Set('deltaAuthMessage',String(e))}
}
function v268Refresh(){
  var b=v268Bridge();if(!b||!b.refreshDeltaAccount){v268Set('deltaAuthMessage','Native Delta account bridge unavailable.');return}
  v268Set('deltaAuthState','REFRESHING','neutral');v268Set('deltaAuthMessage','Refreshing actual Delta account balances...');
  try{b.refreshDeltaAccount()}catch(e){v268Set('deltaAuthMessage',String(e))}
}
function v268Clear(){
  var b=v268Bridge();if(b&&b.clearDeltaCredentials)b.clearDeltaCredentials();
  ['deltaUserId','deltaAccountName','deltaNetEquity','deltaAvailable','deltaTotalBalance'].forEach(function(x){v268Set(x,'NA')});
  v268Set('deltaKeyMask','NOT SAVED');v268Set('deltaWallets','Credentials cleared from Android secure storage.');v268Set('deltaAuthState','NOT CONNECTED','neutral');
}
setTimeout(function(){
  try{
    if(q('deltaSaveVerify'))q('deltaSaveVerify').onclick=v268SaveVerify;
    if(q('deltaRefreshAccount'))q('deltaRefreshAccount').onclick=v268Refresh;
    if(q('deltaClearCredentials'))q('deltaClearCredentials').onclick=v268Clear;
    var b=v268Bridge();
    if(b&&b.deltaCredentialStatus){
      var st=String(b.deltaCredentialStatus()||'NONE');
      if(st==='SAVED'){v268Set('deltaKeyMask','SAVED');v268Set('deltaAuthMessage','Saved Delta credentials found on this phone. Tap Refresh Account to verify current balance.')}
    }
  }catch(e){}
},100);
'''

if 'V2.6.8 Delta authenticated account verification.' not in s:
    s = s.replace('\n})();\n</script>', js + '\n})();\n</script>', 1)

idx.write_text(s)

# Add AndroidX encrypted preferences dependency.
b = root / 'app/build.gradle.kts'
bs = b.read_text()
if 'androidx.security:security-crypto' not in bs:
    if 'dependencies {' in bs:
        bs = bs.replace('dependencies {', 'dependencies {\n    implementation("androidx.security:security-crypto:1.0.0")', 1)
    else:
        bs += '\n\ndependencies {\n    implementation("androidx.security:security-crypto:1.0.0")\n}\n'
bs = re.sub(r'applicationId\s*=\s*"[^"]+"', 'applicationId = "com.dhanpulse.cryptofxstablev263"', bs, count=1)
bs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 39', bs, count=1)
bs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.6.8"', bs, count=1)
b.write_text(bs)

java_dir = root / 'app/src/main/java/com/dhanpulse/cryptofxv11'
mgr = java_dir / 'DeltaAccountManager.java'
mgr.write_text(r'''package com.dhanpulse.cryptofxv11;

import android.content.Context;
import android.content.SharedPreferences;

import androidx.security.crypto.EncryptedSharedPreferences;
import androidx.security.crypto.MasterKeys;

import org.json.JSONArray;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;

final class DeltaAccountManager {
    interface Callback { void onResult(String json); }

    private static final String PREF = "dhanpulse_delta_secure_v268";
    private static final String KEY_API = "delta_api_key";
    private static final String KEY_SECRET = "delta_api_secret";
    private static final String BASE = "https://api.india.delta.exchange";
    private static final ExecutorService EXEC = Executors.newSingleThreadExecutor();
    private static final OkHttpClient HTTP = new OkHttpClient();

    private DeltaAccountManager() {}

    private static SharedPreferences prefs(Context c) throws Exception {
        String alias = MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC);
        return EncryptedSharedPreferences.create(
                PREF, alias, c,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM);
    }

    static void save(Context c, String apiKey, String secret) throws Exception {
        prefs(c).edit().putString(KEY_API, apiKey.trim()).putString(KEY_SECRET, secret.trim()).apply();
    }

    static void clear(Context c) {
        try { prefs(c).edit().clear().apply(); } catch (Exception ignored) {}
    }

    static boolean has(Context c) {
        try {
            SharedPreferences p = prefs(c);
            return !p.getString(KEY_API, "").isEmpty() && !p.getString(KEY_SECRET, "").isEmpty();
        } catch (Exception e) {
            return false;
        }
    }

    static void verifyAsync(Context c, Callback cb) {
        Context app = c.getApplicationContext();
        EXEC.execute(() -> {
            JSONObject out = new JSONObject();
            try {
                SharedPreferences p = prefs(app);
                String key = p.getString(KEY_API, "");
                String secret = p.getString(KEY_SECRET, "");
                if (key.isEmpty() || secret.isEmpty()) throw new Exception("No saved Delta credentials");

                JSONObject pref = signedGet("/v2/users/trading_preferences", key, secret);
                if (!pref.optBoolean("success", false)) throw new Exception(errorText(pref));
                JSONObject pr = pref.optJSONObject("result");
                String userId = pr == null ? "" : String.valueOf(pr.opt("user_id"));

                JSONObject wallets = signedGet("/v2/wallet/balances", key, secret);
                if (!wallets.optBoolean("success", false)) throw new Exception(errorText(wallets));

                String accountName = "";
                String displayName = "";
                try {
                    JSONObject subs = signedGet("/v2/sub_accounts", key, secret);
                    JSONArray sa = subs.optJSONArray("result");
                    if (subs.optBoolean("success", false) && sa != null) {
                        for (int i = 0; i < sa.length(); i++) {
                            JSONObject u = sa.optJSONObject(i);
                            if (u == null) continue;
                            if (userId.equals(String.valueOf(u.opt("id")))) {
                                accountName = u.optString("account_name", "");
                                String fn = u.optString("first_name", "");
                                String ln = u.optString("last_name", "");
                                displayName = (fn + " " + ln).trim();
                                break;
                            }
                        }
                    }
                } catch (Exception ignored) {}

                JSONObject meta = wallets.optJSONObject("meta");
                String netEquity = meta == null ? "" : meta.optString("net_equity", "");
                JSONArray wr = wallets.optJSONArray("result");
                JSONArray clean = new JSONArray();
                String primaryAvailable = "";
                String primaryBalance = "";
                double bestAbs = -1.0;

                if (wr != null) {
                    for (int i = 0; i < wr.length(); i++) {
                        JSONObject w = wr.optJSONObject(i);
                        if (w == null) continue;
                        String asset = w.optString("asset_symbol", "");
                        String bal = w.optString("balance", "0");
                        String avail = w.optString("available_balance", "0");
                        double score = 0.0;
                        try { score = Math.abs(Double.parseDouble(bal)); } catch (Exception ignored) {}
                        if (score > 0.0) {
                            JSONObject cw = new JSONObject();
                            cw.put("asset", asset);
                            cw.put("balance", bal);
                            cw.put("available", avail);
                            clean.put(cw);
                        }
                        if (score > bestAbs) {
                            bestAbs = score;
                            primaryAvailable = asset + " " + avail;
                            primaryBalance = asset + " " + bal;
                        }
                        if (userId.isEmpty() && w.has("user_id")) userId = String.valueOf(w.opt("user_id"));
                    }
                }

                out.put("success", true);
                out.put("userId", userId);
                out.put("accountName", accountName);
                out.put("displayName", displayName);
                out.put("netEquity", netEquity);
                out.put("primaryAvailable", primaryAvailable);
                out.put("primaryBalance", primaryBalance);
                out.put("wallets", clean);
                out.put("keyMask", maskKey(key));
            } catch (Exception e) {
                try {
                    out.put("success", false);
                    out.put("error", e.getMessage() == null ? "Delta authentication failed" : e.getMessage());
                } catch (Exception ignored) {}
            }
            cb.onResult(out.toString());
        });
    }

    private static JSONObject signedGet(String path, String key, String secret) throws Exception {
        String ts = String.valueOf(System.currentTimeMillis() / 1000L);
        String message = "GET" + ts + path;
        String signature = hmacSha256(secret, message);
        Request req = new Request.Builder()
                .url(BASE + path)
                .header("Accept", "application/json")
                .header("api-key", key)
                .header("signature", signature)
                .header("timestamp", ts)
                .header("User-Agent", "DhanPulse-Android/2.6.8")
                .get()
                .build();
        try (Response r = HTTP.newCall(req).execute()) {
            String body = r.body() == null ? "" : r.body().string();
            JSONObject j = body.isEmpty() ? new JSONObject() : new JSONObject(body);
            if (!r.isSuccessful() && !j.optBoolean("success", false)) {
                throw new Exception(errorText(j) + " (HTTP " + r.code() + ")");
            }
            return j;
        }
    }

    private static String hmacSha256(String secret, String message) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        byte[] bytes = mac.doFinal(message.getBytes(StandardCharsets.UTF_8));
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) sb.append(String.format("%02x", b & 0xff));
        return sb.toString();
    }

    private static String errorText(JSONObject j) {
        JSONObject e = j.optJSONObject("error");
        if (e != null) {
            String code = e.optString("code", "");
            String ctx = e.optString("context", "");
            if (!code.isEmpty()) return ctx.isEmpty() ? code : code + ": " + ctx;
        }
        return j.optString("message", "Delta authentication failed");
    }

    private static String maskKey(String key) {
        if (key == null || key.isEmpty()) return "SAVED";
        if (key.length() <= 8) return "••••" + key.substring(Math.max(0, key.length() - 2));
        return key.substring(0, 4) + "••••••••" + key.substring(key.length() - 4);
    }
}
''')

ma = java_dir / 'MainActivity.java'
m = ma.read_text()

bridge_anchor = '''        @JavascriptInterface
        public void onMonitorConfig(String json) {
            startMonitoringService(DhanPulseMonitorService.ACTION_CONFIG_EVENT, json);
        }
'''
addition = bridge_anchor + r'''

        @JavascriptInterface
        public void saveAndVerifyDeltaCredentials(String apiKey, String apiSecret) {
            try {
                if (apiKey == null || apiKey.trim().isEmpty() || apiSecret == null || apiSecret.trim().isEmpty()) {
                    deliverDeltaAccountResult("{\"success\":false,\"error\":\"Enter both API key and API secret\"}");
                    return;
                }
                DeltaAccountManager.save(MainActivity.this, apiKey, apiSecret);
                refreshDeltaAccount();
            } catch (Exception e) {
                deliverDeltaAccountResult("{\"success\":false,\"error\":\"Unable to save Delta credentials securely\"}");
            }
        }

        @JavascriptInterface
        public void refreshDeltaAccount() {
            DeltaAccountManager.verifyAsync(MainActivity.this, MainActivity.this::deliverDeltaAccountResult);
        }

        @JavascriptInterface
        public void clearDeltaCredentials() {
            DeltaAccountManager.clear(MainActivity.this);
        }

        @JavascriptInterface
        public String deltaCredentialStatus() {
            return DeltaAccountManager.has(MainActivity.this) ? "SAVED" : "NONE";
        }
'''
if 'saveAndVerifyDeltaCredentials' not in m:
    if bridge_anchor not in m:
        raise SystemExit('NativeBridge monitor config anchor missing')
    m = m.replace(bridge_anchor, addition, 1)

method_anchor = '\n    @Override\n    protected void onDestroy()'
deliver = r'''
    private void deliverDeltaAccountResult(String json) {
        if (webView == null || json == null) return;
        webView.post(() -> {
            try {
                String js = "window.__deltaAccountResult&&window.__deltaAccountResult(" + JSONObject.quote(json) + ");";
                webView.evaluateJavascript(js, null);
            } catch (Exception ignored) {
            }
        });
    }

'''
if 'private void deliverDeltaAccountResult' not in m:
    if method_anchor not in m:
        raise SystemExit('onDestroy anchor missing')
    m = m.replace(method_anchor, '\n' + deliver + '    @Override\n    protected void onDestroy()', 1)

ma.write_text(m)
