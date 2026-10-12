from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.7.1 iOS Market Pro','Version 2.7.2 Delta Secure Link')
s=s.replace('DhanPulse Delta Exchange India Version 2.7.1 iOS Market Pro.',
            'DhanPulse Delta Exchange India Version 2.7.2 Delta Secure Link.')
s=s.replace('DhanPulse Delta Exchange India Version 2.7.1 iOS Market Pro',
            'DhanPulse Delta Exchange India Version 2.7.2 Delta Secure Link')

# Add private authenticated connection status to account panel.
needle='<div><span>Credential</span><b id="deltaKeyMask">NOT SAVED</b></div>'
if needle in s and 'id="deltaPrivateState"' not in s:
    s=s.replace(needle, needle+'\n    <div><span>Private Feed</span><b id="deltaPrivateState">OFFLINE</b></div>',1)

# Replace any wording suggesting multiple providers.
s=s.replace('Delta Market Context','Delta Secure Context')
s=s.replace('Delta Strategy Shadow Test','Delta Strategy Lab')
s=s.replace('Delta production public REST and WebSocket only. No other API key or provider is used.',
            'Delta Exchange India is the only provider used by this app.')
s=s.replace('Delta Exchange India production public REST and WebSocket feeds are the only market data sources in this build.',
            'Delta Exchange India is the only provider used by this app.')

js=r'''
/* V2.7.2 Delta Secure Link.
   Delta is the only provider. Market data uses Delta official market channels.
   Private account updates use authenticated Delta production websocket. */
var V272={version:'2.7.2',privateConnected:false,privateLastEvent:null};
if(typeof V271!=='undefined')V271.version='2.7.2';
if(typeof V270!=='undefined')V270.version='2.7.2';
if(typeof V268!=='undefined')V268.version='2.7.2';

window.__deltaPrivateStatus=function(payload){
  var d=payload;try{if(typeof d==='string')d=JSON.parse(d)}catch(e){d={state:'ERROR',message:'Invalid private feed response'}}
  V272.privateConnected=!!(d&&d.connected);
  V272.privateLastEvent=d||null;
  var z=q('deltaPrivateState');
  if(z){z.textContent=V272.privateConnected?'CONNECTED':String((d&&d.state)||'OFFLINE');z.className=V272.privateConnected?'bull':'neutral'}
  var msg=q('deltaAuthMessage');
  if(msg&&d&&d.message&&(!V272.privateConnected||/ERROR|REJECT|IP|AUTH/i.test(String(d.state||''))))msg.textContent=d.message;
  if(typeof v270UpdateTop==='function')v270UpdateTop();
  if(typeof v271AccountLine==='function')v271AccountLine();
};
function v272StartPrivate(){
  try{
    var b=window.DhanPulseNative;
    if(b&&b.startDeltaPrivateFeed&&b.deltaCredentialStatus&&String(b.deltaCredentialStatus())==='SAVED')b.startDeltaPrivateFeed();
  }catch(e){}
}
var __v272Acct=window.__deltaAccountResult;
window.__deltaAccountResult=function(payload){
  if(__v272Acct)__v272Acct(payload);
  setTimeout(v272StartPrivate,120);
};
setTimeout(v272StartPrivate,350);
'''
if 'V2.7.2 Delta Secure Link.' not in s:
    s=s.replace('\n})();\n</script>',js+'\n})();\n</script>',1)
idx.write_text(s)

mgr=root/'app/src/main/java/com/dhanpulse/cryptofxv11/DeltaAccountManager.java'
m=mgr.read_text()
if 'static String[] credentials(Context c)' not in m:
    anchor='''    static boolean has(Context c) {
'''
    helper='''    static String[] credentials(Context c) {
        try {
            SharedPreferences p = prefs(c);
            return new String[]{p.getString(KEY_API, ""), p.getString(KEY_SECRET, "")};
        } catch (Exception e) {
            return new String[]{"", ""};
        }
    }

'''
    if anchor not in m: raise SystemExit('DeltaAccountManager anchor missing')
    m=m.replace(anchor,helper+anchor,1)
m=m.replace('DhanPulse-Android/2.6.9','DhanPulse-Android/2.7.2')
mgr.write_text(m)

# Native authenticated Delta websocket. Read-only account/event subscriptions only.
feed=root/'app/src/main/java/com/dhanpulse/cryptofxv11/DeltaPrivateFeed.java'
feed.write_text(r'''package com.dhanpulse.cryptofxv11;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;

final class DeltaPrivateFeed {
    interface Callback { void onStatus(String json); }

    private final Context context;
    private final Callback callback;
    private final OkHttpClient client;
    private WebSocket ws;

    DeltaPrivateFeed(Context context, Callback callback) {
        this.context = context.getApplicationContext();
        this.callback = callback;
        this.client = new OkHttpClient.Builder().retryOnConnectionFailure(true).build();
    }

    synchronized void start() {
        stop();
        String[] c = DeltaAccountManager.credentials(context);
        if (c[0].isEmpty() || c[1].isEmpty()) {
            emit("NO CREDENTIALS", false, "Save and verify your Delta API key and secret first.");
            return;
        }
        final String apiKey = c[0];
        final String secret = c[1];
        Request req = new Request.Builder()
                .url("wss://socket.india.delta.exchange")
                .header("User-Agent", "DhanPulse-Android/2.7.2")
                .build();
        ws = client.newWebSocket(req, new WebSocketListener() {
            @Override public void onOpen(WebSocket webSocket, Response response) {
                try {
                    long ts = System.currentTimeMillis() / 1000L;
                    String sig = hmac(secret, "GET" + ts + "/live");
                    JSONObject payload = new JSONObject();
                    payload.put("api-key", apiKey);
                    payload.put("timestamp", ts);
                    payload.put("signature", sig);
                    JSONObject auth = new JSONObject();
                    auth.put("type", "key-auth");
                    auth.put("payload", payload);
                    webSocket.send(auth.toString());
                    emit("AUTHENTICATING", false, "Authenticating Delta private account feed...");
                } catch (Exception e) {
                    emit("AUTH ERROR", false, "Unable to sign Delta private websocket authentication.");
                }
            }

            @Override public void onMessage(WebSocket webSocket, String text) {
                try {
                    JSONObject j = new JSONObject(text);
                    String type = j.optString("type", "");
                    if ("key-auth".equals(type)) {
                        boolean ok = j.optBoolean("success", false);
                        if (ok) {
                            subscribe(webSocket);
                            emit("CONNECTED", true, "Delta private account feed authenticated.");
                        } else {
                            String status = j.optString("status", "AUTH REJECTED");
                            String message = j.optString("message", "Delta private authentication rejected.");
                            emit(status.toUpperCase(), false, message);
                        }
                        return;
                    }
                    if ("orders".equals(type) || "positions".equals(type) || "margins".equals(type)
                            || "v2/user_trades".equals(type) || "user_trades".equals(type)) {
                        JSONObject out = new JSONObject();
                        out.put("state", type.toUpperCase());
                        out.put("connected", true);
                        out.put("message", "Delta private " + type + " update received.");
                        out.put("event", j);
                        callback.onStatus(out.toString());
                    }
                } catch (Exception ignored) {
                }
            }

            @Override public void onClosing(WebSocket webSocket, int code, String reason) {
                emit("CLOSING", false, reason == null ? "Delta private feed closing." : reason);
            }

            @Override public void onClosed(WebSocket webSocket, int code, String reason) {
                emit("OFFLINE", false, reason == null ? "Delta private feed closed." : reason);
            }

            @Override public void onFailure(WebSocket webSocket, Throwable t, Response response) {
                String msg = t == null ? "Delta private feed connection failed." : t.getMessage();
                emit("ERROR", false, msg == null ? "Delta private feed connection failed." : msg);
            }
        });
    }

    private void subscribe(WebSocket webSocket) throws Exception {
        JSONArray channels = new JSONArray();
        String[] names = new String[]{"orders", "positions", "margins", "v2/user_trades"};
        for (String name : names) {
            JSONObject c = new JSONObject();
            c.put("name", name);
            JSONArray symbols = new JSONArray();
            symbols.put("all");
            c.put("symbols", symbols);
            channels.put(c);
        }
        JSONObject payload = new JSONObject();
        payload.put("channels", channels);
        JSONObject sub = new JSONObject();
        sub.put("type", "subscribe");
        sub.put("payload", payload);
        webSocket.send(sub.toString());
    }

    synchronized void stop() {
        if (ws != null) {
            try { ws.close(1000, "app lifecycle"); } catch (Exception ignored) {}
            ws = null;
        }
    }

    private void emit(String state, boolean connected, String message) {
        try {
            JSONObject o = new JSONObject();
            o.put("state", state);
            o.put("connected", connected);
            o.put("message", message == null ? "" : message);
            callback.onStatus(o.toString());
        } catch (Exception ignored) {}
    }

    private static String hmac(String secret, String message) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        byte[] out = mac.doFinal(message.getBytes(StandardCharsets.UTF_8));
        StringBuilder sb = new StringBuilder(out.length * 2);
        for (byte b : out) sb.append(String.format("%02x", b & 0xff));
        return sb.toString();
    }
}
''')

ma=root/'app/src/main/java/com/dhanpulse/cryptofxv11/MainActivity.java'
a=ma.read_text()
if 'private DeltaPrivateFeed deltaPrivateFeed;' not in a:
    # insert near WebView field or class body.
    p=re.search(r'(private\s+WebView\s+webView\s*;)',a)
    if not p: raise SystemExit('webView field missing')
    a=a[:p.end()]+ '\n    private DeltaPrivateFeed deltaPrivateFeed;' + a[p.end():]

if 'public void startDeltaPrivateFeed()' not in a:
    anchor='''        @JavascriptInterface
        public String deltaCredentialStatus() {
            return DeltaAccountManager.has(MainActivity.this) ? "SAVED" : "NONE";
        }
'''
    extra=anchor+r'''

        @JavascriptInterface
        public void startDeltaPrivateFeed() {
            MainActivity.this.startDeltaPrivateFeedNative();
        }
'''
    if anchor not in a: raise SystemExit('deltaCredentialStatus anchor missing')
    a=a.replace(anchor,extra,1)

if 'private void startDeltaPrivateFeedNative()' not in a:
    method_anchor='''    private void deliverDeltaAccountResult(String json) {
'''
    helper=r'''    private void startDeltaPrivateFeedNative() {
        runOnUiThread(() -> {
            try {
                if (deltaPrivateFeed == null) {
                    deltaPrivateFeed = new DeltaPrivateFeed(MainActivity.this, MainActivity.this::deliverDeltaPrivateStatus);
                }
                deltaPrivateFeed.start();
            } catch (Exception e) {
                deliverDeltaPrivateStatus("{\"state\":\"ERROR\",\"connected\":false,\"message\":\"Unable to start Delta private feed\"}");
            }
        });
    }

    private void deliverDeltaPrivateStatus(String json) {
        if (webView == null || json == null) return;
        webView.post(() -> {
            try {
                String js = "window.__deltaPrivateStatus&&window.__deltaPrivateStatus(" + JSONObject.quote(json) + ");";
                webView.evaluateJavascript(js, null);
            } catch (Exception ignored) {
            }
        });
    }

'''
    if method_anchor not in a: raise SystemExit('deliver account anchor missing')
    a=a.replace(method_anchor,helper+method_anchor,1)

# Start private feed after credential save and stop it with Activity.
a=a.replace('DeltaAccountManager.save(MainActivity.this, apiKey, apiSecret);\n                refreshDeltaAccount();',
            'DeltaAccountManager.save(MainActivity.this, apiKey, apiSecret);\n                refreshDeltaAccount();\n                startDeltaPrivateFeedNative();',1)
a=a.replace('DeltaAccountManager.clear(MainActivity.this);',
            'DeltaAccountManager.clear(MainActivity.this);\n            if (deltaPrivateFeed != null) deltaPrivateFeed.stop();',1)
if 'if (deltaPrivateFeed != null) deltaPrivateFeed.stop();' not in a.split('protected void onDestroy()',1)[1]:
    a=a.replace('protected void onDestroy() {','protected void onDestroy() {\n        if (deltaPrivateFeed != null) deltaPrivateFeed.stop();',1)
ma.write_text(a)

b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 43',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.7.2"',bs,count=1)
b.write_text(bs)
