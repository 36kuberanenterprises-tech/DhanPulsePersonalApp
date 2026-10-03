ar __v26ProcessTick=processTick;
processTick=function(price,ts,qty,buy,eventTime,eventType){__v26ProcessTick(price,ts,qty,buy,eventTime,eventType);try{if(Date.now()-V26.lastAnalysisAt>=140){V26.lastAnalysisAt=Date.now();S.analysis=analyse(S.candles,S.ctx)}V26.map=v26map();v26render(V26.map)}catch(e){}};
setInterval(function(){try{V26.map=v26map();v26render(V26.map)}catch(e){}},1000);
'''

if 'V2.6 ICT Early Structure.' not in s:
    s = s.replace('</script>', js + '\n</script>', 1)

# Update footer wording if still present.
s = s.replace('Native foreground monitoring continues when the app is minimised or the screen is locked.</footer>',
              'Native foreground monitoring continues when the app is minimised or the screen is locked. V2.6 adds early ICT style liquidity, order block, FVG, premium and discount mapping with a late entry veto.</footer>')
idx.write_text(s)

# Android package and version.
b = root / 'app/build.gradle.kts'
bs = b.read_text()
bs = re.sub(r'applicationId\s*=\s*"[^"]+"', 'applicationId = "com.dhanpulse.cryptofxresearchv260"', bs, count=1)
bs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 31', bs, count=1)
bs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.6.0"', bs, count=1)
b.write_text(bs)
