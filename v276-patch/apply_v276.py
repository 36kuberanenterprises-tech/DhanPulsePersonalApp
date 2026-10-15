from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.7.5 DeltaPulse Backend','Version 2.7.6 DeltaPulse Connected')
s=s.replace('DhanPulse Delta Exchange India Version 2.7.5 DeltaPulse Backend.',
            'DhanPulse Delta Exchange India Version 2.7.6 DeltaPulse Connected.')
s=s.replace('DhanPulse Delta Exchange India Version 2.7.5 DeltaPulse Backend',
            'DhanPulse Delta Exchange India Version 2.7.6 DeltaPulse Connected')

css=r'''
/* V2.7.6 backend-only Delta account connection */
#deltaAccountPanel .controls,
#deltaCredentialPartState,
#deltaDirectToggle{display:none!important}
.backend-mode-card{border-color:rgba(47,111,237,.58)!important}
.backend-mode-head span{font-weight:750}
.backend-secure-note{
  display:flex;gap:8px;align-items:flex-start;margin-top:9px;padding:9px 10px;
  border-radius:10px;background:rgba(23,185,120,.06);border:1px solid rgba(23,185,120,.18);
  color:#91a5b5;font-size:9px;line-height:1.45
}
.backend-secure-note b{color:#40d69a}
'''
if 'V2.7.6 backend-only Delta account connection' not in s:
    s=s.replace('</style>',css+'\n</style>',1)

js=r'''
/* V2.7.6 DeltaPulse Connected */
var V276={version:'2.7.6',backend:'https://deltapulse-personal-api.onrender.com'};
if(typeof V275!=='undefined')V275.version='2.7.6';
if(typeof V274!=='undefined')V274.version='2.7.6';
if(typeof V273!=='undefined')V273.version='2.7.6';
if(typeof V272!=='undefined')V272.version='2.7.6';

function v276RefreshUi(){
  var card=q('deltaBackendCard');if(!card)return;
  var p=card.querySelector('p');
  if(p)p.textContent='Delta API Key and API Secret are stored only in your DeltaPulse Render backend. This app uses only APP_ACCESS_TOKEN to verify and read your account.';
  var toggle=q('deltaDirectToggle');if(toggle)toggle.style.display='none';
  var controls=q('deltaAccountPanel')&&q('deltaAccountPanel').querySelector('.controls');if(controls)controls.style.display='none';
  var part=q('deltaCredentialPartState');if(part)part.style.display='none';
  if(!q('backendSecureNote')){
    var n=document.createElement('div');n.id='backendSecureNote';n.className='backend-secure-note';
    n.innerHTML='<b>SECURE</b><span>Delta API credentials stay on Render. The APK never displays, saves, or receives your Delta API Secret in backend mode.</span>';
    card.appendChild(n);
  }
  var lab=card.querySelector('label');
  if(lab){
    lab.childNodes[0].nodeValue='APP Access Token';
    var inp=q('deltaBackendToken');if(inp)inp.placeholder='Paste APP_ACCESS_TOKEN from Render';
  }
  var save=q('deltaBackendSave');if(save)save.textContent='Save APP Token';
  var connect=q('deltaBackendConnect');if(connect)connect.textContent='Connect & Verify Delta';
}
var __v276BackendStatus=window.__deltaBackendStatus;
window.__deltaBackendStatus=function(payload){
  if(__v276BackendStatus)__v276BackendStatus(payload);
  var d=payload;try{if(typeof d==='string')d=JSON.parse(d)}catch(e){d={}}
  if(d&&d.apiKey&&d.apiSecret){
    v274Set('deltaBackendOverall',v274TokenSaved()?'READY':'APP TOKEN NEEDED',v274TokenSaved()?'bull':'neutral');
  }
};
var __v276AccountResult=window.__deltaAccountResult;
window.__deltaAccountResult=function(payload){
  if(__v276AccountResult)__v276AccountResult(payload);
  var d=payload;try{if(typeof d==='string')d=JSON.parse(d)}catch(e){d={}}
  if(d&&d.success){
    v274Set('deltaBackendOverall','CONNECTED','bull');
    v268Set('deltaAuthState','CONNECTED','bull');
    v268Set('deltaAuthMessage','Verified through DeltaPulse backend. Account data is live from Delta Exchange India.');
  }
};
setTimeout(function(){
  v276RefreshUi();
  try{
    if(v274TokenSaved()){
      v274Set('deltaBackendOverall','VERIFYING','neutral');
      v274ConnectBackend();
    }
  }catch(e){}
},360);
'''
if 'V2.7.6 DeltaPulse Connected' not in s:
    s=s.replace('\n})();\n</script>',js+'\n})();\n</script>',1)
idx.write_text(s)

j=root/'app/src/main/java/com/dhanpulse/cryptofxv11/DeltaBackendAccount.java'
m=j.read_text().replace('DhanPulse-Android/2.7.5','DhanPulse-Android/2.7.6')
j.write_text(m)

b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 47',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.7.6"',bs,count=1)
b.write_text(bs)
