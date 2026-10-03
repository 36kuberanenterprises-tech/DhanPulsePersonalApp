from pathlib import Path
import re

root = Path('crypto-forex-app/buildsrc')
idx = root / 'app/src/main/assets/index.html'
s = idx.read_text()

# Keep V2.6 as the stable Android app identity and move trade records to a permanent master key.
s = s.replace('Version 2.6 ICT Early Structure', 'Version 2.6.1 History Preserved')
s = s.replace('DhanPulse Crypto and Forex Version 2.6 ICT Early Structure.', 'DhanPulse Crypto and Forex Version 2.6.1 History Preserved.')
s = s.replace('var TRKEY="dhanpulse_cf_android_trades_v26"', 'var TRKEY="dhanpulse_cf_android_trades_master"')
s = s.replace('V2.6 Signals', 'All Preserved Signals')
s = s.replace('No V2.6 signals recorded yet.', 'No signals recorded yet.')

history_panel = r'''
<div class="panel" id="historyLab">
  <div class="row"><div><h2>Strategy Backtest History</h2><div class="muted small">Trade records are preserved across app updates. Old entries remain available for strategy comparison and backtesting.</div></div><b id="historyCount">0 records</b></div>
  <div id="historySummary" class="muted small" style="margin:10px 0 12px">Building historical strategy summary</div>
  <div class="table"><table><thead><tr><th>Version</th><th>Strategy</th><th>Closed</th><th>Wins</th><th>Losses</th><th>Win Rate</th><th>Net R</th><th>Profit Factor</th></tr></thead><tbody id="historyRows"></tbody></table></div>
</div>
'''
if 'id="historyLab"' not in s:
    anchor = '<div class="panel" id="ictStructure">'
    if anchor not in s:
        raise SystemExit('ICT panel anchor missing')
    s = s.replace(anchor, history_panel + '\n' + anchor, 1)

js = r'''
/* V2.6.1 permanent history preservation.
   From this version onward the app keeps one stable Android package and one permanent
   master trade store. Version specific records are migrated, tagged and retained.
   The old storage keys are deliberately NOT deleted. */
var V261={version:'2.6.1',archiveKey:'dhanpulse_cf_android_trade_archive_master',legacyKeys:[
  'dhanpulse_cf_android_trades_v1','dhanpulse_cf_android_trades_v22','dhanpulse_cf_android_trades_v23',
  'dhanpulse_cf_android_trades_v24','dhanpulse_cf_android_trades_v25','dhanpulse_cf_android_trades_v251',
  'dhanpulse_cf_android_trades_v26','dhanpulse_cf_android_trades_master'
]};
function v261read(key){try{var x=JSON.parse(localStorage.getItem(key)||'[]');return Array.isArray(x)?x:[]}catch(e){return[]}}
function v261versionFromKey(key){
  if(key.indexOf('v251')>=0)return'2.5.1';if(key.indexOf('v26')>=0)return'2.6.0';
  if(key.indexOf('v25')>=0)return'2.5';if(key.indexOf('v24')>=0)return'2.4';
  if(key.indexOf('v23')>=0)return'2.3';if(key.indexOf('v22')>=0)return'2.2';
  if(key.indexOf('v1')>=0)return'legacy';return'unknown';
}
function v261id(t){
  if(t&&t.id)return String(t.id);
  return [t&&t.createdAt||0,t&&t.market||'',t&&t.symbol||'',t&&t.tf||'',t&&t.side||'',
    finite(t&&t.entry)?Number(t.entry).toFixed(8):'',t&&t.strategy||t&&t.stage||''].join('|');
}
function v261merge(groups){
  var out=[],seen={};
  (groups||[]).forEach(function(g){
    var key=g.key||'',ver=v261versionFromKey(key);
    (g.list||[]).forEach(function(raw){
      if(!raw||typeof raw!=='object')return;
      var t=raw,id=v261id(t);if(seen[id])return;seen[id]=1;
      if(!t.sourceVersion)t.sourceVersion=ver;
      out.push(t);
    });
  });
  out.sort(function(a,b){return num(a.createdAt)-num(b.createdAt)});
  return out;
}
function v261migrate(){
  var groups=[];
  V261.legacyKeys.forEach(function(k){groups.push({key:k,list:v261read(k)})});
  groups.push({key:'archive',list:v261read(V261.archiveKey)});
  var all=v261merge(groups);
  try{localStorage.setItem(TRKEY,JSON.stringify(all));localStorage.setItem(V261.archiveKey,JSON.stringify(all))}catch(e){}
  return all;
}
function v261all(){return v261merge([{key:'master',list:v261read(TRKEY)},{key:'archive',list:v261read(V261.archiveKey)}])}
function v261win(t){if(finite(t.pnlR))return t.pnlR>0;var r=String(t.result||'').toUpperCase();return r==='T3'||r==='T2 PROTECTED'||r==='T1 PROTECTED'}
function v261loss(t){if(finite(t.pnlR))return t.pnlR<0;return String(t.result||'').toUpperCase()==='SL'}
function v261renderHistory(){
  var all=v261all(),hc=q('historyCount'),hs=q('historySummary'),body=q('historyRows');
  if(hc)hc.textContent=all.length+' records';
  if(!body)return;
  var groups={};
  all.forEach(function(t){
    var ver=t.sourceVersion||'unknown',st=t.strategy||t.stage||'UNSPECIFIED',key=ver+'|'+st;
    if(!groups[key])groups[key]={ver:ver,st:st,closed:0,w:0,l:0,pos:0,neg:0,net:0,last:0};
    var g=groups[key];g.last=Math.max(g.last,num(t.createdAt));
    if(t.status==='CLOSED'&&String(t.result||'').toUpperCase()!=='AMBIGUOUS'){
      g.closed++;if(v261win(t))g.w++;if(v261loss(t))g.l++;
      var r=finite(t.pnlR)?num(t.pnlR):v261win(t)?1:v261loss(t)?-1:0;g.net+=r;if(r>0)g.pos+=r;if(r<0)g.neg+=Math.abs(r);
    }
  });
  var arr=Object.keys(groups).map(function(k){return groups[k]}).sort(function(a,b){return b.last-a.last});
  body.innerHTML=arr.slice(0,60).map(function(g){var wr=g.closed?g.w/g.closed*100:0,pf=g.neg?g.pos/g.neg:(g.pos?99:0);return '<tr><td>'+g.ver+'</td><td>'+g.st+'</td><td>'+g.closed+'</td><td>'+g.w+'</td><td>'+g.l+'</td><td>'+wr.toFixed(1)+'%</td><td>'+g.net.toFixed(2)+'R</td><td>'+pf.toFixed(2)+'</td></tr>'}).join('')||'<tr><td colspan="8">No closed historical trades yet</td></tr>';
  var closed=all.filter(function(t){return t.status==='CLOSED'&&String(t.result||'').toUpperCase()!=='AMBIGUOUS'}),wins=closed.filter(v261win).length,losses=closed.filter(v261loss).length;
  if(hs)hs.textContent='Preserved '+all.length+' total signals · '+closed.length+' resolved · '+wins+' profitable · '+losses+' losing. History is never automatically deleted.';
}

v261migrate();

/* Wrap the existing save function. New trades are tagged with their engine version and
   every save is mirrored to the append only archive before the UI is refreshed. */
var __v261Save=save;
save=function(list){
  list=Array.isArray(list)?list:[];
  list.forEach(function(t){if(t&&!t.sourceVersion)t.sourceVersion=V261.version});
  var merged=v261merge([{key:'archive',list:v261read(V261.archiveKey)},{key:'master',list:list}]);
  try{localStorage.setItem(V261.archiveKey,JSON.stringify(merged))}catch(e){}
  __v261Save(merged);
  setTimeout(v261renderHistory,0);
};

/* The old destructive Clear Records control is disabled. Old trades are research data. */
setTimeout(function(){
  try{
    var b=q('clear');
    if(b){b.textContent='History Protected';b.disabled=true;b.title='Trade history is preserved for strategy backtesting';}
    v261migrate();
    if(typeof renderTrades==='function')renderTrades();
    v261renderHistory();
  }catch(e){}
},0);
setInterval(v261renderHistory,5000);
'''

if 'V2.6.1 permanent history preservation.' not in s:
    s = s.replace('</script>', js + '\n</script>', 1)
idx.write_text(s)

# IMPORTANT: keep the same package as V2.6 so this installs as an update and retains
# Android WebView localStorage. Only version code/name advance.
b = root / 'app/build.gradle.kts'
bs = b.read_text()
bs = re.sub(r'applicationId\s*=\s*"[^"]+"', 'applicationId = "com.dhanpulse.cryptofxresearchv260"', bs, count=1)
bs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 32', bs, count=1)
bs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.6.1"', bs, count=1)
b.write_text(bs)
