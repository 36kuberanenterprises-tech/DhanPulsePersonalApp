from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.6.5 Live Trade Clarity','Version 2.6.6 Delta Only')
s=s.replace('DhanPulse Crypto and Forex Version 2.6.5 Live Trade Clarity.','DhanPulse Delta Exchange India Version 2.6.6 Delta Only.')
s=s.replace('DhanPulse Delta Exchange India Version 2.6 Delta Only.','DhanPulse Delta Exchange India Version 2.6.6 Delta Only.')
s=s.replace('DhanPulse Delta Exchange India Version 2.6 Delta Only','DhanPulse Delta Exchange India Version 2.6.6 Delta Only')

for old in ["V261.version='2.6.5'","V26.version='2.6.5'","V263.version='2.6.5'","V264.version='2.6.5'","var V265={version:'2.6.5'"]:
    s=s.replace(old,old.replace("2.6.5","2.6.6"))
s=s.replace("version:'2.6.5'","version:'2.6.6'")
s=s.replace("version:'2.6.4'","version:'2.6.6'")
s=s.replace("version:'2.6.3'","version:'2.6.6'")

s=s.replace('Background Shadow Test','Delta Strategy Shadow Test')
s=s.replace('Refresh News','Refresh Delta Context')
s=s.replace("v25shadowMaybe('NEWS'","v25shadowMaybe('DELTA'")
s=s.replace("var ps=['TECH','NEWS','FUSION']","var ps=['TECH','DELTA','FUSION']")

# Public market data does not need credentials. Do not keep exchange credentials in WebView storage.
s=re.sub(
    r'<div class="control"><label>Delta API Key<input id="tdkey".*?</div><div id="msg"',
    '<div class="muted small" style="margin-top:8px"><b>Delta public feed:</b> No API key is required for live market analysis. Private order execution is disabled in this build, and no exchange credential is stored in the WebView.</div><div id="msg"',
    s, count=1, flags=re.S
)
s=s.replace('Credential Info','Delta Public Feed')
s=s.replace('Test Delta Feed','Refresh Delta Feed')

# Keep the permanent master history and latest opportunity engine.
s=s.replace("var V265={version:'2.6.6'};","var V265={version:'2.6.6'};\nvar V266={version:'2.6.6',provider:'DELTA INDIA'};")

# Keep the established package identity so this line remains compatible with the current stable app line.
b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'applicationId\s*=\s*"[^"]+"','applicationId = "com.dhanpulse.cryptofxstablev263"',bs,count=1)
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 37',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.6.6"',bs,count=1)
b.write_text(bs)

idx.write_text(s)
