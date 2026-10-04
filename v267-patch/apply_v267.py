from pathlib import Path
import re

root = Path('crypto-forex-app/buildsrc')
idx = root / 'app/src/main/assets/index.html'
s = idx.read_text()

# Final provider lock: Delta Exchange India production only.
for old in [
    'Version 2.6.6 Delta Only',
    'Version 2.6.5 Live Trade Clarity',
    'Version 2.6.4 Clear Trade Gate',
    'Version 2.6.3 Opportunity Engine Fix'
]:
    s = s.replace(old, 'Version 2.6.7 Delta Production Only')

s = s.replace('DhanPulse Delta Exchange India Version 2.6.6 Delta Only.',
              'DhanPulse Delta Exchange India Version 2.6.7 Delta Production Only.')
s = s.replace('DhanPulse Delta Exchange India Version 2.6.6 Delta Only',
              'DhanPulse Delta Exchange India Version 2.6.7 Delta Production Only')

# Remove legacy provider credential storage names. Public Delta production market data does not need a key.
s = s.replace('dhanpulse_td_key_v1', '')
s = re.sub(r'\bKEY\s*=\s*""', 'KEY=null', s)
s = s.replace('tdkey', 'deltaCredentialPlaceholder')
s = s.replace('savekey', 'deltaCredentialInfo')
s = s.replace('testxau', 'deltaFeedTest')

# Strip any remaining legacy API-key entry wording from the page.
s = re.sub(r'<label>[^<]*(?:API Key|Api Key)[^<]*<input[^>]*id="deltaCredentialPlaceholder"[^>]*>.*?</label>',
           '<div class="muted small"><b>Delta production feed:</b> Public market analysis uses Delta Exchange India directly and requires no API key.</div>',
           s, flags=re.I|re.S)
s = s.replace('For safety, credentials are not stored in the WebView. Delta public market data needs no API key.',
              'Delta Exchange India production public REST and WebSocket feeds are the only market data sources in this build.')
s = s.replace('Public Delta feed: No API key required. Private order execution is not enabled in this build and no exchange credential is stored in the WebView.',
              'Delta Exchange India production public REST and WebSocket feeds are the only market data sources in this build. Private order execution is not enabled in this build.')

# Rename news-era labels because no external news API is used in Delta-only mode.
s = s.replace('News and Candle Intelligence', 'Delta Market Context')
s = s.replace('News Intelligence', 'Delta Market Context')
s = s.replace('News Filtered', 'Delta Context')
s = s.replace('NEWS RISK', 'DELTA CONTEXT RISK')
s = s.replace('news plus candle aligned', 'Delta context plus candle aligned')
s = s.replace('news and candle reaction aligned', 'Delta context and candle reaction aligned')
s = s.replace('news uncertainty', 'Delta context uncertainty')
s = s.replace('Fresh market headlines are compared with live candle reaction, volume, flow, regime and strategy consensus. News never creates a trade by itself.',
              'Delta market structure, funding, open interest, order book, flow, regime and candle reaction are compared with strategy consensus. No external news API is used.')

# Make provider identity explicit in the UI.
s = s.replace('Delta Exchange India · ', 'Delta Exchange India PROD · ')
s = s.replace('Delta Native Stream', 'Delta Production Native Stream')
s = s.replace('Delta Live Stream', 'Delta Production Live Stream')

# Late runtime guard. It intentionally exposes no credential fields and documents the single provider.
guard = r'''
/* V2.6.7 Delta Production Only provider lock.
   No Binance, Twelve Data, GDELT, testnet or other market/news provider is used.
   Public Delta Exchange India market data needs no API credential. */
var V267={version:'2.6.7',provider:'DELTA_EXCHANGE_INDIA_PRODUCTION',
  rest:'https://api.india.delta.exchange',
  ws:'wss://public-socket.india.delta.exchange'};
if(typeof V261!=='undefined')V261.version='2.6.7';
if(typeof V26!=='undefined')V26.version='2.6.7';
if(typeof V263!=='undefined')V263.version='2.6.7';
if(typeof V264!=='undefined')V264.version='2.6.7';
if(typeof V265!=='undefined')V265.version='2.6.7';
if(typeof V266!=='undefined')V266.version='2.6.7';

window.__dpProviderStatus=function(){
  return JSON.stringify({
    version:'2.6.7',
    provider:'Delta Exchange India',
    environment:'PRODUCTION',
    rest:V267.rest,
    websocket:V267.ws,
    publicMarketData:true,
    externalNewsApi:false,
    otherMarketApis:false,
    privateTrading:false
  });
};
setTimeout(function(){
  try{
    var p=q('provider');if(p)p.textContent='Delta Exchange India PROD · '+S.symbol;
    var msg=q('msg');if(msg&&!msg.textContent)msg.textContent='Delta production public REST and WebSocket only. No other API key or provider is used.';
    var inp=q('deltaCredentialPlaceholder');if(inp){inp.value='';inp.type='hidden';inp.disabled=true;}
    var btn=q('deltaCredentialInfo');if(btn){btn.textContent='Delta Public Feed';btn.onclick=function(){if(msg)msg.textContent='Public Delta market data requires no API key. Private order execution is disabled in this build.'}}
  }catch(e){}
},0);
'''
if 'V2.6.7 Delta Production Only provider lock.' not in s:
    s = s.replace('\n})();\n</script>', guard + '\n})();\n</script>', 1)

# Final provider sanitation. This is intentionally strict.
for forbidden in [
    'https://api.twelvedata.com','wss://ws.twelvedata.com',
    'https://fapi.binance.com','wss://fstream.binance.com',
    'https://api.gdeltproject.org'
]:
    s = s.replace(forbidden, 'https://api.india.delta.exchange')

idx.write_text(s)

# Android version/package: keep current stable package so this can update V2.6.6 and preserve history.
b = root / 'app/build.gradle.kts'
bs = b.read_text()
bs = re.sub(r'applicationId\s*=\s*"[^"]+"', 'applicationId = "com.dhanpulse.cryptofxstablev263"', bs, count=1)
bs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 38', bs, count=1)
bs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.6.7"', bs, count=1)
b.write_text(bs)

# Native layer must also be Delta production only.
for java in [
    root / 'app/src/main/java/com/dhanpulse/cryptofxv11/DhanPulseMonitorService.java',
    root / 'app/src/main/java/com/dhanpulse/cryptofxv11/MainActivity.java'
]:
    if not java.exists():
        continue
    x = java.read_text()
    x = x.replace('https://api.gdeltproject.org/', 'https://api.india.delta.exchange/')
    x = x.replace('https://fapi.binance.com', 'https://api.india.delta.exchange')
    x = x.replace('wss://fstream.binance.com', 'wss://public-socket.india.delta.exchange')
    x = x.replace('wss://ws.twelvedata.com', 'wss://public-socket.india.delta.exchange')
    x = x.replace('DhanPulse-Android/2.6.0', 'DhanPulse-Android/2.6.7')
    java.write_text(x)
