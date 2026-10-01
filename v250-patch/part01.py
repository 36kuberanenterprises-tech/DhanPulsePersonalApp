var __v25BaseSelect=v24select;
v24select=function(){
  var sel=__v25BaseSelect();if(!sel||!sel.candidate){v25renderNews(v25newsContext(''));return sel}
  var c=sel.candidate,nc=v25newsContext(c.side);v25shadowMaybe('TECH',c,sel,nc);
  if(nc.block){v25renderNews(nc);return{candidate:null,reason:'WAIT: NEWS RISK · '+nc.reason,regime:sel.regime}}
  if(nc.aligned){c.newsAligned=true;c.support=(c.support||0)+1;c.reasons=(c.reasons||[]).concat(['news plus candle aligned']);if(c.score>=c.threshold+4&&c.support>=2)c.fast=true}
  else if(!nc.quiet&&nc.impact>=4){c.fast=false;c.reasons=(c.reasons||[]).concat(['news uncertainty slowed entry'])}
  v25shadowMaybe('NEWS',c,sel,nc);if((nc.aligned||nc.quiet)&&c.support>=2)v25shadowMaybe('FUSION',c,sel,nc);
  c.newsContext=nc;sel.candidate=c;v25renderNews(nc);return sel;
};
var __v25BasePublish=v24publish;
v24publish=function(c,sel){
  var before=trades().length,nc=c&&c.newsContext?c.newsContext:v25newsContext(c&&c.side||'');__v25BasePublish(c,sel);var list=trades();
  if(list.length>before){var t=list[list.length-1];t.id=String(t.id||'').replace(/^v24_/,'v25_');t.stage=String(t.stage||'').replace('V2.4','V2.5 NEWS FUSION');t.newsBias=nc.bias;t.newsImpact=nc.impact;t.newsAligned=!!nc.aligned;t.newsHeadline=nc.top?nc.top.title:'';t.newsDomain=nc.top?nc.top.domain:'';save(list);renderTrades()}
};
var __v25ProcessTick=processTick;
processTick=function(price,ts,qty,buy,eventTime,eventType){__v25ProcessTick(price,ts,qty,buy,eventTime,eventType);v25shadowUpdate(price)};
setInterval(function(){if(finite(S.livePrice))v25shadowUpdate(S.livePrice)},1500);
setInterval(v25requestNews,60000);
setTimeout(v25requestNews,1800);
setTimeout(function(){var b=q('newsRefresh');if(b)b.onclick=v25requestNews;v25renderNews(v25newsContext(''))},1200);
'''
if 'V2.5 News Intelligence and Shadow Lab' not in s:
    s = s.replace('</script>', js + '\n</script>', 1)
idx.write_text(s)

# Give the new version its own Android package and version.
b = root / 'app/build.gradle.kts'
bs = b.read_text()
bs = re.sub(r'applicationId = "com\\.dhanpulse\\.[^"]+"', 'applicationId = "com.dhanpulse.cryptofxresearchv250"', bs)
bs = re.sub(r'versionCode = \\d+', 'versionCode = 29', bs)
bs = re.sub(r'versionName = "[^"]+"', 'versionName = "2.5.0"', bs)
b.write_text(bs)

# Visible WebView native news fetch. This avoids browser CORS dependency.
ma = root / 'app/src/main/java/com/dhanpulse/cryptofxv11/MainActivity.java'
m = ma.read_text()
if 'okhttp3.OkHttpClient' not in m:
    m = m.replace('import org.json.JSONObject;\n', 'import org.json.JSONObject;\n\nimport java.io.IOException;\nimport java.util.concurrent.TimeUnit;\n\nimport okhttp3.Call;\nimport okhttp3.Callback;\nimport okhttp3.OkHttpClient;\nimport okhttp3.Request;\nimport okhttp3.Response;\n')
if 'private final OkHttpClient newsClient' not in m:
    m = m.replace('private boolean nativeTickReceiverRegistered = false;\n', 'private boolean nativeTickReceiverRegistered = false;\n    private final OkHttpClient newsClient = new OkHttpClient.Builder().callTimeout(8, TimeUnit.SECONDS).build();\n')
helper = r'''
    private boolean allowedNewsUrl(String url) {
        return url != null && url.startsWith("https://api.gdeltproject.org/");
    }

    private void deliverNewsToVisibleWeb(String body) {
        if (webView == null || body == null) return;
        webView.post(() -> {
            try {
                String js = "window.__dhanpulseNewsNative&&window.__dhanpulseNewsNative(" + JSONObject.quote(body) + ");";
                webView.evaluateJavascript(js, null);
            } catch (Exception ignored) {
            }
        });
    }

    private void fetchNewsForVisibleWeb(String url) {
        if (!allowedNewsUrl(url)) return;
        Request request = new Request.Builder().url(url).get().build();
        newsClient.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                deliverNewsToVisibleWeb("{}");
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                try (Response r = response) {
                    String body = r.body() == null ? "{}" : r.body().string();
                    deliverNewsToVisibleWeb(body);
                }
            }
        });
    }

'''
if 'fetchNewsForVisibleWeb' not in m:
    m = m.replace('    private final class NativeBridge {\n', helper + '    private final class NativeBridge {\n', 1)
if 'public void fetchNews(String url)' not in m:
    target = '        @JavascriptInterface\n        public void onMonitorConfig(String json) {\n            startMonitoringService(DhanPulseMonitorService.ACTION_CONFIG_EVENT, json);\n        }\n'
    repl = target + '\n        @JavascriptInterface\n        public void fetchNews(String url) {\n            fetchNewsForVisibleWeb(url);\n        }\n'
    if target not in m:
        raise SystemExit('MainActivity bridge target missing')
    m = m.replace(target, repl, 1)
ma.write_text(m)

# Headless background WebView gets the same news data through the service's existing OkHttp client.
sv = root / 'app/src/main/java/com/dhanpulse/cryptofxv11/DhanPulseMonitorService.java'
v = sv.read_text()
service_helper = r'''
    private boolean allowedNewsUrl(String url) {
        return url != null && url.startsWith("https://api.gdeltproject.org/");
    }

    private void deliverNewsToHeadlessWeb(String body) {
        if (body == null) return;
        mainHandler.post(() -> {
            WebView w = headlessWebView;
            if (w == null) return;
            try {
                String js = "window.__dhanpulseNewsNative&&window.__dhanpulseNewsNative(" + JSONObject.quote(body) + ");";
                w.evaluateJavascript(js, null);
            } catch (Exception ignored) {
            }
        });
    }

    private void fetchNewsForHeadlessWeb(String url) {
        if (!allowedNewsUrl(url) || marketClient == null) return;
        Request request = new Request.Builder().url(url).get().build();
        marketClient.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                deliverNewsToHeadlessWeb("{}");
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                try (Response r = response) {
