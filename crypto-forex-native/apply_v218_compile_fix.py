from pathlib import Path

p = Path(__file__).resolve().parent / "app/src/main/java/com/dhanpulse/cryptofxnative/MainActivity.java"
a = p.read_text(encoding="utf-8")
a = a.replace(
    '        @JavascriptInterface\n        @JavascriptInterface\n        public String getNativeTrades()',
    '        @JavascriptInterface\n        public String getNativeTrades()',
)
a = a.replace(
    '        @JavascriptInterface\n        @JavascriptInterface\n        public void clearNativeTrades()',
    '        @JavascriptInterface\n        public void clearNativeTrades()',
)
p.write_text(a, encoding="utf-8")
print('V2.1.8 compile annotation fix applied')
