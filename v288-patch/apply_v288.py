from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.8.7 Trade Sync Integrity','Version 2.8.8 Multi Market Integrity')
s=s.replace('DhanPulse Version 2.8.7 Trade Sync Integrity.','DhanPulse Version 2.8.8 Multi Market Integrity.')
s=s.replace('DhanPulse Version 2.8.7 Trade Sync Integrity','DhanPulse Version 2.8.8 Multi Market Integrity')

css=r'''
/* V2.8.8 notification and multi market integrity */
.v288-status{
  margin-top:8px;padding:9px 10px;border:1px solid rgba(54,211,153,.20);
  border-radius:10px;background:rgba(54,211,153,.045);font-size:9px;color:#8696a3;line-height:1.45
}
.v288-status b{color:#36d399}
'''
if 'V2.8.8 notification and multi market integrity' not in s:
    s=s.replace('</style>',css+'\n</style>',1)

js=r'''
/* V2.8.8 Multi Market Integrity.
   Builds on startup recovery, full Delta history recovery and canonical trade sync.
   Delta credentials remain on the backend. Flattrade remains a separate read only India market connection. */
var V288={version:'2.8.8'};
if(typeof V287!=='undefined')V287.version='2.8.8';
if(typeof V284!=='undefined')V284.version='2.8.8';
if(typeof V283!=='undefined')V283.version='2.8.8';
if(typeof V281!=='undefined')V281.version='2.8.8';
if(typeof V280!=='undefined')V280.version='2.8.8';

function v288InstallStatus(){
  var note=q('livePerfNote');
  if(note&&!q('v288Integrity')){
    var x=document.createElement('div');x.id='v288Integrity';x.className='v288-status';
    x.innerHTML='<b>INTEGRITY ACTIVE</b> · duplicate signals are canonicalised, terminal trade notifications are de duplicated, and selected TF plus 1m plus HTF history must be ready before publication.';
    note.insertAdjacentElement('afterend',x);
  }
}
function v288RepairVisibleDuplicates(){
  try{
    if(typeof v287repairStores==='function')v287repairStores();
    if(typeof window.__pullTradeJournal==='function')window.__pullTradeJournal();
    if(typeof renderTrades==='function')renderTrades();
    if(typeof v261renderHistory==='function')v261renderHistory();
  }catch(e){}
}
setTimeout(function(){
  v288InstallStatus();
  v288RepairVisibleDuplicates();
  try{
    if(typeof v284ForceRecovery==='function')v284ForceRecovery();
    if(typeof v280FlattradeStatus==='function')v280FlattradeStatus();
  }catch(e){}
},700);
'''
if 'V2.8.8 Multi Market Integrity.' not in s:
    s=s.replace('\n})();\n</script>',js+'\n})();\n</script>',1)
idx.write_text(s)

java_dir=root/'app/src/main/java/com/dhanpulse/cryptofxv11'
svc=java_dir/'DhanPulseMonitorService.java'
t=svc.read_text()

# Add one-time cleanup of stale event notifications from older builds.
create_anchor='''        prefs = getSharedPreferences("dhanpulse_monitor", MODE_PRIVATE);
        createChannels();
'''
if create_anchor in t and 'clearOldEventNotificationsOnce();' not in t:
    t=t.replace(create_anchor,create_anchor+'        clearOldEventNotificationsOnce();\n',1)

# Add native notification identity/dedupe helpers before notifySignal.
signal_anchor='''    private void notifySignal(String json) {
'''
helpers=r'''    private void clearOldEventNotificationsOnce() {
        try {
            SharedPreferences np = getSharedPreferences("dhanpulse_notify_v288", MODE_PRIVATE);
            if (np.getBoolean("old_events_cleared", false)) return;
            NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null && Build.VERSION.SDK_INT >= 23) {
                android.service.notification.StatusBarNotification[] rows = nm.getActiveNotifications();
                if (rows != null) {
                    for (android.service.notification.StatusBarNotification row : rows) {
                        if (row != null && row.getId() != FOREGROUND_ID) nm.cancel(row.getId());
                    }
                }
            }
            np.edit().putBoolean("old_events_cleared", true).apply();
        } catch (Exception ignored) {
        }
    }

    private String notificationPlanKey(JSONObject t) {
        if (t == null) return "unknown";
        String market = t.optString("market", "crypto");
        String symbol = t.optString("symbol", "");
        String tf = t.optString("tf", "");
        String side = t.optString("side", "");
        String strategy = t.optString("strategy", t.optString("stage", ""));
        long created = t.optLong("createdAt", 0L);
        long bucket = created > 0L ? created / 120000L : System.currentTimeMillis() / 120000L;
        return market + "|" + symbol + "|" + tf + "|" + side + "|" + strategy + "|"
                + notificationPrice(t, "entry") + "|" + notificationPrice(t, "sl") + "|"
                + notificationPrice(t, "t1") + "|" + notificationPrice(t, "t2") + "|"
                + notificationPrice(t, "t3") + "|" + bucket;
    }

    private String notificationPrice(JSONObject t, String key) {
        double value = t == null ? Double.NaN : t.optDouble(key, Double.NaN);
        return Double.isNaN(value) ? "NA" : String.format(Locale.US, "%.6f", value);
    }

    private int stableSignalNotificationId(JSONObject t) {
        return 10000 + (notificationPlanKey(t).hashCode() & 0x3fffffff) % 800000;
    }

    private int stableTradeNotificationId(JSONObject t) {
        return 900000 + (notificationPlanKey(t).hashCode() & 0x0fffffff) % 90000;
    }

    private boolean suppressRepeatedNotification(JSONObject t, boolean tradeUpdate) {
        try {
            if (t == null) return false;
            String state = tradeUpdate
                    ? t.optString("status", "") + "|" + t.optString("result", "UPDATE") + "|" + t.optString("resultDisplay", "")
                    : "SIGNAL";
            String signature = notificationPlanKey(t) + "|" + state;
            String prefKey = "n_" + Integer.toHexString(signature.hashCode());
            long now = System.currentTimeMillis();
            SharedPreferences np = getSharedPreferences("dhanpulse_notify_v288", MODE_PRIVATE);
            long previous = np.getLong(prefKey, 0L);
            long window = tradeUpdate ? 180000L : 45000L;
            if (previous > 0L && now - previous < window) return true;
            np.edit().putLong(prefKey, now).apply();
        } catch (Exception ignored) {
        }
        return false;
    }

'''
if helpers.strip() not in t:
    if signal_anchor not in t: raise SystemExit('notifySignal anchor missing')
    t=t.replace(signal_anchor,helpers+signal_anchor,1)

# Signal notifications: one plan should produce one alert, not duplicate foreground/headless alerts.
sig_parse='''            JSONObject j = new JSONObject(json);
            String side = j.optString("side", "SIGNAL");
'''
if sig_parse in t and 'suppressRepeatedNotification(j, false)' not in t:
    t=t.replace(sig_parse,'''            JSONObject j = new JSONObject(json);
            if (suppressRepeatedNotification(j, false)) return;
            String side = j.optString("side", "SIGNAL");
''',1)

old_signal_notify='''            nm.notify((int) (System.currentTimeMillis() % 100000) + 3000, b.build());'''
if old_signal_notify in t:
    t=t.replace(old_signal_notify,'''            nm.notify(stableSignalNotificationId(j), b.build());''',1)

# Trade notifications: merge duplicate plan events and update one notification card for that plan.
trade_parse='''            JSONObject outer = new JSONObject(json);
            JSONObject t = outer.optJSONObject("trade");
'''
if trade_parse in t and 'suppressRepeatedNotification(t == null ? outer : t, true)' not in t:
    t=t.replace(trade_parse,trade_parse+'''            if (suppressRepeatedNotification(t == null ? outer : t, true)) return;
''',1)

old_trade_notify='''            nm.notify((int) (System.currentTimeMillis() % 100000) + 4000, b.build());'''
if old_trade_notify in t:
    t=t.replace(old_trade_notify,'''            nm.notify(stableTradeNotificationId(t == null ? outer : t), b.build());''',1)

# Keep current package identity and bump native user-agent/version.
t=t.replace('DhanPulse-Android/2.8.7','DhanPulse-Android/2.8.8')
svc.write_text(t)

# Flattrade backend client remains read only and uses the existing protected DeltaPulse backend.
ft=java_dir/'FlattradeBackend.java'
if not ft.exists():
    raise SystemExit('FlattradeBackend.java missing after V2.8.7 pipeline')
z=ft.read_text()
z=re.sub(r'DhanPulse-Android/2\.[0-9.]+','DhanPulse-Android/2.8.8',z)
ft.write_text(z)

# Delta backend stays server-side; no API key/secret is embedded.
db=java_dir/'DeltaBackendAccount.java'
if db.exists():
    z=db.read_text()
    z=re.sub(r'DhanPulse-Android/2\.[0-9.]+','DhanPulse-Android/2.8.8',z)
    db.write_text(z)

b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'applicationId\s*=\s*"[^"]+"','applicationId = "com.dhanpulse.cryptofxstablev263"',bs,count=1)
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 54',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.8.8"',bs,count=1)
b.write_text(bs)
