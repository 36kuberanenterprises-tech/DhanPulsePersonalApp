se;
}
function v26newsGate(c){
  if(typeof v25newsContext!=='function')return{ok:true,nc:null};var nc=v25newsContext(c.side);if(nc.block)return{ok:false,nc:nc,reason:'WAIT: NEWS RISK · '+nc.reason};
  if(nc.aligned){c.score=Math.min(99,c.score+3);c.reasons.push('news and candle reaction aligned')}else if(!nc.quiet&&nc.impact>=4){c.score-=3;c.fast=false;c.reasons.push('news uncertainty')}
  c.newsContext=nc;return{ok:true,nc:nc};
}
function v26selectICT(){
  var m=v26map();V26.map=m;v26render(m);if(!m)return null;var fg=v24feedGate(v23regime());if(!fg.ok||v24activeTrade()||v24lossBrake()||v24tradeLimit())return null;
  var x=[v26reversal('BUY',m),v26reversal('SELL',m),v26continuation('BUY',m),v26continuation('SELL',m)].filter(Boolean).sort(function(a,b){return b.score-a.score});if(!x.length)return null;
  var best=x[0],opp=x.find(function(z){return z.side!==best.side});if(opp&&best.score-opp.score<10)return{candidate:null,reason:'WAIT: ICT direction conflict',regime:v23regime()};
  if(v26late(best,m))return{candidate:null,reason:'WAIT: ICT move already left the entry zone',regime:v23regime()};
  if(v24cooldownBlocked(best))return{candidate:null,reason:'WAIT: cooldown after recent trade',regime:v23regime()};
  var ng=v26newsGate(best);if(!ng.ok)return{candidate:null,reason:ng.reason,regime:v23regime()};
  best.support=(best.microMSS?1:0)+(best.newsContext&&best.newsContext.aligned?1:0)+(best.idealZone?1:0);best.fast=best.microMSS||best.score>=best.threshold+5;
  return{candidate:best,reason:'',regime:v23regime()};
}
function v26render(m){
  if(!m)return;var e=function(id,v,cl){var z=q(id);if(z){z.textContent=v;if(cl)z.className=cl}};
  e('ictBias',m.bias===1?'BULLISH':'BEARISH',m.bias===1?'bull':'bear');e('ictPD',m.pd+(m.ote?' · OTE':''),m.pd==='DISCOUNT'?'bull':m.pd==='PREMIUM'?'bear':'neutral');e('ictBSL',v26fmt(m.bsl&&m.bsl.p));e('ictSSL',v26fmt(m.ssl&&m.ssl.p));
  var ob=m.pd==='DISCOUNT'?m.bullOB:m.bearOB,fvg=m.pd==='DISCOUNT'?m.bullFVG:m.bearFVG;e('ictOB',ob?v26fmt(ob.lo)+' to '+v26fmt(ob.hi):'NONE');e('ictFVG',fvg?v26fmt(fvg.lo)+' to '+v26fmt(fvg.hi):'NONE');
  var sw=m.bearSweep?'BUY SIDE SWEPT':m.bullSweep?'SELL SIDE SWEPT':'NONE';e('ictSweep',sw,m.bearSweep?'bear':m.bullSweep?'bull':'neutral');var tr=m.bearSweep?'SELL WATCH':m.bullSweep?'BUY WATCH':(v26touch(m.price,m.bullOB,m.av,.18)?'BUY ZONE':v26touch(m.price,m.bearOB,m.av,.18)?'SELL ZONE':'WAIT');e('ictTrigger',tr,tr.indexOf('BUY')===0?'bull':tr.indexOf('SELL')===0?'bear':'neutral');e('ictState',tr==='WAIT'?'SCANNING':'ARMED',tr==='WAIT'?'neutral':'bull');
}
var __v26BaseSelect=v24select;
v24select=function(){
  var ict=v26selectICT();if(ict&&ict.candidate)return ict;if(ict&&ict.reason&&/NEWS RISK|direction conflict|move already|cooldown/.test(ict.reason))return ict;
  var base=__v26BaseSelect();if(base&&base.candidate){var m=V26.map||v26map();if(v26late(base.candidate,m))return{candidate:null,reason:'WAIT: late entry veto · move already extended from OB/FVG',regime:base.regime};}
  return base;
};
var __v26BasePlan=v24plan;
v24plan=function(c){
  if(!c||!c.ict)return __v26BasePlan(c);var m=c.ictMap||V26.map||v26map(),price=finite(S.livePrice)?S.livePrice:(m?m.price:S.analysis.last.c),av=Math.max(m?m.av:S.analysis.atr,1e-9),sg=v26sg(c.side),z=c.idealZone,r,sl;
  if(c.side==='BUY'){var anchor=Math.min(c.sweepLevel||price,z?z.lo:price);sl=anchor-av*.12;r=Math.max(price-sl,av*.38)}else{var anchor2=Math.max(c.sweepLevel||price,z?z.hi:price);sl=anchor2+av*.12;r=Math.max(sl-price,av*.38)}
  if(c.side==='BUY'&&sl>=price)sl=price-r;if(c.side==='SELL'&&sl<=price)sl=price+r;r=Math.abs(price-sl);
  var t1=price+sg*r*.72,t2=price+sg*r*1.30,t3=price+sg*r*2.05;
  if(m){if(c.side==='BUY'){if(m.eq>price+r*.35)t1=Math.max(t1,m.eq);if(m.lastH&&m.lastH.p>t1)t2=Math.max(t2,m.lastH.p)}else{if(m.eq<price-r*.35)t1=Math.min(t1,m.eq);if(m.lastL&&m.lastL.p<t1)t2=Math.min(t2,m.lastL.p)}}
  if(c.side==='BUY'){t2=Math.max(t2,t1+r*.35);t3=Math.max(t3,t2+r*.45)}else{t2=Math.min(t2,t1-r*.35);t3=Math.min(t3,t2-r*.45)}
  return{direction:c.side,entry:price,sl:sl,t1:t1,t2:t2,t3:t3,risk:r};
};
var __v26BasePublish=v24publish;
v24publish=function(c,sel){var before=trades().length;__v26BasePublish(c,sel);var a=trades();if(a.length>before&&c&&c.ict){var t=a[a.length-1];t.id=String(t.id||'').replace(/^v24_/,'v26_');t.stage='V2.6 ICT EARLY · '+c.strategy+' Q'+c.score;t.ict=true;t.ictSweepLevel=c.sweepLevel||null;t.ictZone=c.idealZone||null;t.resultDisplay=v251ResultLabel(t);save(a);renderTrades()}};

/* Add liquidity and ICT zone overlays to the existing chart. */
function v26drawOverlay(){
  if(BACKGROUND_MODE)return;var m=V26.map||v26map(),cv=q('chart');if(!m||!cv||!S.candles.length)return;var r=cv.getBoundingClientRect(),dpr=Math.min(window.devicePixelRatio||1,2),W=Math.max(300,r.width),H=W<520?300:340,x=cv.getContext('2d');x.save();x.setTransform(dpr,0,0,dpr,0,0);ensureChartView();var count=Math.min(S.chartView.visible,S.candles.length),endIdx=Math.max(count,S.candles.length-S.chartView.rightOffset),startIdx=Math.max(0,endIdx-count),cs=S.candles.slice(startIdx,endIdx),raw=[];cs.forEach(function(c){raw.push(c.h,c.l)});if(!raw.length){x.restore();return}var mn=Math.min.apply(null,raw),mx=Math.max.apply(null,raw),rg0=Math.max(mx-mn,Math.abs(cs[cs.length-1].c)*.0005),pad=rg0*.08;mn-=pad;mx+=pad;var rg=mx-mn,L=58,R=9,T=12,B=25,y=function(v){return T+(mx-v)/rg*(H-T-B)},inside=function(v){return finite(v)&&v>=mn&&v<=mx};
  function level(v,label,col){if(!inside(v))return;x.setLineDash([4,4]);x.strokeStyle=col;x.globalAlpha=.6;x.beginPath();x.moveTo(L,y(v));x.lineTo(W-R,y(v));x.stroke();x.setLineDash([]);x.globalAlpha=.9;x.fillStyle=col;x.font='bold 8px Arial';x.fillText(label,L+6,y(v)-3)}
  function zone(z,label,col){if(!z||z.hi<mn||z.lo>mx)return;var hi=Math.min(mx,z.hi),lo=Math.max(mn,z.lo),top=y(hi),bot=y(lo);x.globalAlpha=.08;x.fillStyle=col;x.fillRect(L,Math.min(top,bot),W-L-R,Math.max(2,Math.abs(bot-top)));x.globalAlpha=.9;x.fillStyle=col;x.font='bold 8px Arial';x.fillText(label,W-78,Math.min(top,bot)+10)}
  level(m.bsl&&m.bsl.p,'BSL','#ff9aaa');level(m.ssl&&m.ssl.p,'SSL','#83e6b4');level(m.eq,'EQ 50%','#aab8c4');zone(m.bullOB,'ICT BULL OB','#53d99a');zone(m.bearOB,'ICT BEAR OB','#ff7481');zone(m.bullFVG,'ICT BULL FVG','#5ccfe6');zone(m.bearFVG,'ICT BEAR FVG','#e1a15a');x.restore();
}
var __v26Draw=draw;draw=function(){__v26Draw();try{v26drawOverlay()}catch(e){}};

/* Keep the ICT map and selected-timeframe analysis live, including background mode. */
v