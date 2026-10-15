from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.7.2 Delta Secure Link','Version 2.7.3 Secure API Vault')
s=s.replace('DhanPulse Delta Exchange India Version 2.7.2 Delta Secure Link.',
            'DhanPulse Delta Exchange India Version 2.7.3 Secure API Vault.')
s=s.replace('DhanPulse Delta Exchange India Version 2.7.2 Delta Secure Link',
            'DhanPulse Delta Exchange India Version 2.7.3 Secure API Vault')

# Give the account panel a clear two-step credential workflow.
css=r'''
/* V2.7.3 credential vault */
.credential-row{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:end}
.credential-row label{margin:0!important}
.credential-save{min-width:92px!important;min-height:42px!important;background:#1b2633!important;border-color:#344457!important;color:#dce6f2!important}
.credential-state{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 2px}
.credential-pill{font-size:9px;font-weight:700;letter-spacing:.05em;padding:6px 9px;border-radius:999px;border:1px solid #343d48;background:#151a20;color:#8994a0}
.credential-pill.saved{color:#3bd596;border-color:rgba(59,213,150,.35);background:rgba(59,213,150,.07)}
@media(max-width:680px){.credential-row{grid-template-columns:1fr auto}.credential-save{min-width:82px!important;padding:8px!important}}
'''
if 'V2.7.3 credential vault' not in s:
    s=s.replace('</style>',css+'\n</style>',1)

js=r'''
/* V2.7.3 Secure API Vault.
   Key and secret can be saved separately in Android encrypted storage.
   This fixes losing a pasted key when Android backgrounds and reloads the WebView. */
var V273={version:'2.7.3'};
if(typeof V272!=='undefined')V272.version='2.7.3';
if(typeof V271!=='undefined')V271.version='2.7.3';
if(typeof V270!=='undefined')V270.version='2.7.3';
if(typeof V268!=='undefined')V268.version='2.7.3';

function v273Bridge(){return window.DhanPulseNative||null}
function v273Parts(){
  try{
    var b=v273Bridge();
    if(!b||!b.deltaCredentialPartsStatus)return{key:false,secret:false};
    var x=b.deltaCredentialPartsStatus(),d=typeof x==='string'?JSON.parse(x):x;
    return{key:!!d.key,secret:!!d.secret};
  }catch(e){return{key:false,secret:false}}
}
function v273SetState(){
  var p=v273Parts(),ks=q('deltaKeyPartState'),ss=q('deltaSecretPartState');
  if(ks){ks.textContent=p.key?'API KEY SAVED':'API KEY NOT SAVED';ks.className='credential-pill'+(p.key?' saved':'')}
  if(ss){ss.textContent=p.secret?'API SECRET SAVED':'API SECRET NOT SAVED';ss.className='credential-pill'+(p.secret?' saved':'')}
  if(typeof v271AccountLine==='function')v271AccountLine();
  return p;
}
function v273SaveKey(){
  var b=v273Bridge(),el=q('deltaApiKey'),v=el?el.value.trim():'';
  if(!v){v268Set('deltaAuthMessage','Paste the Delta API Key first.');return}
  try{
    b.saveDeltaApiKey(v);el.value='';v268Set('deltaAuthMessage','API Key saved securely. You can now switch to Notes, copy the API Secret, and return here.');
    v273SetState();
  }catch(e){v268Set('deltaAuthMessage','Unable to save API Key securely.')}
}
function v273SaveSecret(){
  var b=v273Bridge(),el=q('deltaApiSecret'),v=el?el.value.trim():'';
  if(!v){v268Set('deltaAuthMessage','Paste the Delta API Secret first.');return}
  try{
    b.saveDeltaApiSecret(v);el.value='';v268Set('deltaAuthMessage','API Secret saved securely. Tap Connect & Verify.');
    v273SetState();
  }catch(e){v268Set('deltaAuthMessage','Unable to save API Secret securely.')}
}
function v273Connect(){
  var b=v273Bridge(),k=q('deltaApiKey')?q('deltaApiKey').value.trim():'',sec=q('deltaApiSecret')?q('deltaApiSecret').value.trim():'';
  try{
    if(k)b.saveDeltaApiKey(k);
    if(sec)b.saveDeltaApiSecret(sec);
    if(q('deltaApiKey'))q('deltaApiKey').value='';
    if(q('deltaApiSecret'))q('deltaApiSecret').value='';
    var p=v273SetState();
    if(!p.key||!p.secret){v268Set('deltaAuthState','NOT READY','neutral');v268Set('deltaAuthMessage',!p.key?'Save the API Key first.':'Save the API Secret first.');return}
    v268Set('deltaAuthState','VERIFYING','neutral');
    v268Set('deltaAuthMessage','Verifying saved credentials with Delta Exchange India...');
    if(b&&b.refreshDeltaAccount)b.refreshDeltaAccount();
  }catch(e){v268Set('deltaAuthMessage','Unable to verify saved Delta credentials.')}
}
function v273Layout(){
  try{
    var panel=q('deltaAccountPanel');if(!panel)return;
    var key=q('deltaApiKey'),sec=q('deltaApiSecret');
    if(key&&!q('deltaSaveKey')){
      var parent=key.closest('label');
      var row=document.createElement('div');row.className='credential-row';
      parent.parentNode.insertBefore(row,parent);row.appendChild(parent);
      var b=document.createElement('button');b.id='deltaSaveKey';b.className='credential-save';b.textContent='Save Key';b.onclick=v273SaveKey;row.appendChild(b);
    }
    if(sec&&!q('deltaSaveSecret')){
      var parent2=sec.closest('label');
      var row2=document.createElement('div');row2.className='credential-row';
      parent2.parentNode.insertBefore(row2,parent2);row2.appendChild(parent2);
      var b2=document.createElement('button');b2.id='deltaSaveSecret';b2.className='credential-save';b2.textContent='Save Secret';b2.onclick=v273SaveSecret;row2.appendChild(b2);
    }
    if(!q('deltaCredentialPartState')){
      var st=document.createElement('div');st.id='deltaCredentialPartState';st.className='credential-state';
      st.innerHTML='<span id="deltaKeyPartState" class="credential-pill">API KEY NOT SAVED</span><span id="deltaSecretPartState" class="credential-pill">API SECRET NOT SAVED</span>';
      var controls=panel.querySelector('.controls');if(controls)controls.insertAdjacentElement('afterend',st);
    }
    var connect=q('deltaSaveVerify');if(connect){connect.textContent='Connect & Verify';connect.onclick=v273Connect}
    var p=v273SetState();
    if((p.key||p.secret)&&!(p.key&&p.secret)){
      setTimeout(function(){if(typeof v271Go==='function')v271Go('account');else panel.scrollIntoView({block:'start'})},220);
    }
  }catch(e){}
}
setTimeout(v273Layout,180);
setInterval(v273SetState,2500);
'''
if 'V2.7.3 Secure API Vault.' not in s:
    s=s.replace('\n})();\n</script>',js+'\n})();\n</script>',1)

idx.write_text(s)

mgr=root/'app/src/main/java/com/dhanpulse/cryptofxv11/DeltaAccountManager.java'
m=mgr.read_text()
anchor='''    static void save(Context c, String apiKey, String secret) throws Exception {
        prefs(c).edit().putString(KEY_API, apiKey.trim()).putString(KEY_SECRET, secret.trim()).apply();
    }
'''
if anchor not in m:
    raise SystemExit('DeltaAccountManager save anchor missing')
if 'static void saveKey(Context c' not in m:
    extra=anchor+'''\n    static void saveKey(Context c, String apiKey) throws Exception {
        if (apiKey == null || apiKey.trim().isEmpty()) throw new IllegalArgumentException("Empty API key");
        prefs(c).edit().putString(KEY_API, apiKey.trim()).apply();
    }

    static void saveSecret(Context c, String secret) throws Exception {
        if (secret == null || secret.trim().isEmpty()) throw new IllegalArgumentException("Empty API secret");
        prefs(c).edit().putString(KEY_SECRET, secret.trim()).apply();
    }

    static boolean hasKey(Context c) {
        try { return !prefs(c).getString(KEY_API, "").isEmpty(); } catch (Exception e) { return false; }
    }

    static boolean hasSecret(Context c) {
        try { return !prefs(c).getString(KEY_SECRET, "").isEmpty(); } catch (Exception e) { return false; }
    }
'''
    m=m.replace(anchor,extra,1)
m=m.replace('DhanPulse-Android/2.7.2','DhanPulse-Android/2.7.3')
mgr.write_text(m)

ma=root/'app/src/main/java/com/dhanpulse/cryptofxv11/MainActivity.java'
a=ma.read_text()
bridge_anchor='''        @JavascriptInterface
        public void saveAndVerifyDeltaCredentials(String apiKey, String apiSecret) {
'''
if bridge_anchor not in a: raise SystemExit('NativeBridge credential anchor missing')
if 'public void saveDeltaApiKey(String apiKey)' not in a:
    methods=r'''        @JavascriptInterface
        public void saveDeltaApiKey(String apiKey) {
            try {
                DeltaAccountManager.saveKey(MainActivity.this, apiKey);
            } catch (Exception ignored) {
            }
        }

        @JavascriptInterface
        public void saveDeltaApiSecret(String apiSecret) {
            try {
                DeltaAccountManager.saveSecret(MainActivity.this, apiSecret);
            } catch (Exception ignored) {
            }
        }

        @JavascriptInterface
        public String deltaCredentialPartsStatus() {
            try {
                return "{\"key\":" + DeltaAccountManager.hasKey(MainActivity.this)
                        + ",\"secret\":" + DeltaAccountManager.hasSecret(MainActivity.this) + "}";
            } catch (Exception e) {
                return "{\"key\":false,\"secret\":false}";
            }
        }

'''
    a=a.replace(bridge_anchor,methods+bridge_anchor,1)

# Make the old combined save method accept partial values and persist whichever part is present.
old='''                if (apiKey == null || apiKey.trim().isEmpty() || apiSecret == null || apiSecret.trim().isEmpty()) {
                    deliverDeltaAccountResult("{\"success\":false,\"error\":\"Enter both API key and API secret\"}");
                    return;
                }
                DeltaAccountManager.save(MainActivity.this, apiKey, apiSecret);
                refreshDeltaAccount();
                startDeltaPrivateFeedNative();
'''
new='''                if (apiKey != null && !apiKey.trim().isEmpty()) DeltaAccountManager.saveKey(MainActivity.this, apiKey);
                if (apiSecret != null && !apiSecret.trim().isEmpty()) DeltaAccountManager.saveSecret(MainActivity.this, apiSecret);
                if (!DeltaAccountManager.has(MainActivity.this)) {
                    deliverDeltaAccountResult("{\"success\":false,\"error\":\"Save both API key and API secret first\"}");
                    return;
                }
                refreshDeltaAccount();
                startDeltaPrivateFeedNative();
'''
if old in a:
    a=a.replace(old,new,1)

ma.write_text(a)

b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 44',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.7.3"',bs,count=1)
b.write_text(bs)
