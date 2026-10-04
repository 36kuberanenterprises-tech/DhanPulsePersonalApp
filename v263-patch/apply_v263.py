from pathlib import Path
import re

root = Path('crypto-forex-app/buildsrc')
idx = root / 'app/src/main/assets/index.html'
s = idx.read_text()

s = s.replace('Version 2.6.2 Stable Migration', 'Version 2.6.3 Opportunity Engine Fix')
s = s.replace('DhanPulse Crypto and Forex Version 2.6.2 Stable Migration.', 'DhanPulse Crypto and Forex Version 2.6.3 Opportunity Engine Fix.')

marker = '\n})();\n\n/* V2.4 Precision Fast override.'
if marker not in s:
    raise SystemExit('V2.4 scope marker missing')
s = s.replace(marker, '\n\n/* V2.4 Precision Fast override.', 1)

panel = r'''
<div class="panel" id="opportunityEngine">
  <div class="row"><div><h2>Opportunity Capture Engine</h2><div class="muted small">Uses the selected timeframe for context and 1 minute structure for early trigger. It can act on liquidity sweeps, OB/FVG retests and micro breakouts without waiting for the full selected candle to close.</div></div><b id="oppState" class="neutral">STARTING</b></div>
  <div class="context" style="margin-top:12px">
    <div><span>Engine Scope</span><b id="scopeState">REPAIRING</b></div>
    <div><span>1m Trigger</span><b id="oppMicro">WAIT</b></div>
    <div><span>Best Opportunity</span><b id="oppBest">NONE</b></div>
    <div><span>Opportunity Score</span><b id="oppScore">0</b></div>
    <div><span>Entry Location</span><b id="oppLocation">WAIT</b></div>
    <div><span>Current Gate</span><b id="oppGate">WAIT</b></div>
  </div>
</div>
'''
if 'id="opportunityEngine"' not in s:
    anchor = '<div class="panel" id="migrationNote">'
    if anchor not in s:
        anchor = '<div class="panel" id="historyLab">'
    if anchor not in s:
        raise SystemExit('history panel anchor missing')
    s = s.replace(anchor, panel + '\n' + anchor, 1)

js = r'''
/* V2.6.3 Opportunity Engine Fix.
   This block runs INSIDE the original application scope. It repairs the previous patch
   scope problem, keeps history active, and adds an early microstructure path so a 15m
   chart can use 1m liquidity / CHoCH style triggers without chasing a mature move. */
if(typeof V261!=='undefined')V261.version='2.6.3';
if(typeof V26!=='undefined')V26.version='2.6.3';
var V263={version:'2.6.3',last:null,lastGate:'STARTING',lastMicro:null,lastSelectAt:0};
function v263e(id,v,cl){var z=q(id);if(z){z.textContent=v;if(cl)z.className=cl}}
function v263max(a,k){var v=-Infinity;(a||[]).forEach(function(x){v=Math.max(v,num(x[k]))});return v}
function v263min(a,k){var v=Infinity;(a||[]).forEach(function(x){v=Math.min(v,num(x[k]))});return v}
function v263zone(lo,hi,mid){return{lo:lo,hi:hi,mid:finite(mid)?mid:(lo+hi)/2}}
function v263near(p,z,av,m){return !!z&&v26zoneDistance(p,z)<=Math.max(av*(m||.30),1e-9)}

var __v263OldMap=v26map;
v26map=function(){
  var first=null;try{first=__v263OldMap()}catch(e){}
  if(first)return first;
  var c=S.candles||[];if(c.length<24||!S.analysis)return null;
  var end=v26closedIndex(c);if(end<18)return null;
  var live=c[c.length-1],price=finite(S.livePrice)?S.livePrice:live.c,av=Math.max(S.analysis.atr||atr(c,14)[Math.max(0,end)]||Math.abs(price)*.001,1e-9);
  var prior=c.slice(Math.max(0,end-42),Math.max(1,end-3));if(prior.length<12)prior=c.slice(Math.max(0,end-24),Math.max(1,end-1));
  if(!prior.length)return null;
  var hi=v263max(prior,'h'),lo=v263min(prior,'l'),hiBar=prior.reduce(function(a,b){return b.h>a.h?b:a},prior[0]),loBar=prior.reduce(function(a,b){return b.l<a.l?b:a},prior[0]);
  var lastH={i:c.indexOf(hiBar),p:hi,t:hiBar.t},lastL={i:c.indexOf(loBar),p:lo,t:loBar.t};
  var rangeHi=Math.max(hi,lo),rangeLo=Math.min(hi,lo),eq=(rangeHi+rangeLo)/2,pd=price>eq?'PREMIUM':price<eq?'DISCOUNT':'EQUILIBRIUM';
  var bullOB=v26findOB(c,end,av,1),bearOB=v26findOB(c,end,av,-1),bullFVG=v26findFvg(c,end,av,1),bearFVG=v26findFvg(c,end,av,-1);
  var mic=S.microCandles||[],me=mic.length-2,mav=mic.length>16?(atr(mic,14)[mic.length-1]||av*.22):av*.22;
  var mBullOB=me>10?v26findOB(mic,me,mav,1):null,mBearOB=me>10?v26findOB(mic,me,mav,-1):null,mBullFVG=me>10?v26findFvg(mic,me,mav,1):null,mBearFVG=me>10?v26findFvg(mic,me,mav,-1):null;
  function near(a,b){if(!a)return b;if(!b)return a;return v26zoneDistance(price,a)<=v26zoneDistance(price,b)?a:b}
  bullOB=near(bullOB,mBullOB);bearOB=near(bearOB,mBearOB);bullFVG=near(bullFVG,mBullFVG);bearFVG=near(bearFVG,mBearFVG);
  var recent=c.slice(Math.max(0,end-2));
  var bearSweep=recent.some(function(x){return x.h>hi+av*.02})&&price<hi-av*.003;
  var bullSweep=recent.some(function(x){return x.l<lo-av*.02})&&price>lo+av*.003;
  var htf=S.analysis.htf,trend=S.analysis.trend,extBias=htf==='Bullish'?1:htf==='Bearish'?-1:trend==='Bullish'?1:trend==='Bearish'?-1:(price>=eq?1:-1),rr=Math.max(rangeHi-rangeLo,1e-9),oteRatio=extBias===1?(rangeHi-price)/rr:(price-rangeLo)/rr,ote=oteRatio>=.62&&oteRatio<=.79;
  return{price:price,av:av,end:end,lastH:lastH,lastL:lastL,rangeHi:rangeHi,rangeLo:rangeLo,eq:eq,pd:pd,bsl:lastH,ssl:lastL,bullOB:bullOB,bearOB:bearOB,bullFVG:bullFVG,bearFVG:bearFVG,bearSweep:bearSweep,bullSweep:bullSweep,bias:extBias,ote:ote,oteRatio:oteRatio,fallback:true};
};

function v263micro(){
  var m=S.microCandles||[],price=finite(S.livePrice)?S.livePrice:(m.length?m[m.length-1].c:null);if(m.length<24||!finite(price))return{ready:false,label:'WAIT'};
  var end=m.length-1,ma=Math.max(atr(m,14)[end]||((S.analysis&&S.analysis.atr)||Math.abs(price)*.001)*.22,1e-9),prior=m.slice(Math.max(0,end-28),Math.max(1,end-5));if(prior.length<12)return{ready:false,label:'WAIT'};
  var hi=v263max(prior,'h'),lo=v263min(prior,'l'),recent=m.slice(Math.max(0,end-5)),cur=m[end],rng=Math.max(cur.h-cur.l,1e-9),upper=cur.h-Math.max(cur.o,cur.c),lower=Math.min(cur.o,cur.c)-cur.l;
  var bearSweep=recent.some(function(x){return x.h>hi+ma*.035&&x.c<hi+ma*.04})&&price<hi+ma*.02;
  var bullSweep=recent.some(function(x){return x.l<lo-ma*.035&&x.c>lo-ma*.04})&&price>lo-ma*.02;
  var pre=m.slice(Math.max(0,end-7),end),localH=v263max(pre,'h'),localL=v263min(pre,'l'),bosUp=price>localH+ma*.018,bosDn=price<localL-ma*.018;
  var rejectBuy=lower/rng>.28&&price>(cur.h+cur.l)/2,rejectSell=upper/rng>.28&&price<(cur.h+cur.l)/2,imp=(price-m[Math.max(0,end-4)].o)/ma,flow=fastFlow(),obi=num(S.ctx.orderBookImbalance||0);
  var ema9m=ema(m.map(function(x){return x.c}),9),es=ema9m[end]!=null&&ema9m[Math.max(8,end-3)]!=null?(ema9m[end]-ema9m[Math.max(8,end-3)])/ma:0;
  var label=bullSweep?'LOW SWEPT':bearSweep?'HIGH SWEPT':bosUp?'MICRO BOS UP':bosDn?'MICRO BOS DOWN':imp>.28?'IMPULSE UP':imp<-.28?'IMPULSE DOWN':'WATCH';
  return{ready:true,price:price,atr:ma,hi:hi,lo:lo,bearSweep:bearSweep,bullSweep:bullSweep,bosUp:bosUp,bosDn:bosDn,rejectBuy:rejectBuy,rejectSell:rejectSell,impulse:imp,emaSlope:es,flow:flow,obi:obi,label:label};
}
function v263mk(side,name,score,threshold,reasons,m,z,level,mic){
  return{side:side,strategy:name,score:Math.round(score),threshold:threshold,reasons:reasons||[],support:0,fast:score>=threshold+3,ict:true,v263:true,ictMap:m,idealZone:z||null,level:finite(level)?level:null,sweepLevel:finite(level)?level:null,microMSS:side==='BUY'?!!mic.bosUp:!!mic.bosDn,microAtr:mic.atr};
}
function v263rev(side,m,mic){
  var sg=side==='BUY'?1:-1,selSweep=side==='BUY'?m.bullSweep:m.bearSweep,microSweep=side==='BUY'?mic.bullSweep:mic.bearSweep,analysisSweep=String(S.analysis&&S.analysis.smc&&S.analysis.smc.sweep||'').indexOf(side==='BUY'?'Bullish':'Bearish')===0;
  if(!selSweep&&!microSweep&&!analysisSweep)return null;
  var zone=side==='BUY'?(m.bullOB||m.bullFVG):(m.bearOB||m.bearFVG),fvg=side==='BUY'?m.bullFVG:m.bearFVG,re=[],score=44;
  if(microSweep){score+=18;re.push('1m liquidity sweep')}if(selSweep){score+=8;re.push('selected TF liquidity sweep')}if(analysisSweep){score+=5;re.push('structure sweep')}
  var loc=side==='BUY'?m.price<=m.eq:m.price>=m.eq;if(loc){score+=8;re.push(side==='BUY'?'discount location':'premium location')}else score-=4;
  if(v263near(m.price,zone,m.av,.34)){score+=10;re.push('OB/FVG entry zone')}if(v263near(m.price,fvg,m.av,.25)){score+=5;re.push('FVG confluence')}
  var reclaim=side==='BUY'?m.price>mic.lo:m.price<mic.hi;if(reclaim){score+=7;re.push('liquidity reclaimed')}
  var bos=side==='BUY'?mic.bosUp:mic.bosDn,rej=side==='BUY'?mic.rejectBuy:mic.rejectSell;if(bos){score+=14;re.push('1m structure break')}if(rej){score+=8;re.push('1m rejection')}
  if(sg*mic.impulse>.18){score+=8;re.push('micro impulse turned')}else if(sg*mic.impulse<-.30)score-=8;
  if(m.bias===sg){score+=5;re.push('higher context aligned')}else score-=3;
  if(mic.flow&&mic.flow.total>0){if(sg*mic.flow.imbalance>.06){score+=5;re.push('taker flow aligned')}else if(sg*mic.flow.imbalance<-.12)score-=6}
  if(sg*mic.obi>.08)score+=3;else if(sg*mic.obi<-.18)score-=3;
  var threshold=70;if(score<threshold||(!bos&&!rej&&sg*mic.impulse<.24))return null;
  var lvl=microSweep?(side==='BUY'?mic.lo:mic.hi):(side==='BUY'?m.lastL.p:m.lastH.p);return v263mk(side,'ICT MICRO LIQUIDITY REVERSAL',score,threshold,re,m,zone||fvg,lvl,mic);
}
function v263cont(side,m,mic){
  var sg=side==='BUY'?1:-1,zone=side==='BUY'?(m.bullOB||m.bullFVG):(m.bearOB||m.bearFVG),fvg=side==='BUY'?m.bullFVG:m.bearFVG;if(!zone&&!fvg)return null;
  var closeZone=v263near(m.price,zone,m.av,.36)||v263near(m.price,fvg,m.av,.28);if(!closeZone)return null;
  var context=(m.bias===sg)||((S.analysis&&S.analysis.trend)===(side==='BUY'?'Bullish':'Bearish'));if(!context)return null;
  var re=['context aligned'],score=42;if(m.bias===sg)score+=8;if(side==='BUY'?m.price<=m.eq:m.price>=m.eq){score+=7;re.push(side==='BUY'?'discount pullback':'premium pullback')}
  if(v263near(m.price,zone,m.av,.30)){score+=17;re.push('order block retest')}if(v263near(m.price,fvg,m.av,.24)){score+=10;re.push('FVG retest')}
  var bos=side==='BUY'?mic.bosUp:mic.bosDn,rej=side==='BUY'?mic.rejectBuy:mic.rejectSell;if(bos){score+=11;re.push('1m continuation break')}if(rej){score+=7;re.push('1m rejection')}
  if(sg*mic.impulse>.12){score+=9;re.push('micro impulse aligned')}else if(sg*mic.impulse<-.25)score-=7;
  if(sg*mic.emaSlope>.06)score+=5;
  if(mic.flow&&mic.flow.total>0&&sg*mic.flow.imbalance>.05)score+=4;
  var threshold=70;if(score<threshold||(!bos&&!rej&&sg*mic.impulse<.20))return null;
  return v263mk(side,'ICT MICRO OB FVG CONTINUATION',score,threshold,re,m,zone||fvg,zone?zone.mid:(fvg?fvg.mid:null),mic);
}
function v263break(side,m,mic){
  var sg=side==='BUY'?1:-1,bos=side==='BUY'?mic.bosUp:mic.bosDn;if(!bos||sg*mic.impulse<.24)return null;
  var level=side==='BUY'?mic.hi:mic.lo,dist=Math.abs(m.price-level);if(dist>Math.max(m.av*.42,mic.atr*1.15))return null;
  var context=(m.bias===sg)||((S.analysis&&S.analysis.trend)===(side==='BUY'?'Bullish':'Bearish'));if(!context)return null;
  var re=['1m structure breakout','entry still near breakout'],score=52;if(m.bias===sg)score+=8;if(sg*mic.impulse>.40){score+=10;re.push('strong micro displacement')}else score+=6;
  if(sg*mic.emaSlope>.08)score+=6;if(mic.flow&&mic.flow.total>0&&sg*mic.flow.imbalance>.06)score+=5;if(sg*mic.obi>.08)score+=3;
  var threshold=74;if(score<threshold)return null;var z=v263zone(level-mic.atr*.10,level+mic.atr*.10,level);return v263mk(side,'ICT MICRO BREAKOUT',score,threshold,re,m,z,level,mic);
}
function v263render(m,mic,c,gate){
  v263e('scopeState','ACTIVE','bull');v263e('oppMicro',mic&&mic.ready?mic.label:'WAIT',mic&&(/UP|LOW/.test(mic.label))?'bull':mic&&(/DOWN|HIGH/.test(mic.label))?'bear':'neutral');
  v263e('oppBest',c?c.side+' '+c.strategy.replace('ICT MICRO ',''): 'NONE',c?(c.side==='BUY'?'bull':'bear'):'neutral');v263e('oppScore',c?(c.score+' / '+c.threshold):'0');
  var loc=m?(m.pd+(m.ote?' · OTE':'')):'WAIT';v263e('oppLocation',loc,m&&m.pd==='DISCOUNT'?'bull':m&&m.pd==='PREMIUM'?'bear':'neutral');v263e('oppGate',gate||'SCANNING',/READY|ARMING|CANDIDATE/.test(gate||'')?'bull':/BLOCK|LATE|CONFLICT|NEWS|LOSS/.test(gate||'')?'bear':'neutral');
  v263e('oppState',c?'ARMED':'SCANNING',c?'bull':'neutral');
}
function v263select(){
  var reg=v23regime(),fg=v24feedGate(reg),m=v26map(),mic=v263micro();V26.map=m;v26render(m);V263.lastMicro=mic;
  if(!m||!mic.ready){V263.lastGate='WAIT: structure data building';v263render(m,mic,null,V263.lastGate);return null}
  if(!fg.ok){V263.lastGate='BLOCK: '+fg.reason;v263render(m,mic,null,V263.lastGate);return{candidate:null,reason:V263.lastGate,regime:reg,block:true}}
  if(v24activeTrade()){V263.lastGate='WAIT: existing signal open';v263render(m,mic,null,V263.lastGate);return null}
  var brake=v24lossBrake();if(brake){V263.lastGate='BLOCK: '+brake;v263render(m,mic,null,V263.lastGate);return{candidate:null,reason:V263.lastGate,regime:reg,block:true}}
  if(v24tradeLimit()){V263.lastGate='WAIT: frequency control';v263render(m,mic,null,V263.lastGate);return null}
  var all=[v263rev('BUY',m,mic),v263rev('SELL',m,mic),v263cont('BUY',m,mic),v263cont('SELL',m,mic),v263break('BUY',m,mic),v263break('SELL',m,mic)].filter(Boolean).sort(function(a,b){return b.score-a.score});
  if(!all.length){V263.lastGate='SCANNING: no early trigger';v263render(m,mic,null,V263.lastGate);return null}
  var best=all[0],opp=all.find(function(x){return x.side!==best.side});if(opp&&best.score-opp.score<8){V263.lastGate='WAIT: micro direction conflict';v263render(m,mic,null,V263.lastGate);return{candidate:null,reason:V263.lastGate,regime:reg,block:true}}
  if(v26late(best,m)){V263.lastGate='WAIT: late move veto';v263render(m,mic,null,V263.lastGate);return{candidate:null,reason:V263.lastGate,regime:reg,block:true}}
  if(v24cooldownBlocked(best)){V263.lastGate='WAIT: cooldown';v263render(m,mic,null,V263.lastGate);return null}
  var ng=v26newsGate(best);if(!ng.ok){V263.lastGate=ng.reason;v263render(m,mic,null,V263.lastGate);return{candidate:null,reason:ng.reason,regime:reg,block:true}}
  best.support=best.reasons.length;best.fast=best.score>=best.threshold+3;V263.last=best;V263.lastGate='CANDIDATE READY';v263render(m,mic,best,V263.lastGate);return{candidate:best,reason:'',regime:reg};
}
var __v263BaseSelect=v24select;
v24select=function(){var o=v263select();if(o&&o.candidate)return o;if(o&&o.block)return o;var b=__v263BaseSelect();if(!b||!b.candidate){if(V263.lastGate.indexOf('CANDIDATE')<0&&b&&b.reason)V263.lastGate=b.reason;v263render(V26.map||v26map(),V263.lastMicro||v263micro(),null,V263.lastGate)}return b};

var __v263BasePlan=v24plan;
v24plan=function(c){
  if(!c||!c.v263)return __v263BasePlan(c);var m=c.ictMap||V26.map||v26map(),p=finite(S.livePrice)?S.livePrice:m.price,sg=c.side==='BUY'?1:-1,ma=Math.max(c.microAtr||m.av*.22,1e-9),floor=Math.max(ma*1.05,m.av*.24,Math.abs(p)*(num(S.ctx.spreadBps||0)*7)/10000),z=c.idealZone,anchor=c.sweepLevel;
  var sl;if(c.side==='BUY'){var a=finite(anchor)?anchor:(z?z.lo:p-floor);sl=Math.min(p-floor,a-ma*.14);if(z)sl=Math.min(sl,z.lo-ma*.12)}else{var a2=finite(anchor)?anchor:(z?z.hi:p+floor);sl=Math.max(p+floor,a2+ma*.14);if(z)sl=Math.max(sl,z.hi+ma*.12)}
  var r=Math.max(Math.abs(p-sl),floor);if(c.side==='BUY'&&sl>=p)sl=p-r;if(c.side==='SELL'&&sl<=p)sl=p+r;r=Math.abs(p-sl);return{direction:c.side,entry:p,sl:sl,t1:p+sg*r*.70,t2:p+sg*r*1.25,t3:p+sg*r*1.90,risk:r};
};

var __v263Publish=v24publish;
v24publish=function(c,sel){var before=trades().length;__v263Publish(c,sel);var a=trades();if(a.length>before){var t=a[a.length-1];t.sourceVersion='2.6.3';if(c&&c.v263)t.stage='V2.6.3 OPPORTUNITY · '+c.strategy+' Q'+c.score;save(a);renderTrades();if(typeof v261renderHistory==='function')v261renderHistory()}};

window.__dpEngineSnapshot=function(){try{return JSON.stringify({version:'2.6.3',market:S.market,symbol:S.symbol,tf:S.tf,feed:S.feedMode,analysis:!!S.analysis,ict:!!(V26&&V26.map),micro:V263.lastMicro&&V263.lastMicro.label,gate:V263.lastGate,last:V263.last&&{side:V263.last.side,strategy:V263.last.strategy,score:V263.last.score,threshold:V263.last.threshold}})}catch(e){return '{}'}};
setInterval(function(){try{var m=v26map(),mic=v263micro();V26.map=m;v26render(m);v263render(m,mic,V263.last,V263.lastGate)}catch(e){}},800);
'''

if 'V2.6.3 Opportunity Engine Fix.' not in s:
    s = s.replace('\n</script>', js + '\n})();\n</script>', 1)
else:
    raise SystemExit('V2.6.3 already present')
idx.write_text(s)

b = root / 'app/build.gradle.kts'
bs = b.read_text()
bs = re.sub(r'applicationId\s*=\s*"[^"]+"', 'applicationId = "com.dhanpulse.cryptofxstablev263"', bs, count=1)
bs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 34', bs, count=1)
bs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.6.3"', bs, count=1)
b.write_text(bs)
