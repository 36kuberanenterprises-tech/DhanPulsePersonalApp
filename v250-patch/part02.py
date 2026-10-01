                    String body = r.body() == null ? "{}" : r.body().string();
                    deliverNewsToHeadlessWeb(body);
                }
            }
        });
    }

'''
if 'fetchNewsForHeadlessWeb' not in v:
    v = v.replace('    private final class NativeBridge {\n', service_helper + '    private final class NativeBridge {\n', 1)
if 'public void fetchNews(String url)' not in v:
    target2 = '        @JavascriptInterface\n        public void onMonitorConfig(String json) {\n            if (json != null) prefs.edit().putString("monitor_config", json).apply();\n        }\n'
    repl2 = target2 + '\n        @JavascriptInterface\n        public void fetchNews(String url) {\n            fetchNewsForHeadlessWeb(url);\n        }\n'
    if target2 not in v:
        raise SystemExit('Service bridge target missing')
    v = v.replace(target2, repl2, 1)
sv.write_text(v)
