from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.8.3 Stable Data Pipeline','Version 2.8.4 Full Data Recovery')
s=s.replace('DhanPulse Version 2.8.3 Stable Data Pipeline.','DhanPulse Version 2.8.4 Full Data Recovery.')
s=s.replace('DhanPulse Version 2.8.3 Stable Data Pipeline','DhanPulse Version 2.8.4 Full Data Recovery')

# Native bootstrap now owns selected timeframe history as well as 1m and HTF,
# so indicators do not depend on the older WebView history loader.
old='''    var micro=v283CandleRows(d.micro||[]),htf=v283CandleRows(d.htf||[]);
    if(micro.length)S.microCandles=micro.slice(-260);
    if(htf.length)S.htfCandles=htf.slice(-180);
    if(d.context)v283ApplyContext(d.context);
    V283.bootstrapDone=!!(S.microCandles&&S.microCandles.length>=24&&S.htfCandles&&S.htfCandles.length>=20);
    V283.retries=0;
    v283RunEngines();
'''
new='''    var selected=v283CandleRows(d.selected||[]),micro=v283CandleRows(d.micro||[]),htf=v283CandleRows(d.htf||[]);
    if(selected.length)S.candles=selected.slice(-420);
    if(micro.length)S.microCandles=micro.slice(-320);
    if(htf.length)S.htfCandles=htf.slice(-220);
    if(d.context)v283ApplyContext(d.context);
    if(S.candles&&S.candles.length>=20&&typeof analyse==="function")S.analysis=analyse(S.candles,S.ctx||{});
    V283.bootstrapDone=!!(S.candles&&S.candles.length>=20&&S.microCandles&&S.microCandles.length>=24&&S.htfCandles&&S.htfCandles.length>=20);
    V283.retries=0;
    if(typeof render==="function")render();
    v283RunEngines();
'''
if old not in s:
    raise SystemExit('V2.8.3 bootstrap assignment block not found')
s=s.replace(old,new,1)

js=r'''
/* V2.8.4 Full Data Recovery.
   Selected timeframe, 1m trigger history and HTF structure are all recovered natively. */
var V284={version:'2.8.4',lastRequestedKey:''};
if(typeof V283!=='undefined')V283.version='2.8.4';
if(typeof V282!=='undefined')V282.version='2.8.4';

function v284PipelineText(){
  try{
    var a=(S&&S.candles&&S.candles.length)||0;
    var m=(S&&S.microCandles&&S.microCandles.length)||0;
    var h=(S&&S.htfCandles&&S.htfCandles.length)||0;
    var ph=v283q('pipelineHealth');
    if(ph){
      var ok=a>=20&&m>=24&&h>=20;
      ph.className='pipeline-health '+(ok?'ok':'');
      var sp=ph.querySelector('span');
      if(sp)sp.textContent=ok
        ?'DATA READY · '+a+' selected · '+m+' 1m · '+h+' HTF candles'
        :'RECOVERING DATA · '+a+' selected · '+m+' 1m · '+h+' HTF';
    }
    if(a>=20&&S.analysis){
      var atr=v283q('atr'),trend=v283q('trend'),ht=v283q('htf');
      if(atr&&/^(NA|—|-)?$/.test((atr.textContent||'').trim()))atr.textContent='CALCULATING';
      if(trend&&/^(NA|—|-)?$/.test((trend.textContent||'').trim()))trend.textContent='CALCULATING';
      if(ht&&/^(NA|—|-)?$/.test((ht.textContent||'').trim()))ht.textContent='CALCULATING';
    }
  }catch(e){}
}
function v284ForceRecovery(){
  try{
    v283EnsureSymbols();
    V283.bootstrapDone=false;V283.bootstrapBusy=false;V283.retries=0;
    var key=v283Symbol()+'|'+v283Tf();
    V284.lastRequestedKey=key;
    v283Bootstrap();
    setTimeout(v283Context,180);
  }catch(e){}
}
function v284Bind(){
  var symbol=v283q('symbol'),tf=v283q('tf'),refresh=v283q('refresh');
  if(symbol&&!symbol.dataset.v284){
    symbol.dataset.v284='1';
    symbol.addEventListener('change',function(){
      try{if(S)S.symbol=String(symbol.value||'BTCUSD')}catch(e){}
      setTimeout(v284ForceRecovery,40);
    });
  }
  if(tf&&!tf.dataset.v284){
    tf.dataset.v284='1';
    tf.addEventListener('change',function(){
      try{if(S)S.tf=String(tf.value||'5m')}catch(e){}
      setTimeout(v284ForceRecovery,40);
    });
  }
  if(refresh&&!refresh.dataset.v284){
    refresh.dataset.v284='1';
    refresh.addEventListener('click',function(){setTimeout(v284ForceRecovery,30)},true);
  }
}
setTimeout(function(){v284Bind();v284ForceRecovery()},520);
setInterval(function(){
  v284Bind();v284PipelineText();
  try{
    var key=v283Symbol()+'|'+v283Tf();
    if(key!==V284.lastRequestedKey){V284.lastRequestedKey=key;v284ForceRecovery()}
  }catch(e){}
},1400);
'''
if 'V2.8.4 Full Data Recovery.' not in s:
    s=s.replace('\n})();\n</script>',js+'\n})();\n</script>',1)

idx.write_text(s)

repair=root/'app/src/main/java/com/dhanpulse/cryptofxv11/DeltaDataRepair.java'
t=repair.read_text()

old_java='''                String clean = cleanSymbol(symbol);
                String htf = higherTf(tf);
                long end = System.currentTimeMillis() / 1000L;
                long microStart = end - 5L * 60L * 60L;
                long htfStart = end - 14L * 24L * 60L * 60L;
                JSONArray micro = history(clean, "1m", microStart, end);
                JSONArray higher = history(clean, htf, htfStart, end);
                JSONObject ctx = context(clean);
                out.put("success", true);
                out.put("symbol", clean);
                out.put("microResolution", "1m");
                out.put("higherResolution", htf);
                out.put("micro", micro);
                out.put("htf", higher);
                out.put("context", ctx);
'''
new_java='''                String clean = cleanSymbol(symbol);
                String selectedTf = cleanResolution(tf);
                String htf = higherTf(selectedTf);
                long end = System.currentTimeMillis() / 1000L;
                long selectedStart = historyStart(selectedTf, end, 420);
                long microStart = historyStart("1m", end, 320);
                long htfStart = historyStart(htf, end, 220);
                JSONArray selected = history(clean, selectedTf, selectedStart, end);
                JSONArray micro = "1m".equals(selectedTf)
                        ? selected
                        : history(clean, "1m", microStart, end);
                JSONArray higher = htf.equals(selectedTf)
                        ? selected
                        : history(clean, htf, htfStart, end);
                JSONObject ctx = context(clean);
                if (selected.length() < 20) throw new Exception("Delta selected timeframe history returned too few candles");
                if (micro.length() < 24) throw new Exception("Delta 1m history returned too few candles");
                if (higher.length() < 20) throw new Exception("Delta higher timeframe history returned too few candles");
                out.put("success", true);
                out.put("symbol", clean);
                out.put("selectedResolution", selectedTf);
                out.put("microResolution", "1m");
                out.put("higherResolution", htf);
                out.put("selected", selected);
                out.put("micro", micro);
                out.put("htf", higher);
                out.put("context", ctx);
'''
if old_java not in t:
    raise SystemExit('DeltaDataRepair bootstrap block not found')
t=t.replace(old_java,new_java,1)

insert='''    private static String cleanResolution(String tf) {
        String x = tf == null ? "5m" : tf.trim();
        switch (x) {
            case "1m": case "3m": case "5m": case "15m": case "30m":
            case "1h": case "2h": case "4h": case "6h": case "1d": case "1w":
                return x;
            default: return "5m";
        }
    }

    private static long resolutionSeconds(String tf) {
        switch (cleanResolution(tf)) {
            case "1m": return 60L;
            case "3m": return 180L;
            case "5m": return 300L;
            case "15m": return 900L;
            case "30m": return 1800L;
            case "1h": return 3600L;
            case "2h": return 7200L;
            case "4h": return 14400L;
            case "6h": return 21600L;
            case "1d": return 86400L;
            case "1w": return 604800L;
            default: return 300L;
        }
    }

    private static long historyStart(String tf, long end, int bars) {
        long seconds = resolutionSeconds(tf);
        long requested = seconds * Math.max(40L, (long) bars + 20L);
        return Math.max(1L, end - requested);
    }

'''
anchor='''    private static String higherTf(String tf) {
'''
if insert.strip() not in t:
    if anchor not in t: raise SystemExit('higherTf anchor not found')
    t=t.replace(anchor,insert+anchor,1)

t=t.replace('DhanPulse-Android/2.8.3','DhanPulse-Android/2.8.4')
repair.write_text(t)

# Bump other native user agents where present.
for p in [
    root/'app/src/main/java/com/dhanpulse/cryptofxv11/DeltaBackendAccount.java',
    root/'app/src/main/java/com/dhanpulse/cryptofxv11/FlattradeBackend.java',
    root/'app/src/main/java/com/dhanpulse/cryptofxv11/DhanPulseMonitorService.java'
]:
    if p.exists():
        z=p.read_text()
        z=re.sub(r'DhanPulse-Android/2\.[0-9.]+','DhanPulse-Android/2.8.4',z)
        p.write_text(z)

b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 52',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.8.4"',bs,count=1)
b.write_text(bs)
