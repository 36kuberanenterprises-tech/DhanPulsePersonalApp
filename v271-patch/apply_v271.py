from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.7.0 Advanced Console','Version 2.7.1 iOS Market Pro')
s=s.replace('DhanPulse Delta Exchange India Version 2.7.0 Advanced Console.',
            'DhanPulse Delta Exchange India Version 2.7.1 iOS Market Pro.')
s=s.replace('DhanPulse Delta Exchange India Version 2.7.0 Advanced Console',
            'DhanPulse Delta Exchange India Version 2.7.1 iOS Market Pro')

css=r'''
/* V2.7.1 original iOS market pro theme.
   Visual language combines clean broker-app hierarchy, chart-first density and iOS navigation.
   No third-party branding or assets are copied. */
:root{
  --ios-bg:#0b0d10;
  --ios-surface:#12151a;
  --ios-surface2:#171b21;
  --ios-raised:#1d2229;
  --ios-line:#2a3038;
  --ios-line2:#353c46;
  --ios-text:#f5f7fa;
  --ios-muted:#8c96a3;
  --ios-blue:#2f6fed;
  --ios-blue2:#5a8cff;
  --ios-green:#17b978;
  --ios-red:#ef5b5b;
  --ios-amber:#e9aa37;
}
html{background:var(--ios-bg)!important}
body{
  background:var(--ios-bg)!important;
  color:var(--ios-text)!important;
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Inter","Segoe UI",Roboto,Arial,sans-serif!important;
  letter-spacing:-.01em;
}
body:before{display:none!important}
.app{
  max-width:1080px!important;
  padding:calc(8px + env(safe-area-inset-top)) 12px calc(92px + env(safe-area-inset-bottom))!important;
}
header{
  min-height:58px!important;
  display:flex!important;
  align-items:center!important;
  position:sticky!important;
  top:0!important;
  z-index:90!important;
  margin:0 -12px 10px!important;
  padding:8px 14px!important;
  background:rgba(11,13,16,.90)!important;
  border-bottom:1px solid rgba(255,255,255,.07)!important;
  backdrop-filter:saturate(180%) blur(20px)!important;
  -webkit-backdrop-filter:saturate(180%) blur(20px)!important;
}
.brand{gap:9px!important;min-width:0}
.logo{
  width:39px!important;height:39px!important;padding:2px!important;border-radius:11px!important;
  box-shadow:none!important;background:#fff!important
}
.brand h1{font-size:18px!important;font-weight:760!important;letter-spacing:-.02em}
.brand .muted{font-size:10px!important;color:#7f8995!important;margin-top:2px}
.statusarea{max-width:none!important;gap:6px!important;flex-wrap:nowrap!important}
.ver{
  font-size:9px!important;white-space:nowrap!important;padding:5px 8px!important;
  border:1px solid var(--ios-line)!important;background:var(--ios-surface)!important;color:#8f99a5!important
}
.badge{
  font-size:9px!important;padding:5px 8px!important;border-radius:999px!important;
  border:1px solid rgba(23,185,120,.32)!important;background:rgba(23,185,120,.08)!important
}
.panel{
  background:var(--ios-surface)!important;
  border:1px solid var(--ios-line)!important;
  border-radius:14px!important;
  box-shadow:none!important;
  padding:14px!important;
  margin-bottom:10px!important;
}
.panel h2{font-size:14px!important;font-weight:720!important;letter-spacing:-.012em}
.muted{color:var(--ios-muted)!important}
.small{font-size:10px!important}
button,select,input{
  min-height:42px!important;border-radius:10px!important;
  border:1px solid var(--ios-line)!important;
  background:var(--ios-surface2)!important;color:var(--ios-text)!important;
  -webkit-tap-highlight-color:transparent!important
}
button{font-weight:680!important}
button:active{transform:scale(.985)}
.primary,.pro-api-toggle{
  background:var(--ios-blue)!important;border-color:var(--ios-blue)!important;color:#fff!important;
  box-shadow:none!important
}
.secondary{background:var(--ios-raised)!important;border-color:var(--ios-line2)!important;color:#dfe5eb!important}
.danger{background:transparent!important;color:#ff7474!important}
label{font-size:10px!important;color:var(--ios-muted)!important;font-weight:560!important}
.control{gap:8px!important}
.hero{gap:10px!important}
.price{font-size:34px!important;font-weight:760!important;letter-spacing:-.035em!important}
.metrics,.context,.perf{gap:7px!important;margin-top:10px!important}
.metrics div,.context div,.perf div,.plan div,.ind{
  background:var(--ios-surface2)!important;
  border:1px solid var(--ios-line)!important;
  border-radius:10px!important;padding:10px!important
}
.metrics span,.context span,.perf span,.plan span,.ind .n{
  font-size:9px!important;color:#7f8995!important;text-transform:uppercase!important;letter-spacing:.055em!important
}
.decision{min-height:142px!important}
.decision b{font-size:38px!important;font-weight:780!important;letter-spacing:-.035em!important}
.buy b,.bull{color:var(--ios-green)!important}
.sell b,.bear{color:var(--ios-red)!important}
.wait b,.neutral{color:var(--ios-amber)!important}
.stage{
  background:var(--ios-surface2)!important;border-color:var(--ios-line)!important;
  font-size:9px!important;color:#96a0ab!important;padding:5px 9px!important
}
.grid2{gap:10px!important}
canvas{
  height:350px!important;
  background:#0b0d10!important;
  border:1px solid #232930!important;
  border-radius:10px!important;
  margin-top:8px!important
}
.chart-tools{gap:6px!important}
.chart-tools button{
  min-width:42px!important;min-height:34px!important;padding:6px 10px!important;
  background:#181c22!important;border-color:#2b3139!important
}
.chart-tools .live-btn{background:rgba(23,185,120,.10)!important;border-color:rgba(23,185,120,.36)!important;color:#35ca8e!important}
.chart-status{font-size:9px!important;padding:5px 8px!important;background:#171b20!important}
.table{border:1px solid var(--ios-line)!important;border-radius:10px!important;background:var(--ios-surface2)!important}
table{background:transparent!important}
th,td{border-bottom:1px solid #252b33!important;font-size:10px!important;padding:9px 8px!important}
th{color:#76818d!important;font-weight:650!important;background:#15191e!important}
#deltaAccountPanel{
  background:var(--ios-surface)!important;
  border:1px solid rgba(47,111,237,.55)!important;
  box-shadow:0 0 0 1px rgba(47,111,237,.06)!important
}
#deltaAccountPanel .context>div{background:var(--ios-surface2)!important;border-color:var(--ios-line)!important}
#deltaAuthState{font-size:9px!important}
.pro-nav{
  display:grid!important;grid-template-columns:1.2fr 1fr 1fr!important;gap:7px!important;margin:2px 0 10px!important
}
.pro-chip{
  min-height:43px!important;border-radius:11px!important;
  background:var(--ios-surface)!important;border:1px solid var(--ios-line)!important;
  padding:8px 10px!important;box-shadow:none!important
}
.pro-chip strong{font-size:9px!important;letter-spacing:.055em!important}
.pro-chip span{font-size:9px!important;color:#7e8995!important}
.pro-workspace{margin-bottom:9px!important}
.pro-workspace-title{font-size:9px!important;color:#798490!important;letter-spacing:.08em!important}
.pro-workspace-badge{
  font-size:8px!important;padding:5px 8px!important;color:#28c98a!important;
  background:rgba(23,185,120,.07)!important;border-color:rgba(23,185,120,.26)!important
}
.ios-account-strip{
  display:flex;align-items:center;justify-content:space-between;gap:10px;
  padding:10px 12px;margin:0 0 10px;background:var(--ios-surface);
  border:1px solid var(--ios-line);border-radius:12px
}
.ios-account-strip .left{display:flex;align-items:center;gap:9px;min-width:0}
.ios-account-strip .avatar{
  width:32px;height:32px;border-radius:50%;display:grid;place-items:center;font-size:12px;font-weight:760;
  color:#dfe9ff;background:#18233a;border:1px solid #2b416f
}
.ios-account-strip .txt{min-width:0}
.ios-account-strip .title{font-size:12px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ios-account-strip .sub{font-size:9px;color:var(--ios-muted);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ios-account-strip button{min-height:34px!important;padding:6px 10px!important;font-size:10px!important;background:var(--ios-blue)!important;border-color:var(--ios-blue)!important}
.ios-section-label{
  font-size:10px;font-weight:720;color:#7e8994;text-transform:uppercase;letter-spacing:.09em;
  margin:15px 2px 7px
}
#iosTabBar{
  position:fixed;left:50%;bottom:calc(8px + env(safe-area-inset-bottom));transform:translateX(-50%);
  z-index:999;width:min(calc(100% - 20px),620px);height:64px;padding:5px 7px;
  display:grid;grid-template-columns:repeat(5,1fr);gap:2px;
  background:rgba(24,27,32,.91);border:1px solid rgba(255,255,255,.10);border-radius:19px;
  box-shadow:0 12px 40px rgba(0,0,0,.40);
  backdrop-filter:saturate(180%) blur(22px);-webkit-backdrop-filter:saturate(180%) blur(22px)
}
.ios-tab{
  min-height:52px!important;padding:4px 2px!important;border:none!important;background:transparent!important;
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;color:#7f8a96!important;border-radius:13px!important
}
.ios-tab svg{width:18px;height:18px;display:block;stroke:currentColor;stroke-width:1.8;fill:none}
.ios-tab span{font-size:8px;font-weight:640}
.ios-tab.active{color:#75a1ff!important;background:rgba(47,111,237,.12)!important;border:none!important}
.ios-float-title{
  display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:9px
}
.ios-float-title .t{font-size:11px;font-weight:720;color:#dce2e8}
.ios-float-title .s{font-size:9px;color:#77828e}
#migrationNote{display:none!important}
footer{padding-bottom:72px!important;color:#626b75!important;font-size:9px!important}
@media(max-width:680px){
  .app{padding-left:10px!important;padding-right:10px!important}
  header{margin-left:-10px!important;margin-right:-10px!important}
  .ver{display:none!important}
  .logo{width:36px!important;height:36px!important}
  .brand h1{font-size:17px!important}
  .hero{grid-template-columns:1fr!important}
  .price{font-size:32px!important}
  .control{grid-template-columns:1fr 1fr!important}
  .control button{grid-column:1/-1}
  .pro-nav{grid-template-columns:1fr 1fr 1fr!important}
  .pro-chip{padding:7px 8px!important}
  .pro-chip span{display:none!important}
  .metrics,.context,.perf{grid-template-columns:1fr 1fr!important}
  .inds{grid-template-columns:1fr 1fr!important}
  #deltaAccountPanel .context{grid-template-columns:1fr 1fr!important}
  #deltaAccountPanel .controls{grid-template-columns:1fr!important}
  canvas{height:320px!important}
}
'''
if 'V2.7.1 original iOS market pro theme.' not in s:
    s=s.replace('</style>',css+'\n</style>',1)

js=r'''
/* V2.7.1 iOS market pro layout */
var V271={version:'2.7.1'};
if(typeof V270!=='undefined')V270.version='2.7.1';
if(typeof V268!=='undefined')V268.version='2.7.1';
if(typeof V261!=='undefined')V261.version='2.7.1';
if(typeof V26!=='undefined')V26.version='2.7.1';
if(typeof V263!=='undefined')V263.version='2.7.1';
if(typeof V264!=='undefined')V264.version='2.7.1';
if(typeof V265!=='undefined')V265.version='2.7.1';
if(typeof V266!=='undefined')V266.version='2.7.1';
if(typeof V267!=='undefined')V267.version='2.7.1';

function v271Icon(name){
  var d={
    market:'<path d="M4 16V9m5 7V5m5 11v-4m5 4V3"/>',
    chart:'<path d="M3 16l4-5 4 3 6-8 4 3"/><path d="M3 20h18"/>',
    signal:'<path d="M5 12h3l2-5 4 10 2-5h3"/><circle cx="12" cy="12" r="9"/>',
    trades:'<path d="M5 5h14v14H5z"/><path d="M8 9h8M8 13h8M8 17h5"/>',
    account:'<circle cx="12" cy="8" r="3"/><path d="M5.5 20c.8-4 3-6 6.5-6s5.7 2 6.5 6"/>'
  };
  return '<svg viewBox="0 0 24 24" aria-hidden="true">'+(d[name]||'')+'</svg>';
}
function v271Panel(el){return el&&el.closest?el.closest('.panel'):null}
function v271Target(name){
  if(name==='market')return document.querySelector('.app > .panel');
  if(name==='chart')return v271Panel(q('chart'));
  if(name==='signal')return q('decisionCard')||q('opportunityEngine');
  if(name==='trades')return v271Panel(q('trades'))||q('historyLab');
  if(name==='account')return q('deltaAccountPanel');
  return null;
}
function v271Go(name){
  var t=v271Target(name);if(t)t.scrollIntoView({behavior:'smooth',block:'start'});
  document.querySelectorAll('.ios-tab').forEach(function(b){b.classList.toggle('active',b.getAttribute('data-go')===name)});
  if(name==='account')setTimeout(function(){var k=q('deltaApiKey');if(k&&!v270AccountConnected())k.focus()},450);
}
function v271AccountLine(){
  var strip=q('iosAccountStrip');if(!strip)return;
  var on=false;try{on=v270AccountConnected()}catch(e){}
  var holder=q('deltaHolderName'),avail=q('deltaAvailable'),title=q('iosAcctTitle'),sub=q('iosAcctSub'),btn=q('iosAcctBtn');
  if(title)title.textContent=on?((holder&&holder.textContent&&holder.textContent!=='NA'&&holder.textContent!=='Not returned by Delta')?holder.textContent:'Delta account connected'):'Connect Delta account';
  if(sub)sub.textContent=on?('Available '+((avail&&avail.textContent)||'balance loading')):'Add production API key and secret securely';
  if(btn)btn.textContent=on?'Account':'Connect';
}
function v271Label(panel,text){
  if(!panel||panel.previousElementSibling&&panel.previousElementSibling.classList&&panel.previousElementSibling.classList.contains('ios-section-label'))return;
  var l=document.createElement('div');l.className='ios-section-label';l.textContent=text;panel.parentNode.insertBefore(l,panel);
}
function v271Layout(){
  try{
    document.body.classList.add('ios-fusion');
    var app=document.querySelector('.app'),head=app&&app.querySelector('header');if(!app||!head)return;

    var pn=q('proNav');
    if(pn){
      pn.innerHTML=
        '<div class="pro-chip live"><strong>DELTA</strong><span id="proFeedState">LIVE</span></div>'+
        '<button id="proApiJump" class="pro-chip api" style="width:100%"><strong>ACCOUNT</strong><span id="proApiState">CONNECT</span></button>'+
        '<div class="pro-chip engine"><strong>ENGINE</strong><span>ACTIVE</span></div>';
      if(q('proApiJump'))q('proApiJump').onclick=function(){v271Go('account')};
    }

    if(!q('iosAccountStrip')){
      var strip=document.createElement('div');strip.id='iosAccountStrip';strip.className='ios-account-strip';
      strip.innerHTML='<div class="left"><div class="avatar">DP</div><div class="txt"><div id="iosAcctTitle" class="title">Connect Delta account</div><div id="iosAcctSub" class="sub">Add production API key and secret securely</div></div></div><button id="iosAcctBtn">Connect</button>';
      if(pn)pn.insertAdjacentElement('afterend',strip);else head.insertAdjacentElement('afterend',strip);
      q('iosAcctBtn').onclick=function(){v271Go('account')};
    }

    var marketPanel=document.querySelector('.app > .panel');
    var hero=document.querySelector('.app > .hero');
    var chartPanel=v271Panel(q('chart'));
    var signalGrid=q('entry')&&q('entry').closest('.grid2');
    if(hero&&chartPanel&&hero.nextElementSibling!==chartPanel)hero.insertAdjacentElement('afterend',chartPanel);
    if(chartPanel&&signalGrid&&chartPanel.nextElementSibling!==signalGrid)chartPanel.insertAdjacentElement('afterend',signalGrid);

    if(marketPanel)v271Label(marketPanel,'Market');
    if(chartPanel)v271Label(chartPanel,'Chart');
    if(q('opportunityEngine'))v271Label(q('opportunityEngine'),'Signal Intelligence');
    var perf=v271Panel(q('trades'));if(perf)v271Label(perf,'Performance');
    if(q('deltaAccountPanel'))v271Label(q('deltaAccountPanel'),'Account');

    if(chartPanel){
      var h=chartPanel.querySelector('h2');if(h)h.textContent='Advanced Chart';
      var d=chartPanel.querySelector('.muted.small');if(d)d.textContent='Live Delta candles · pinch to zoom · drag for history · ICT liquidity and OB/FVG overlays';
    }
    var marketH=marketPanel&&marketPanel.querySelector('.pro-workspace-title');if(marketH)marketH.textContent='Market';
    var refresh=q('refresh');if(refresh)refresh.textContent='Analyse Now';

    if(!q('iosTabBar')){
      var bar=document.createElement('nav');bar.id='iosTabBar';
      [['market','Market'],['chart','Chart'],['signal','Signals'],['trades','Trades'],['account','Account']].forEach(function(x,i){
        var b=document.createElement('button');b.className='ios-tab'+(i===0?' active':'');b.setAttribute('data-go',x[0]);
        b.innerHTML=v271Icon(x[0])+'<span>'+x[1]+'</span>';b.onclick=function(){v271Go(x[0])};bar.appendChild(b);
      });
      document.body.appendChild(bar);
    }

    var acct=q('deltaAccountPanel');
    if(acct){
      var h2=acct.querySelector('h2');if(h2)h2.textContent='Delta Account';
      var sub=acct.querySelector('.row .muted.small');if(sub)sub.textContent='Securely connect your Delta India production account to verify holder name and live balances.';
      var save=q('deltaSaveVerify');if(save)save.textContent='Connect & Verify';
      var refreshA=q('deltaRefreshAccount');if(refreshA)refreshA.textContent='Refresh Balance';
      var clear=q('deltaClearCredentials');if(clear)clear.textContent='Remove API';
    }
    v271AccountLine();
  }catch(e){}
}
var __v271AccountResult=window.__deltaAccountResult;
window.__deltaAccountResult=function(payload){
  if(__v271AccountResult)__v271AccountResult(payload);
  setTimeout(function(){v271AccountLine();if(typeof v270UpdateTop==='function')v270UpdateTop()},80);
};
setTimeout(v271Layout,120);
setInterval(v271AccountLine,1800);
'''
if 'V2.7.1 iOS market pro layout' not in s:
    s=s.replace('\n})();\n</script>',js+'\n})();\n</script>',1)

idx.write_text(s)

b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 42',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.7.1"',bs,count=1)
b.write_text(bs)
