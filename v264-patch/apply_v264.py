from pathlib import Path
import re

root = Path('crypto-forex-app/buildsrc')
idx = root / 'app/src/main/assets/index.html'
s = idx.read_text()

s = s.replace('Version 2.6.3 Opportunity Engine Fix', 'Version 2.6.4 Clear Trade Gate')
s = s.replace('DhanPulse Crypto and Forex Version 2.6.3 Opportunity Engine Fix.', 'DhanPulse Crypto and Forex Version 2.6.4 Clear Trade Gate.')

# Add two diagnostics so the user can see the actual selected and micro volatility used.
needle = '<div><span>Current Gate</span><b id="oppGate">WAIT</b></div>'
replacement = needle + '\n    <div><span>Selected ATR %</span><b id="oppAtr">NA</b></div>\n    <div><span>1m ATR %</span><b id="oppMicroAtr">NA</b></div>'
if needle in s and 'id="oppAtr"' not in s:
    s = s.replace(needle, replacement, 1)

js = r'''
/* V2.6.4 Clear Trade Gate.
   Fixes two user-visible problems:
   1) legacy imported trades with unknown prices must show N/A, never 0.000000;
   2) early opportunity logic must not be blanket-blocked by a selected-timeframe ATR
      threshold when live 1m structure is already moving. */
if(typeof V261!=='undefined')V261.version='2.6.4';
if(typeof V26!=='undefined')V26.version='2.6.4';
if(typeof V263!=='undefined')V263.version='2.6.4';
var V264={version:'2.6.4',lastFeed:null};

function v264Vol(reg,mic){
  var p=finite(S.livePrice)?Math.abs(S.livePrice):(S.analysis&&S.analysis.last?Math.abs(S.analysis.last.c):0);
  var selected=reg&&finite(reg.atrPct)?num(reg.atrPct):0;
  var micro=mic&&mic.ready&&p>0?num(mic.atr)/p*100:0;
  return{selected:selected,micro:micro};
}
function v264FeedGate(reg,mic){
  if(!S.analysis)return{ok:false,reason:'analysis unavailable',selected:0,micro:0};
  var now=Date.now(),age=S.lastMarketEventAt?now-S.lastMarketEventAt:999999,spread=num(S.ctx.spreadBps||0),v=v264Vol(reg,mic);
  if(S.market==='crypto'&&age>4500)return{ok:false,reason:'live feed stale '+Math.round(age)+' ms',selected:v.selected,micro:v.micro};
  if(S.market==='crypto'&&spread>4.0)return{ok:false,reason:'spread '+spread.toFixed(2)+' bp too wide',selected:v.selected,micro:v.micro};
  if(reg&&reg.type==='EXTREME VOL')return{ok:false,reason:'extreme volatility veto',selected:v.selected,micro:v.micro};
  var minSel={'1m':.012,'5m':.025,'15m':.035,'30m':.045,'1h':.060,'4h':.090}[S.tf]||.025;
  var microMoving=!!(mic&&mic.ready&&(Math.abs(num(mic.impulse))>=.20||mic.bosUp||mic.bosDn||mic.bullSweep||mic.bearSweep));
  var microAlive=v.micro>=.006;
  if(v.selected<minSel&&!microMoving&&!microAlive){
    return{ok:false,reason:'quiet market · '+v.selected.toFixed(3)+'% selected / '+v.micro.toFixed(3)+'% 1m',selected:v.selected,micro:v.micro};
  }
  var note=v.selected<minSel?'1m opportunity override':'volatility active';
  return{ok:true,reason:note,selected:v.selected,micro:v.micro};
}

/* Replace the precision feed gate with the adaptive gate. This keeps stale-feed,
   wide-spread and extreme-volatility protection, but removes the blanket low-ATR block. */
v24feedGate=function(reg){var mic=(typeof v263micro==='function')?v263micro():null;var g=v264FeedGate(reg,mic);V264.lastFeed=g;return{ok:g.ok,reason:g.reason}};

var __v264Render=v263render;
v263render=function(m,mic,c,gate){
  __v264Render(m,mic,c,gate);
  var v=v264Vol(v23regime(),mic);
  v263e('oppAtr',v.selected?v.selected.toFixed(3)+'%':'0.000%');
  v263e('oppMicroAtr',v.micro?v.micro.toFixed(3)+'%':'0.000%');
  if(!c&&mic&&mic.ready){
    var watch=/DOWN|HIGH/.test(mic.label)?'SELL WATCH':/UP|LOW/.test(mic.label)?'BUY WATCH':'NONE';
    if(watch!=='NONE')v263e('oppBest',watch,'neutral');
    if(watch!=='NONE')v263e('oppScore','WATCH');
  }
  var g=String(gate||'');
  if(g.indexOf('volatility too low for fast precision')>=0){
    var fg=v264FeedGate(v23regime(),mic);
    v263e('oppGate',fg.ok?'SCANNING · '+fg.reason:'BLOCK · '+fg.reason,fg.ok?'neutral':'bear');
  }
};

/* Run early candidate discovery first, then apply the adaptive feed gate.
   This makes the UI show what was observed even when a gate rejects publication. */
var __v264Select=v263select;
v263select=function(){
  var reg=v23regime(),m=v26map(),mic=v263micro();V26.map=m;v26render(m);V263.lastMicro=mic;
  if(!m||!mic.ready){V263.lastGate='WAIT: structure data building';v263render(m,mic,null,V263.lastGate);return null}
  var all=[v263rev('BUY',m,mic),v263rev('SELL',m,mic),v263cont('BUY',m,mic),v263cont('SELL',m,mic),v263break('BUY',m,mic),v263break('SELL',m,mic)].filter(Boolean).sort(function(a,b){return b.score-a.score});
  var observed=all.length?all[0]:null;
  var fg=v264FeedGate(reg,mic);V264.lastFeed=fg;
  if(!fg.ok){
    V263.lastGate='BLOCK: '+fg.reason;
    v263render(m,mic,observed,V263.lastGate);
    return{candidate:null,reason:V263.lastGate,regime:reg,block:true};
  }
  if(v24activeTrade()){V263.lastGate='WAIT: existing signal open';v263render(m,mic,observed,V263.lastGate);return null}
  var brake=v24lossBrake();if(brake){V263.lastGate='BLOCK: '+brake;v263render(m,mic,observed,V263.lastGate);return{candidate:null,reason:V263.lastGate,regime:reg,block:true}}
  if(v24tradeLimit()){V263.lastGate='WAIT: frequency control';v263render(m,mic,observed,V263.lastGate);return null}
  if(!all.length){V263.lastGate='SCANNING: no early trigger';v263render(m,mic,null,V263.lastGate);return null}
  var best=all[0],opp=all.find(function(x){return x.side!==best.side});
  if(opp&&best.score-opp.score<8){V263.lastGate='WAIT: micro direction conflict';v263render(m,mic,best,V263.lastGate);return{candidate:null,reason:V263.lastGate,regime:reg,block:true}}
  if(v26late(best,m)){V263.lastGate='WAIT: late move veto';v263render(m,mic,best,V263.lastGate);return{candidate:null,reason:V263.lastGate,regime:reg,block:true}}
  if(v24cooldownBlocked(best)){V263.lastGate='WAIT: cooldown';v263render(m,mic,best,V263.lastGate);return null}
  var ng=v26newsGate(best);if(!ng.ok){V263.lastGate=ng.reason;v263render(m,mic,best,V263.lastGate);return{candidate:null,reason:ng.reason,regime:reg,block:true}}
  best.support=best.reasons.length;best.fast=best.score>=best.threshold+3;V263.last=best;V263.lastGate='CANDIDATE READY · '+fg.reason;v263render(m,mic,best,V263.lastGate);return{candidate:best,reason:'',regime:reg};
};

/* Mark the imported V2.6 screenshot result explicitly as legacy research evidence.
   Exact entry/SL/target prices were not available during migration. */
function v264FixLegacy(){
  try{
    var a=v261all(),changed=false;
    a.forEach(function(t){
      if(t&&t.legacyImported){
        if(!t.legacyPriceUnknown){t.legacyPriceUnknown=true;changed=true}
        t.resultDisplay='SL HIT · LEGACY IMPORT';
        t.stage='Imported V2.6 legacy result · exact prices unavailable';
      }
    });
    if(changed)save(a);
  }catch(e){}
}
var __v264RenderTrades=renderTrades;
renderTrades=function(){
  __v264RenderTrades();
  try{
    var ts=trades().slice().reverse().slice(0,100),body=q('trades');
    if(!body)return;
    var rows=body.querySelectorAll('tr');
    for(var i=0;i<rows.length&&i<ts.length;i++){
      var t=ts[i],cells=rows[i].children;
      if(t&&t.legacyImported&&cells.length>=12){
        cells[4].innerHTML=(t.side||'')+'<br><small>LEGACY IMPORT · exact prices unavailable · '+(finite(t.pnlR)?Number(t.pnlR).toFixed(2)+'R':'')+'</small>';
        for(var j=5;j<=9;j++)cells[j].textContent='N/A';
        cells[10].textContent='CLOSED';
        cells[11].textContent='SL HIT · LEGACY';
      }
    }
  }catch(e){}
};
v264FixLegacy();
setTimeout(function(){v264FixLegacy();renderTrades();if(typeof v261renderHistory==='function')v261renderHistory()},250);

window.__dpEngineSnapshot=function(){try{var r=v23regime(),m=v263micro(),g=v264FeedGate(r,m);return JSON.stringify({version:'2.6.4',market:S.market,symbol:S.symbol,tf:S.tf,feed:S.feedMode,selectedAtrPct:g.selected,microAtrPct:g.micro,gate:g.reason,ict:!!(V26&&V26.map),micro:m&&m.label,last:V263.last&&{side:V263.last.side,strategy:V263.last.strategy,score:V263.last.score,threshold:V263.last.threshold}})}catch(e){return '{}'}};
'''
if 'V2.6.4 Clear Trade Gate.' not in s:
    s = s.replace('\n})();\n</script>', js + '\n})();\n</script>', 1)
else:
    raise SystemExit('V2.6.4 already present')
idx.write_text(s)

b = root / 'app/build.gradle.kts'
bs = b.read_text()
# Keep the V2.6.3 package so this is a true update and keeps its WebView history.
bs = re.sub(r'applicationId\s*=\s*"[^"]+"', 'applicationId = "com.dhanpulse.cryptofxstablev263"', bs, count=1)
bs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 35', bs, count=1)
bs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.6.4"', bs, count=1)
b.write_text(bs)

# workflow retrigger
