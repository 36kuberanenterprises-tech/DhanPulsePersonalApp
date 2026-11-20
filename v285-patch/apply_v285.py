from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.8.4 Full Data Recovery','Version 2.8.5 Unified Runtime Gate')
s=s.replace('DhanPulse Version 2.8.4 Full Data Recovery.','DhanPulse Version 2.8.5 Unified Runtime Gate.')
s=s.replace('DhanPulse Version 2.8.4 Full Data Recovery','DhanPulse Version 2.8.5 Unified Runtime Gate')

# Missing Delta fields must remain unavailable, never silently become numeric zero.
s=s.replace(
    "function v283num(v){var n=Number(v);return Number.isFinite(n)?n:null}",
    "function v283num(v){if(v===null||v===undefined||v==='')return null;var n=Number(v);return Number.isFinite(n)?n:null}"
)
s=s.replace(
    "var prev=v283num(S.lastCtxOI),oi=v283num(d.openInterest),delta=(prev&&oi!=null)?(oi-prev)/prev*100:0;",
    "var prev=v283num(S.lastCtxOI),oi=v283num(d.openInterest),delta=(prev!=null&&prev>0&&oi!=null)?(oi-prev)/prev*100:null;"
)

# Final visible wording must not expose retired engine generations.
for a,b in [
    ('V2.3 Research Auto','Unified Signal Engine'),
    ('V2.2 SIGNALS','LIVE SIGNALS'),
    ('V2.2 Signals','Live Signals'),
    ('V2.2 QUALITY ENGINE','UNIFIED SIGNAL ENGINE'),
    ('V2.2 quality engine','unified signal engine'),
    ('No V2.2 signals recorded yet.','No live signals recorded yet.'),
    ('Delta Account Verification','Delta Account'),
    ('News engine starting','Delta market context active'),
]:
    s=s.replace(a,b)

css=r'''
/* V2.8.5 Unified Runtime Gate */
.v285-readiness{margin-top:10px;padding:10px 12px;border:1px solid #303844;border-radius:12px;background:#13181e}
.v285-readiness.ok{border-color:rgba(34,197,94,.45)}
.v285-readiness.warn{border-color:rgba(245,158,11,.45)}
.v285-readiness.bad{border-color:rgba(239,68,68,.45)}
.v285-readiness .v285-title{font-size:10px;font-weight:800;letter-spacing:.04em}
.v285-readiness .v285-note{font-size:9px;color:#8995a3;line-height:1.45;margin-top:4px}
.v285-readiness .v285-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;margin-top:8px}
.v285-readiness .v285-grid>div{padding:7px;border:1px solid #2a323c;border-radius:8px;background:#11161b}
.v285-readiness span{display:block;font-size:7px;color:#74808c;text-transform:uppercase}
.v285-readiness b{display:block;font-size:9px;margin-top:3px}
@media(max-width:680px){.v285-readiness .v285-grid{grid-template-columns:1fr 1fr}}
'''
if 'V2.8.5 Unified Runtime Gate */' not in s:
    s=s.replace('</style>',css+'\n</style>',1)

js=r'''
/* V2.8.5 Unified Runtime Gate.
   Indicators may calculate while history is warming, but BUY/SELL publication is blocked
   until selected TF, 1m trigger, HTF, live tick and Delta context are all usable. */
var V285={version:'2.8.5',installed:false,lastReason:'STARTING',lastKey:'',lastReady:false};
if(typeof V284!=='undefined')V284.version='2.8.5';
if(typeof V283!=='undefined')V283.version='2.8.5';

function v285el(id){return document.getElementById(id)}
function v285n(v){if(v===null||v===undefined||v==='')return null;var x=Number(v);return Number.isFinite(x)?x:null}
function v285age(ts){
  var x=v285n(ts);if(x==null||x<=0)return Infinity;
  if(x<100000000000)x*=1000;
  return Math.max(0,Date.now()-x);
}
function v285tfMs(tf){
  return ({'1m':60000,'3m':180000,'5m':300000,'15m':900000,'30m':1800000,'1h':3600000,'2h':7200000,'4h':14400000,'6h':21600000,'1d':86400000,'1w':604800000})[String(tf||'5m')]||300000;
}
function v285Readiness(){
  try{
    var selected=(S&&S.candles&&S.candles.length)||0;
    var micro=(S&&S.microCandles&&S.microCandles.length)||0;
    var htf=(S&&S.htfCandles&&S.htfCandles.length)||0;
    var price=v285n(S&&S.livePrice);
    var tickAge=v285age(S&&S.lastMarketEventAt);
    var contextAge=(typeof V283!=='undefined'&&V283.lastContextAt)?Math.max(0,Date.now()-V283.lastContextAt):Infinity;
    var last=S&&S.candles&&S.candles.length?S.candles[S.candles.length-1]:null;
    var candleAge=last?v285age(last.t):Infinity;
    var candleFresh=candleAge<=Math.max(v285tfMs(S&&S.tf)*2.5,180000);
    var dataReady=selected>=60&&micro>=60&&htf>=40;
    var liveReady=price!=null&&price>0&&tickAge<=8000;
    var contextReady=contextAge<=25000;
    var analysisReady=!!(S&&S.analysis&&v285n(S.analysis.atr)!=null);
    var ready=dataReady&&liveReady&&contextReady&&candleFresh&&analysisReady;
    var reasons=[];
    if(selected<60)reasons.push('selected history '+selected+'/60');
    if(micro<60)reasons.push('1m history '+micro+'/60');
    if(htf<40)reasons.push('HTF history '+htf+'/40');
    if(!candleFresh)reasons.push('selected candle stale');
    if(!liveReady)reasons.push('live Delta tick stale');
    if(!contextReady)reasons.push('Delta context stale');
    if(!analysisReady)reasons.push('indicator engine warming');
    return {ready:ready,selected:selected,micro:micro,htf:htf,tickAge:tickAge,contextAge:contextAge,candleAge:candleAge,reasons:reasons};
  }catch(e){return{ready:false,selected:0,micro:0,htf:0,tickAge:Infinity,contextAge:Infinity,candleAge:Infinity,reasons:['runtime state unavailable']}}
}
function v285Wait(reason){
  var card=v285el('decisionCard'),decision=v285el('decision'),score=v285el('score'),stage=v285el('stage'),why=v285el('reason'),pdir=v285el('pdir');
  if(card)card.className='panel decision wait';
  if(decision)decision.textContent='WAIT';
  if(score)score.textContent='Readiness gate';
  if(stage)stage.textContent='DATA NOT READY';
  if(why)why.textContent=reason||'Waiting for complete Delta market data';
  if(pdir)pdir.textContent='WAIT';
  ['entry','sl','t1','t2','t3'].forEach(function(id){var e=v285el(id);if(e)e.textContent='—'});
}
function v285InstallPanel(){
  if(v285el('v285Readiness'))return;
  var first=document.querySelector('.app > .panel');if(!first)return;
  var box=document.createElement('div');box.id='v285Readiness';box.className='v285-readiness warn';
  box.innerHTML='<div class="v285-title">Unified Data Readiness</div><div id="v285ReadinessNote" class="v285-note">Checking Delta market pipeline</div>'+
    '<div class="v285-grid"><div><span>Selected TF</span><b id="v285Sel">0</b></div><div><span>1m Trigger</span><b id="v285Micro">0</b></div>'+
    '<div><span>Higher TF</span><b id="v285Htf">0</b></div><div><span>Live Feed</span><b id="v285Live">WAIT</b></div></div>';
  first.appendChild(box);
}
function v285RenderReadiness(){
  v285InstallPanel();
  var r=v285Readiness(),box=v285el('v285Readiness'),note=v285el('v285ReadinessNote');
  if(box)box.className='v285-readiness '+(r.ready?'ok':(r.tickAge===Infinity?'bad':'warn'));
  if(v285el('v285Sel'))v285el('v285Sel').textContent=r.selected;
  if(v285el('v285Micro'))v285el('v285Micro').textContent=r.micro;
  if(v285el('v285Htf'))v285el('v285Htf').textContent=r.htf;
  if(v285el('v285Live'))v285el('v285Live').textContent=r.tickAge===Infinity?'WAIT':(r.tickAge<=8000?'LIVE':'STALE');
  if(note)note.textContent=r.ready?'READY · signal publication enabled':('WAIT · '+r.reasons.join(' · '));
  V285.lastReady=r.ready;V285.lastReason=r.reasons.join(' · ');
  if(!r.ready)v285Wait(V285.lastReason);
  return r;
}
function v285CleanText(){
  document.querySelectorAll('b,strong,div,span').forEach(function(e){
    if(e.children&&e.children.length)return;
    var t=(e.textContent||'').trim();
    if(t==='V2.3 Research Auto')e.textContent='Unified Signal Engine';
    if(t==='V2.2 SIGNALS'||t==='V2.2 Signals')e.textContent='LIVE SIGNALS';
    if(t==='No V2.2 signals recorded yet.')e.textContent='No live signals recorded yet.';
    if(t==='Feed Latency')e.textContent='Local Event Delay';
    if(t==='Total Observed')e.textContent='Local Processing Total';
  });
  var low=document.querySelectorAll('.panel h2');
  low.forEach(function(h){
    if((h.textContent||'').trim()==='Low Latency Engine'){
      var p=h.parentElement&&h.parentElement.querySelector('.muted.small');
      if(p)p.textContent='Measures DhanPulse processing after an event reaches the phone. It does not measure exchange to internet network latency.';
    }
  });
  var nh=v285el('newsHeadline');if(nh&&/news engine starting/i.test(nh.textContent||''))nh.textContent='Delta market context active';
}
function v285AccurateLatency(){
  try{
    if(S&&v285n(S.feedLatencyMs)===0&&v285n(S.lastMarketExchangeAt)==null)S.feedLatencyMs=null;
    if(S&&v285n(S.totalLatencyMs)!=null&&v285n(S.engineMs)!=null&&v285n(S.feedLatencyMs)==null)S.totalLatencyMs=S.engineMs;
  }catch(e){}
}
function v285ContextLabels(){
  try{
    var ctx=S&&S.ctx||{},v=v285n(ctx.quoteVolume24h),chg=v285n(ctx.priceChangePercent24h),obi=v285n(ctx.orderBookImbalance),oiChg=v285n(ctx.oiDeltaPct);
    var buyPct=obi==null?null:Math.max(0,Math.min(100,(1+obi)*50)),sellPct=buyPct==null?null:100-buyPct;
    document.querySelectorAll('.context>div').forEach(function(row){
      var sp=row.querySelector('span'),b=row.querySelector('b');if(!sp||!b)return;
      var label=(sp.textContent||'').trim().toUpperCase();
      if(label==='24 HOUR VOLUME'||label==='24 HOUR TURNOVER'){
        sp.textContent='24 HOUR TURNOVER';
        b.textContent=v==null?'NA':(v>=1000000000?(v/1000000000).toFixed(2)+'B USD':v>=1000000?(v/1000000).toFixed(2)+'M USD':Math.round(v).toLocaleString()+' USD');
      }
      if(label==='ORDER BOOK'){
        b.textContent=buyPct==null?'NA':('Buy '+buyPct.toFixed(1)+'% · Sell '+sellPct.toFixed(1)+'%');
        b.className=obi==null?'neutral':obi>.05?'bull':obi<-.05?'bear':'neutral';
      }
      if(label==='OPEN INTEREST CHANGE'&&oiChg==null){b.textContent='NA';b.className='neutral'}
      if(label==='24 HOUR'&&chg==null){b.textContent='NA';b.className='neutral'}
    });
  }catch(e){}
}
function v285GateLegacy(){
  if(typeof v24select==='function'&&!v24select.__v285){
    var old=v24select;
    var wrapped=function(){
      var r=v285Readiness();
      if(!r.ready)return{candidate:null,reason:'WAIT: '+r.reasons.join(' · '),regime:(typeof v23regime==='function'?v23regime():null)};
      return old.apply(this,arguments);
    };
    wrapped.__v285=true;v24select=wrapped;
  }
  if(typeof v263select==='function'&&!v263select.__v285){
    var old2=v263select;
    var wrapped2=function(){
      var r=v285Readiness();
      if(!r.ready){
        try{if(typeof v263render==='function')v263render(null,null,null,'WAIT: '+r.reasons.join(' · '))}catch(e){}
        return null;
      }
      return old2.apply(this,arguments);
    };
    wrapped2.__v285=true;v263select=wrapped2;
  }
}
function v285AlignChart(){
  try{
    if(!S||!S.candles||!S.candles.length)return;
    var last=S.candles[S.candles.length-1],lp=v285n(S.livePrice),lc=last?v285n(last.c):null,atr=S.analysis?v285n(S.analysis.atr):null;
    if(lp!=null&&lc!=null&&atr!=null&&atr>0&&Math.abs(lp-lc)>Math.max(atr*3,lp*.015)){
      v285Wait('WAIT: live price and selected candle history are not aligned');
      V285.lastReady=false;V285.lastReason='live price and selected candle history are not aligned';
    }
    if(S.chartView){S.chartView.rightOffset=0;if(!S.chartView.visible||S.chartView.visible<40)S.chartView.visible=Math.min(80,S.candles.length)}
  }catch(e){}
}
function v285Cycle(){
  v285GateLegacy();v285CleanText();v285AccurateLatency();v285ContextLabels();v285AlignChart();v285RenderReadiness();
}
setTimeout(function(){V285.installed=true;v285Cycle()},700);
setInterval(v285Cycle,1000);
'''
if 'V2.8.5 Unified Runtime Gate.' not in s:
    s=s.replace('\n})();\n</script>',js+'\n})();\n</script>',1)

idx.write_text(s)

# Correct the generated Delta repair client after V2.8.4.
repair=root/'app/src/main/java/com/dhanpulse/cryptofxv11/DeltaDataRepair.java'
if repair.exists():
    jt=repair.read_text()
    jt=jt.replace(
        'putNumber(out, "ltpChange24h", t.opt("ltp_change_24h"));',
        'putNumber(out, "ltpChange24h", t.opt("ltp_change_24h"));\n            putNumber(out, "tickerTimestamp", t.opt("timestamp"));'
    )
    repair.write_text(jt)

# Update native identifiers.
for p in [
    root/'app/src/main/java/com/dhanpulse/cryptofxv11/DeltaDataRepair.java',
    root/'app/src/main/java/com/dhanpulse/cryptofxv11/DeltaBackendAccount.java',
    root/'app/src/main/java/com/dhanpulse/cryptofxv11/FlattradeBackend.java',
    root/'app/src/main/java/com/dhanpulse/cryptofxv11/DhanPulseMonitorService.java'
]:
    if p.exists():
        t=p.read_text()
        t=re.sub(r'DhanPulse-Android/2\.[0-9.]+','DhanPulse-Android/2.8.5',t)
        p.write_text(t)

b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 53',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.8.5"',bs,count=1)
b.write_text(bs)
