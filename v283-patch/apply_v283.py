from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

s=s.replace('Version 2.8.2 Startup Recovery','Version 2.8.3 Stable Data Pipeline')
s=s.replace('DhanPulse Version 2.8.2 Startup Recovery.','DhanPulse Version 2.8.3 Stable Data Pipeline.')
s=s.replace('DhanPulse Version 2.8.2 Startup Recovery','DhanPulse Version 2.8.3 Stable Data Pipeline')

# Make the final static HTML correct even before JavaScript starts.
direct_block='''  <div class="controls" style="margin-top:12px">
    <label>Delta API Key
      <input id="deltaApiKey" type="password" autocomplete="off" placeholder="Enter production API key">
    </label>
    <label>Delta API Secret
      <input id="deltaApiSecret" type="password" autocomplete="off" placeholder="Enter matching API secret">
    </label>
    <button id="deltaSaveVerify">Save and Verify</button>
    <button id="deltaRefreshAccount" class="secondary">Refresh Account</button>
    <button id="deltaClearCredentials" class="secondary">Clear Credentials</button>
  </div>
'''
s=s.replace(direct_block,'')
s=s.replace('<b id="deltaAuthState" class="neutral">NOT CONNECTED</b>',
            '<b id="deltaAuthState" class="neutral">CHECKING BACKEND</b>')
s=s.replace('<div><span>Credential</span><b id="deltaKeyMask">NOT SAVED</b></div>',
            '<div><span>Server Credential</span><b id="deltaKeyMask">CHECKING</b></div>')
s=s.replace('<div><span>Private Feed</span><b id="deltaPrivateState">OFFLINE</b></div>',
            '<div><span>Account Mode</span><b id="deltaPrivateState">BACKEND</b></div>')
s=s.replace('<b id="oppState" class="neutral">STARTING</b>',
            '<b id="oppState" class="neutral">LOADING DATA</b>')
s=s.replace('<div><span>Engine Scope</span><b id="scopeState">REPAIRING</b></div>',
            '<div><span>Engine Scope</span><b id="scopeState">BUILDING DATA</b></div>')
s=s.replace('<div><span>Current Gate</span><b id="oppGate">WAIT</b></div>',
            '<div><span>Current Gate</span><b id="oppGate">WAIT: loading history</b></div>')
s=s.replace('<button id="clear" class="danger">Clear Records</button>',
            '<button id="clear" class="danger" disabled>History Protected</button>')

# Remove stale generation labels and messages visible in the current app.
for a,b in [
    ('News engine starting','Delta market context active'),
    ('V2.3 Research Auto','Adaptive Signal Engine'),
    ('V2.2 SIGNALS','LIVE SIGNALS'),
    ('V2.2 Signals','Live Signals'),
    ('No V2.2 signals recorded yet.','No live signals recorded yet.'),
    ('No V2.6 signals recorded yet.','No live signals recorded yet.'),
    ('V2.2 QUALITY ENGINE','CURRENT SIGNAL ENGINE'),
    ('V2.2 quality engine','current signal engine'),
    ('Delta Account Verification','Delta Account'),
    ('Save credentials to verify the Delta account.','Account verification uses the secure DeltaPulse backend.'),
    ('Enter your Delta India production API key and API secret on this phone. They are encrypted in Android secure storage and are never written to WebView storage or GitHub.',
     'Delta API credentials stay on your DeltaPulse Render backend. The APK never needs your Delta API Key or Secret.'),
    ('The ICT Early Structure controller can arm intrabar around liquidity sweeps, order blocks and fair value gaps. It still checks live flow, structure, news risk, spread and conflict before publishing.',
     'The ICT Early Structure controller can arm intrabar around liquidity sweeps, order blocks and fair value gaps. It checks live flow, structure, Delta market context, spread and conflict before publishing.'),
]:
    s=s.replace(a,b)

css=r'''
/* V2.8.3 stable data pipeline */
#deltaAccountPanel .controls,
#deltaCredentialPartState,
#deltaDirectToggle{display:none!important}
.v283-access{
  margin:11px 0;padding:12px;border:1px solid rgba(47,111,237,.40);
  border-radius:12px;background:#131922
}
.v283-access-head{display:flex;align-items:center;justify-content:space-between;gap:8px}
.v283-access-head b{font-size:11px}.v283-access-head span{font-size:9px;color:#8f9aa6}
.v283-token{display:grid;grid-template-columns:1fr auto;gap:7px;align-items:end;margin-top:9px}
.v283-token button{min-height:42px!important}
.v283-server-note{font-size:9px;color:#8c99a5;line-height:1.45;margin-top:8px}
.v283-server-note strong{color:#38d399}
.v283-pipeline{
  display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-top:9px
}
.v283-pipeline>div{padding:8px;border:1px solid #2b333d;border-radius:9px;background:#14191f}
.v283-pipeline span{display:block;font-size:8px;color:#78838e;text-transform:uppercase;letter-spacing:.055em}
.v283-pipeline b{display:block;font-size:10px;margin-top:4px;overflow-wrap:anywhere}
#clear[disabled]{opacity:.55!important;cursor:not-allowed!important}
@media(max-width:680px){
  .v283-token{grid-template-columns:1fr}
  .v283-pipeline{grid-template-columns:1fr 1fr 1fr}
}
'''
if 'V2.8.3 stable data pipeline' not in s:
    s=s.replace('</style>',css+'\n</style>',1)

js=r'''
/* V2.8.3 Stable Data Pipeline.
   Final repair layer for Delta context, 1m/HTF history, server account state and stale UI labels. */
var V283={version:'2.8.3',bootstrapDone:false,bootstrapBusy:false,contextBusy:false,retries:0,lastContextAt:0};
if(typeof V282!=='undefined')V282.version='2.8.3';
if(typeof V281!=='undefined')V281.version='2.8.3';
if(typeof V280!=='undefined')V280.version='2.8.3';

function v283q(id){return document.getElementById(id)}
function v283set(id,val,cl){
  var e=v283q(id);if(!e)return;
  e.textContent=(val==null||val==='')?'NA':String(val);
  if(cl)e.className=cl;
}
function v283num(v){var n=Number(v);return Number.isFinite(n)?n:null}
function v283bridge(){return window.DhanPulseNative||null}

function v283EnsureSymbols(){
  var el=v283q('symbol');if(!el)return;
  var wanted=['BTCUSD','ETHUSD'];
  var vals=Array.from(el.options||[]).map(function(o){return String(o.value||o.textContent||'')});
  wanted.forEach(function(x){
    if(vals.indexOf(x)<0){
      var o=document.createElement('option');o.value=x;o.textContent=x;el.appendChild(o);
    }
  });
  var current=(typeof S!=='undefined'&&S&&String(S.symbol||''))||String(el.value||'');
  if(wanted.indexOf(current)<0)current='BTCUSD';
  el.value=current;
  try{if(S)S.symbol=current}catch(e){}
}
function v283Tf(){try{return String(S&&S.tf||'5m')}catch(e){return '5m'}}
function v283Symbol(){try{return String(S&&S.symbol||'BTCUSD')}catch(e){return 'BTCUSD'}}

function v283CandleRows(rows){
  if(!Array.isArray(rows))return[];
  return rows.map(function(x){
    var t=v283num(x.time),o=v283num(x.open),h=v283num(x.high),l=v283num(x.low),c=v283num(x.close),v=v283num(x.volume);
    return{t:t,o:o,h:h,l:l,c:c,v:v||0,closed:true};
  }).filter(function(x){return x.t!=null&&x.o>0&&x.h>=x.l&&x.c>0}).sort(function(a,b){return a.t-b.t});
}
function v283ApplyContext(d){
  if(!d||d.success===false)return;
  try{
    var prev=v283num(S.lastCtxOI),oi=v283num(d.openInterest),delta=(prev&&oi!=null)?(oi-prev)/prev*100:0;
    if(oi!=null)S.lastCtxOI=oi;
    S.ctx=S.ctx||{};
    var patch={
      openInterest:oi,
      oiDeltaPct:delta,
      basisBps:v283num(d.basisBps),
      markPrice:v283num(d.markPrice),
      indexPrice:v283num(d.spotPrice),
      orderBookImbalance:v283num(d.orderBookImbalance),
      spreadBps:v283num(d.spreadBps),
      priceChangePercent24h:v283num(d.ltpChange24h),
      quoteVolume24h:v283num(d.turnoverUsd)
    };
    Object.keys(patch).forEach(function(k){if(patch[k]!=null)S.ctx[k]=patch[k]});
    V283.lastContextAt=Date.now();
    if(typeof render==='function')render();
    if(typeof v26map==='function'&&typeof v26render==='function'){try{var m=v26map();if(typeof V26!=='undefined')V26.map=m;v26render(m)}catch(e){}}
  }catch(e){}
}
function v283BootstrapState(label,good){
  v283set('scopeState',label,good?'bull':'neutral');
  v283set('oppState',good?'SCANNING':'LOADING','neutral');
  if(!good)v283set('oppGate','WAIT: loading 1 minute and higher timeframe history','neutral');
  var ph=v283q('pipelineHealth');
  if(ph){
    ph.className='pipeline-health '+(good?'ok':'');
    var sp=ph.querySelector('span');if(sp)sp.textContent=good?'Market pipeline ready · selected + 1m + HTF':'Loading complete Delta market structure history';
  }
}
function v283RunEngines(){
  try{
    if(typeof S==='undefined'||!S)return;
    if(S.candles&&S.candles.length>=20&&typeof analyse==='function')S.analysis=analyse(S.candles,S.ctx||{});
    if(typeof render==='function')render();
    var map=null,mic=null;
    if(typeof v26map==='function')map=v26map();
    if(typeof V26!=='undefined')V26.map=map;
    if(typeof v26render==='function')v26render(map);
    if(typeof v263micro==='function')mic=v263micro();
    if(map&&mic&&mic.ready){
      v283BootstrapState('ACTIVE',true);
      if(typeof v263select==='function')try{v263select()}catch(e){}
      else if(typeof v263render==='function')try{v263render(map,mic,null,'SCANNING')}catch(e){}
    }else{
      v283set('scopeState','BUILDING DATA','neutral');
      v283set('oppState','BUILDING','neutral');
      v283set('oppGate',!map?'WAIT: building selected timeframe structure':'WAIT: building 1 minute trigger history','neutral');
      var ict=v283q('ictState');if(ict&&/SCANNING|STARTING/.test(ict.textContent||''))ict.textContent='BUILDING STRUCTURE';
    }
  }catch(e){}
}
window.__v283Bootstrap=function(payload){
  V283.bootstrapBusy=false;
  var d=payload;try{if(typeof d==='string')d=JSON.parse(d)}catch(e){d={success:false,error:'Invalid repair response'}}
  if(!d||d.success===false){
    v283BootstrapState('RETRYING DATA',false);
    if(V283.retries<3){
      V283.retries++;
      setTimeout(v283Bootstrap,[2500,7000,16000][V283.retries-1]||16000);
    }else{
      v283set('scopeState','DATA UNAVAILABLE','bear');
      v283set('oppState','WAIT','neutral');
      v283set('oppGate','WAIT: Delta history unavailable · use Refresh Analysis','bear');
    }
    return;
  }
  try{
    var micro=v283CandleRows(d.micro||[]),htf=v283CandleRows(d.htf||[]);
    if(micro.length)S.microCandles=micro.slice(-260);
    if(htf.length)S.htfCandles=htf.slice(-180);
    if(d.context)v283ApplyContext(d.context);
    V283.bootstrapDone=!!(S.microCandles&&S.microCandles.length>=24&&S.htfCandles&&S.htfCandles.length>=20);
    V283.retries=0;
    v283RunEngines();
  }catch(e){
    v283set('scopeState','DATA ERROR','bear');
  }
};
window.__v283Context=function(payload){
  V283.contextBusy=false;
  var d=payload;try{if(typeof d==='string')d=JSON.parse(d)}catch(e){d=null}
  if(d&&d.success!==false)v283ApplyContext(d);
};
function v283Bootstrap(){
  if(V283.bootstrapBusy)return;
  var b=v283bridge();if(!b||!b.repairDeltaData)return;
  V283.bootstrapBusy=true;v283BootstrapState('LOADING DATA',false);
  try{b.repairDeltaData(v283Symbol(),v283Tf())}catch(e){V283.bootstrapBusy=false}
}
function v283Context(){
  if(V283.contextBusy)return;
  var b=v283bridge();if(!b||!b.refreshDeltaMarketContext)return;
  V283.contextBusy=true;
  try{b.refreshDeltaMarketContext(v283Symbol())}catch(e){V283.contextBusy=false}
}

function v283InstallAccount(){
  var panel=v283q('deltaAccountPanel');if(!panel)return;
  var h=panel.querySelector('h2');if(h)h.textContent='Delta Account';
  var sub=panel.querySelector('.row .muted.small');
  if(sub)sub.textContent='Your Delta API Key and Secret stay securely on the DeltaPulse Render backend. DhanPulse only requests the verified account summary.';
  var oldCard=v283q('deltaBackendCard');if(oldCard)oldCard.remove();
  var controls=panel.querySelector('.controls');if(controls)controls.remove();
  var part=v283q('deltaCredentialPartState');if(part)part.style.display='none';
  var toggle=v283q('deltaDirectToggle');if(toggle)toggle.style.display='none';

  var spans=panel.querySelectorAll('.context span');
  spans.forEach(function(x){
    if(x.textContent.trim()==='Credential')x.textContent='Server Credential';
    if(x.textContent.trim()==='Private Feed')x.textContent='Account Mode';
  });
  if(!v283q('v283AccountAccess')){
    var box=document.createElement('div');box.id='v283AccountAccess';box.className='v283-access';
    box.innerHTML='<div class="v283-access-head"><b>Secure Backend Account Access</b><span id="v283AccessState">CHECKING</span></div>'+
      '<div id="v283TokenRow" class="v283-token"><label>APP Access Token<input id="v283AppToken" type="password" autocomplete="off" placeholder="Enter current APP_ACCESS_TOKEN from Render"></label><button id="v283SaveVerify">Save & Verify</button></div>'+
      '<div class="v283-pipeline"><div><span>Delta API</span><b id="v283DeltaCred">CHECKING</b></div><div><span>App Access</span><b id="v283TokenState">CHECKING</b></div><div><span>Account</span><b id="v283AccountState">CHECKING</b></div></div>'+
      '<div class="v283-server-note"><strong>SERVER SIDE</strong> · Delta API credentials never need to be entered in this APK.</div>';
    var ctx=panel.querySelector('.context');if(ctx)ctx.parentNode.insertBefore(box,ctx);else panel.appendChild(box);
    v283q('v283SaveVerify').onclick=function(){
      var b=v283bridge(),el=v283q('v283AppToken'),v=el?el.value.trim():'';
      if(!v){v283set('v283AccessState','ENTER TOKEN','neutral');return}
      try{
        if(b&&b.saveDeltaBackendToken)b.saveDeltaBackendToken(v);
        el.value='';v283set('v283TokenState','SAVED','bull');v283VerifyAccount();
      }catch(e){v283set('v283AccessState','SAVE FAILED','bear')}
    };
  }
}
function v283TokenSaved(){
  try{var b=v283bridge();return !!(b&&b.deltaBackendTokenStatus&&String(b.deltaBackendTokenStatus())==='SAVED')}catch(e){return false}
}
function v283VerifyAccount(){
  var b=v283bridge();
  if(!v283TokenSaved()){
    v283set('v283TokenState','REQUIRED','neutral');v283set('v283AccountState','LOCKED','neutral');
    v283set('deltaAuthState','APP TOKEN REQUIRED','neutral');return;
  }
  v283set('v283TokenState','SAVED','bull');v283set('v283AccountState','VERIFYING','neutral');
  v283set('deltaAuthState','VERIFYING','neutral');
  try{if(b&&b.verifyDeltaBackendAccount)b.verifyDeltaBackendAccount()}catch(e){v283set('v283AccountState','ERROR','bear')}
}
var __v283OldBackendStatus=window.__deltaBackendStatus;
window.__deltaBackendStatus=function(payload){
  if(__v283OldBackendStatus)try{__v283OldBackendStatus(payload)}catch(e){}
  var d=payload;try{if(typeof d==='string')d=JSON.parse(d)}catch(e){d={}}
  var ready=!!(d&&d.apiKey&&d.apiSecret);
  v283set('v283DeltaCred',ready?'SERVER SAVED':'MISSING',ready?'bull':'bear');
  v283set('deltaKeyMask',ready?'SERVER SAVED':'NOT CONFIGURED',ready?'bull':'neutral');
  v283set('v283AccessState',ready?(v283TokenSaved()?'READY':'APP TOKEN NEEDED'):'DELTA CONFIG MISSING',ready?'neutral':'bear');
  if(ready&&v283TokenSaved())v283VerifyAccount();
};
var __v283OldAccountResult=window.__deltaAccountResult;
window.__deltaAccountResult=function(payload){
  if(__v283OldAccountResult)try{__v283OldAccountResult(payload)}catch(e){}
  var d=payload;try{if(typeof d==='string')d=JSON.parse(d)}catch(e){d={success:false,error:'Invalid account response'}}
  if(d&&d.success){
    v283set('deltaAuthState','CONNECTED','bull');
    v283set('deltaUserId',d.userId||'NA');
    v283set('deltaAccountName',d.accountName||'MAIN');
    v283set('deltaHolderName',d.holderName||d.displayName||'Not returned by Delta');
    v283set('deltaNetEquity',d.netEquity||'NA');
    v283set('deltaAvailable',d.primaryAvailable||'NA');
    v283set('deltaTotalBalance',d.primaryBalance||'NA');
    v283set('deltaKeyMask','SERVER SAVED','bull');
    v283set('deltaPrivateState','BACKEND READ ONLY','bull');
    v283set('v283AccountState','VERIFIED','bull');
    v283set('v283AccessState','CONNECTED','bull');
    var row=v283q('v283TokenRow');if(row)row.style.display='none';
  }else{
    var msg=String(d&&d.error||'Account verification failed');
    v283set('deltaAuthState',/token|401|access/i.test(msg)?'APP TOKEN INVALID':'ACCOUNT ERROR','bear');
    v283set('v283AccountState','NOT VERIFIED','bear');
    var row2=v283q('v283TokenRow');if(row2)row2.style.display='grid';
    var am=v283q('deltaAuthMessage');if(am)am.textContent=msg;
  }
};

function v283CleanLabels(){
  var clear=v283q('clear');if(clear){clear.textContent='History Protected';clear.disabled=true;clear.onclick=null}
  var nh=v283q('newsHeadline');if(nh&&/news engine starting/i.test(nh.textContent||''))nh.textContent='Delta market context active';
  document.querySelectorAll('b,strong,div,span').forEach(function(e){
    if(e.children&&e.children.length)return;
    var t=(e.textContent||'').trim();
    if(t==='V2.3 Research Auto')e.textContent='Adaptive Signal Engine';
    if(t==='V2.2 SIGNALS')e.textContent='LIVE SIGNALS';
    if(t==='No V2.2 signals recorded yet.')e.textContent='No live signals recorded yet.';
  });
}
function v283Startup(){
  v283EnsureSymbols();
  v283InstallAccount();
  v283CleanLabels();
  try{
    var b=v283bridge();if(b&&b.checkDeltaBackendStatus)b.checkDeltaBackendStatus();
  }catch(e){}
  if(v283TokenSaved())v283VerifyAccount();
  setTimeout(v283Bootstrap,300);
  setTimeout(v283Context,650);
}
setTimeout(v283Startup,220);
setInterval(function(){
  v283EnsureSymbols();
  v283CleanLabels();
  v283RunEngines();
  if(Date.now()-V283.lastContextAt>15000)v283Context();
  if(!V283.bootstrapDone&&!V283.bootstrapBusy&&V283.retries<3)v283Bootstrap();
},2500);
'''
if 'V2.8.3 Stable Data Pipeline.' not in s:
    s=s.replace('\n})();\n</script>',js+'\n})();\n</script>',1)

idx.write_text(s)

java_dir=root/'app/src/main/java/com/dhanpulse/cryptofxv11'
repair=java_dir/'DeltaDataRepair.java'
repair.write_text(r'''package com.dhanpulse.cryptofxv11;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;

final class DeltaDataRepair {
    interface Callback { void onResult(String json); }
    private static final String DELTA = "https://api.india.delta.exchange";
    private static final OkHttpClient HTTP = new OkHttpClient();
    private static final ExecutorService EXEC = Executors.newSingleThreadExecutor();

    private DeltaDataRepair() {}

    static void contextAsync(String symbol, Callback cb) {
        EXEC.execute(() -> cb.onResult(context(symbol).toString()));
    }

    static void bootstrapAsync(String symbol, String tf, Callback cb) {
        EXEC.execute(() -> {
            JSONObject out = new JSONObject();
            try {
                String clean = cleanSymbol(symbol);
                String htf = higherTf(tf);
                long end = System.currentTimeMillis() / 1000L;
                long microStart = end - 5L * 60L * 60L;
                long htfStart = end - 14L * 24L * 60L * 60L;
                JSONArray micro = history(clean, "1m", microStart, end);
                JSONArray higher = history(clean, htf, htfStart, end);
                JSONObject ctx = context(clean);
                out.put("success", true);
                out.put("symbol", clean);
                out.put("microResolution", "1m");
                out.put("higherResolution", htf);
                out.put("micro", micro);
                out.put("htf", higher);
                out.put("context", ctx);
            } catch (Exception e) {
                try {
                    out.put("success", false);
                    out.put("error", e.getMessage() == null ? "Delta bootstrap failed" : e.getMessage());
                } catch (Exception ignored) {}
            }
            cb.onResult(out.toString());
        });
    }

    private static JSONObject context(String symbol) {
        JSONObject out = new JSONObject();
        try {
            String clean = cleanSymbol(symbol);
            JSONObject ticker = getJson(DELTA + "/v2/tickers/" + clean);
            if (!ticker.optBoolean("success", false)) throw new Exception("Delta ticker unavailable");
            JSONObject t = ticker.optJSONObject("result");
            if (t == null) throw new Exception("Delta ticker result missing");

            JSONObject bookWrap = getJson(DELTA + "/v2/l2orderbook/" + clean + "?depth=20");
            JSONObject book = bookWrap.optJSONObject("result");
            JSONArray buy = book == null ? null : book.optJSONArray("buy");
            JSONArray sell = book == null ? null : book.optJSONArray("sell");
            double buySize = levelSize(buy), sellSize = levelSize(sell);
            JSONObject q = t.optJSONObject("quotes");
            if (buySize <= 0 && q != null) buySize = number(q.opt("bid_size"));
            if (sellSize <= 0 && q != null) sellSize = number(q.opt("ask_size"));
            double denom = buySize + sellSize;
            double imbalance = denom > 0 ? (buySize - sellSize) / denom : 0.0;
            double bid = q == null ? 0 : number(q.opt("best_bid"));
            double ask = q == null ? 0 : number(q.opt("best_ask"));
            double mid = bid > 0 && ask > 0 ? (bid + ask) / 2.0 : 0;
            double spread = mid > 0 ? (ask - bid) / mid * 10000.0 : 0;
            double mark = number(t.opt("mark_price")), spot = number(t.opt("spot_price"));
            Double basis = mark > 0 && spot > 0 ? (mark - spot) / spot * 10000.0 : null;

            out.put("success", true);
            out.put("symbol", clean);
            putNumber(out, "ltpChange24h", t.opt("ltp_change_24h"));
            putNumber(out, "openInterest", t.opt("oi"));
            putNumber(out, "openInterestValueUsd", t.opt("oi_value_usd"));
            putNumber(out, "turnoverUsd", t.opt("turnover_usd"));
            putNumber(out, "volume", t.opt("volume"));
            if (mark > 0) out.put("markPrice", mark);
            if (spot > 0) out.put("spotPrice", spot);
            if (basis != null) out.put("basisBps", basis);
            if (bid > 0) out.put("bestBid", bid);
            if (ask > 0) out.put("bestAsk", ask);
            out.put("spreadBps", spread);
            out.put("buySize", buySize);
            out.put("sellSize", sellSize);
            out.put("orderBookImbalance", imbalance);
            out.put("source", "DELTA_TICKER_PLUS_L2");
        } catch (Exception e) {
            try {
                out.put("success", false);
                out.put("error", e.getMessage() == null ? "Delta context failed" : e.getMessage());
            } catch (Exception ignored) {}
        }
        return out;
    }

    private static JSONArray history(String symbol, String resolution, long start, long end) throws Exception {
        String url = DELTA + "/v2/history/candles?symbol=" + symbol + "&resolution=" + resolution
                + "&start=" + start + "&end=" + end;
        JSONObject j = getJson(url);
        if (!j.optBoolean("success", false)) throw new Exception("Delta " + resolution + " history unavailable");
        JSONArray a = j.optJSONArray("result");
        return a == null ? new JSONArray() : a;
    }

    private static JSONObject getJson(String url) throws Exception {
        Request req = new Request.Builder().url(url)
                .header("Accept", "application/json")
                .header("User-Agent", "DhanPulse-Android/2.8.3")
                .get().build();
        try (Response r = HTTP.newCall(req).execute()) {
            String body = r.body() == null ? "" : r.body().string();
            if (!r.isSuccessful()) throw new Exception("Delta HTTP " + r.code());
            return body.isEmpty() ? new JSONObject() : new JSONObject(body);
        }
    }

    private static double levelSize(JSONArray a) {
        double total = 0;
        if (a == null) return 0;
        for (int i = 0; i < a.length(); i++) {
            JSONObject row = a.optJSONObject(i);
            if (row != null) total += number(row.opt("size"));
        }
        return total;
    }

    private static double number(Object v) {
        try { return Double.parseDouble(String.valueOf(v)); }
        catch (Exception e) { return 0.0; }
    }

    private static void putNumber(JSONObject out, String key, Object v) throws Exception {
        if (v == null || JSONObject.NULL.equals(v)) return;
        try { out.put(key, Double.parseDouble(String.valueOf(v))); } catch (Exception ignored) {}
    }

    private static String cleanSymbol(String s) {
        String x = s == null ? "" : s.trim().toUpperCase();
        if (!x.matches("[A-Z0-9:_-]{3,40}")) return "BTCUSD";
        return x;
    }

    private static String higherTf(String tf) {
        String x = tf == null ? "5m" : tf;
        switch (x) {
            case "1m": return "5m";
            case "3m": return "15m";
            case "5m": return "15m";
            case "15m": return "1h";
            case "30m": return "2h";
            case "1h": return "4h";
            case "2h": return "6h";
            case "4h": return "1d";
            case "6h": return "1d";
            case "1d": return "1w";
            default: return "15m";
        }
    }
}
''')

ma=java_dir/'MainActivity.java'
a=ma.read_text()
anchor='''        @JavascriptInterface
        public void flattradeStatus() {
'''
if anchor not in a: raise SystemExit('Flattrade bridge anchor missing')
if 'public void repairDeltaData(String symbol, String timeframe)' not in a:
    methods=r'''        @JavascriptInterface
        public void repairDeltaData(String symbol, String timeframe) {
            DeltaDataRepair.bootstrapAsync(symbol, timeframe, json ->
                    deliverJavascriptCallback("__v283Bootstrap", json));
        }

        @JavascriptInterface
        public void refreshDeltaMarketContext(String symbol) {
            DeltaDataRepair.contextAsync(symbol, json ->
                    deliverJavascriptCallback("__v283Context", json));
        }

'''
    a=a.replace(anchor,methods+anchor,1)
ma.write_text(a)

# Bump user agents where present.
for p in [
    root/'app/src/main/java/com/dhanpulse/cryptofxv11/DeltaBackendAccount.java',
    root/'app/src/main/java/com/dhanpulse/cryptofxv11/FlattradeBackend.java',
    root/'app/src/main/java/com/dhanpulse/cryptofxv11/DhanPulseMonitorService.java'
]:
    if p.exists():
        t=p.read_text()
        t=re.sub(r'DhanPulse-Android/2\.[0-9.]+','DhanPulse-Android/2.8.3',t)
        p.write_text(t)

b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 51',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.8.3"',bs,count=1)
b.write_text(bs)
