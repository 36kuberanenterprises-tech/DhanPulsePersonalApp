from pathlib import Path

root = Path('crypto-forex-app/buildsrc')
idx = root / 'app/src/main/assets/index.html'
s = idx.read_text()

s = s.replace('Version 2.3.4 Lock Screen Fix', 'Version 2.4 Precision Fast')
s = s.replace('DhanPulse Crypto and Forex Version 2.3.4 Lock Screen Fix.', 'DhanPulse Crypto and Forex Version 2.4 Precision Fast.')
s = s.replace('var TRKEY="dhanpulse_cf_android_trades_v23"', 'var TRKEY="dhanpulse_cf_android_trades_v24"')
s = s.replace('V2.3 Signals', 'V2.4 Signals')
s = s.replace('No V2.3 signals recorded yet.', 'No V2.4 signals recorded yet.')
s = s.replace('(t.strategy||t.stage||"V2.3")', '(t.strategy||t.stage||"V2.4")')

block = r'''
/* V2.4 Precision Fast override.
   Goal: maximise precision and reduce decision latency without pretending that an 80% win rate can be guaranteed.
   Uses the V2.3 six-family research engine, then adds stricter hard gates, same-side consensus,
   faster persistent confirmation, native-tick execution and tighter anti-chase / loss controls. */
var V24={candidate:null,lastEvalAt:0,lastPublishedAt:0,lastPublishedKey:"",version:"2.4"};
function v24sg(side){return side==="BUY"?1:-1}
function v24threshold(name){
  var base={"TREND CONTINUATION":92,"PULLBACK":93,"BREAKOUT":95,"LIQUIDITY REVERSAL":96,"MEAN REVERSION":96,"MOMENTUM IGNITION":96}[name]||95;
  var st=v23strategyStats(name),add=0,pause=false;
  if(st.n>=5&&st.shrunkR<0)add+=2;
  if(st.n>=8&&st.shrunkR<-.05)add+=3;
  if(st.n>=10&&st.shrunkR<-.12){add+=4;pause=true}
  if(st.n>=8&&st.shrunkR>.18)add-=1;
  return{threshold:v23clamp(base+add,90,99),pause:pause,stats:st};
}
function v24feedGate(reg){
  if(!S.analysis)return{ok:false,reason:"analysis unavailable"};
  var now=Date.now(),age=S.lastMarketEventAt?now-S.lastMarketEventAt:999999,spread=num(S.ctx.spreadBps||0);
  if(S.market==="crypto"&&age>1800)return{ok:false,reason:"live feed slower than precision limit"};
  if(S.market==="crypto"&&spread>2.5)return{ok:false,reason:"spread above precision limit"};
  var minAtr={"1m":.020,"5m":.040,"15m":.055,"30m":.070,"1h":.090,"4h":.130}[S.tf]||.040;
  if(reg.atrPct<minAtr)return{ok:false,reason:"volatility too low for fast precision"};
  if(reg.type==="EXTREME VOL")return{ok:false,reason:"extreme volatility veto"};
  return{ok:true,reason:""};
}
function v24hardContext(c,reg){
  var side=c.side,sg=v24sg(side),a=S.analysis,mc=v23micro(),flow=mc.flow,htf=a&&a.htf||"NA",want=side==="BUY"?"Bullish":"Bearish";
  var trendFam=c.strategy==="TREND CONTINUATION"||c.strategy==="PULLBACK";
  var breakFam=c.strategy==="BREAKOUT"||c.strategy==="MOMENTUM IGNITION";
  var reverseFam=c.strategy==="LIQUIDITY REVERSAL"||c.strategy==="MEAN REVERSION";
  if(trendFam&& !((side==="BUY"&&reg.type==="TREND UP")||(side==="SELL"&&reg.type==="TREND DOWN")))return{ok:false,reason:"strategy regime mismatch"};
  if(breakFam&& !((side==="BUY"&&reg.type==="BREAKOUT UP")||(side==="SELL"&&reg.type==="BREAKOUT DOWN")))return{ok:false,reason:"breakout regime mismatch"};
  if(reverseFam&&!(reg.type==="RANGE"||reg.type==="TRANSITION"))return{ok:false,reason:"reversal outside range transition"};
  if((trendFam||breakFam)&&htf!==want)return{ok:false,reason:"higher timeframe not aligned"};
  if(reverseFam&&htf!=="Neutral"&&htf!=="NA"&&htf!==want&&reg.adx>=19)return{ok:false,reason:"reversal fighting higher timeframe"};
  if(flow.total>0&&sg*flow.imbalance<-.06)return{ok:false,reason:"live taker flow opposing"};
  if((trendFam||breakFam)&&sg*mc.impulse<.04)return{ok:false,reason:"micro impulse not confirmed"};
  if(c.strategy==="BREAKOUT"&&reg.volRatio<1.35)return{ok:false,reason:"breakout volume insufficient"};
  if(c.strategy==="MOMENTUM IGNITION"&&reg.volRatio<1.50)return{ok:false,reason:"momentum volume insufficient"};
  return{ok:true,reason:""};
}
function v24activeTrade(){return v23activeTrade()}
function v24tradeLimit(){
  var now=Date.now(),list=trades().filter(function(t){return t.symbol===S.symbol&&t.tf===S.tf&&now-t.createdAt<21600000});
  var hour=list.filter(function(t){return now-t.createdAt<3600000}).length;
  return hour>=2||list.length>=4;
}
function v24lossBrake(){
  var x=v23closed().filter(function(t){return t.symbol===S.symbol&&t.tf===S.tf&&t.result!=="AMBIGUOUS"&&finite(t.pnlR)}).slice(-6);
  if(!x.length)return null;
  var last=x[x.length-1],age=Date.now()-(last.closedAt||last.createdAt),tail2=x.slice(-2),tail3=x.slice(-3),sum=x.slice(-5).reduce(function(z,t){return z+num(t.pnlR)},0);
  if(tail3.length===3&&tail3.every(function(t){return t.pnlR<0})&&age<Math.max(1800000,v23tfCooldown(6)))return"three loss precision circuit breaker";
  if(tail2.length===2&&tail2.every(function(t){return t.pnlR<0})&&age<Math.max(900000,v23tfCooldown(3)))return"two loss cooldown";
  if(x.length>=5&&sum<=-2.0&&age<Math.max(1800000,v23tfCooldown(4)))return"recent expectancy drawdown";
  return null;
}
function v24cooldownBlocked(c){
  var list=v23closed().filter(function(t){return t.symbol===S.symbol&&t.tf===S.tf&&t.result!=="AMBIGUOUS"});
  if(!list.length)return false;
  var last=list[list.length-1],age=Date.now()-(last.closedAt||last.createdAt);
  if(last.result==="SL"&&age<v23tfCooldown(3))return true;
  if(age<v23tfCooldown(.55))return true;
  var same=list.filter(function(t){return t.strategy===c.strategy}).slice(-1)[0];
  if(same&&finite(same.pnlR)&&same.pnlR<0&&Date.now()-(same.closedAt||same.createdAt)<v23tfCooldown(5))return true;
  return false;
}
function v24select(){
  var reg=v23regime(),fg=v24feedGate(reg);
  if(!fg.ok)return{candidate:null,reason:"BLOCKED: "+fg.reason,regime:reg};
  if(v24activeTrade())return{candidate:null,reason:"WAIT: existing signal still open",regime:reg};
  var brake=v24lossBrake();if(brake)return{candidate:null,reason:"WAIT: "+brake,regime:reg};
  if(v24tradeLimit())return{candidate:null,reason:"WAIT: precision frequency limit",regime:reg};
  var all=v23families().map(function(c){var t=v24threshold(c.strategy);c.threshold=t.threshold;c.paused=t.pause;c.liveStats=t.stats;var hc=v24hardContext(c,reg);c.hardOK=hc.ok;c.hardReason=hc.reason;return c}).filter(function(c){return !c.paused&&c.hardOK});
  var qualified=all.filter(function(c){return c.score>=c.threshold});
  if(!qualified.length)return{candidate:null,reason:"WAIT: no strategy cleared precision threshold",regime:reg};
  var qb=qualified.filter(function(c){return c.side==="BUY"}).sort(function(a,b){return b.score-a.score}),qs=qualified.filter(function(c){return c.side==="SELL"}).sort(function(a,b){return b.score-a.score});
  var bestB=qb[0],bestS=qs[0];
  if(bestB&&bestS&&Math.abs(bestB.score-bestS.score)<18)return{candidate:null,reason:"WAIT: precision conflict veto",regime:reg};
  var best=!bestS||(bestB&&bestB.score>bestS.score)?bestB:bestS;
  var opp=all.filter(function(c){return c.side!==best.side}).sort(function(a,b){return b.score-a.score})[0];
  if(opp&&opp.score>=opp.threshold-5&&best.score-opp.score<18)return{candidate:null,reason:"WAIT: opposite setup too close",regime:reg};
  var support=all.filter(function(c){return c.side===best.side&&c.strategy!==best.strategy&&c.score>=c.threshold-5}).length;
  if(support<1)return{candidate:null,reason:"WAIT: independent confirmation missing",regime:reg};
  if(best.score<best.threshold+3&&support<2)return{candidate:null,reason:"WAIT: precision consensus insufficient",regime:reg};
  if(v24cooldownBlocked(best))return{candidate:null,reason:"WAIT: cooldown after recent trade",regime:reg};
  best.support=support;
  best.fast=(best.score>=best.threshold+5&&support>=2);
  return{candidate:best,reason:"",regime:reg};
}
function v24plan(c){
  var a=S.analysis,reg=v23regime(),x=S.candles[reg.idx],price=finite(S.livePrice)?S.livePrice:x.c,av=Math.max((atr(S.candles,14)[reg.idx])||a.atr||Math.abs(price)*.001,1e-9);
  var rm={"TREND CONTINUATION":1.22,"PULLBACK":1.12,"BREAKOUT":1.32,"LIQUIDITY REVERSAL":1.18,"MEAN REVERSION":1.12,"MOMENTUM IGNITION":1.38}[c.strategy]||1.22;
  var target={"TREND CONTINUATION":[.70,1.30,1.95],"PULLBACK":[.65,1.20,1.80],"BREAKOUT":[.75,1.35,2.00],"LIQUIDITY REVERSAL":[.60,1.12,1.70],"MEAN REVERSION":[.58,1.08,1.62],"MOMENTUM IGNITION":[.80,1.40,2.05]}[c.strategy]||[.70,1.25,1.90];
  var spread=num(S.ctx.spreadBps||0),minr=Math.max(Math.abs(price)*.0007,Math.abs(price)*(spread*8)/10000),r=Math.max(av*rm,minr),sl;
  if(c.side==="BUY"){
    sl=price-r;if(finite(c.level)&&c.level<price&&price-c.level<av*1.8)sl=Math.min(sl,c.level-av*.18);r=price-sl;
    return{direction:"BUY",entry:price,sl:sl,t1:price+r*target[0],t2:price+r*target[1],t3:price+r*target[2],risk:r};
  }
  sl=price+r;if(finite(c.level)&&c.level>price&&c.level-price<av*1.8)sl=Math.max(sl,c.level+av*.18);r=sl-price;
  return{direction:"SELL",entry:price,sl:sl,t1:price-r*target[0],t2:price-r*target[1],t3:price-r*target[2],risk:r};
}
function v24publish(c,sel){
  var p=v24plan(c),now=Date.now(),riskBps=p.risk/Math.max(Math.abs(p.entry),1e-9)*10000,spread=num(S.ctx.spreadBps||0);
  if(S.market==="crypto"&&riskBps<Math.max(7,spread*8)){V24.candidate=null;return}
  var key=S.market+"|"+S.symbol+"|"+S.tf+"|"+c.side+"|"+c.strategy+"|"+Math.round(p.entry/Math.max((S.analysis&&S.analysis.atr||1)*.16,1e-9));
  if(V24.lastPublishedKey===key&&now-V24.lastPublishedAt<v23tfCooldown(1.2))return;
  var mode=c.fast?"FAST PRECISION":"PRECISION";
  var t={id:"v24_"+now+"_"+Math.random().toString(36).slice(2,7),market:S.market,symbol:S.symbol,tf:S.tf,side:c.side,strategy:c.strategy,stage:"V2.4 "+mode+" Q"+c.score+" "+sel.regime.type,quality:c.score,regime:sel.regime.type,support:c.support||0,reasons:c.reasons.slice(0,7),entry:p.entry,sl:p.sl,t1:p.t1,t2:p.t2,t3:p.t3,status:"OPEN",result:"OPEN",h1:false,h2:false,h3:false,preProtect:false,protect:null,createdAt:now};
  var list=trades();list.push(t);save(list);V24.lastPublishedAt=now;V24.lastPublishedKey=key;S.lastTradeLogAt=now;S.lastTradeLogSource="V2.4 "+mode;nativeSignal(t);renderTrades();
}
function v24confirmStep(){
  var now=Date.now();if(now-V24.lastEvalAt<180)return;V24.lastEvalAt=now;
  var sel=v24select(),c=sel.candidate,card=q("decisionCard");
  if(!c){V24.candidate=null;if(q("decision")){if(card)card.className="panel decision wait";q("decision").textContent="WAIT";q("score").textContent="Regime "+(sel.regime?sel.regime.type:"WAIT");q("stage").textContent=sel.reason||"WAIT";q("reason").textContent=sel.reason||"No precision setup";q("pdir").textContent="WAIT"}return}
  var plan=v24plan(c);if(card)card.className="panel decision "+c.side.toLowerCase();q("decision").textContent=c.side;q("score").textContent="Precision "+c.score+" / "+c.threshold+" · Support "+(c.support||0);q("reason").textContent=c.reasons.slice(0,6).join(" • ");q("pdir").textContent=c.side;q("entry").textContent=fmt(plan.entry,dec(plan.entry));q("sl").textContent=fmt(plan.sl,dec(plan.entry));q("t1").textContent=fmt(plan.t1,dec(plan.entry));q("t2").textContent=fmt(plan.t2,dec(plan.entry));q("t3").textContent=fmt(plan.t3,dec(plan.entry));
  var key=S.symbol+"|"+S.tf+"|"+c.side+"|"+c.strategy,fast=!!c.fast;
  var needFast={"TREND CONTINUATION":1200,"PULLBACK":1200,"BREAKOUT":900,"LIQUIDITY REVERSAL":1400,"MEAN REVERSION":1500,"MOMENTUM IGNITION":850}[c.strategy]||1200;
  var needSlow={"TREND CONTINUATION":2600,"PULLBACK":2600,"BREAKOUT":2200,"LIQUIDITY REVERSAL":3000,"MEAN REVERSION":3200,"MOMENTUM IGNITION":2000}[c.strategy]||2600;
  var need=fast?needFast:needSlow,minCount=fast?3:4,price=finite(S.livePrice)?S.livePrice:S.analysis.last.c,av=Math.max(S.analysis.atr||1,1e-9),chase=fast?.11:.17;
  if(!V24.candidate||V24.candidate.key!==key){V24.candidate={key:key,first:now,last:now,count:1,firstPrice:price,minScore:c.score,c:c,sel:sel};q("stage").textContent=c.strategy+" · "+(fast?"FAST ARMING":"PRECISION ARMING")+" 1/"+minCount;return}
  if(Math.abs(price-V24.candidate.firstPrice)>av*chase){V24.candidate={key:key,first:now,last:now,count:1,firstPrice:price,minScore:c.score,c:c,sel:sel};q("stage").textContent=c.strategy+" · RESET CHASE FILTER";return}
  V24.candidate.last=now;V24.candidate.count++;V24.candidate.minScore=Math.min(V24.candidate.minScore,c.score);V24.candidate.c=c;V24.candidate.sel=sel;
  var elapsed=now-V24.candidate.first;q("stage").textContent=c.strategy+" · "+(fast?"FAST":"PRECISION")+" "+Math.min(minCount,V24.candidate.count)+"/"+minCount+" · "+Math.max(0,Math.ceil((need-elapsed)/100)/10)+"s";
  var floor=fast?c.threshold+2:c.threshold;
  if(elapsed>=need&&V24.candidate.count>=minCount&&V24.candidate.minScore>=floor){v24publish(c,sel);V24.candidate=null}
}
function v24closeTrade(t,res,px,evt){var risk=Math.max(Math.abs(t.entry-t.sl),1e-9);t.status="CLOSED";t.result=res;t.exitPrice=px;t.pnlR=res==="AMBIGUOUS"?null:(t.side==="BUY"?(px-t.entry)/risk:(t.entry-px)/risk);t.closedAt=evt||Date.now();return true}
function v24applyTick(t,price,evt){
  if(t.status!=="OPEN"||!finite(price))return false;
  var ch=false,risk=Math.max(Math.abs(t.entry-t.sl),1e-9),sg=t.side==="BUY"?1:-1,move=sg*(price-t.entry)/risk;
  var pre=t.entry+sg*risk*.04,p1=t.entry+sg*risk*.18,p2=t.entry+sg*risk*.80;
  if(!t.preProtect&&move>=.55){t.preProtect=true;t.protect=pre;t.result="early protection";ch=true}
  var stop=t.h2?p2:t.h1?p1:t.preProtect?pre:t.sl;
  if((t.side==="BUY"&&price<=stop)||(t.side==="SELL"&&price>=stop))return v24closeTrade(t,t.h2?"T2 PROTECTED":t.h1?"T1 PROTECTED":t.preProtect?"PROTECTED":"SL",stop,evt);
  if(((t.side==="BUY"&&price>=t.t1)||(t.side==="SELL"&&price<=t.t1))&&!t.h1){t.h1=true;t.protect=p1;t.result="T1 protected";ch=true}
  if(((t.side==="BUY"&&price>=t.t2)||(t.side==="SELL"&&price<=t.t2))&&!t.h2){t.h2=true;t.protect=p2;t.result="T2 protected";ch=true}
  if((t.side==="BUY"&&price>=t.t3)||(t.side==="SELL"&&price<=t.t3)){t.h3=true;return v24closeTrade(t,"T3",t.t3,evt)}
  var holdBars={"BREAKOUT":6,"MOMENTUM IGNITION":5,"TREND CONTINUATION":9,"PULLBACK":8,"LIQUIDITY REVERSAL":7,"MEAN REVERSION":7}[t.strategy]||8;
  if(Date.now()-t.createdAt>tfMs(t.tf)*holdBars)return v24closeTrade(t,"TIME EXIT",price,evt);
  return ch;
}
function v24applyCandle(t,c){
  if(t.status!=="OPEN")return false;
  var risk=Math.max(Math.abs(t.entry-t.sl),1e-9),sg=t.side==="BUY"?1:-1,pre=t.entry+sg*risk*.04,p1=t.entry+sg*risk*.18,p2=t.entry+sg*risk*.80,stop=t.h2?p2:t.h1?p1:t.preProtect?pre:t.sl;
  var hitStop=t.side==="BUY"?c.l<=stop:c.h>=stop,hit1=t.side==="BUY"?c.h>=t.t1:c.l<=t.t1,hit2=t.side==="BUY"?c.h>=t.t2:c.l<=t.t2,hit3=t.side==="BUY"?c.h>=t.t3:c.l<=t.t3,newTarget=(!t.h1&&hit1)||(!t.h2&&hit2)||(!t.h3&&hit3);
  if(hitStop&&newTarget)return v24closeTrade(t,"AMBIGUOUS",t.entry,c.t);
  if(hitStop)return v24closeTrade(t,t.h2?"T2 PROTECTED":t.h1?"T1 PROTECTED":t.preProtect?"PROTECTED":"SL",stop,c.t);
  var ch=false;if(hit1&&!t.h1){t.h1=true;t.protect=p1;t.result="T1 protected";ch=true}if(hit2&&!t.h2){t.h2=true;t.protect=p2;t.result="T2 protected";ch=true}if(hit3){t.h3=true;return v24closeTrade(t,"T3",t.t3,c.t)}return ch;
}

v23feedGate=v24feedGate;
v23select=v24select;
v23plan=v24plan;
v23publish=v24publish;
v23confirmStep=v24confirmStep;
v23applyTick=v24applyTick;
v23applyCandle=v24applyCandle;
'''

pos = s.rfind('</script>')
if pos < 0:
    raise SystemExit('script closing tag not found')
s = s[:pos] + block + '\n' + s[pos:]
idx.write_text(s)

b = root / 'app/build.gradle.kts'
bs = b.read_text()
bs = bs.replace('applicationId = "com.dhanpulse.cryptofxresearchv234"', 'applicationId = "com.dhanpulse.cryptofxresearchv240"')
bs = bs.replace('versionCode = 27', 'versionCode = 28')
bs = bs.replace('versionName = "2.3.4"', 'versionName = "2.4.0"')
b.write_text(bs)
