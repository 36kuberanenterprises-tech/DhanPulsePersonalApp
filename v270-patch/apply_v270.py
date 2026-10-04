from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.6.9 Delta Holder Verify','Version 2.7.0 Advanced Console')
s=s.replace('DhanPulse Delta Exchange India Version 2.6.9 Delta Holder Verify.',
            'DhanPulse Delta Exchange India Version 2.7.0 Advanced Console.')
s=s.replace('DhanPulse Delta Exchange India Version 2.6.9 Delta Holder Verify',
            'DhanPulse Delta Exchange India Version 2.7.0 Advanced Console')

css=r'''
/* V2.7 Advanced mobile trading console */
:root{
  --dp-bg:#061019;--dp-panel:#0b1823;--dp-panel2:#0e2130;--dp-line:#21394b;
  --dp-accent:#2d9cff;--dp-accent2:#36d399;--dp-warn:#ffb526;--dp-danger:#ff566f;
  --dp-text:#f3f8fc;--dp-muted:#8fa6b8;
}
body{background:
  radial-gradient(circle at 84% -8%,rgba(45,156,255,.16),transparent 34%),
  radial-gradient(circle at 0% 38%,rgba(54,211,153,.06),transparent 31%),
  var(--dp-bg)!important;color:var(--dp-text)}
.app{max-width:980px!important;padding-bottom:42px!important}
header{background:rgba(6,16,25,.86);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
  position:sticky;top:0;z-index:50;margin:0 -2px 12px;padding:12px 4px 10px;border-bottom:1px solid rgba(90,142,179,.18)}
.logo{border-radius:16px!important;box-shadow:0 7px 24px rgba(0,0,0,.28)}
.ver{background:#0b1a26!important;border:1px solid #29485f!important;border-radius:999px!important;padding:7px 12px!important}
.panel{background:linear-gradient(155deg,rgba(14,33,48,.94),rgba(8,22,32,.98))!important;
 border:1px solid rgba(83,132,166,.32)!important;border-radius:24px!important;
 box-shadow:0 14px 40px rgba(0,0,0,.20)!important;margin-bottom:16px!important}
button,input,select{border-radius:14px!important}
button{font-weight:750!important;letter-spacing:.01em}
select,input{background:#07141e!important;border:1px solid #29485f!important;color:#f3f8fc!important}
select:focus,input:focus{border-color:#38a8ff!important;box-shadow:0 0 0 3px rgba(45,156,255,.12)!important;outline:none!important}
#deltaAccountPanel{border-color:rgba(45,156,255,.58)!important;
 background:linear-gradient(145deg,rgba(11,32,47,.99),rgba(7,20,30,.99))!important;
 box-shadow:0 20px 55px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.03)!important}
#deltaAccountPanel h2{font-size:1.15rem!important;margin-bottom:4px!important}
#deltaAccountPanel .controls{display:grid!important;grid-template-columns:1fr 1fr!important;gap:10px!important}
#deltaAccountPanel .controls label{grid-column:span 1}
#deltaAccountPanel .controls button{min-height:48px}
#deltaAccountPanel .context{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:9px!important}
#deltaAccountPanel .context>div{background:#07151f!important;border:1px solid rgba(82,133,169,.25)!important;border-radius:16px!important;padding:12px!important;min-width:0}
#deltaAccountPanel .context span{display:block;color:#7892a6!important;font-size:.72rem!important;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px}
#deltaAccountPanel .context b{display:block;overflow-wrap:anywhere;font-size:.94rem}
#deltaAuthState{padding:7px 11px!important;border-radius:999px!important;border:1px solid currentColor!important;font-size:.72rem!important;letter-spacing:.08em}
#deltaAuthState.bull{color:#43e7a7!important;background:rgba(54,211,153,.08)}
#deltaAuthState.bear{color:#ff7185!important;background:rgba(255,86,111,.08)}
.pro-nav{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:8px;margin:4px 0 14px}
.pro-chip{background:#091722;border:1px solid rgba(76,127,164,.32);border-radius:16px;padding:10px 12px;min-height:52px;
 display:flex;align-items:center;justify-content:space-between;gap:8px;box-shadow:0 8px 25px rgba(0,0,0,.12)}
.pro-chip strong{font-size:.76rem;letter-spacing:.06em;text-transform:uppercase}
.pro-chip span{font-size:.72rem;color:#8fa6b8;white-space:nowrap}
.pro-chip.live strong{color:#43e7a7}.pro-chip.api strong{color:#56b7ff}.pro-chip.engine strong{color:#ffc14d}
.pro-workspace{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 12px}
.pro-workspace-title{font-size:.78rem;text-transform:uppercase;letter-spacing:.12em;color:#8aa1b4;font-weight:800}
.pro-workspace-badge{font-size:.72rem;color:#43e7a7;background:rgba(54,211,153,.08);border:1px solid rgba(54,211,153,.3);padding:6px 10px;border-radius:999px}
.tabs{display:none!important}
#decisionCard{border-color:rgba(255,181,38,.38)!important}
#decisionCard.buy{border-color:rgba(54,211,153,.58)!important;box-shadow:0 18px 48px rgba(54,211,153,.08)!important}
#decisionCard.sell{border-color:rgba(255,86,111,.58)!important;box-shadow:0 18px 48px rgba(255,86,111,.08)!important}
#decisionCard.wait{border-color:rgba(255,181,38,.38)!important}
#decision{letter-spacing:.02em!important}
#price{font-variant-numeric:tabular-nums}
.pro-api-toggle{background:linear-gradient(135deg,#1779c8,#2d9cff)!important;color:#fff!important;border:none!important}
.pro-api-note{display:flex;align-items:center;gap:8px;color:#86a1b5;font-size:.76rem;margin-top:8px}
.pro-dot{width:8px;height:8px;border-radius:50%;background:#ffb526;box-shadow:0 0 0 4px rgba(255,181,38,.08)}
.pro-dot.on{background:#43e7a7;box-shadow:0 0 0 4px rgba(54,211,153,.08)}
@media(max-width:680px){
  .app{padding-left:12px!important;padding-right:12px!important}
  header{padding-top:10px}
  .pro-nav{grid-template-columns:1fr 1fr}
  .pro-chip:first-child{grid-column:1/-1}
  #deltaAccountPanel .controls{grid-template-columns:1fr!important}
  #deltaAccountPanel .context{grid-template-columns:1fr 1fr!important}
  #deltaAccountPanel{padding:16px!important}
  .panel{border-radius:21px!important}
}
'''
if 'V2.7 Advanced mobile trading console' not in s:
    s=s.replace('</style>',css+'\n</style>',1)

js=r'''
/* V2.7.0 advanced console layout */
var V270={version:'2.7.0'};
if(typeof V268!=='undefined')V268.version='2.7.0';
if(typeof V261!=='undefined')V261.version='2.7.0';
if(typeof V26!=='undefined')V26.version='2.7.0';
if(typeof V263!=='undefined')V263.version='2.7.0';
if(typeof V264!=='undefined')V264.version='2.7.0';
if(typeof V265!=='undefined')V265.version='2.7.0';
if(typeof V266!=='undefined')V266.version='2.7.0';
if(typeof V267!=='undefined')V267.version='2.7.0';

function v270AccountConnected(){
  try{
    var b=window.DhanPulseNative;
    return !!(b&&b.deltaCredentialStatus&&String(b.deltaCredentialStatus())==='SAVED');
  }catch(e){return false}
}
function v270UpdateTop(){
  var a=q('proApiState'),d=q('proApiDot');
  if(a){var on=v270AccountConnected();a.textContent=on?'SAVED':'CONNECT';if(d)d.className='pro-dot'+(on?' on':'')}
  var f=q('proFeedState');if(f)f.textContent=(S&&S.feedMode?String(S.feedMode).replace('DELTA ',''):'STARTING');
}
function v270Layout(){
  try{
    var app=document.querySelector('.app'),head=app&&app.querySelector('header');if(!app||!head)return;
    if(!q('proNav')){
      var nav=document.createElement('div');nav.id='proNav';nav.className='pro-nav';
      nav.innerHTML=
       '<div class="pro-chip live"><strong>DELTA LIVE</strong><span id="proFeedState">STARTING</span></div>'+
       '<button id="proApiJump" class="pro-chip api" style="width:100%"><strong>API & ACCOUNT</strong><span id="proApiState">CONNECT</span></button>'+
       '<div class="pro-chip engine"><strong>ENGINE</strong><span>CONTINUOUS</span></div>';
      head.insertAdjacentElement('afterend',nav);
      q('proApiJump').onclick=function(){var p=q('deltaAccountPanel');if(p){p.scrollIntoView({behavior:'smooth',block:'start'});setTimeout(function(){var k=q('deltaApiKey');if(k)k.focus()},500)}};
    }
    var first=app.querySelector(':scope > .panel');
    var acct=q('deltaAccountPanel');
    if(first&&acct&&first!==acct&&first.nextElementSibling!==acct)first.insertAdjacentElement('afterend',acct);
    if(first&&!first.querySelector('.pro-workspace')){
      var w=document.createElement('div');w.className='pro-workspace';
      w.innerHTML='<div class="pro-workspace-title">Market Workspace</div><div class="pro-workspace-badge">DELTA PERPETUALS · PRODUCTION</div>';
      first.insertBefore(w,first.firstChild);
    }
    if(acct&&!q('proApiDot')){
      var note=document.createElement('div');note.className='pro-api-note';
      note.innerHTML='<i id="proApiDot" class="pro-dot"></i><span>API credentials are entered here and stored encrypted on this phone.</span>';
      var msg=q('deltaAuthMessage');if(msg)msg.insertAdjacentElement('afterend',note);else acct.appendChild(note);
    }
    var save=q('deltaSaveVerify');if(save){save.textContent='Connect & Verify Delta';save.classList.add('pro-api-toggle')}
    var refresh=q('deltaRefreshAccount');if(refresh)refresh.textContent='Refresh Live Account';
    var clear=q('deltaClearCredentials');if(clear)clear.textContent='Remove Credentials';
    var ak=q('deltaApiKey');if(ak)ak.placeholder='Production API key';
    var sk=q('deltaApiSecret');if(sk)sk.placeholder='Production API secret';
    v270UpdateTop();
  }catch(e){}
}
var __v270AccountResult=window.__deltaAccountResult;
window.__deltaAccountResult=function(payload){if(__v270AccountResult)__v270AccountResult(payload);setTimeout(v270UpdateTop,50)};
setTimeout(v270Layout,80);
setInterval(v270UpdateTop,1500);
'''
if 'V2.7.0 advanced console layout' not in s:
    s=s.replace('\n})();\n</script>',js+'\n})();\n</script>',1)

idx.write_text(s)

b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 41',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.7.0"',bs,count=1)
b.write_text(bs)
