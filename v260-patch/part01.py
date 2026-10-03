urn z.lo-price;if(price>z.hi)return price-z.hi;return 0}
function v26microState(side,av){
  var m=S.microCandles||[],n=m.length;if(n<8)return{mss:false,reject:false,impulse:0,flow:fastFlow(),level:null};
  var x=m[n-1],prev=m.slice(Math.max(0,n-7),n-1),sg=v26sg(side),flow=fastFlow(),level=side==='BUY'?Math.max.apply(null,prev.map(function(z){return z.h})):Math.min.apply(null,prev.map(function(z){return z.l}));
  var mss=side==='BUY'?x.c>level:x.c<level,rng=Math.max(x.h-x.l,1e-9),upper=x.h-Math.max(x.o,x.c),lower=Math.min(x.o,x.c)-x.l;
  var reject=side==='BUY'?(lower/rng>.32&&x.c>(x.h+x.l)/2):(upper/rng>.32&&x.c<(x.h+x.l)/2);
  var look=m.slice(Math.max(0,n-5));var impulse=look.length>1?sg*(look[look.length-1].c-look[0].o)/Math.max(av*.35,1e-9):0;
  return{mss:mss,reject:reject,impulse:impulse,flow:flow,level:level};
}
function v26map(){
  var c=S.candles||[];if(c.length<40||!S.analysis)return null;var end=v26closedIndex(c),live=c[c.length-1],price=finite(S.livePrice)?S.livePrice:live.c,av=Math.max(S.analysis.atr||atr(c,14)[c.length-1]||Math.abs(price)*.001,1e-9),pv=v26pivots(c,end),lastH=pv.highs.length?pv.highs[pv.highs.length-1]:null,lastL=pv.lows.length?pv.lows[pv.lows.length-1]:null;
  if(!lastH||!lastL)return null;
  var rangeHi=Math.max(lastH.p,lastL.p),rangeLo=Math.min(lastH.p,lastL.p),eq=(rangeHi+rangeLo)/2,pd=price>eq?'PREMIUM':price<eq?'DISCOUNT':'EQUILIBRIUM';
  var bsl=v26nearestSwing(pv.highs,price,true)||lastH,ssl=v26nearestSwing(pv.lows,price,false)||lastL;
  var bullOB=v26findOB(c,end,av,1),bearOB=v26findOB(c,end,av,-1),bullFVG=v26findFvg(c,end,av,1),bearFVG=v26findFvg(c,end,av,-1);
  var mic=S.microCandles||[],me=mic.length-2,mav=mic.length>16?(atr(mic,14)[mic.length-1]||av*.22):av*.22,mBullOB=me>10?v26findOB(mic,me,mav,1):null,mBearOB=me>10?v26findOB(mic,me,mav,-1):null,mBullFVG=me>10?v26findFvg(mic,me,mav,1):null,mBearFVG=me>10?v26findFvg(mic,me,mav,-1):null;
  function chooseNear(a,b){if(!a)return b;if(!b)return a;return v26zoneDistance(price,a)<=v26zoneDistance(price,b)?a:b}
  bullOB=chooseNear(bullOB,mBullOB);bearOB=chooseNear(bearOB,mBearOB);bullFVG=chooseNear(bullFVG,mBullFVG);bearFVG=chooseNear(bearFVG,mBearFVG);
  var cur=c[c.length-1],bearSweep=cur.h>lastH.p+av*.025&&price<lastH.p-av*.005,bullSweep=cur.l<lastL.p-av*.025&&price>lastL.p+av*.005;
  var extBias=S.analysis.htf==='Bullish'?1:S.analysis.htf==='Bearish'?-1:(S.analysis.trend==='Bullish'?1:-1),rr=Math.max(rangeHi-rangeLo,1e-9),oteRatio=extBias===1?(rangeHi-price)/rr:(price-rangeLo)/rr,ote=oteRatio>=.62&&oteRatio<=.79;
  return{price:price,av:av,end:end,lastH:lastH,lastL:lastL,rangeHi:rangeHi,rangeLo:rangeLo,eq:eq,pd:pd,bsl:bsl,ssl:ssl,bullOB:bullOB,bearOB:bearOB,bullFVG:bullFVG,bearFVG:bearFVG,bearSweep:bearSweep,bullSweep:bullSweep,bias:extBias,ote:ote,oteRatio:oteRatio};
}
function v26touch(price,z,av,m){return !!z&&v26zoneDistance(price,z)<=av*(m||.12)}
function v26candidate(side,strategy,score,reasons,threshold,map,extra){var c={side:side,strategy:strategy,score:Math.round(score),threshold:threshold,reasons:reasons||[],support:0,fast:true,ict:true,level:null,ictMap:map};if(extra)Object.keys(extra).forEach(function(k){c[k]=extra[k]});return c}
function v26reversal(side,m){
  var sg=v26sg(side),micro=v26microState(side,m.av),flow=micro.flow,reasons=[],score=0,sweep=side==='SELL'?m.bearSweep:m.bullSweep,liq=side==='SELL'?m.lastH:m.lastL,zone=side==='SELL'?m.bearOB:m.bullOB,fvg=side==='SELL'?m.bearFVG:m.bullFVG;
  if(!sweep)return null;score+=27;reasons.push(side==='SELL'?'buy side liquidity swept':'sell side liquidity swept');
  var locOk=side==='SELL'?m.price>=m.eq:m.price<=m.eq;if(locOk){score+=10;reasons.push(side==='SELL'?'premium location':'discount location')}else score-=10;
  var nearL=Math.abs(m.price-liq.p)<=m.av*.42;if(nearL){score+=12;reasons.push('entry still close to swept liquidity')}else score-=18;
  if(v26touch(m.price,zone,m.av,.28)){score+=15;reasons.push('order block interaction')}else if(zone&&Math.abs(m.price-zone.mid)<=m.av*.45){score+=8;reasons.push('near order block')}
  if(v26touch(m.price,fvg,m.av,.20)){score+=8;reasons.push('fair value gap confluence')}
  if(micro.reject){score+=10;reasons.push('micro rejection')}
  if(micro.mss){score+=15;reasons.push('micro market structure shift')}
  if(sg*micro.impulse>.10){score+=8;reasons.push('micro displacement started')}
  if(flow.total>0&&sg*flow.imbalance>.06){score+=8;reasons.push('live taker flow turned')}
  else if(flow.total>0&&sg*flow.imbalance<-.10)score-=12;
  if(m.bias===sg){score+=4;reasons.push('higher timeframe supports')}else score-=3;
  if(score<78)return null;
  return v26candidate(side,'ICT LIQUIDITY REVERSAL',score,reasons,82,m,{sweepLevel:liq.p,idealZone:zone||fvg,level:liq.p,microMSS:micro.mss});
}
function v26continuation(side,m){
  var sg=v26sg(side);if(m.bias!==sg)return null;var zone=side==='BUY'?m.bullOB:m.bearOB,fvg=side==='BUY'?m.bullFVG:m.bearFVG;if(!zone&&!fvg)return null;
  var micro=v26microState(side,m.av),flow=micro.flow,reasons=[],score=18,locOk=side==='BUY'?m.price<=m.eq:m.price>=m.eq,zt=v26touch(m.price,zone,m.av,.18),ft=v26touch(m.price,fvg,m.av,.15);
  reasons.push('higher timeframe structure aligned');if(locOk){score+=12;reasons.push(side==='BUY'?'discount pullback':'premium pullback')}else score-=8;if(m.ote){score+=8;reasons.push('OTE 62 to 79 retracement')}
  if(zt){score+=24;reasons.push('order block mitigation')}else if(zone&&v26zoneDistance(m.price,zone)<=m.av*.32){score+=12;reasons.push('approaching order block')}
  if(ft){score+=13;reasons.push('fair value gap mitigation')}
  if(!zt&&!ft)return null;
  if(micro.reject){score+=10;reasons.push('micro rejection from zone')}
  if(micro.mss){score+=13;reasons.push('micro structure resumed')}
  if(sg*micro.impulse>.06){score+=8;reasons.push('micro impulse resumed')}
  if(flow.total>0&&sg*flow.imbalance>.04){score+=8;reasons.push('live flow aligned')}else if(flow.total>0&&sg*flow.imbalance<-.10)score-=12;
  if(score<76)return null;
  return v26candidate(side,'ICT OB FVG CONTINUATION',score,reasons,80,m,{idealZone:zone||fvg,level:zone?zone.mid:(fvg?fvg.mid:null),microMSS:micro.mss});
}
function v26late(c,m){
  if(!c||!m)return false;var p=m.price,av=m.av;
  if(c.ict){var z=c.idealZone;if(z&&v26zoneDistance(p,z)>av*.38)return true;if(c.sweepLevel&&Math.abs(p-c.sweepLevel)>av*.55)return true;return false}
  var zone=c.side==='BUY'?(m.bullOB||m.bullFVG):(m.bearOB||m.bearFVG);if(zone&&v26zoneDistance(p,zone)>av*.58)return true;
  return fal