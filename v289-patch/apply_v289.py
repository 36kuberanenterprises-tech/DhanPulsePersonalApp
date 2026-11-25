from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.8.8 Multi Market Integrity','Version 2.8.9 Punch Integrity')
s=s.replace('DhanPulse Version 2.8.8 Multi Market Integrity.','DhanPulse Version 2.8.9 Punch Integrity.')
s=s.replace('DhanPulse Version 2.8.8 Multi Market Integrity','DhanPulse Version 2.8.9 Punch Integrity')

js=r'''
/* V2.8.9 Punch Integrity.
   Final live revalidation before signal publication.
   One open trade per instrument across timeframes.
   Prevents stale armed candidates and late chase entries from being recorded. */
var V289={version:'2.8.9',lastReject:'',lastRejectAt:0};

function v289LiveOpenForInstrument(){
  var list=trades();
  for(var i=list.length-1;i>=0;i--){
    var t=list[i];
    if(t&&t.status==='OPEN'&&t.market===S.market&&t.symbol===S.symbol)return t;
  }
  return null;
}

/* One canonical open trade per instrument. 5m / 30m can confirm, but cannot create competing positions. */
v24activeTrade=function(){return v289LiveOpenForInstrument()};
v23activeTrade=function(){return v289LiveOpenForInstrument()};

function v289Reject(reason){
  V289.lastReject=reason||'WAIT';
  V289.lastRejectAt=Date.now();
  try{
    if(typeof V263!=='undefined')V263.lastGate='WAIT: '+V289.lastReject;
    if(q('oppGate'))q('oppGate').textContent='WAIT: '+V289.lastReject;
    if(q('stage'))q('stage').textContent='WAIT: '+V289.lastReject;
  }catch(e){}
}

function v289FreshFeed(){
  var now=Date.now();
  if(!finite(S.livePrice)||Number(S.livePrice)<=0)return false;
  if(!S.lastMarketEventAt)return false;
  return now-S.lastMarketEventAt>=0 && now-S.lastMarketEventAt<=1600;
}

function v289SameCandidate(a,b){
  if(!a||!b)return false;
  return a.side===b.side && a.strategy===b.strategy;
}

function v289FinalGate(c){
  if(!c)return{ok:false,reason:'candidate missing'};
  if(v289LiveOpenForInstrument())return{ok:false,reason:'instrument already has an open trade'};
  if(!v289FreshFeed())return{ok:false,reason:'live tick is stale'};

  var freshSel;
  try{freshSel=v24select()}catch(e){freshSel=null}
  var fresh=freshSel&&freshSel.candidate;
  if(!fresh)return{ok:false,reason:(freshSel&&freshSel.reason)||'setup no longer valid'};
  if(!v289SameCandidate(c,fresh))return{ok:false,reason:'setup changed before punch'};

  var nowPrice=Number(S.livePrice);
  var arm=V24&&V24.candidate?V24.candidate:null;
  var armPrice=arm&&finite(arm.firstPrice)?Number(arm.firstPrice):nowPrice;
  var p;
  try{p=v24plan(fresh)}catch(e){p=null}
  if(!p||!finite(p.entry)||!finite(p.sl)||!finite(p.risk)||p.risk<=0)return{ok:false,reason:'price plan unavailable'};

  var signed=(fresh.side==='BUY'?1:-1)*(nowPrice-armPrice);
  var chaseLimit=Math.max(p.risk*.14, Math.abs(nowPrice)*0.00012);
  if(signed>chaseLimit)return{ok:false,reason:'late chase blocked'};
  if(Math.abs(nowPrice-armPrice)>Math.max(p.risk*.32,Math.abs(nowPrice)*0.00035))
    return{ok:false,reason:'armed price moved too far'};

  /* Do not punch if the market has already travelled materially toward T1 before publication. */
  var firstRisk=Math.max(Math.abs(p.entry-p.sl),1e-9);
  var toward=(fresh.side==='BUY'?nowPrice-p.entry:p.entry-nowPrice)/firstRisk;
  if(toward>.18)return{ok:false,reason:'move already started before punch'};

  return{ok:true,candidate:fresh,sel:freshSel};
}

var __v289Publish=v24publish;
v24publish=function(c,sel){
  var g=v289FinalGate(c);
  if(!g.ok){
    V24.candidate=null;
    v289Reject(g.reason);
    return;
  }
  __v289Publish(g.candidate,g.sel||sel);
};

/* Make frequency control instrument-wide rather than timeframe-only. */
v24tradeLimit=function(){
  var now=Date.now(),list=trades().filter(function(t){
    return t&&t.market===S.market&&t.symbol===S.symbol&&now-t.createdAt<21600000;
  });
  var hour=list.filter(function(t){return now-t.createdAt<3600000}).length;
  return hour>=2||list.length>=4;
};

/* Expose diagnostics so the UI/native layer can show why a punch was refused. */
window.__dpPunchIntegrity=function(){
  try{
    var open=v289LiveOpenForInstrument();
    return JSON.stringify({
      version:'2.8.9',
      symbol:S.symbol,
      tf:S.tf,
      livePrice:finite(S.livePrice)?S.livePrice:null,
      feedAgeMs:S.lastMarketEventAt?Date.now()-S.lastMarketEventAt:null,
      openTrade:open?{id:open.id,tf:open.tf,side:open.side,strategy:open.strategy}:null,
      lastReject:V289.lastReject,
      lastRejectAt:V289.lastRejectAt
    });
  }catch(e){return '{}'}
};
'''
if 'V2.8.9 Punch Integrity.' not in s:
    s=s.replace('\n})();\n</script>',js+'\n})();\n</script>',1)
idx.write_text(s)

b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 55',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.8.9"',bs,count=1)
b.write_text(bs)

svc=root/'app/src/main/java/com/dhanpulse/cryptofxv11/DhanPulseMonitorService.java'
if svc.exists():
    t=svc.read_text().replace('DhanPulse-Android/2.8.8','DhanPulse-Android/2.8.9')
    svc.write_text(t)

for name in ['DeltaBackendAccount.java','FlattradeBackend.java','DeltaDataRepair.java']:
    p=root/'app/src/main/java/com/dhanpulse/cryptofxv11'/name
    if p.exists():
        z=p.read_text()
        z=re.sub(r'DhanPulse-Android/2\.[0-9.]+','DhanPulse-Android/2.8.9',z)
        p.write_text(z)
