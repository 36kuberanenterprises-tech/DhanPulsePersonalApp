from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.8.0 Multi Market','Version 2.8.1 Unified Secure Backend')
s=s.replace('DhanPulse Version 2.8.0 Multi Market.','DhanPulse Version 2.8.1 Unified Secure Backend.')
s=s.replace('DhanPulse Version 2.8.0 Multi Market','DhanPulse Version 2.8.1 Unified Secure Backend')

css=r'''
/* V2.8.1 unified backend credentials */
#deltaAccountPanel .controls,
#deltaCredentialPartState,
#deltaDirectToggle{display:none!important}
#deltaAccountPanel .backend-mode-card{border-color:rgba(23,185,120,.38)!important}
.unified-security{
  margin-top:10px;padding:10px 11px;border:1px solid rgba(23,185,120,.20);
  border-radius:10px;background:rgba(23,185,120,.055);font-size:9px;line-height:1.5;color:#8fa2b0
}
.unified-security b{color:#36d399}
'''
if 'V2.8.1 unified backend credentials' not in s:
    s=s.replace('</style>',css+'\n</style>',1)

js=r'''
/* V2.8.1 Unified Secure Backend.
   Delta API key/secret are server-side only. No Delta key fields are exposed in the APK. */
var V281={version:'2.8.1',deltaBackend:'https://deltapulse-personal-api.onrender.com',flattradeBackend:'https://deltapulse-personal-api.onrender.com'};
if(typeof V280!=='undefined')V280.version='2.8.1';
if(typeof V276!=='undefined')V276.version='2.8.1';
if(typeof V275!=='undefined')V275.version='2.8.1';

function v281DeltaUi(){
  var panel=q('deltaAccountPanel');if(!panel)return;
  var h=panel.querySelector('h2');if(h)h.textContent='Delta Exchange Account';
  var sub=panel.querySelector('.row .muted.small');
  if(sub)sub.textContent='Delta API Key and Secret are already configured securely in your DeltaPulse Render backend. No Delta credentials are entered in this APK.';
  var controls=panel.querySelector('.controls');if(controls)controls.style.display='none';
  var parts=q('deltaCredentialPartState');if(parts)parts.style.display='none';
  var toggle=q('deltaDirectToggle');if(toggle)toggle.style.display='none';

  var card=q('deltaBackendCard');
  if(card){
    var p=card.querySelector('p');
    if(p)p.textContent='Delta authentication is handled by your existing Render backend variables. The app only uses your encrypted APP access token to request the account summary.';
    var lab=card.querySelector('label');
    if(lab){
      lab.childNodes[0].nodeValue='APP Access Token';
      var inp=q('deltaBackendToken');if(inp)inp.placeholder='Same APP_ACCESS_TOKEN for Delta and Flattrade';
    }
    var save=q('deltaBackendSave');if(save)save.textContent='Save App Token';
    var connect=q('deltaBackendConnect');if(connect)connect.textContent='Verify Delta Account';
    if(!q('unifiedSecurityNote')){
      var n=document.createElement('div');n.id='unifiedSecurityNote';n.className='unified-security';
      n.innerHTML='<b>SERVER-SIDE CREDENTIALS</b><br>DELTA_API_KEY and DELTA_API_SECRET never need to be pasted into DhanPulse. They remain in Render and sign requests there.';
      card.appendChild(n);
    }
  }
}
function v281ReuseTokenForFlattrade(){
  try{
    var saved=v274TokenSaved();
    var row=q('ftAppToken')&&q('ftAppToken').closest('.ft-token-row');
    if(row)row.style.display=saved?'none':'grid';
    if(saved)v280Text('ftMessage','Using the same encrypted APP access token already saved for Delta. Configure Flattrade API Key and Secret on Render, then authorize Flattrade.');
  }catch(e){}
}
setTimeout(function(){
  v281DeltaUi();
  v281ReuseTokenForFlattrade();
  try{
    if(v274TokenSaved()){
      v274Set('deltaBackendOverall','VERIFYING','neutral');
      v274ConnectBackend();
    }
  }catch(e){}
},650);
setInterval(v281ReuseTokenForFlattrade,2500);
'''
if 'V2.8.1 Unified Secure Backend.' not in s:
    s=s.replace('\n})();\n</script>',js+'\n})();\n</script>',1)

idx.write_text(s)

# Bump native user-agent where present.
for p in [
    root/'app/src/main/java/com/dhanpulse/cryptofxv11/DeltaBackendAccount.java',
    root/'app/src/main/java/com/dhanpulse/cryptofxv11/FlattradeBackend.java'
]:
    if p.exists():
        t=p.read_text()
        t=t.replace('DhanPulse-Android/2.8.0','DhanPulse-Android/2.8.1')
        t=t.replace('DhanPulse-Android/2.7.6','DhanPulse-Android/2.8.1')
        p.write_text(t)

b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 49',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.8.1"',bs,count=1)
b.write_text(bs)
