from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.6.8 Delta Account Verify','Version 2.6.9 Delta Holder Verify')
s=s.replace('DhanPulse Delta Exchange India Version 2.6.8 Delta Account Verify.',
            'DhanPulse Delta Exchange India Version 2.6.9 Delta Holder Verify.')
s=s.replace('DhanPulse Delta Exchange India Version 2.6.8 Delta Account Verify',
            'DhanPulse Delta Exchange India Version 2.6.9 Delta Holder Verify')

# Add a dedicated account-holder row.
needle='<div><span>Account Name</span><b id="deltaAccountName">NA</b></div>'
if needle in s and 'id="deltaHolderName"' not in s:
    s=s.replace(needle, needle+'\n    <div><span>Account Holder</span><b id="deltaHolderName">NA</b></div>',1)

# Display verified holder name returned by Delta.
s=s.replace("v268Set('deltaAccountName',d.accountName||d.displayName||'Not returned by API');",
            "v268Set('deltaAccountName',d.accountName||'NA');\n  v268Set('deltaHolderName',d.holderName||d.displayName||'Not returned by Delta');")
s=s.replace("['deltaUserId','deltaAccountName','deltaNetEquity','deltaAvailable','deltaTotalBalance'].forEach",
            "['deltaUserId','deltaAccountName','deltaHolderName','deltaNetEquity','deltaAvailable','deltaTotalBalance'].forEach")

# Version marker.
s=s.replace("var V268={version:'2.6.8'};","var V268={version:'2.6.9'};")
for old in ["V261.version='2.6.8'","V26.version='2.6.8'","V263.version='2.6.8'","V264.version='2.6.8'","V265.version='2.6.8'","V266.version='2.6.8'","V267.version='2.6.8'"]:
    s=s.replace(old,old.replace("2.6.8","2.6.9"))
idx.write_text(s)

# Improve authenticated account matching. Delta /v2/sub_accounts documents first_name/last_name/account_name.
mgr=root/'app/src/main/java/com/dhanpulse/cryptofxv11/DeltaAccountManager.java'
m=mgr.read_text()
old='''                String accountName = "";
                String displayName = "";
                try {
                    JSONObject subs = signedGet("/v2/sub_accounts", key, secret);
                    JSONArray sa = subs.optJSONArray("result");
                    if (subs.optBoolean("success", false) && sa != null) {
                        for (int i = 0; i < sa.length(); i++) {
                            JSONObject u = sa.optJSONObject(i);
                            if (u == null) continue;
                            if (userId.equals(String.valueOf(u.opt("id")))) {
                                accountName = u.optString("account_name", "");
                                String fn = u.optString("first_name", "");
                                String ln = u.optString("last_name", "");
                                displayName = (fn + " " + ln).trim();
                                break;
                            }
                        }
                    }
                } catch (Exception ignored) {}
'''
new='''                String accountName = "";
                String displayName = "";
                String holderName = "";
                try {
                    JSONObject subs = signedGet("/v2/sub_accounts", key, secret);
                    JSONArray sa = subs.optJSONArray("result");
                    if (subs.optBoolean("success", false) && sa != null) {
                        JSONObject selected = null;
                        for (int i = 0; i < sa.length(); i++) {
                            JSONObject u = sa.optJSONObject(i);
                            if (u == null) continue;
                            String id = String.valueOf(u.opt("id"));
                            if (!userId.isEmpty() && userId.equals(id)) { selected = u; break; }
                            if (selected == null && !u.optBoolean("is_sub_account", true)) selected = u;
                        }
                        if (selected == null && sa.length() == 1) selected = sa.optJSONObject(0);
                        if (selected != null) {
                            if (userId.isEmpty()) userId = String.valueOf(selected.opt("id"));
                            accountName = selected.optString("account_name", "");
                            String fn = selected.optString("first_name", "").trim();
                            String ln = selected.optString("last_name", "").trim();
                            holderName = (fn + " " + ln).trim();
                            displayName = holderName;
                        }
                    }
                } catch (Exception ignored) {}
'''
if old not in m:
    raise SystemExit('Delta subaccount block not found')
m=m.replace(old,new,1)
m=m.replace('out.put("displayName", displayName);','out.put("displayName", displayName);\n                out.put("holderName", holderName);',1)
m=m.replace('DhanPulse-Android/2.6.8','DhanPulse-Android/2.6.9')
mgr.write_text(m)

# App version.
b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 40',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.6.9"',bs,count=1)
b.write_text(bs)
