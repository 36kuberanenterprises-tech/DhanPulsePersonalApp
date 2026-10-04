from pathlib import Path
import re

root = Path('crypto-forex-app/buildsrc')
idx = root / 'app/src/main/assets/index.html'
s = idx.read_text()

s = s.replace('Version 2.6.4 Clear Trade Gate', 'Version 2.6.5 Live Trade Clarity')
s = s.replace('DhanPulse Crypto and Forex Version 2.6.4 Clear Trade Gate.', 'DhanPulse Crypto and Forex Version 2.6.5 Live Trade Clarity.')
s = s.replace('<h2>Recorded Signal Performance</h2>', '<h2>Live Signal Performance</h2>', 1)
s = s.replace(
  'This stable app line keeps one permanent history store for future updates. The known V2.6 BTCUSDT 5m liquidity SELL loss is imported once as legacy research data so the strategy backtest does not start from zero.',
  'This stable app line keeps one permanent history store for future updates. Legacy imported records are kept only in Strategy Backtest History and are never counted as new live trades.'
)
if 'id="livePerfNote"' not in s:
    needle = '<div class="muted small">T1, T2, T3 and SL are checked live on incoming market ticks. Candle data is used as backup.</div>'
    if needle in s:
        s = s.replace(needle, needle + '\n  <div id="livePerfNote" class="muted small" style="margin-top:6px"></div>', 1)

js = r'''
/* V2.6.5 Live Trade Clarity.
   Legacy imported research rows remain preserved for historical comparison, but they are
   excluded from live performance, live loss brakes, live cooldowns and the live trade table.
   New publications are refused unless every price field is a valid positive market price. */
if(typeof V261!=='undefined')V261.version='2.6.5';
if(typeof V26!=='undefined')V26.version='2.6.5';
if(typeof V263!=='undefined')V263.version='2.6.5';
if(typeof V264!=='undefined')V264.version='2.6.5';
var V265={version:'2.6.5'};

function v265LiveTrades(){
  return trades().filter(function(t){return t&&!t.legacyImported});
}
function v265LegacyTrades(){
  return trades().filter(function(t){return t&&t.legacyImported});
}

/* Historical seed must never influence current adaptive strategy behaviour. */
v23closed=function(){
  return v265LiveTrades().filter(function(t){return t.status==='CLOSED'});
};

function v265ResultLabel(t){
  var r=String((t&&t.resultDisplay)|| (t&&t.result) || '').toUpperCase();
  if(r==='SL')return'SL HIT';
  if(r==='T3')return'TARGET 3 HIT';
  if(r==='T2 PROTECTED')return'TARGET 2 HIT · PROFIT PROTECTED';
  if(r==='T1 PROTECTED')return'TARGET 1 HIT · PROFIT PROTECTED';
  if(r==='TIME EXIT')return'TIME EXIT';
  if(r==='AMBIGUOUS')return'AMBIGUOUS BACKUP';
  if(r==='OPEN'){
    if(t&&t.h2)return'TARGET 2 HIT · RUNNING';
    if(t&&t.h1)return'TARGET 1 HIT · RUNNING';
    return'OPEN';
  }
  return r||'OPEN';
}

function v265ValidPlan(p){
  if(!p)return false;
  var vals=[p.entry,p.sl,p.t1,p.t2,p.t3,p.risk];
  if(!vals.every(function(x){return finite(x)&&Number(x)>0}))return false;
  if(Math.abs(p.entry-p.sl)<1e-9)return false;
  if(p.direction==='BUY' && !(p.sl<p.entry&&p.t1>p.entry&&p.t2>p.t1&&p.t3>p.t2))return false;
  if(p.direction==='SELL' && !(p.sl>p.entry&&p.t1<p.entry&&p.t2<p.t1&&p.t3<p.t2))return false;
  return true;
}
var __v265Publish=v24publish;
v24publish=function(c,sel){
  var p;
  try{p=v24plan(c)}catch(e){p=null}
  if(!v265ValidPlan(p)){
    V24.candidate=null;
    if(typeof V263!=='undefined')V263.lastGate='BLOCK: invalid price plan';
    if(q('oppGate'))q('oppGate').textContent='BLOCK: invalid price plan';
    if(q('stage'))q('stage').textContent='WAIT: invalid Entry / SL / target plan';
    return;
  }
  __v265Publish(c,sel);
};

renderTrades=function(){
  renderTradeLogState(true);
  var live=v265LiveTrades().slice().reverse(),legacy=v265LegacyTrades(),tot=live.length;
  var closed=live.filter(function(t){return t.status==='CLOSED'});
  var resolved=closed.filter(function(t){return String(t.result||'').toUpperCase()!=='AMBIGUOUS'&&finite(t.pnlR)});
  var amb=closed.filter(function(t){return String(t.result||'').toUpperCase()==='AMBIGUOUS'}).length;
  var prof=resolved.filter(function(t){return t.pnlR>0}).length,loss=resolved.filter(function(t){return t.pnlR<0}).length;
  var open=live.filter(function(t){return t.status==='OPEN'}).length;
  var h1=live.filter(function(t){return t.h1}).length,h2=live.filter(function(t){return t.h2}).length,h3=live.filter(function(t){return t.h3}).length;
  var net=resolved.reduce(function(z,t){return z+num(t.pnlR)},0),avg=resolved.length?net/resolved.length:0;
  var gp=resolved.filter(function(t){return t.pnlR>0}).reduce(function(z,t){return z+num(t.pnlR)},0);
  var gl=Math.abs(resolved.filter(function(t){return t.pnlR<0}).reduce(function(z,t){return z+num(t.pnlR)},0));
  var pf=gl?gp/gl:(gp>0?99:0),pc=function(n,d){return d?((n/d)*100).toFixed(1)+'%':'0.0%'};
  if(q('perf'))q('perf').innerHTML=
    '<div><span>Live Signals</span><b>'+tot+'</b></div>'+
    '<div><span>Resolved Closed</span><b>'+resolved.length+'</b></div>'+
    '<div><span>Profit Rate</span><b>'+pc(prof,resolved.length)+'</b></div>'+
    '<div><span>Loss Rate</span><b>'+pc(loss,resolved.length)+'</b></div>'+
    '<div><span>Net R</span><b>'+net.toFixed(2)+'R</b></div>'+
    '<div><span>Average R</span><b>'+avg.toFixed(3)+'R</b></div>'+
    '<div><span>Profit Factor</span><b>'+pf.toFixed(2)+'</b></div>'+
    '<div><span>T1 Touch Rate</span><b>'+pc(h1,tot)+'</b></div>'+
    '<div><span>T2 Touch Rate</span><b>'+pc(h2,tot)+'</b></div>'+
    '<div><span>T3 Full Hit</span><b>'+pc(h3,tot)+'</b></div>'+
    '<div><span>Ambiguous Backup</span><b>'+amb+'</b></div>'+
    '<div><span>Open Signals</span><b>'+open+'</b></div>';
  if(q('livePerfNote'))q('livePerfNote').textContent=legacy.length?
    'Live statistics exclude '+legacy.length+' legacy research record'+(legacy.length===1?'':'s')+'. Legacy records remain preserved in Strategy Backtest History below.':
    'Only genuine live signals from this app line are counted here.';
  if(q('trades')){
    q('trades').innerHTML=live.slice(0,100).map(function(t){
      var d=finite(t.entry)?dec(t.entry):2;
      var label=(t.strategy||t.stage||'V2.6.5')+(finite(t.quality)?' Q'+t.quality:'')+(finite(t.pnlR)?' · '+Number(t.pnlR).toFixed(2)+'R':'');
      return '<tr><td>'+new Date(t.createdAt).toLocaleString('en-IN')+'</td><td>'+t.market+'</td><td>'+t.symbol+'</td><td>'+t.tf+'</td><td>'+t.side+'<br><small>'+label+'</small></td>'+
        '<td>'+(finite(t.entry)&&t.entry>0?fmt(t.entry,d):'INVALID')+'</td>'+
        '<td>'+(finite(t.sl)&&t.sl>0?fmt(t.sl,d):'INVALID')+'</td>'+
        '<td>'+(finite(t.t1)&&t.t1>0?fmt(t.t1,d):'INVALID')+'</td>'+
        '<td>'+(finite(t.t2)&&t.t2>0?fmt(t.t2,d):'INVALID')+'</td>'+
        '<td>'+(finite(t.t3)&&t.t3>0?fmt(t.t3,d):'INVALID')+'</td>'+
        '<td>'+t.status+'</td><td>'+v265ResultLabel(t)+'</td></tr>';
    }).join('') || '<tr><td colspan="12">No live trades recorded yet. Legacy research records are shown only in Strategy Backtest History.</td></tr>';
  }
};

setTimeout(function(){renderTrades();if(typeof v261renderHistory==='function')v261renderHistory()},300);
'''
if 'V2.6.5 Live Trade Clarity.' not in s:
    s = s.replace('\n})();\n</script>', js + '\n})();\n</script>', 1)
else:
    raise SystemExit('V2.6.5 already present')
idx.write_text(s)

b = root / 'app/build.gradle.kts'
bs = b.read_text()
bs = re.sub(r'applicationId\s*=\s*"[^"]+"', 'applicationId = "com.dhanpulse.cryptofxstablev263"', bs, count=1)
bs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 36', bs, count=1)
bs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.6.5"', bs, count=1)
b.write_text(bs)
