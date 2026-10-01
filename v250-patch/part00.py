from pathlib import Path
import re

root = Path('crypto-forex-app/buildsrc')
idx = root / 'app/src/main/assets/index.html'
s = idx.read_text()

s = s.replace('Version 2.4 Precision Fast', 'Version 2.5 News Intelligence Lab')
s = s.replace('DhanPulse Crypto and Forex Version 2.4 Precision Fast.', 'DhanPulse Crypto and Forex Version 2.5 News Intelligence Lab.')
s = s.replace('var TRKEY="dhanpulse_cf_android_trades_v24"', 'var TRKEY="dhanpulse_cf_android_trades_v25"')
s = s.replace('V2.4 Signals', 'V2.5 Signals')
s = s.replace('No V2.4 signals recorded yet.', 'No V2.5 signals recorded yet.')
s = s.replace('(t.strategy||t.stage||"V2.4")', '(t.strategy||t.stage||"V2.5")')

panel = r'''
<div class="panel" id="newsIntel">
  <div class="row">
    <div>
      <h2>News and Candle Intelligence</h2>
      <div class="muted small">Fresh market headlines are compared with live candle reaction, volume, flow, regime and strategy consensus. News never creates a trade by itself.</div>
    </div>
    <button id="newsRefresh" class="secondary">Refresh News</button>
  </div>
  <div id="newsPerf" class="perf" style="margin-top:12px"></div>
  <div id="newsHeadline" class="muted small" style="margin-top:10px">News engine starting</div>
  <h3 style="margin-top:16px">Background Shadow Test</h3>
  <div class="muted small">The app forward tests Technical, News Filtered and Fusion profiles without sending extra signals. Results are stored separately for comparison.</div>
  <div class="table" style="margin-top:10px"><table><thead><tr><th>Profile</th><th>Closed</th><th>Win Rate</th><th>Net R</th><th>Profit Factor</th></tr></thead><tbody id="shadowRows"></tbody></table></div>
  <div id="shadowLeader" class="muted small" style="margin-top:8px"></div>
</div>
'''
marker = '<div class="panel"><h2>XAUUSD and Forex Data Setup</h2>'
if 'id="newsIntel"' not in s:
    if marker not in s:
        raise SystemExit('news panel insertion target missing')
    s = s.replace(marker, panel + marker, 1)

js = r'''
/* V2.5 News Intelligence and Shadow Lab.
   News is supporting context only. Production signals still originate from the V2.4 precision engine.
   High impact conflict can veto a trade, aligned news plus matching candle reaction can support a fast path.
   Three forward shadow profiles continuously compare Technical, News Filtered and Fusion behaviour. */
var V25N={items:[],status:"STARTING",lastFetch:0,lastError:"",lastUrl:"",source:"GDELT",ctx:null};
var V25SHADOWKEY="dhanpulse_v25_shadow_lab";
var V25LASTSHADOW={};
function v25esc(x){return String(x==null?"":x).replace(/[&<>\"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})}
function v25seen(s){var m=String(s||"").match(/^(\d{4})(\d{2})(\d{2})T?(\d{2})(\d{2})(\d{2})/);return m?Date.UTC(+m[1],+m[2]-1,+m[3],+m[4],+m[5],+m[6]):0}
function v25has(t,arr){for(var i=0;i<arr.length;i++)if(t.indexOf(arr[i])>=0)return true;return false}
function v25count(t,arr){var n=0;for(var i=0;i<arr.length;i++)if(t.indexOf(arr[i])>=0)n++;return n}
function v25classify(a){
  var title=String(a&&a.title||""),t=title.toLowerCase(),impact=0;
  var critical=["federal reserve","fomc","cpi","inflation report","payroll","jobs report","sec approval","sec rejects","etf approval","etf rejection","hack","exploit","breach","exchange outage","liquidation cascade","bankruptcy","default","war","attack","sanctions","tariff"];
  var high=["sec","etf","rate cut","rate hike","interest rate","inflation","jobs","payroll","hack","exploit","liquidation","outflow","inflow","lawsuit","regulation","ban","approval","rejection","outage","whale","treasury","yield","dollar"];
  var pos=["approval","approved","inflow","adoption","reserve","rate cut","easing","partnership","launch","upgrade","record high","accumulation","buying","surge","rally","bullish","recovery"];
  var neg=["hack","exploit","breach","lawsuit","charges","ban","outflow","liquidation","collapse","default","seizure","crackdown","rejection","rejected","rate hike","hawkish","war","attack","sanctions","outage","selloff","plunge"];
  var crit=v25has(t,critical),hi=v25count(t,high),p=v25count(t,pos),n=v25count(t,neg);
  if(crit)impact+=4;impact+=Math.min(4,hi);
  var sym=String(S.symbol||"").toUpperCase();
  if((sym.indexOf("BTC")===0&&v25has(t,["bitcoin","btc"]))||(sym.indexOf("ETH")===0&&v25has(t,["ethereum","ether","eth"]))||(sym.indexOf("XAU")===0&&v25has(t,["gold","xau"])))impact+=2;
  if(S.market==="crypto"&&v25has(t,["crypto","cryptocurrency","bitcoin","ethereum"]))impact+=1;
  var bias=p>n?1:n>p?-1:0;
  return{title:title,url:String(a&&a.url||""),domain:String(a&&a.domain||""),seen:v25seen(a&&a.seendate),impact:impact,bias:bias,critical:crit,pos:p,neg:n};
}
function v25query(){
  var sym=String(S.symbol||"").toUpperCase();
  if(sym.indexOf("BTC")===0)return '(bitcoin OR BTC OR cryptocurrency OR crypto OR "Federal Reserve" OR FOMC OR CPI OR inflation OR SEC OR ETF)';
  if(sym.indexOf("ETH")===0)return '(ethereum OR ether OR ETH OR cryptocurrency OR crypto OR "Federal Reserve" OR FOMC OR CPI OR inflation OR SEC OR ETF)';
  if(sym.indexOf("XAU")===0)return '(gold OR XAU OR "Federal Reserve" OR FOMC OR CPI OR inflation OR payroll OR jobs OR dollar OR yields)';
  if(S.market==="forex")return '('+sym.slice(0,3)+' OR '+sym.slice(3,6)+' OR "Federal Reserve" OR FOMC OR CPI OR inflation OR payroll OR jobs OR dollar OR yields)';
  return '(crypto OR bitcoin OR ethereum OR "Federal Reserve" OR FOMC OR CPI OR inflation)';
}
function v25newsUrl(){return 'https://api.gdeltproject.org/api/v2/doc/doc?query='+encodeURIComponent(v25query())+'&mode=ArtList&maxrecords=25&format=json&timespan=30min&sort=HybridRel'}
window.__dhanpulseNewsNative=function(txt){
  try{
    var d=JSON.parse(txt||'{}'),arr=Array.isArray(d.articles)?d.articles:[];
    V25N.items=arr.map(v25classify).filter(function(x){return x.title}).sort(function(a,b){return (b.impact-a.impact)||((b.seen||0)-(a.seen||0))}).slice(0,25);
    V25N.status='LIVE';V25N.lastFetch=Date.now();V25N.lastError='';v25renderNews(v25newsContext(''));
  }catch(e){V25N.status='ERROR';V25N.lastError='parse';v25renderNews(v25newsContext(''))}
};
function v25requestNews(){
  var url=v25newsUrl();V25N.lastUrl=url;V25N.status='REFRESHING';v25renderNews(v25newsContext(''));
  try{
    if(window.DhanPulseNative&&typeof DhanPulseNative.fetchNews==='function'){DhanPulseNative.fetchNews(url);return}
  }catch(e){}
  fetch(url,{cache:'no-store'}).then(function(r){return r.text()}).then(window.__dhanpulseNewsNative).catch(function(e){V25N.status='UNAVAILABLE';V25N.lastError=String(e&&e.message||e);v25renderNews(v25newsContext(''))});
}
function v25newsContext(side){
  var now=Date.now(),recent=(V25N.items||[]).filter(function(x){return !x.seen||now-x.seen<=45*60000}),hi=recent.filter(function(x){return x.impact>=3}),pos=0,neg=0,total=0,crit=false;
  hi.forEach(function(x){total+=x.impact;if(x.bias>0)pos+=x.impact;if(x.bias<0)neg+=x.impact;if(x.critical&&(!x.seen||now-x.seen<=20*60000))crit=true});
  var bias=pos-neg>=3?1:neg-pos>=3?-1:0,mixed=pos>=3&&neg>=3&&Math.abs(pos-neg)<Math.max(4,(pos+neg)*.35),mc=v23micro(),reaction=num(mc.impulse||0),sg=side==="BUY"?1:side==="SELL"?-1:0;
  var aligned=!!sg&&bias===sg&&sg*reaction>.06,totalImpact=total,conflict=!!sg&&bias===-sg&&(-sg)*reaction>.08,shock=crit&&Math.abs(reaction)>.45;
  var block=(crit&&mixed&&shock)||(conflict&&(crit||totalImpact>=6));
  var quiet=hi.length===0,reason=block?(mixed?'mixed high impact news with candle shock':'high impact news and candle reaction oppose trade'):aligned?'news and candle reaction aligned':quiet?'no fresh high impact headline':'news context neutral';
  return{available:V25N.status==='LIVE'||V25N.status==='REFRESHING',status:V25N.status,bias:bias,mixed:mixed,critical:crit,impact:totalImpact,aligned:aligned,conflict:conflict,shock:shock,block:block,quiet:quiet,reaction:reaction,reason:reason,top:hi[0]||recent[0]||null,count:hi.length};
}
function v25renderNews(ctx){
  ctx=ctx||v25newsContext('');V25N.ctx=ctx;
  var p=q('newsPerf'),h=q('newsHeadline');if(!p)return;
  var label=ctx.bias>0?'POSITIVE':ctx.bias<0?'NEGATIVE':ctx.mixed?'MIXED':'NEUTRAL',rx=finite(ctx.reaction)?ctx.reaction.toFixed(2)+' ATR':'NA',age=V25N.lastFetch?Math.max(0,Math.round((Date.now()-V25N.lastFetch)/1000))+'s':'NA';
  p.innerHTML='<div><span>News Feed</span><b>'+v25esc(V25N.status)+'</b></div><div><span>Context</span><b>'+label+'</b></div><div><span>Impact Score</span><b>'+Number(ctx.impact||0).toFixed(0)+'</b></div><div><span>Candle Reaction</span><b>'+rx+'</b></div><div><span>High Impact</span><b>'+ctx.count+'</b></div><div><span>Updated</span><b>'+age+'</b></div>';
  if(h){var x=ctx.top;h.innerHTML=x?'<b>'+v25esc(x.title)+'</b> · '+v25esc(x.domain||'source')+' · '+v25esc(ctx.reason):'No fresh relevant headline found. Technical engine remains active.'}
  v25renderShadow();
}
function v25shadowList(){try{var x=JSON.parse(localStorage.getItem(V25SHADOWKEY)||'[]');return Array.isArray(x)?x:[]}catch(e){return[]}}
function v25shadowSave(x){try{localStorage.setItem(V25SHADOWKEY,JSON.stringify(x.slice(-600)))}catch(e){}}
function v25shadowMaybe(profile,c,sel,nc){
  if(!c||!sel)return;var now=Date.now(),open=v25shadowList();
  if(open.some(function(t){return t.status==='OPEN'&&t.profile===profile&&t.symbol===S.symbol&&t.tf===S.tf}))return;
  var ded=profile+'|'+S.symbol+'|'+S.tf+'|'+c.side+'|'+c.strategy;if(V25LASTSHADOW[ded]&&now-V25LASTSHADOW[ded]<Math.max(60000,tfMs(S.tf)*.7))return;
  var p=v24plan(c),risk=Math.max(Math.abs(p.entry-p.sl),1e-9),rr1=Math.abs(p.t1-p.entry)/risk;
  open.push({id:'sh_'+now+'_'+Math.random().toString(36).slice(2,6),profile:profile,symbol:S.symbol,tf:S.tf,side:c.side,strategy:c.strategy,entry:p.entry,sl:p.sl,t1:p.t1,risk:risk,rr1:rr1,status:'OPEN',result:'OPEN',createdAt:now,newsImpact:nc?nc.impact:0,newsBias:nc?nc.bias:0});
  V25LASTSHADOW[ded]=now;v25shadowSave(open);
}
function v25shadowUpdate(price){
  if(!finite(price))return;var a=v25shadowList(),changed=false,now=Date.now();
  a.forEach(function(t){if(t.status!=='OPEN'||t.symbol!==S.symbol||t.tf!==S.tf)return;var win=t.side==='BUY'?price>=t.t1:price<=t.t1,loss=t.side==='BUY'?price<=t.sl:price>=t.sl;if(win){t.status='CLOSED';t.result='WIN';t.pnlR=t.rr1;t.closedAt=now;changed=true}else if(loss){t.status='CLOSED';t.result='LOSS';t.pnlR=-1;t.closedAt=now;changed=true}else if(now-t.createdAt>tfMs(t.tf)*10){t.status='CLOSED';t.result='TIME';t.pnlR=t.side==='BUY'?(price-t.entry)/t.risk:(t.entry-price)/t.risk;t.closedAt=now;changed=true}});
  if(changed){v25shadowSave(a);v25renderShadow()}
}
function v25shadowStat(profile){var x=v25shadowList().filter(function(t){return t.profile===profile&&t.status==='CLOSED'&&finite(t.pnlR)}),w=x.filter(function(t){return t.pnlR>0}).length,net=x.reduce(function(z,t){return z+num(t.pnlR)},0),gp=x.filter(function(t){return t.pnlR>0}).reduce(function(z,t){return z+t.pnlR},0),gl=Math.abs(x.filter(function(t){return t.pnlR<0}).reduce(function(z,t){return z+t.pnlR},0));return{n:x.length,win:x.length?w/x.length*100:0,net:net,pf:gl?gp/gl:(gp>0?99:0)}}
function v25renderShadow(){var body=q('shadowRows'),lead=q('shadowLeader');if(!body)return;var ps=['TECH','NEWS','FUSION'],stats=ps.map(function(p){var s=v25shadowStat(p);s.p=p;return s});body.innerHTML=stats.map(function(s){return'<tr><td>'+s.p+'</td><td>'+s.n+'</td><td>'+s.win.toFixed(1)+'%</td><td>'+s.net.toFixed(2)+'R</td><td>'+s.pf.toFixed(2)+'</td></tr>'}).join('');var eligible=stats.filter(function(s){return s.n>=20}).sort(function(a,b){return b.net-a.net});if(lead)lead.textContent=eligible.length?'Observed leader after at least 20 resolved shadow trades: '+eligible[0].p+' · '+eligible[0].win.toFixed(1)+'% win · '+eligible[0].net.toFixed(2)+'R. Production does not auto switch from this small sample.':'Shadow lab needs at least 20 resolved trades per profile before showing an observed leader.'}
