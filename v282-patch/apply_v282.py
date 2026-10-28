from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.8.1 Unified Secure Backend','Version 2.8.2 Startup Recovery')
s=s.replace('DhanPulse Version 2.8.1 Unified Secure Backend.','DhanPulse Version 2.8.2 Startup Recovery.')
s=s.replace('DhanPulse Version 2.8.1 Unified Secure Backend','DhanPulse Version 2.8.2 Startup Recovery')

# Critical startup repair: V2.6.6 removed these legacy controls but the old handlers
# were still executed unconditionally. That exception stopped setSymbols() and load().
s=s.replace(
'''q("deltaCredentialInfo").onclick=function(){q("deltaCredentialPlaceholder").value="";q("msg").textContent="Delta Exchange India is the only provider used by this app."};
q("deltaFeedTest").onclick=function(){S.market="crypto";saveMonitorConfig();setSymbols();load();q("msg").textContent="Testing Delta public REST and WebSocket feed."};
''',
'''if(q("deltaCredentialInfo"))q("deltaCredentialInfo").onclick=function(){if(q("deltaCredentialPlaceholder"))q("deltaCredentialPlaceholder").value="";if(q("msg"))q("msg").textContent="Delta Exchange India is the only provider used by this app."};
if(q("deltaFeedTest"))q("deltaFeedTest").onclick=function(){S.market="crypto";saveMonitorConfig();setSymbols();load();if(q("msg"))q("msg").textContent="Testing Delta public REST and WebSocket feed."};
''')

# Guard the second removed legacy credential field reference in startup initialization.
s=s.replace(
'''window.onresize=function(){ensureChartView();draw()};window.onbeforeunload=stop;var kk=localStorage.getItem(KEY)||"";if(kk)q("deltaCredentialPlaceholder").value=kk;loadMonitorConfig();''',
'''window.onresize=function(){ensureChartView();draw()};window.onbeforeunload=stop;var kk=KEY?localStorage.getItem(KEY)||"":"";if(kk&&q("deltaCredentialPlaceholder"))q("deltaCredentialPlaceholder").value=kk;loadMonitorConfig();''')

css=r'''
/* V2.8.2 startup and data pipeline status */
.pipeline-health{
  display:flex;align-items:center;gap:7px;margin:7px 0 0;font-size:9px;color:#81909e
}
.pipeline-health i{width:7px;height:7px;border-radius:50%;background:#e5ad45;box-shadow:0 0 0 3px rgba(229,173,69,.08)}
.pipeline-health.ok i{background:#35d394;box-shadow:0 0 0 3px rgba(53,211,148,.08)}
.pipeline-health.err i{background:#ef6674;box-shadow:0 0 0 3px rgba(239,102,116,.08)}
'''
if 'V2.8.2 startup and data pipeline status' not in s:
    s=s.replace('</style>',css+'\n</style>',1)

js=r'''
/* V2.8.2 Startup Recovery.
   The market bootstrap must complete before strategy/ICT/chart panels can operate. */
var V282={version:'2.8.2',startedAt:Date.now()};
if(typeof V281!=='undefined')V281.version='2.8.2';
if(typeof V280!=='undefined')V280.version='2.8.2';

function v282Health(state,text){
  var e=q('pipelineHealth');if(!e)return;
  e.className='pipeline-health '+(state||'');
  var s=e.querySelector('span');if(s)s.textContent=text||'Checking market data';
}
function v282InstallHealth(){
  var first=document.querySelector('.app > .panel');
  if(first&&!q('pipelineHealth')){
    var e=document.createElement('div');e.id='pipelineHealth';e.className='pipeline-health';
    e.innerHTML='<i></i><span>Starting market data pipeline</span>';
    first.appendChild(e);
  }
}
function v282Check(){
  try{
    if(!q('symbol'))return;
    if(!q('symbol').options.length){
      setSymbols();
    }
    if(S&&S.candles&&S.candles.length>=20&&S.analysis){
      v282Health('ok','Market data ready · '+S.candles.length+' candles · '+S.symbol+' · '+S.tf);
      return;
    }
    if(S&&S.livePrice&&(!S.candles||S.candles.length<20)){
      v282Health('','Live price connected · loading candle history and indicators');
    }else{
      v282Health('','Connecting Delta market history');
    }
  }catch(e){
    v282Health('err','Startup check failed · tap Refresh Analysis');
  }
}
setTimeout(function(){
  v282InstallHealth();
  try{
    setSymbols();
    saveMonitorConfig();
    if(!S.candles||S.candles.length<20)load();
  }catch(e){
    v282Health('err','Startup recovery: '+String(e&&e.message||e));
  }
},120);
setInterval(v282Check,1200);
'''
if 'V2.8.2 Startup Recovery.' not in s:
    s=s.replace('\n})();\n</script>',js+'\n})();\n</script>',1)

idx.write_text(s)

# Bump native user agents where present.
for p in [
    root/'app/src/main/java/com/dhanpulse/cryptofxv11/DeltaBackendAccount.java',
    root/'app/src/main/java/com/dhanpulse/cryptofxv11/FlattradeBackend.java'
]:
    if p.exists():
        t=p.read_text()
        t=t.replace('DhanPulse-Android/2.8.1','DhanPulse-Android/2.8.2')
        p.write_text(t)

b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 50',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.8.2"',bs,count=1)
b.write_text(bs)
