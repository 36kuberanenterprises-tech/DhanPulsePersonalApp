from pathlib import Path
import re

root = Path('crypto-forex-app/buildsrc')
idx = root / 'app/src/main/assets/index.html'
s = idx.read_text()

# Version and fresh performance records.
s = s.replace('Version 2.5.1 Continuous Background', 'Version 2.6 ICT Early Structure')
s = s.replace('DhanPulse Crypto and Forex Version 2.5.1 Continuous Background.', 'DhanPulse Crypto and Forex Version 2.6 ICT Early Structure.')
s = s.replace('var TRKEY="dhanpulse_cf_android_trades_v251"', 'var TRKEY="dhanpulse_cf_android_trades_v26"')
s = s.replace('V2.5.1 Signals', 'V2.6 Signals')
s = s.replace('No V2.5.1 signals recorded yet.', 'No V2.6 signals recorded yet.')
s = s.replace('The research adaptive controller publishes only after closed candle, regime, volatility, price volume, derivatives context, conflict and live performance checks pass.',
              'The ICT Early Structure controller can arm intrabar around liquidity sweeps, order blocks and fair value gaps. It still checks live flow, structure, news risk, spread and conflict before publishing.')

# Add a visible structure panel before the news panel.
panel = r'''
<div class="panel" id="ictStructure">
  <div class="row"><div><h2>ICT Early Structure Engine</h2><div class="muted small">Maps liquidity, premium and discount, order blocks, fair value gaps and live market structure shifts. ICT labels are used as trading heuristics, not as guaranteed institutional signals.</div></div><b id="ictState" class="neutral">SCANNING</b></div>
  <div class="context" style="margin-top:12px">
    <div><span>Structure Bias</span><b id="ictBias">NA</b></div>
    <div><span>Price Location</span><b id="ictPD">NA</b></div>
    <div><span>Buy Side Liquidity</span><b id="ictBSL">NA</b></div>
    <div><span>Sell Side Liquidity</span><b id="ictSSL">NA</b></div>
    <div><span>Order Block</span><b id="ictOB">NA</b></div>
    <div><span>Fair Value Gap</span><b id="ictFVG">NA</b></div>
    <div><span>Liquidity Event</span><b id="ictSweep">NONE</b></div>
    <div><span>Early Trigger</span><b id="ictTrigger">WAIT</b></div>
  </div>
</div>
'''
if 'id="ictStructure"' not in s:
    anchor = '<div class="panel" id="newsIntel">'
    if anchor not in s:
        raise SystemExit('news panel anchor missing')
    s = s.replace(anchor, panel + '\n' + anchor, 1)

# Recalculate live analysis after the synthetic candle has been updated, before the
# current precision confirm step evaluates a setup. The old engine often evaluated
# a stale selected-timeframe analysis until the next context refresh.
old_tick = 'var __v23ProcessTick=processTick;processTick=function(price,ts,qty,buy,eventTime,eventType){__v23ProcessTick(price,ts,qty,buy,eventTime,eventType);v23confirmStep()};'
new_tick = 'var __v23ProcessTick=processTick;processTick=function(price,ts,qty,buy,eventTime,eventType){__v23ProcessTick(price,ts,qty,buy,eventTime,eventType);try{if(typeof V26!=="undefined"&&V26&&Date.now()-(V26.lastAnalysisAt||0)>=140){V26.lastAnalysisAt=Date.now();S.analysis=analyse(S.candles,S.ctx)}}catch(e){}v23confirmStep()};'
if old_tick in s:
    s = s.replace(old_tick, new_tick, 1)
else:
    raise SystemExit('v23 process tick anchor missing')

# ICT candidates use a shorter persistence window than ordinary precision strategies.
s = s.replace('}[c.strategy]||1200;\n  var needSlow=', '}[c.strategy]||(String(c.strategy||"").indexOf("ICT ")===0?650:1200);\n  var needSlow=', 1)
s = s.replace('}[c.strategy]||2600;\n  var need=fast?', '}[c.strategy]||(String(c.strategy||"").indexOf("ICT ")===0?1100:2600);\n  var need=fast?', 1)

js = r'''
/* V2.6 ICT Early Structure.
   Objective: identify a probable turning or continuation area before the move is mature.
   ICT terminology is treated as a price-structure heuristic. A setup still requires live
   confirmation and all existing feed, risk, news, spread and loss controls. */
var V26={lastAnalysisAt:0,map:null,lastMapAt:0,version:'2.6'};
function v26clamp(x,a,b){return Math.max(a,Math.min(b,x))}
function v26sg(side){return side==='BUY'?1:-1}
function v26fmt(v){return finite(v)?fmt(v,dec(v)):'NA'}
function v26closedIndex(c){if(!c||!c.length)return-1;var i=c.length-1;return c[i]&&c[i].closed?i:Math.max(0,i-1)}
function v26pivots(c,end){
  var hs=[],ls=[],a=Math.max(3,end-70);
  for(var i=a;i<=end-2;i++){
    if(c[i].h>c[i-1].h&&c[i].h>=c[i-2].h&&c[i].h>c[i+1].h&&c[i].h>=c[i+2].h)hs.push({i:i,p:c[i].h,t:c[i].t});
    if(c[i].l<c[i-1].l&&c[i].l<=c[i-2].l&&c[i].l<c[i+1].l&&c[i].l<=c[i+2].l)ls.push({i:i,p:c[i].l,t:c[i].t});
  }
  return{highs:hs,lows:ls};
}
function v26nearestSwing(list,price,wantAbove){
  if(!list||!list.length)return null;var best=null,bd=Infinity;
  list.forEach(function(z){var ok=wantAbove?z.p>=price:z.p<=price;if(ok){var d=Math.abs(z.p-price);if(d<bd){bd=d;best=z}}});
  return best||list[list.length-1];
}
function v26avgVolume(c,end,n){var x=c.slice(Math.max(0,end-(n||20)),end).map(function(z){return num(z.v||0)}).filter(function(v){return v>0});return x.length?x.reduce(function(a,b){return a+b},0)/x.length:0}
function v26findFvg(c,end,av,dir){
  for(var j=end;j>=Math.max(2,end-28);j--){
    if(dir===1&&c[j].l>c[j-2].h&&c[j].l-c[j-2].h>av*.055){var lo=c[j-2].h,hi=c[j].l,valid=true;for(var k=j+1;k<=end;k++)if(c[k].l<lo-av*.05){valid=false;break}if(valid)return{dir:1,lo:lo,hi:hi,j:j,mid:(lo+hi)/2}}
    if(dir===-1&&c[j].h<c[j-2].l&&c[j-2].l-c[j].h>av*.055){var lo2=c[j].h,hi2=c[j-2].l,valid2=true;for(var k2=j+1;k2<=end;k2++)if(c[k2].h>hi2+av*.05){valid2=false;break}if(valid2)return{dir:-1,lo:lo2,hi:hi2,j:j,mid:(lo2+hi2)/2}}
  }
  return null;
}
function v26findOB(c,end,av,dir){
  var avgV=v26avgVolume(c,end,20);
  for(var j=end;j>=Math.max(8,end-22);j--){
    var body=Math.abs(c[j].c-c[j].o),rng=Math.max(c[j].h-c[j].l,1e-9),volOk=!avgV||num(c[j].v)>=avgV*.95;
    if(body<av*.55||body/rng<.48||!volOk)continue;
    var impulse=dir===1&&c[j].c>c[j].o?1:dir===-1&&c[j].c<c[j].o?-1:0;if(!impulse)continue;
    var ob=null;
    for(var k=j-1;k>=Math.max(0,j-5);k--){if(dir===1&&c[k].c<c[k].o){ob=c[k];break}if(dir===-1&&c[k].c>c[k].o){ob=c[k];break}}
    if(!ob)continue;
    var lo=dir===1?ob.l:Math.min(ob.o,ob.c),hi=dir===1?Math.max(ob.o,ob.c):ob.h,invalid=false;
    for(var m=j+1;m<=end;m++){if(dir===1&&c[m].c<lo-av*.10){invalid=true;break}if(dir===-1&&c[m].c>hi+av*.10){invalid=true;break}}
    if(!invalid)return{dir:dir,lo:lo,hi:hi,j:j,mid:(lo+hi)/2,origin:ob.t};
  }
  return null;
}
function v26zoneDistance(price,z){if(!z)return Infinity;if(price<z.lo)ret