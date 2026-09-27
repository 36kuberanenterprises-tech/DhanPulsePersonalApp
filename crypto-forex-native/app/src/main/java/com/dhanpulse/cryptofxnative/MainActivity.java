package com.dhanpulse.cryptofxnative;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.PowerManager;
import android.provider.Settings;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.LinkedHashMap;
import java.util.Map;

public class MainActivity extends Activity {
    private static final String PREFS = "dhanpulse_native_monitor";
    private static final String TRADES = "native_trades_json";
    private WebView webView;
    private SharedPreferences prefs;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.rgb(7, 16, 24));
        getWindow().setNavigationBarColor(Color.rgb(7, 16, 24));
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);

        webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        }
        webView.setWebChromeClient(new WebChromeClient());
        webView.addJavascriptInterface(new AndroidBridge(), "AndroidNative");
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                injectNativeBridge();
            }
        });
        setContentView(webView);
        requestNotificationPermission();
        ensureService();
        webView.loadUrl("file:///android_asset/index.html");
    }

    @Override
    protected void onResume() {
        super.onResume();
        ensureService();
        if (webView != null) webView.onResume();
    }

    @Override
    protected void onPause() {
        if (webView != null) webView.onPause();
        super.onPause();
    }

    private void requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 401);
        }
    }

    private void ensureService() {
        Intent i = new Intent(this, BackgroundService.class);
        i.setAction(BackgroundService.ACTION_START);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(i); else startService(i);
    }

    private void injectNativeBridge() {
        String js = "(function(){" +
                "if(window.__dhanpulseNativeBridge)return;window.__dhanpulseNativeBridge=true;" +
                "var K='dhanpulse_cf_android_trades_v1';var lastNative='';" +
                "function mergeTrades(){try{" +
                "var localRaw=localStorage.getItem(K)||'[]';AndroidNative.importTrades(localRaw);" +
                "var nativeRaw=AndroidNative.getNativeTrades()||'[]';" +
                "if(nativeRaw!==lastNative){lastNative=nativeRaw;var l=JSON.parse(localRaw),n=JSON.parse(nativeRaw),m={};" +
                "(Array.isArray(l)?l:[]).forEach(function(t){m[t.id||t.slot||t.key]=t});" +
                "(Array.isArray(n)?n:[]).forEach(function(t){var k=t.id||t.slot||t.key,o=m[k];if(!o||t.status==='CLOSED'||(t.updatedAt||0)>=(o.updatedAt||0))m[k]=t});" +
                "var a=Object.keys(m).map(function(k){return m[k]}).sort(function(a,b){return (a.createdAt||0)-(b.createdAt||0)}).slice(-1500);" +
                "localStorage.setItem(K,JSON.stringify(a));if(window.S)S.tradeCache=a;if(window.renderTrades)renderTrades();}" +
                "}catch(e){}}" +
                "function sync(){try{var s=document.getElementById('symbol'),tf=document.getElementById('tf');if(s&&tf)AndroidNative.setMonitoringConfig(s.value,tf.value);" +
                "var st=JSON.parse(AndroidNative.getNativeState()||'{}');var e=document.getElementById('bgState');if(e){e.textContent=st.active?'NATIVE ACTIVE':'STARTING';e.className=st.active?'bull':'neutral';}" +
                "e=document.getElementById('bgHeartbeat');if(e)e.textContent=(st.tickAgeMs!=null?('tick age '+st.tickAgeMs+' ms · '):'')+(st.feedMode||'STARTING');" +
                "e=document.getElementById('bgSymbol');if(e)e.textContent=st.symbol||'';e=document.getElementById('bgTf');if(e)e.textContent=st.tf||'';" +
                "mergeTrades();AndroidNative.ensureService();}catch(e){}}" +
                "['symbol','tf'].forEach(function(id){var e=document.getElementById(id);if(e)e.addEventListener('change',function(){setTimeout(sync,30)})});" +
                "var c=document.getElementById('clear');if(c)c.addEventListener('click',function(){setTimeout(function(){if(!localStorage.getItem(K))AndroidNative.clearNativeTrades()},350)});" +
                "var anchor=document.getElementById('bgState');if(anchor){var p=anchor.closest('.panel');if(p&&!document.getElementById('nativeBatteryBtn')){var b=document.createElement('button');b.id='nativeBatteryBtn';b.textContent='Allow 24/7 Background';b.style.marginTop='12px';b.style.width='100%';b.onclick=function(){AndroidNative.openBatterySettings()};p.appendChild(b);}}" +
                "setInterval(sync,1000);sync();})();";
        webView.evaluateJavascript(js, null);
    }

    private static boolean validSymbol(String symbol) {
        return symbol != null && symbol.matches("[A-Z0-9]{5,20}");
    }

    private static boolean validTf(String tf) {
        return tf != null && tf.matches("(1m|3m|5m|15m|30m|1h|2h|4h|1d)");
    }

    private void mergeUiTrades(String json) {
        try {
            JSONArray nativeArr = new JSONArray(prefs.getString(TRADES, "[]"));
            JSONArray uiArr = new JSONArray(json == null ? "[]" : json);
            Map<String, JSONObject> map = new LinkedHashMap<>();
            for (int i = 0; i < nativeArr.length(); i++) {
                JSONObject t = nativeArr.optJSONObject(i);
                if (t != null) map.put(tradeKey(t), t);
            }
            for (int i = 0; i < uiArr.length(); i++) {
                JSONObject incoming = uiArr.optJSONObject(i);
                if (incoming == null) continue;
                String key = tradeKey(incoming);
                JSONObject old = map.get(key);
                if (old == null) {
                    map.put(key, incoming);
                } else {
                    String oldStatus = old.optString("status", "OPEN");
                    String newStatus = incoming.optString("status", "OPEN");
                    long oldUpdated = old.optLong("updatedAt", 0);
                    long newUpdated = incoming.optLong("updatedAt", 0);
                    if (("OPEN".equals(oldStatus) && "CLOSED".equals(newStatus)) || newUpdated > oldUpdated) {
                        map.put(key, incoming);
                    }
                }
            }
            JSONArray out = new JSONArray();
            int skip = Math.max(0, map.size() - 1500);
            int index = 0;
            for (JSONObject value : map.values()) {
                if (index++ >= skip) out.put(value);
            }
            prefs.edit().putString(TRADES, out.toString()).apply();
        } catch (Exception ignored) {
        }
    }

    private static String tradeKey(JSONObject t) {
        String id = t.optString("id", "");
        if (!id.isEmpty()) return id;
        String slot = t.optString("slot", "");
        if (!slot.isEmpty()) return slot;
        return t.optString("key", String.valueOf(t.hashCode()));
    }

    public final class AndroidBridge {
        @JavascriptInterface
        public void setMonitoringConfig(String symbol, String tf) {
            if (!validSymbol(symbol) || !validTf(tf)) return;
            String oldSymbol = prefs.getString("symbol", "BTCUSDT");
            String oldTf = prefs.getString("tf", "5m");
            if (symbol.equals(oldSymbol) && tf.equals(oldTf)) return;
            prefs.edit().putString("symbol", symbol).putString("tf", tf).apply();
            Intent i = new Intent(MainActivity.this, BackgroundService.class);
            i.setAction(BackgroundService.ACTION_CONFIG);
            i.putExtra("symbol", symbol);
            i.putExtra("tf", tf);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(i); else startService(i);
        }

        @JavascriptInterface
        public String getNativeState() {
            try {
                long now = System.currentTimeMillis();
                long hb = prefs.getLong("heartbeat", 0);
                long tick = prefs.getLong("last_tick_received", 0);
                JSONObject o = new JSONObject();
                o.put("active", hb > 0 && now - hb < 5000);
                o.put("heartbeatAgeMs", hb > 0 ? now - hb : -1);
                o.put("tickAgeMs", tick > 0 ? Math.max(0, now - tick) : -1);
                o.put("lastPrice", prefs.getString("last_price", ""));
                o.put("feedMode", prefs.getString("feed_mode", "STARTING"));
                o.put("signalState", prefs.getString("signal_state", "MONITORING"));
                o.put("symbol", prefs.getString("symbol", "BTCUSDT"));
                o.put("tf", prefs.getString("tf", "5m"));
                o.put("reconnects", prefs.getInt("reconnects", 0));
                o.put("engineMs", prefs.getString("engine_ms", ""));
                return o.toString();
            } catch (Exception e) {
                return "{}";
            }
        }

        @JavascriptInterface
        public String getNativeTrades() {
            return prefs.getString(TRADES, "[]");
        }

        @JavascriptInterface
        public void importTrades(String json) {
            mergeUiTrades(json);
        }

        @JavascriptInterface
        public void clearNativeTrades() {
            prefs.edit().putString(TRADES, "[]").apply();
        }

        @JavascriptInterface
        public void ensureService() {
            MainActivity.this.runOnUiThread(MainActivity.this::ensureService);
        }

        @JavascriptInterface
        public void openBatterySettings() {
            MainActivity.this.runOnUiThread(() -> {
                try {
                    PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !pm.isIgnoringBatteryOptimizations(getPackageName())) {
                        Intent i = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
                        i.setData(Uri.parse("package:" + getPackageName()));
                        startActivity(i);
                    } else {
                        startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));
                    }
                } catch (Exception ignored) {
                    startActivity(new Intent(Settings.ACTION_SETTINGS));
                }
            });
        }
    }
}
