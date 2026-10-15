from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.7.4 Backend Variables','Version 2.7.5 DeltaPulse Backend')
s=s.replace('DhanPulse Delta Exchange India Version 2.7.4 Backend Variables.',
            'DhanPulse Delta Exchange India Version 2.7.5 DeltaPulse Backend.')
s=s.replace('DhanPulse Delta Exchange India Version 2.7.4 Backend Variables',
            'DhanPulse Delta Exchange India Version 2.7.5 DeltaPulse Backend')

s=s.replace('Recommended · Backend Variables','Recommended · DeltaPulse Backend')
s=s.replace('Keep DELTA_API_KEY and DELTA_API_SECRET in the DhanPulse backend variables. The APK never needs those two credentials. Enter only your separate Backend Access Token below.',
            'Your Delta API Key and Secret stay in the existing DeltaPulse Render backend. Enter only APP_ACCESS_TOKEN once in this app.')
s=s.replace('Backend Access Token','APP Access Token')
s=s.replace('Enter your backend access token','Enter the same APP_ACCESS_TOKEN saved in Render')
s=s.replace('Save Token','Save APP Token')
s=s.replace('Connect Using Backend Variables','Connect Delta Account')
s=s.replace('Connecting to Delta through DhanPulse backend variables...',
            'Connecting to Delta through your DeltaPulse Render backend...')
s=s.replace('Connected securely through DhanPulse backend variables. API key and secret remain on the server.',
            'Connected securely through DeltaPulse backend. API key and secret remain only on Render.')

js=r'''
/* V2.7.5 DeltaPulse backend binding */
var V275={version:'2.7.5',backend:'https://deltapulse-personal-api.onrender.com'};
if(typeof V274!=='undefined')V274.version='2.7.5';
if(typeof V273!=='undefined')V273.version='2.7.5';
if(typeof V272!=='undefined')V272.version='2.7.5';
setTimeout(function(){
  var card=q('deltaBackendCard');
  if(card){
    var p=card.querySelector('p');
    if(p)p.textContent='Your Delta API Key and Secret stay in the existing DeltaPulse Render backend. Enter only APP_ACCESS_TOKEN once in this app.';
    var lab=card.querySelector('label');
    if(lab){
      lab.childNodes[0].nodeValue='APP Access Token';
      var inp=q('deltaBackendToken');if(inp)inp.placeholder='Enter APP_ACCESS_TOKEN from Render';
    }
    var save=q('deltaBackendSave');if(save)save.textContent='Save APP Token';
    var connect=q('deltaBackendConnect');if(connect)connect.textContent='Connect Delta Account';
  }
},300);
'''
if 'V2.7.5 DeltaPulse backend binding' not in s:
    s=s.replace('\n})();\n</script>',js+'\n})();\n</script>',1)
idx.write_text(s)

j=root/'app/src/main/java/com/dhanpulse/cryptofxv11/DeltaBackendAccount.java'
m=j.read_text()
m=m.replace('private static final String BASE = "https://dhanpulse-personal-api.onrender.com";',
            'private static final String BASE = "https://deltapulse-personal-api.onrender.com";')
m=m.replace('.url(BASE + "/api/delta/status")','.url(BASE + "/api/status")')
m=m.replace('.url(BASE + "/api/delta/account")','.url(BASE + "/api/account/summary")')
m=m.replace('.header("X-Delta-Access-Token", token)','.header("X-App-Token", token)')
m=m.replace('.post(body).build();','.get().build();')
m=m.replace('DhanPulse-Android/2.7.4','DhanPulse-Android/2.7.5')

# Normalize DeltaPulse /api/status to the shape expected by the UI.
old='''                    String body = r.body() == null ? "{}" : r.body().string();
                    cb.onResult(body);
'''
new='''                    String body = r.body() == null ? "{}" : r.body().string();
                    try {
                        JSONObject src = new JSONObject(body);
                        JSONObject out = new JSONObject();
                        boolean creds = src.optBoolean("credentials_configured", false);
                        boolean protectedAccess = src.optBoolean("private_access_protected", false);
                        out.put("configured", creds && protectedAccess);
                        out.put("apiKey", creds);
                        out.put("apiSecret", creds);
                        out.put("accessToken", protectedAccess);
                        cb.onResult(out.toString());
                    } catch (Exception e) {
                        JSONObject fail = new JSONObject();
                        fail.put("configured", false);
                        fail.put("apiKey", false);
                        fail.put("apiSecret", false);
                        fail.put("accessToken", false);
                        cb.onResult(fail.toString());
                    }
'''
if old in m:
    m=m.replace(old,new,1)
else:
    raise SystemExit('DeltaBackendAccount status block missing')

j.write_text(m)

b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 46',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.7.5"',bs,count=1)
b.write_text(bs)
