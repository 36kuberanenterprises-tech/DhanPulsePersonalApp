from pathlib import Path
import re, json

ROOT = Path(__file__).resolve().parent
SERVICE = ROOT / "app/src/main/java/com/dhanpulse/cryptofxnative/BackgroundService.java"
ACTIVITY = ROOT / "app/src/main/java/com/dhanpulse/cryptofxnative/MainActivity.java"
GRADLE = ROOT / "app/build.gradle.kts"
INDEX = ROOT / "app/src/main/assets/index.html"


def replace_method(text, signature, new_method):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f"Method not found: {signature}")
    brace = text.find("{", start)
    if brace < 0:
        raise SystemExit(f"Opening brace not found: {signature}")
    depth = 0
    in_str = None
    esc = False
    end = None
    for i in range(brace, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == in_str:
                in_str = None
            continue
        if ch in ('"', "'"):
            in_str = ch
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise SystemExit(f"Method end not found: {signature}")
    return text[:start] + new_method.rstrip() + text[end:]


s = SERVICE.read_text(encoding="utf-8")

# -----------------------------------------------------------------------------
# 1. Fallback feed state.  If Binance WebSocket is blocked by the phone network,
# use actual Binance aggregate trades + depth REST endpoints instead of a simple
# ticker price.  Aggregate trades contain trade side, size and exchange time, so
# the native microstructure engine can still build order flow rather than guessing.
# -----------------------------------------------------------------------------
field_anchor = '    private volatile String wsEndpointMode = "RAW SUBSCRIBE";\n'
fields = '''    private volatile String wsEndpointMode = "RAW SUBSCRIBE";\n    private volatile boolean restMicroBusy = false;\n    private volatile long lastRestMicroPoll = 0L;\n    private volatile long lastRestMicroReceived = 0L;\n    private volatile long lastRestDepthReceived = 0L;\n    private volatile long lastRestAggTradeId = -1L;\n    private volatile String nativeTurnState = "MONITORING";\n    private volatile String nativeTurnLocation = "NA";\n    private volatile String nativeTurnReason = "Waiting for native microstructure";\n    private volatile String nativeTurnFlow = "NA";\n'''
if field_anchor not in s:
    raise SystemExit('V2.1.6 field anchor not found')
s = s.replace(field_anchor, fields, 1)

# Reset fallback sequencing when the symbol/timeframe connection is rebuilt.
s = s.replace(
    '        lastWsTradeReceived = 0L;\n        lastSocketOpenedAt = 0L;',
    '        lastWsTradeReceived = 0L;\n        lastSocketOpenedAt = 0L;\n        lastRestAggTradeId = -1L;\n        lastRestMicroReceived = 0L;\n        lastRestDepthReceived = 0L;',
    1
)

# -----------------------------------------------------------------------------
# 2. Watchdog.  WS is still preferred, but after a short WS outage the app begins
# polling aggregate trades + depth.  The old price-only REST endpoint remains a
# last-resort display/position tracker, not the primary fallback entry feed.
# -----------------------------------------------------------------------------
old_watch = '''            long wsRef = lastWsTradeReceived > 0 ? lastWsTradeReceived : lastSocketOpenedAt;
            long wsAge = wsRef > 0 ? now - wsRef : Long.MAX_VALUE;
            if (wsAge > 2500L) fetchRestPrice();
            if (wsAge > 7000L && now - lastReconnectAttempt > 6000L) {
                lastReconnectAttempt = now;
                engine.execute(() -> reconnectNow("watchdog stale WS trade feed"));
            }'''
new_watch = '''            long wsRef = lastWsTradeReceived > 0 ? lastWsTradeReceived : lastSocketOpenedAt;
            long wsAge = wsRef > 0 ? now - wsRef : Long.MAX_VALUE;
            if (wsAge > 1800L) {
                fetchRestMicrostructure();
                if (lastRestMicroReceived == 0L || now - lastRestMicroReceived > 3000L) fetchRestPrice();
            }
            if (wsAge > 7000L && now - lastReconnectAttempt > 6000L) {
                lastReconnectAttempt = now;
                engine.execute(() -> reconnectNow("watchdog stale WS trade feed"));
            }'''
if old_watch not in s:
    raise SystemExit('V2.1.6 watchdog target not found')
s = s.replace(old_watch, new_watch, 1)

# -----------------------------------------------------------------------------
# 3. REST microstructure fallback implementation.
# -----------------------------------------------------------------------------
rest_methods = r'''    private void fetchRestMicrostructure() {
        long now = System.currentTimeMillis();
        if (restMicroBusy || now - lastRestMicroPoll < 900L) return;
        restMicroBusy = true;
        lastRestMicroPoll = now;
        fetchRestDepth();
        Request req = new Request.Builder()
                .url("https://fapi.binance.com/fapi/v1/aggTrades?symbol=" + symbol + "&limit=100")
                .build();
        client.newCall(req).enqueue(new Callback() {
            @Override public void onFailure(Call call, IOException e) { restMicroBusy = false; }
            @Override public void onResponse(Call call, Response response) throws IOException {
                String body = "[]";
                try (Response r = response) {
                    if (r.body() != null) body = r.body().string();
                }
                final String payload = body;
                engine.execute(() -> {
                    try { ingestRestAggTrades(payload); }
                    finally { restMicroBusy = false; }
                });
            }
        });
    }

    private void fetchRestDepth() {
        Request req = new Request.Builder()
                .url("https://fapi.binance.com/fapi/v1/depth?symbol=" + symbol + "&limit=20")
                .build();
        client.newCall(req).enqueue(new Callback() {
            @Override public void onFailure(Call call, IOException e) {}
            @Override public void onResponse(Call call, Response response) throws IOException {
                String body = "{}";
                try (Response r = response) {
                    if (r.body() != null) body = r.body().string();
                }
                final String payload = body;
                engine.execute(() -> ingestRestDepth(payload));
            }
        });
    }

    private void ingestRestDepth(String body) {
        try {
            JSONObject data = new JSONObject(body);
            JSONArray bids = data.optJSONArray("bids");
            JSONArray asks = data.optJSONArray("asks");
            double bidWeighted = 0.0, askWeighted = 0.0;
            if (bids != null) {
                for (int j = 0; j < Math.min(20, bids.length()); j++) {
                    JSONArray row = bids.optJSONArray(j);
                    if (row == null || row.length() < 2) continue;
                    double p = row.optDouble(0, 0.0), q = row.optDouble(1, 0.0);
                    if (j == 0 && p > 0) bestBid = p;
                    double w = 1.0 / (1.0 + j * 0.35);
                    bidWeighted += Math.max(0.0, p * q) * w;
                }
            }
            if (asks != null) {
                for (int j = 0; j < Math.min(20, asks.length()); j++) {
                    JSONArray row = asks.optJSONArray(j);
                    if (row == null || row.length() < 2) continue;
                    double p = row.optDouble(0, 0.0), q = row.optDouble(1, 0.0);
                    if (j == 0 && p > 0) bestAsk = p;
                    double w = 1.0 / (1.0 + j * 0.35);
                    askWeighted += Math.max(0.0, p * q) * w;
                }
            }
            double total = bidWeighted + askWeighted;
            if (total > 0) {
                long now = System.currentTimeMillis();
                double rawDepth = (bidWeighted - askWeighted) / total;
                addDepthSample(now, rawDepth);
                orderBookImbalance = depthComposite();
                lastDepthReceived = now;
                lastRestDepthReceived = now;
            }
            if (Double.isFinite(bestBid) && Double.isFinite(bestAsk) && bestBid > 0 && bestAsk >= bestBid) {
                double mid = (bestBid + bestAsk) / 2.0;
                spreadBps = mid > 0 ? (bestAsk - bestBid) / mid * 10000.0 : Double.NaN;
            }
        } catch (Exception ignored) {}
    }

    private void ingestRestAggTrades(String body) {
        try {
            JSONArray arr = new JSONArray(body);
            if (arr.length() == 0) return;
            long now = System.currentTimeMillis();
            if (lastRestAggTradeId < 0L) {
                int start = Math.max(0, arr.length() - 80);
                JSONObject latest = null;
                for (int i = start; i < arr.length(); i++) {
                    JSONObject t = arr.optJSONObject(i);
                    if (t == null) continue;
                    long id = t.optLong("a", -1L);
                    double qty = t.optDouble("q", 0.0);
                    long ts = t.optLong("T", now);
                    boolean aggressiveBuy = !t.optBoolean("m", false);
                    if (qty > 0) addFlow(ts, qty, aggressiveBuy);
                    if (id > lastRestAggTradeId) lastRestAggTradeId = id;
                    latest = t;
                }
                lastRestMicroReceived = now;
                if (latest != null) {
                    double p = latest.optDouble("p", Double.NaN);
                    long ts = latest.optLong("T", now);
                    if (Double.isFinite(p)) processTick(p, 0.0, false, ts, "REST MICRO");
                }
                return;
            }

            boolean gotNew = false;
            for (int i = 0; i < arr.length(); i++) {
                JSONObject t = arr.optJSONObject(i);
                if (t == null) continue;
                long id = t.optLong("a", -1L);
                if (id <= lastRestAggTradeId) continue;
                double p = t.optDouble("p", Double.NaN);
                double q = t.optDouble("q", 0.0);
                long ts = t.optLong("T", now);
                boolean aggressiveBuy = !t.optBoolean("m", false);
                lastRestAggTradeId = Math.max(lastRestAggTradeId, id);
                if (Double.isFinite(p)) {
                    lastRestMicroReceived = now;
                    processTick(p, q, aggressiveBuy, ts, "REST MICRO");
                    gotNew = true;
                }
            }
            if (!gotNew) lastRestMicroReceived = now;
        } catch (Exception ignored) {}
    }

'''
anchor = '    private void fetchRestPrice() {'
if anchor not in s:
    raise SystemExit('fetchRestPrice anchor not found')
s = s.replace(anchor, rest_methods + anchor, 1)

# -----------------------------------------------------------------------------
# 4. Entry feed authority.  WS remains best. REST MICRO is permitted only while
# actual aggregate trades and depth are both fresh. Plain REST ticker is never
# allowed to create a signal.
# -----------------------------------------------------------------------------
new_process_tick = r'''    private void processTick(double price, double qty, boolean aggressiveBuy, long exchangeTs, String source) {
        long startNs = System.nanoTime();
        long now = System.currentTimeMillis();
        lastPrice = price;
        lastTickReceived = now;
        lastExchangeEvent = exchangeTs;

        boolean wsTrade = "WS TRADE".equals(source);
        boolean restMicro = "REST MICRO".equals(source);
        if (wsTrade) {
            lastWsTradeReceived = now;
            feedMode = "WS TRADE";
        } else if (restMicro) {
            lastRestMicroReceived = now;
            if (lastWsTradeReceived == 0L || now - lastWsTradeReceived > 1800L) feedMode = "REST MICRO";
        } else if (lastWsTradeReceived == 0L || now - lastWsTradeReceived > 2500L) {
            if (lastRestMicroReceived > 0L && now - lastRestMicroReceived < 2500L) feedMode = "REST MICRO";
            else feedMode = source;
        }

        if (qty > 0) addFlow(exchangeTs, qty, aggressiveBuy);
        updateSynthetic(microCandles, price, exchangeTs, 60_000L, qty, aggressiveBuy);
        updateSynthetic(mainCandles, price, exchangeTs, tfMillis(tf), qty, aggressiveBuy);
        checkTrades(price, exchangeTs);

        boolean depthFresh = lastDepthReceived > 0L && now - lastDepthReceived < 3500L;
        boolean microFresh = lastRestMicroReceived > 0L && now - lastRestMicroReceived < 2500L;
        boolean entryFeed = wsTrade || (restMicro && microFresh && depthFresh);

        if (entryFeed) {
            Turning turn = detectTurningFast(price);
            nativeTurnState = turn.state;
            nativeTurnLocation = turn.location;
            nativeTurnReason = turn.reason;
            nativeTurnFlow = String.format(Locale.US, "%.1f%%", turn.flow * 100.0);
            signalState = turn.state;
            considerFastTurning(turn, price);
            if (now - lastMainSignalAt > 150L) {
                lastMainSignalAt = now;
                analyseMainAndMaybeRecord();
            }
        } else {
            nativeTurnState = "FEED RECOVERY";
            nativeTurnLocation = "NA";
            nativeTurnReason = restMicro ? "Aggregate trades active; waiting for fresh depth" : "Building native microstructure feed";
            nativeTurnFlow = "NA";
            signalState = "MONITOR ONLY · " + source + " · BUILDING MICRO FEED";
        }
        lastEngineMs = (System.nanoTime() - startNs) / 1_000_000.0;
    }'''
s = replace_method(s, '    private void processTick(double price, double qty, boolean aggressiveBuy, long exchangeTs, String source)', new_process_tick)

# -----------------------------------------------------------------------------
# 5. Tighten reversal detection.  A falling candle near its low is no longer
# called BOTTOM WATCH just because it has a lower wick. A reversal must reclaim
# the swept level / fast EMA or break micro structure. Continuation is handled by
# the separate momentum/trend engines.
# -----------------------------------------------------------------------------
new_turn = r'''    private Turning detectTurningFast(double price) {
        if (microCandles.size() < 22 || !Double.isFinite(price)) return Turning.monitoring();
        int i = microCandles.size() - 1;
        Candle x = microCandles.get(i);
        double av = atrLast(microCandles, 14);
        if (!Double.isFinite(av) || av <= 0) av = Math.abs(price) * 0.0015;

        double priorHigh = maxHigh(microCandles, Math.max(0, i - 12), i);
        double priorLow = minLow(microCandles, Math.max(0, i - 12), i);
        double microHigh = maxHigh(microCandles, Math.max(0, i - 4), i);
        double microLow = minLow(microCandles, Math.max(0, i - 4), i);

        int n = microCandles.size();
        double[] close = new double[n];
        for (int j = 0; j < n; j++) close[j] = microCandles.get(j).c;
        double[] e5 = ema(close, 5);
        double fast = e5[n - 1];

        double flow = ensembleFlow();
        double depth = depthComposite();
        double range = Math.max(x.h - x.l, 1e-9);
        double loc = (price - x.l) / range;
        double upper = (x.h - Math.max(x.o, price)) / range;
        double lower = (Math.min(x.o, price) - x.l) / range;

        boolean topSweep = x.h > priorHigh + av * 0.03;
        boolean bottomSweep = x.l < priorLow - av * 0.03;
        boolean topReclaim = topSweep && price < priorHigh - av * 0.02 && loc < 0.55;
        boolean bottomReclaim = bottomSweep && price > priorLow + av * 0.02 && loc > 0.45;
        boolean topWick = upper > 0.34 && loc < 0.46 && (!Double.isFinite(fast) || price < fast);
        boolean bottomWick = lower > 0.34 && loc > 0.54 && (!Double.isFinite(fast) || price > fast);
        boolean microBreakDown = price < microLow - av * 0.015;
        boolean microBreakUp = price > microHigh + av * 0.015;
        boolean sellFlow = flow < -0.07;
        boolean buyFlow = flow > 0.07;
        boolean sellBook = depth < -0.10;
        boolean buyBook = depth > 0.10;
        boolean downImpulse = price < x.o && loc < 0.30 && (flow < -0.03 || depth < -0.05);
        boolean upImpulse = price > x.o && loc > 0.70 && (flow > 0.03 || depth > 0.05);

        int ts = 0, bs = 0;
        ArrayList<String> tr = new ArrayList<>();
        ArrayList<String> br = new ArrayList<>();
        if (topSweep) { ts += 3; tr.add("high liquidity swept"); }
        if (topReclaim) { ts += 3; tr.add("swept high rejected"); }
        else if (topWick) { ts += 1; tr.add("upper wick rejection"); }
        if (sellFlow) { ts += 2; tr.add("persistent seller flow"); }
        if (sellBook) { ts += 1; tr.add("depth favors sellers"); }
        if (Double.isFinite(fast) && price < fast) { ts += 1; tr.add("below fast EMA"); }
        if (microBreakDown) { ts += 2; tr.add("micro structure broke down"); }

        if (bottomSweep) { bs += 3; br.add("low liquidity swept"); }
        if (bottomReclaim) { bs += 3; br.add("swept low reclaimed"); }
        else if (bottomWick) { bs += 1; br.add("lower wick rejection"); }
        if (buyFlow) { bs += 2; br.add("persistent buyer flow"); }
        if (buyBook) { bs += 1; br.add("depth favors buyers"); }
        if (Double.isFinite(fast) && price > fast) { bs += 1; br.add("above fast EMA"); }
        if (microBreakUp) { bs += 2; br.add("micro structure broke up"); }

        if (downImpulse && !bottomReclaim) {
            return new Turning("DOWN IMPULSE", -1, Math.max(2, ts), false, "TREND", flow,
                    "Bearish impulse active; no confirmed bottom reclaim", priorLow);
        }
        if (upImpulse && !topReclaim) {
            return new Turning("UP IMPULSE", 1, Math.max(2, bs), false, "TREND", flow,
                    "Bullish impulse active; no confirmed top rejection", priorHigh);
        }

        Turning out = new Turning("MID RANGE", 0, 0, false, "MID", flow, "No confirmed turning point", Double.NaN);
        boolean nearTop = (priorHigh - price) <= av * 0.35 || topSweep;
        boolean nearBottom = (price - priorLow) <= av * 0.35 || bottomSweep;
        if (nearTop && ts >= 3 && (topReclaim || topWick))
            out = new Turning("TOP WATCH", -1, ts, false, "TOP", flow, join(tr), priorHigh);
        if (nearBottom && bs >= 3 && bs > ts && (bottomReclaim || bottomWick))
            out = new Turning("BOTTOM WATCH", 1, bs, false, "BOTTOM", flow, join(br), priorLow);

        if (ts >= 7 && (topReclaim || (topWick && microBreakDown)) &&
                (sellFlow || sellBook || microBreakDown) && (!Double.isFinite(fast) || price < fast))
            out = new Turning("TOP SELL TRIGGER", -1, ts, true, "TOP", flow, join(tr), x.h);
        if (bs >= 7 && (bottomReclaim || (bottomWick && microBreakUp)) &&
                (buyFlow || buyBook || microBreakUp) && (!Double.isFinite(fast) || price > fast))
            out = new Turning("BOTTOM BUY TRIGGER", 1, bs, true, "BOTTOM", flow, join(br), x.l);
        return out;
    }'''
s = replace_method(s, '    private Turning detectTurningFast(double price)', new_turn)

# Heartbeat exposes the real fallback and native turning diagnostics.
needle = '                .putString("ws_endpoint_mode", wsEndpointMode)\n'
replacement = '''                .putString("ws_endpoint_mode", wsEndpointMode)\n                .putLong("last_rest_micro_received", lastRestMicroReceived)\n                .putLong("last_rest_depth_received", lastRestDepthReceived)\n                .putString("native_turn_state", nativeTurnState)\n                .putString("native_turn_location", nativeTurnLocation)\n                .putString("native_turn_reason", nativeTurnReason)\n                .putString("native_turn_flow", nativeTurnFlow)\n'''
if needle not in s:
    raise SystemExit('heartbeat V2.1.6 anchor not found')
s = s.replace(needle, replacement, 1)
s = s.replace('t.put("engineVersion", "2.1.0");', 't.put("engineVersion", "2.1.6");')
SERVICE.write_text(s, encoding="utf-8")


# -----------------------------------------------------------------------------
# 6. Android bridge state + UI. Browser calculations remain diagnostic; native
# turning state and native recorded plan own all visible signal panels and chart
# trade levels. This removes contradictions such as BOTTOM WATCH during a strong
# native bearish impulse.
# -----------------------------------------------------------------------------
a = ACTIVITY.read_text(encoding="utf-8")
a = a.replace(
    '                long wsTick = prefs.getLong("last_ws_trade_received", 0);',
    '                long wsTick = prefs.getLong("last_ws_trade_received", 0);\n                long restMicro = prefs.getLong("last_rest_micro_received", 0);',
    1
)
a = a.replace(
    '                o.put("wsEndpointMode", prefs.getString("ws_endpoint_mode", ""));',
    '                o.put("wsEndpointMode", prefs.getString("ws_endpoint_mode", ""));\n'
    '                o.put("restMicroAgeMs", restMicro > 0 ? Math.max(0, now - restMicro) : -1);\n'
    '                o.put("turnState", prefs.getString("native_turn_state", "MONITORING"));\n'
    '                o.put("turnLocation", prefs.getString("native_turn_location", "NA"));\n'
    '                o.put("turnReason", prefs.getString("native_turn_reason", "Waiting for native microstructure"));\n'
    '                o.put("turnFlow", prefs.getString("native_turn_flow", "NA"));',
    1
)

js = r'''(function(){
if(window.__dhanpulseNativeBridgeV216)return;
window.__dhanpulseNativeBridgeV216=true;
window.__nativeDecisionAuthority=true;
var K='dhanpulse_cf_android_trades_v21',lastNative='',lastState={};
function el(id){return document.getElementById(id)}
function num(v){var n=Number(v);return isFinite(n)?n:null}
function fmt(v){var n=num(v);if(n===null)return 'NA';return Math.abs(n)>=1000?n.toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2}):n.toFixed(4)}
function nativeTrades(){try{var a=JSON.parse(AndroidNative.getNativeTrades()||'[]');return Array.isArray(a)?a:[]}catch(e){return []}}
function latestOpen(st,a){var best=null;(a||[]).forEach(function(t){if(t.status==='OPEN'&&t.symbol===(st.symbol||'')&&t.tf===(st.tf||'')){if(!best||(t.createdAt||0)>(best.createdAt||0))best=t}});return best}
function copyNativeTrades(){try{var raw=AndroidNative.getNativeTrades()||'[]';if(raw!==lastNative){lastNative=raw;var a=JSON.parse(raw);if(!Array.isArray(a))a=[];localStorage.setItem(K,JSON.stringify(a));if(window.S)S.tradeCache=a;if(window.renderTrades)renderTrades()}}catch(e){}}
function paint(st){
 lastState=st||{};
 var fm=String(st.feedMode||'STARTING'),ss=String(st.signalState||'MONITORING');
 var ws=fm.indexOf('WS')===0,rm=fm.indexOf('REST MICRO')===0,entryFeed=ws||rm;
 var c=el('conn');if(c){c.textContent='NATIVE '+fm;c.className='badge '+(entryFeed?'live':'')}
 var bg=el('bgState');if(bg){bg.textContent=st.active?'NATIVE ACTIVE':'STARTING';bg.className=st.active?'bull':'neutral'}
 var bh=el('bgHeartbeat');if(bh)bh.textContent='tick '+(st.tickAgeMs>=0?st.tickAgeMs:'NA')+' ms · '+fm+' · '+ss;
 var bs=el('bgSymbol');if(bs)bs.textContent=st.symbol||'';var bt=el('bgTf');if(bt)bt.textContent=st.tf||'';
 var tl=el('tradeLogState');if(tl)tl.textContent='Native V2.1.6 · '+fm+' · '+ss+' · tick '+(st.tickAgeMs>=0?st.tickAgeMs:'NA')+' ms';
 var lp=num(st.lastPrice),pe=el('price');if(pe&&lp!==null)pe.textContent=fmt(lp);
 var ts=el('turnState');if(ts)ts.textContent=st.turnState||'MONITORING';
 var tloc=el('turnLocation');if(tloc)tloc.textContent=st.turnLocation||'NA';
 var tf=el('turnFlow');if(tf)tf.textContent=st.turnFlow||'NA';
 var tr=el('turnReason');if(tr)tr.textContent=st.turnReason||'Waiting for native microstructure';
 var em=el('engineMs');if(em&&st.engineMs)em.textContent=st.engineMs+' ms';
 var ev=el('eventType');if(ev)ev.textContent=fm;
 var a=nativeTrades(),open=latestOpen(st,a),side='',stage='',reason='',q=Number(st.ensembleConfidence||0);
 if(open){side=String(open.side||'');stage='RECORDED · '+String(open.stage||'NATIVE SIGNAL');reason='Native signal recorded and being tracked';}
 else if(ss.indexOf('TRIGGERED')>=0){side=ss.indexOf('BUY')>=0?'BUY':ss.indexOf('SELL')>=0?'SELL':'';stage=ss;reason='Native trigger fired. Recording sync in progress';}
 else if(ss.indexOf('ARMED')>=0){stage=ss;reason='Native setup is armed and waiting for final confirmation';}
 else if(rm){stage=ss;reason='REST aggregate trades + Depth20 microstructure active. Native entries are enabled.';}
 else if(!entryFeed){stage='FEED RECOVERY · '+fm;reason='Building aggregate-trade/depth fallback. Price-only REST never creates a trade.';}
 else {stage=ss;reason='Native engine is monitoring. No confirmed entry yet';}
 var d=el('decision'),card=el('decisionCard'),sc=el('score'),sg=el('stage'),rs=el('reason'),pd=el('pdir');
 var published=(side==='BUY'||side==='SELL');
 if(d)d.textContent=published?side:'WAIT';
 if(card)card.className='panel decision '+(published?side.toLowerCase():'wait');
 if(sc)sc.textContent='Native Q '+q+' | '+(st.activeStrategy||'WAIT');
 if(sg)sg.textContent='Stage: '+(stage||'WAIT');
 if(rs)rs.textContent=reason;
 if(pd)pd.textContent=published?side:'WAIT';
 ['entry','sl','t1','t2','t3'].forEach(function(id){var x=el(id);if(x)x.textContent=open?fmt(open[id]):'NA'});
 window.__nativeChartPlan=open?{direction:side,entry:Number(open.entry),sl:Number(open.sl),t1:Number(open.t1),t2:Number(open.t2),t3:Number(open.t3)}:null;
 var r=el('record');if(r){r.disabled=true;r.textContent='Native Auto Record'}
 try{if(window.draw)draw()}catch(e){}
}
window.__renderNativeDecision=function(){paint(lastState||{})};
function sync(){try{var s=el('symbol'),tf=el('tf');if(s&&tf)AndroidNative.setMonitoringConfig(s.value,tf.value);var st=JSON.parse(AndroidNative.getNativeState()||'{}');paint(st);copyNativeTrades();AndroidNative.ensureService()}catch(e){}}
['symbol','tf'].forEach(function(id){var x=el(id);if(x)x.addEventListener('change',function(){setTimeout(sync,40)})});
var clr=el('clear');if(clr)clr.addEventListener('click',function(){setTimeout(function(){AndroidNative.clearNativeTrades();localStorage.removeItem(K);if(window.S)S.tradeCache=[];copyNativeTrades()},250)});
var anchor=el('bgState');if(anchor){var p=anchor.closest('.panel');if(p&&!el('nativeBatteryBtn')){var b=document.createElement('button');b.id='nativeBatteryBtn';b.textContent='Allow 24/7 Background';b.style.marginTop='12px';b.style.width='100%';b.onclick=function(){AndroidNative.openBatterySettings()};p.appendChild(b)}}
setInterval(sync,300);sync();
})();'''
java_method = '''    private void injectNativeBridge() {\n        String js = %s;\n        webView.evaluateJavascript(js, null);\n    }''' % json.dumps(js)
a = replace_method(a, '    private void injectNativeBridge()', java_method)
a = a.replace('Native V2.1.5 · ', 'Native V2.1.6 · ')
ACTIVITY.write_text(a, encoding="utf-8")


# Web view: no browser BUY/SELL flicker between native sync cycles, and chart
# levels are drawn only for a recorded native signal.
h = INDEX.read_text(encoding="utf-8")
h = replace_method(h, 'function renderFast(price)', 'function renderFast(price){if(finite(price)){q("price").textContent=fmt(price,dec(price));renderMarketStamp()}}')
h = h.replace(
    'var fs=effectiveSignal(),pl=fs?fs.plan:S.analysis.plan,dir=fs?fs.decision:S.analysis.decision;',
    'var pl=window.__nativeChartPlan||null,dir=pl?pl.direction:"WAIT";',
    1
)
h = h.replace('Version 2.1.5 WS Recovery', 'Version 2.1.6 Hybrid Micro Feed')
h = h.replace('V2.1.5 Signals', 'V2.1.6 Signals')
h = h.replace('No V2.1.5 signals recorded yet.', 'No V2.1.6 signals recorded yet.')
h = h.replace('NATIVE V2.1.5', 'NATIVE V2.1.6')
INDEX.write_text(h, encoding="utf-8")


g = GRADLE.read_text(encoding="utf-8")
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 27', g)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.1.6"', g)
GRADLE.write_text(g, encoding="utf-8")

print('DhanPulse V2.1.6 hybrid REST microstructure fallback and native signal correction applied')
