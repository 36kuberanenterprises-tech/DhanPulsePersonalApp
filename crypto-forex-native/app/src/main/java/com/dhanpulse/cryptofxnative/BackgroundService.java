package com.dhanpulse.cryptofxnative;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ServiceInfo;
import android.net.ConnectivityManager;
import android.net.Network;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;

import androidx.annotation.Nullable;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.IOException;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;

public class BackgroundService extends Service {
    public static final String ACTION_START = "com.dhanpulse.cryptofxnative.START";
    public static final String ACTION_CONFIG = "com.dhanpulse.cryptofxnative.CONFIG";
    public static final String ACTION_CLEAR = "com.dhanpulse.cryptofxnative.CLEAR";

    private static final String PREFS = "dhanpulse_native_monitor";
    private static final String TRADES_KEY = "native_trades_json";
    private static final String CHANNEL = "dhanpulse_monitor_native";
    private static final String SIGNAL_CHANNEL = "dhanpulse_signal_native";
    private static final int NOTIFICATION_ID = 1901;

    private SharedPreferences prefs;
    private Handler handler;
    private ExecutorService engine;
    private OkHttpClient client;
    private WebSocket socket;
    private PowerManager.WakeLock wakeLock;
    private ConnectivityManager connectivityManager;
    private ConnectivityManager.NetworkCallback networkCallback;
    private final AtomicInteger generation = new AtomicInteger(0);

    private String symbol = "BTCUSDT";
    private String tf = "5m";
    private volatile String feedMode = "STARTING";
    private volatile String signalState = "MONITORING";
    private volatile double lastPrice = Double.NaN;
    private volatile long lastTickReceived = 0L;
    private volatile long lastExchangeEvent = 0L;
    private volatile double lastEngineMs = 0.0;
    private volatile int reconnects = 0;
    private volatile boolean restBusy = false;
    private volatile long lastRestSync = 0L;
    private volatile long lastNotificationUpdate = 0L;
    private volatile long lastTradesReload = 0L;

    private final ArrayList<Candle> microCandles = new ArrayList<>();
    private final ArrayList<Candle> mainCandles = new ArrayList<>();
    private final ArrayDeque<FlowTrade> flowTrades = new ArrayDeque<>();
    private double flowBuy = 0.0;
    private double flowSell = 0.0;
    private volatile double orderBookImbalance = 0.0;

    private final ArrayList<JSONObject> trades = new ArrayList<>();
    private String lastTradesRaw = "[]";

    private String pendingTurnKey = null;
    private int pendingTurnCount = 0;
    private String lastRecordedTurnKey = null;
    private long lastRecordedTurnAt = 0L;
    private long lastMainSignalAt = 0L;
    private String lastMainSignalKey = null;

    @Override
    public void onCreate() {
        super.onCreate();
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        handler = new Handler(Looper.getMainLooper());
        engine = Executors.newSingleThreadExecutor();
        client = new OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(0, TimeUnit.MILLISECONDS)
                .writeTimeout(10, TimeUnit.SECONDS)
                .pingInterval(15, TimeUnit.SECONDS)
                .retryOnConnectionFailure(true)
                .build();
        symbol = normalizeSymbol(prefs.getString("symbol", "BTCUSDT"));
        tf = normalizeTf(prefs.getString("tf", "5m"));
        acquireWakeLock();
        createChannels();
        startForegroundSafe(buildNotification("Starting native market engine"));
        registerNetworkCallback();
        engine.execute(() -> {
            reloadTradesFromPrefs();
            reconnectNow("service start");
        });
        handler.post(watchdog);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null) {
            String action = intent.getAction();
            if (ACTION_CLEAR.equals(action)) {
                engine.execute(() -> {
                    trades.clear();
                    persistTrades();
                });
            } else if (ACTION_CONFIG.equals(action)) {
                String newSymbol = normalizeSymbol(intent.getStringExtra("symbol"));
                String newTf = normalizeTf(intent.getStringExtra("tf"));
                if (!newSymbol.equals(symbol) || !newTf.equals(tf)) {
                    symbol = newSymbol;
                    tf = newTf;
                    prefs.edit().putString("symbol", symbol).putString("tf", tf).apply();
                    engine.execute(() -> reconnectNow("configuration changed"));
                }
            }
        }
        return START_STICKY;
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        generation.incrementAndGet();
        if (socket != null) {
            try { socket.cancel(); } catch (Exception ignored) {}
            socket = null;
        }
        if (networkCallback != null && connectivityManager != null) {
            try { connectivityManager.unregisterNetworkCallback(networkCallback); } catch (Exception ignored) {}
        }
        handler.removeCallbacksAndMessages(null);
        if (wakeLock != null && wakeLock.isHeld()) {
            try { wakeLock.release(); } catch (Exception ignored) {}
        }
        if (engine != null) engine.shutdownNow();
        if (client != null) {
            try { client.dispatcher().executorService().shutdown(); } catch (Exception ignored) {}
            try { client.connectionPool().evictAll(); } catch (Exception ignored) {}
        }
        super.onDestroy();
    }

    private void acquireWakeLock() {
        PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "DhanPulse::NativeMarketMonitor");
        wakeLock.setReferenceCounted(false);
        wakeLock.acquire();
    }

    private void createChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            NotificationChannel monitor = new NotificationChannel(CHANNEL, "DhanPulse Background Monitoring", NotificationManager.IMPORTANCE_LOW);
            monitor.setDescription("Continuous crypto market monitoring and signal tracking");
            monitor.setShowBadge(false);
            nm.createNotificationChannel(monitor);
            NotificationChannel signals = new NotificationChannel(SIGNAL_CHANNEL, "DhanPulse Signals", NotificationManager.IMPORTANCE_HIGH);
            signals.setDescription("DhanPulse buy and sell signal notifications");
            nm.createNotificationChannel(signals);
        }
    }

    private void startForegroundSafe(Notification notification) {
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
        } else {
            startForeground(NOTIFICATION_ID, notification);
        }
    }

    private Notification buildNotification(String text) {
        Intent open = new Intent(this, MainActivity.class);
        PendingIntent pi = PendingIntent.getActivity(this, 0, open, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder b = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O ? new Notification.Builder(this, CHANNEL) : new Notification.Builder(this);
        String price = Double.isFinite(lastPrice) ? formatPrice(lastPrice) : "waiting";
        return b.setSmallIcon(android.R.drawable.stat_notify_sync_noanim)
                .setContentTitle("DhanPulse Native Monitor")
                .setContentText(symbol + " " + price + " · " + text)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setContentIntent(pi)
                .build();
    }

    private void updateNotification() {
        long now = System.currentTimeMillis();
        long age = lastTickReceived > 0 ? now - lastTickReceived : -1;
        String text = feedMode + (age >= 0 ? " · tick " + age + " ms" : "") + " · " + signalState;
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        nm.notify(NOTIFICATION_ID, buildNotification(text));
    }

    private void notifySignal(String side, String stage, double entry) {
        Intent open = new Intent(this, MainActivity.class);
        PendingIntent pi = PendingIntent.getActivity(this, 1, open, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder b = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O ? new Notification.Builder(this, SIGNAL_CHANNEL) : new Notification.Builder(this);
        Notification n = b.setSmallIcon(android.R.drawable.stat_notify_more)
                .setContentTitle("DhanPulse " + side + " Trigger")
                .setContentText(symbol + " · " + stage + " · Entry " + formatPrice(entry))
                .setAutoCancel(true)
                .setContentIntent(pi)
                .build();
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        nm.notify((int) (System.currentTimeMillis() % 100000) + 2000, n);
    }

    private void registerNetworkCallback() {
        connectivityManager = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        networkCallback = new ConnectivityManager.NetworkCallback() {
            @Override
            public void onAvailable(Network network) {
                handler.postDelayed(() -> engine.execute(() -> reconnectNow("network available")), 400);
            }

            @Override
            public void onLost(Network network) {
                feedMode = "NETWORK LOST";
                writeHeartbeat();
            }
        };
        try { connectivityManager.registerDefaultNetworkCallback(networkCallback); } catch (Exception ignored) {}
    }

    private final Runnable watchdog = new Runnable() {
        @Override
        public void run() {
            long now = System.currentTimeMillis();
            writeHeartbeat();
            if (now - lastTradesReload > 2000) {
                lastTradesReload = now;
                engine.execute(BackgroundService.this::reloadTradesFromPrefs);
            }
            if (lastTickReceived == 0 || now - lastTickReceived > 2500) fetchRestPrice();
            if (lastTickReceived > 0 && now - lastTickReceived > 10000) {
                engine.execute(() -> reconnectNow("watchdog stale feed"));
            }
            if (now - lastRestSync > 30000) {
                lastRestSync = now;
                fetchHistory("1m", true);
                if (!"1m".equals(tf)) fetchHistory(tf, false); else fetchHistory("1m", false);
            }
            if (now - lastNotificationUpdate > 5000) {
                lastNotificationUpdate = now;
                updateNotification();
            }
            handler.postDelayed(this, 1000);
        }
    };

    private void writeHeartbeat() {
        long now = System.currentTimeMillis();
        SharedPreferences.Editor e = prefs.edit()
                .putLong("heartbeat", now)
                .putLong("last_tick_received", lastTickReceived)
                .putLong("last_exchange_event", lastExchangeEvent)
                .putString("last_price", Double.isFinite(lastPrice) ? String.valueOf(lastPrice) : "")
                .putString("feed_mode", feedMode)
                .putString("signal_state", signalState)
                .putString("symbol", symbol)
                .putString("tf", tf)
                .putInt("reconnects", reconnects)
                .putString("engine_ms", String.format(Locale.US, "%.3f", lastEngineMs));
        e.apply();
    }

    private void reconnectNow(String reason) {
        int gen = generation.incrementAndGet();
        if (socket != null) {
            try { socket.cancel(); } catch (Exception ignored) {}
            socket = null;
        }
        feedMode = "CONNECTING";
        signalState = "MONITORING";
        flowTrades.clear();
        flowBuy = 0;
        flowSell = 0;
        pendingTurnKey = null;
        pendingTurnCount = 0;
        fetchHistory("1m", true);
        if (!"1m".equals(tf)) fetchHistory(tf, false); else fetchHistory("1m", false);
        openSocket(gen);
    }

    private void openSocket(int gen) {
        String lower = symbol.toLowerCase(Locale.US);
        String streams = lower + "@aggTrade/" + lower + "@bookTicker/" + lower + "@kline_1m";
        if (!"1m".equals(tf)) streams += "/" + lower + "@kline_" + tf;
        Request req = new Request.Builder().url("wss://fstream.binance.com/stream?streams=" + streams).build();
        socket = client.newWebSocket(req, new WebSocketListener() {
            @Override
            public void onOpen(WebSocket webSocket, Response response) {
                if (gen != generation.get()) return;
                feedMode = "WS LIVE";
                writeHeartbeat();
            }

            @Override
            public void onMessage(WebSocket webSocket, String text) {
                if (gen != generation.get()) return;
                engine.execute(() -> processSocketMessage(text));
            }

            @Override
            public void onFailure(WebSocket webSocket, Throwable t, Response response) {
                if (gen != generation.get()) return;
                feedMode = "WS RECONNECTING";
                reconnects++;
                long delay = Math.min(30000, 1000L * Math.max(1, Math.min(30, reconnects)));
                handler.postDelayed(() -> engine.execute(() -> {
                    if (gen == generation.get()) reconnectNow("websocket failure");
                }), delay);
            }

            @Override
            public void onClosed(WebSocket webSocket, int code, String reason) {
                if (gen != generation.get()) return;
                feedMode = "WS CLOSED";
                handler.postDelayed(() -> engine.execute(() -> {
                    if (gen == generation.get()) reconnectNow("websocket closed");
                }), 1500);
            }
        });
    }

    private void processSocketMessage(String text) {
        long startNs = System.nanoTime();
        try {
            JSONObject root = new JSONObject(text);
            String stream = root.optString("stream", "");
            JSONObject data = root.optJSONObject("data");
            if (data == null) return;
            if (stream.endsWith("@aggTrade")) {
                double price = data.optDouble("p", Double.NaN);
                double qty = data.optDouble("q", 0.0);
                long ts = data.optLong("T", data.optLong("E", System.currentTimeMillis()));
                boolean aggressiveBuy = !data.optBoolean("m", false);
                if (Double.isFinite(price)) processTick(price, qty, aggressiveBuy, ts, "WS TRADE");
            } else if (stream.endsWith("@bookTicker")) {
                double bidQty = data.optDouble("B", 0.0);
                double askQty = data.optDouble("A", 0.0);
                double total = bidQty + askQty;
                orderBookImbalance = total > 0 ? (bidQty - askQty) / total : 0.0;
            } else if (stream.contains("@kline_")) {
                JSONObject k = data.optJSONObject("k");
                if (k != null) processKline(k);
            }
        } catch (Exception ignored) {
        } finally {
            lastEngineMs = (System.nanoTime() - startNs) / 1_000_000.0;
        }
    }

    private void processKline(JSONObject k) {
        try {
            String interval = k.optString("i", "");
            Candle c = new Candle(
                    k.optLong("t", 0L),
                    k.optDouble("o", 0.0),
                    k.optDouble("h", 0.0),
                    k.optDouble("l", 0.0),
                    k.optDouble("c", 0.0),
                    k.optDouble("v", 0.0),
                    k.optDouble("V", 0.0),
                    k.optBoolean("x", false)
            );
            if ("1m".equals(interval)) upsertCandle(microCandles, c);
            if (tf.equals(interval)) upsertCandle(mainCandles, c.copy());
            if ("1m".equals(tf) && "1m".equals(interval)) upsertCandle(mainCandles, c.copy());
            if (c.closed && tf.equals(interval)) analyseMainAndMaybeRecord();
        } catch (Exception ignored) {
        }
    }

    private void processTick(double price, double qty, boolean aggressiveBuy, long exchangeTs, String source) {
        long startNs = System.nanoTime();
        long now = System.currentTimeMillis();
        lastPrice = price;
        lastTickReceived = now;
        lastExchangeEvent = exchangeTs;
        feedMode = source;
        if (qty > 0) addFlow(exchangeTs, qty, aggressiveBuy);
        updateSynthetic(microCandles, price, exchangeTs, 60_000L, qty, aggressiveBuy);
        updateSynthetic(mainCandles, price, exchangeTs, tfMillis(tf), qty, aggressiveBuy);
        checkTrades(price, exchangeTs);
        Turning turn = detectTurningFast(price);
        signalState = turn.state;
        considerFastTurning(turn, price);
        if (now - lastMainSignalAt > 150) {
            lastMainSignalAt = now;
            analyseMainAndMaybeRecord();
        }
        lastEngineMs = (System.nanoTime() - startNs) / 1_000_000.0;
    }

    private void fetchRestPrice() {
        if (restBusy) return;
        restBusy = true;
        Request req = new Request.Builder().url("https://fapi.binance.com/fapi/v1/ticker/price?symbol=" + symbol).build();
        client.newCall(req).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                restBusy = false;
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                try (Response r = response) {
                    String body = r.body() != null ? r.body().string() : "{}";
                    JSONObject o = new JSONObject(body);
                    double p = o.optDouble("price", Double.NaN);
                    if (Double.isFinite(p)) engine.execute(() -> processTick(p, 0.0, false, System.currentTimeMillis(), "REST BACKUP"));
                } catch (Exception ignored) {
                } finally {
                    restBusy = false;
                }
            }
        });
    }

    private void fetchHistory(String interval, boolean micro) {
        Request req = new Request.Builder().url("https://fapi.binance.com/fapi/v1/klines?symbol=" + symbol + "&interval=" + interval + "&limit=300").build();
        client.newCall(req).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                try (Response r = response) {
                    String body = r.body() != null ? r.body().string() : "[]";
                    JSONArray arr = new JSONArray(body);
                    ArrayList<Candle> parsed = new ArrayList<>();
                    for (int i = 0; i < arr.length(); i++) {
                        JSONArray row = arr.optJSONArray(i);
                        if (row == null || row.length() < 10) continue;
                        parsed.add(new Candle(
                                row.optLong(0, 0L),
                                row.optDouble(1, 0.0),
                                row.optDouble(2, 0.0),
                                row.optDouble(3, 0.0),
                                row.optDouble(4, 0.0),
                                row.optDouble(5, 0.0),
                                row.optDouble(9, 0.0),
                                true
                        ));
                    }
                    engine.execute(() -> {
                        ArrayList<Candle> target = micro ? microCandles : mainCandles;
                        target.clear();
                        target.addAll(parsed);
                        trimCandles(target);
                    });
                } catch (Exception ignored) {
                }
            }
        });
    }

    private void addFlow(long ts, double qty, boolean buy) {
        flowTrades.addLast(new FlowTrade(ts, qty, buy));
        if (buy) flowBuy += qty; else flowSell += qty;
        trimFlow(System.currentTimeMillis());
        while (flowTrades.size() > 900) {
            FlowTrade f = flowTrades.removeFirst();
            if (f.buy) flowBuy -= f.qty; else flowSell -= f.qty;
        }
        if (flowBuy < 0) flowBuy = 0;
        if (flowSell < 0) flowSell = 0;
    }

    private void trimFlow(long now) {
        long cut = now - 12000L;
        while (!flowTrades.isEmpty() && flowTrades.peekFirst().time < cut) {
            FlowTrade f = flowTrades.removeFirst();
            if (f.buy) flowBuy -= f.qty; else flowSell -= f.qty;
        }
        if (flowBuy < 0) flowBuy = 0;
        if (flowSell < 0) flowSell = 0;
    }

    private double flowImbalance() {
        trimFlow(System.currentTimeMillis());
        double total = flowBuy + flowSell;
        return total > 0 ? (flowBuy - flowSell) / total : 0.0;
    }

    private Turning detectTurningFast(double price) {
        if (microCandles.size() < 18 || !Double.isFinite(price)) return Turning.monitoring();
        int i = microCandles.size() - 1;
        Candle x = microCandles.get(i);
        double av = atrLast(microCandles, 14);
        if (!Double.isFinite(av) || av <= 0) av = Math.abs(price) * 0.0015;
        double ph = maxHigh(microCandles, i - 12, i);
        double pl = minLow(microCandles, i - 12, i);
        double microLow = minLow(microCandles, i - 4, i);
        double microHigh = maxHigh(microCandles, i - 4, i);
        double flow = flowImbalance();
        double range = Math.max(x.h - x.l, 1e-9);
        double loc = (price - x.l) / range;
        double upper = (x.h - Math.max(x.o, price)) / range;
        double lower = (Math.min(x.o, price) - x.l) / range;
        boolean topSweep = x.h > ph + av * 0.025;
        boolean bottomSweep = x.l < pl - av * 0.025;
        boolean topReject = (topSweep && price < ph) || (upper > 0.38 && price < x.h - av * 0.16);
        boolean bottomReject = (bottomSweep && price > pl) || (lower > 0.38 && price > x.l + av * 0.16);
        boolean sellFlow = flow < -0.10;
        boolean buyFlow = flow > 0.10;
        boolean sellBook = orderBookImbalance < -0.15;
        boolean buyBook = orderBookImbalance > 0.15;
        boolean downAccel = price < x.o && loc < 0.44;
        boolean upAccel = price > x.o && loc > 0.56;
        int ts = 0;
        int bs = 0;
        ArrayList<String> tr = new ArrayList<>();
        ArrayList<String> br = new ArrayList<>();
        if (topSweep) { ts += 3; tr.add("high liquidity swept"); }
        if (topReject) { ts += 2; tr.add("top rejected"); }
        if (sellFlow) { ts += 2; tr.add("taker sell pressure"); }
        if (sellBook) { ts += 1; tr.add("book selling"); }
        if (downAccel) { ts += 1; tr.add("price turning down"); }
        if (price < microLow) { ts += 2; tr.add("micro low broken"); }
        if (bottomSweep) { bs += 3; br.add("low liquidity swept"); }
        if (bottomReject) { bs += 2; br.add("bottom reclaimed"); }
        if (buyFlow) { bs += 2; br.add("taker buy pressure"); }
        if (buyBook) { bs += 1; br.add("book buying"); }
        if (upAccel) { bs += 1; br.add("price turning up"); }
        if (price > microHigh) { bs += 2; br.add("micro high broken"); }
        boolean nearTop = (ph - price) <= av * 0.35 || topSweep;
        boolean nearBottom = (price - pl) <= av * 0.35 || bottomSweep;
        Turning out = new Turning("MID RANGE", 0, 0, false, "MID", flow, "No turning point", Double.NaN);
        if (nearTop && ts >= 2) out = new Turning("TOP WATCH", -1, ts, false, "TOP", flow, join(tr), ph);
        if (nearBottom && bs >= 2 && bs > ts) out = new Turning("BOTTOM WATCH", 1, bs, false, "BOTTOM", flow, join(br), pl);
        if (ts >= 6 && topReject && (sellFlow || sellBook || price < microLow)) out = new Turning("TOP SELL TRIGGER", -1, ts, true, "TOP", flow, join(tr), x.h);
        if (bs >= 6 && bottomReject && (buyFlow || buyBook || price > microHigh)) out = new Turning("BOTTOM BUY TRIGGER", 1, bs, true, "BOTTOM", flow, join(br), x.l);
        return out;
    }

    private void considerFastTurning(Turning turn, double price) {
        if (turn == null || !turn.trigger) {
            pendingTurnKey = null;
            pendingTurnCount = 0;
            return;
        }
        double microAtr = atrLast(microCandles, 14);
        if (!Double.isFinite(microAtr) || microAtr <= 0) microAtr = Math.abs(price) * 0.0015;
        double keyScale = Math.max(microAtr * 0.08, 1e-9);
        String key = symbol + "|" + turn.state + "|" + Math.round(price / keyScale);
        long now = System.currentTimeMillis();
        if (key.equals(lastRecordedTurnKey) && now - lastRecordedTurnAt < 90000) return;
        if (!key.equals(pendingTurnKey)) {
            pendingTurnKey = key;
            pendingTurnCount = 1;
            return;
        }
        pendingTurnCount++;
        if (pendingTurnCount < 3) return;
        Plan plan = fastPlan(turn, price);
        if (plan != null) {
            String side = turn.dir == 1 ? "BUY" : "SELL";
            if (recordSignal(side, turn.state, turn.score, plan, "native ultra live")) {
                lastRecordedTurnKey = key;
                lastRecordedTurnAt = now;
                notifySignal(side, turn.state, price);
            }
        }
        pendingTurnKey = null;
        pendingTurnCount = 0;
    }

    private Plan fastPlan(Turning turn, double price) {
        if (turn == null || !turn.trigger) return null;
        double selectedAtr = atrLast(mainCandles, 14);
        if (!Double.isFinite(selectedAtr) || selectedAtr <= 0) selectedAtr = Math.abs(price) * 0.004;
        double microAtr = atrLast(microCandles, 14);
        if (!Double.isFinite(microAtr) || microAtr <= 0) microAtr = selectedAtr * 0.25;
        double r = Math.max(microAtr * 1.1, selectedAtr * 0.28);
        if (turn.dir == 1) {
            double sl = Math.min(price - r, Double.isFinite(turn.level) ? turn.level - r * 0.12 : price - r);
            double risk = price - sl;
            return new Plan(price, sl, price + risk, price + risk * 1.55, price + risk * 2.1);
        } else {
            double sl = Math.max(price + r, Double.isFinite(turn.level) ? turn.level + r * 0.12 : price + r);
            double risk = sl - price;
            return new Plan(price, sl, price - risk, price - risk * 1.55, price - risk * 2.1);
        }
    }

    private void analyseMainAndMaybeRecord() {
        if (mainCandles.size() < 60) return;
        int n = mainCandles.size();
        double[] close = new double[n];
        for (int i = 0; i < n; i++) close[i] = mainCandles.get(i).c;
        double[] e5 = ema(close, 5);
        double[] e9 = ema(close, 9);
        double[] e15 = ema(close, 15);
        double[] rsi = rsi(close, 14);
        double[] atr = atr(mainCandles, 14);
        double[] macdHist = macdHist(close);
        int i = n - 1;
        Candle x = mainCandles.get(i);
        double base = 0;
        base += e5[i] > e9[i] ? 1 : -1;
        base += x.c > e9[i] ? 1 : -1;
        base += e9[i] > e15[i] ? 1 : -1;
        double slope = e9[i] - e9[Math.max(0, i - 2)];
        base += slope > 0 ? 1 : slope < 0 ? -1 : 0;
        int st = supertrendDirection(mainCandles, 10, 2.2);
        base += st >= 0 ? 1 : -1;
        if (Double.isFinite(rsi[i])) base += rsi[i] > 52 ? 1 : rsi[i] < 48 ? -1 : 0;
        double mh = macdHist[i];
        double mhp = macdHist[Math.max(0, i - 1)];
        base += (mh > 0 || mh > mhp) ? 1 : ((mh < 0 || mh < mhp) ? -1 : 0);
        double mid = smaLast(close, 20);
        if (Double.isFinite(mid)) base += x.c > mid ? 1 : -1;
        double vw = vwapLast(mainCandles);
        if (Double.isFinite(vw)) base += x.c > vw ? 1 : -1;
        base += candlePatternScore(x);
        int smc = smcScore(mainCandles, atr);
        base += orderBookImbalance > 0.05 ? 1 : orderBookImbalance < -0.05 ? -1 : 0;
        double score = base + smc;
        String side = null;
        String stage = null;
        if (score >= 8 && smc >= 1 && x.c > e9[i] && e5[i] >= e9[i]) {
            side = "BUY";
            stage = "CONFIRMED BUY";
        } else if (score <= -8 && smc <= -1 && x.c < e9[i] && e5[i] <= e9[i]) {
            side = "SELL";
            stage = "CONFIRMED SELL";
        }
        if (side == null) return;
        long candleTime = x.t;
        String key = symbol + "|" + tf + "|" + candleTime + "|" + side;
        long now = System.currentTimeMillis();
        if (key.equals(lastMainSignalKey) && now - lastMainSignalAt < 60000) return;
        double av = atr[i];
        if (!Double.isFinite(av) || av <= 0) av = Math.abs(x.c) * 0.004;
        double risk = av * 1.05;
        Plan plan;
        if ("BUY".equals(side)) {
            double sl = x.c - risk;
            plan = new Plan(x.c, sl, x.c + risk, x.c + risk * 1.55, x.c + risk * 2.1);
        } else {
            double sl = x.c + risk;
            plan = new Plan(x.c, sl, x.c - risk, x.c - risk * 1.55, x.c - risk * 2.1);
        }
        if (recordSignal(side, stage, (int) Math.round(score), plan, "native confirmed")) {
            lastMainSignalKey = key;
            lastMainSignalAt = now;
            signalState = stage;
            notifySignal(side, stage, x.c);
        }
    }

    private int smcScore(List<Candle> c, double[] atr) {
        int i = c.size() - 1;
        Candle x = c.get(i);
        double av = atr[i];
        if (!Double.isFinite(av) || av <= 0) av = Math.abs(x.c) * 0.004;
        int score = 0;
        for (int j = i; j >= Math.max(12, i - 5); j--) {
            double ph = maxHigh(c, j - 10, j);
            double pl = minLow(c, j - 10, j);
            if (c.get(j).c > ph) { score += 2; break; }
            if (c.get(j).c < pl) { score -= 2; break; }
        }
        for (int j = i; j >= Math.max(2, i - 24); j--) {
            double aj = Double.isFinite(atr[j]) ? atr[j] : av;
            if (c.get(j).l > c.get(j - 2).h && c.get(j).l - c.get(j - 2).h > aj * 0.08) { score += nearZone(x.c, c.get(j - 2).h, c.get(j).l, av, 0.6) ? 2 : 1; break; }
            if (c.get(j).h < c.get(j - 2).l && c.get(j - 2).l - c.get(j).h > aj * 0.08) { score -= nearZone(x.c, c.get(j).h, c.get(j - 2).l, av, 0.6) ? 2 : 1; break; }
        }
        for (int j = i; j >= Math.max(11, i - 4); j--) {
            double priorH = maxHigh(c, j - 10, j);
            double priorL = minLow(c, j - 10, j);
            if (c.get(j).l < priorL && c.get(j).c > priorL) { score += 2; break; }
            if (c.get(j).h > priorH && c.get(j).c < priorH) { score -= 2; break; }
        }
        for (int j = i; j >= Math.max(1, i - 2); j--) {
            Candle z = c.get(j);
            double a = Double.isFinite(atr[j]) ? atr[j] : av;
            double body = Math.abs(z.c - z.o);
            double range = Math.max(z.h - z.l, 1e-9);
            double loc = (z.c - z.l) / range;
            if (body > a * 0.7) {
                if (z.c > z.o && loc > 0.68) score += 1;
                else if (z.c < z.o && loc < 0.32) score -= 1;
                break;
            }
        }
        if (x.v > 0) {
            double sum = 0;
            int count = 0;
            for (int j = Math.max(0, i - 20); j < i; j++) {
                if (c.get(j).v > 0) { sum += c.get(j).v; count++; }
            }
            double avg = count > 0 ? sum / count : 0;
            if (avg > 0 && x.v > avg * 1.3) score += x.c > x.o ? 1 : x.c < x.o ? -1 : 0;
        }
        return score;
    }

    private boolean recordSignal(String side, String stage, int score, Plan plan, String source) {
        reloadTradesFromPrefs();
        for (JSONObject t : trades) {
            if ("OPEN".equals(t.optString("status")) && symbol.equals(t.optString("symbol")) && tf.equals(t.optString("tf")) && side.equals(t.optString("side"))) return false;
        }
        long now = System.currentTimeMillis();
        try {
            JSONObject t = new JSONObject();
            String slot = "crypto|" + symbol + "|" + tf + "|" + (now / 2500L) + "|" + side;
            t.put("id", "native-" + now + "-" + Math.abs(slot.hashCode()));
            t.put("slot", slot);
            t.put("key", slot);
            t.put("source", source);
            t.put("stage", stage);
            t.put("score", score);
            t.put("shiftScore", 0);
            t.put("createdAt", now);
            t.put("signalCandleTime", now);
            t.put("market", "crypto");
            t.put("symbol", symbol);
            t.put("tf", tf);
            t.put("side", side);
            t.put("entry", plan.entry);
            t.put("sl", plan.sl);
            t.put("t1", plan.t1);
            t.put("t2", plan.t2);
            t.put("t3", plan.t3);
            t.put("status", "OPEN");
            t.put("result", "OPEN");
            t.put("h1", false);
            t.put("h2", false);
            t.put("h3", false);
            t.put("closedAt", JSONObject.NULL);
            t.put("updatedAt", now);
            trades.add(t);
            while (trades.size() > 1500) trades.remove(0);
            persistTrades();
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private void checkTrades(double price, long evt) {
        boolean changed = false;
        for (JSONObject t : trades) {
            if (!"OPEN".equals(t.optString("status"))) continue;
            if (!symbol.equals(t.optString("symbol"))) continue;
            String side = t.optString("side", "");
            double sl = t.optDouble("sl", Double.NaN);
            double t1 = t.optDouble("t1", Double.NaN);
            double t2 = t.optDouble("t2", Double.NaN);
            double t3 = t.optDouble("t3", Double.NaN);
            try {
                if ("BUY".equals(side)) {
                    if (Double.isFinite(sl) && price <= sl) {
                        t.put("status", "CLOSED"); t.put("result", "SL"); t.put("closedAt", evt); changed = true;
                    } else {
                        if (Double.isFinite(t1) && price >= t1 && !t.optBoolean("h1")) { t.put("h1", true); changed = true; }
                        if (Double.isFinite(t2) && price >= t2 && !t.optBoolean("h2")) { t.put("h2", true); changed = true; }
                        if (Double.isFinite(t3) && price >= t3 && !t.optBoolean("h3")) { t.put("h3", true); t.put("status", "CLOSED"); t.put("result", "T3"); t.put("closedAt", evt); changed = true; }
                    }
                } else if ("SELL".equals(side)) {
                    if (Double.isFinite(sl) && price >= sl) {
                        t.put("status", "CLOSED"); t.put("result", "SL"); t.put("closedAt", evt); changed = true;
                    } else {
                        if (Double.isFinite(t1) && price <= t1 && !t.optBoolean("h1")) { t.put("h1", true); changed = true; }
                        if (Double.isFinite(t2) && price <= t2 && !t.optBoolean("h2")) { t.put("h2", true); changed = true; }
                        if (Double.isFinite(t3) && price <= t3 && !t.optBoolean("h3")) { t.put("h3", true); t.put("status", "CLOSED"); t.put("result", "T3"); t.put("closedAt", evt); changed = true; }
                    }
                }
                if ("OPEN".equals(t.optString("status"))) {
                    String result = t.optBoolean("h2") ? "T2 running" : t.optBoolean("h1") ? "T1 running" : "OPEN";
                    if (!result.equals(t.optString("result"))) { t.put("result", result); changed = true; }
                }
                if (changed) t.put("updatedAt", System.currentTimeMillis());
            } catch (Exception ignored) {
            }
        }
        if (changed) persistTrades();
    }

    private void reloadTradesFromPrefs() {
        String raw = prefs.getString(TRADES_KEY, "[]");
        if (raw == null) raw = "[]";
        if (raw.equals(lastTradesRaw)) return;
        try {
            JSONArray arr = new JSONArray(raw);
            trades.clear();
            for (int i = 0; i < arr.length(); i++) {
                JSONObject t = arr.optJSONObject(i);
                if (t != null) trades.add(t);
            }
            lastTradesRaw = raw;
        } catch (Exception ignored) {
        }
    }

    private void persistTrades() {
        JSONArray arr = new JSONArray();
        for (JSONObject t : trades) arr.put(t);
        String raw = arr.toString();
        lastTradesRaw = raw;
        prefs.edit().putString(TRADES_KEY, raw).apply();
    }

    private static void upsertCandle(ArrayList<Candle> list, Candle c) {
        if (c == null || c.t <= 0) return;
        int n = list.size();
        if (n > 0 && list.get(n - 1).t == c.t) list.set(n - 1, c); else if (n == 0 || c.t > list.get(n - 1).t) list.add(c);
        trimCandles(list);
    }

    private static void updateSynthetic(ArrayList<Candle> list, double price, long ts, long ms, double qty, boolean buy) {
        if (!Double.isFinite(price)) return;
        long bucket = (ts / ms) * ms;
        if (list.isEmpty() || list.get(list.size() - 1).t < bucket) {
            list.add(new Candle(bucket, price, price, price, price, Math.max(0, qty), buy ? Math.max(0, qty) : 0.0, false));
        } else {
            Candle c = list.get(list.size() - 1);
            if (c.t == bucket) {
                c.h = Math.max(c.h, price);
                c.l = Math.min(c.l, price);
                c.c = price;
                if (qty > 0) {
                    c.v += qty;
                    if (buy) c.tb += qty;
                }
            }
        }
        trimCandles(list);
    }

    private static void trimCandles(ArrayList<Candle> list) {
        while (list.size() > 400) list.remove(0);
    }

    private static double[] ema(double[] a, int p) {
        double[] out = new double[a.length];
        java.util.Arrays.fill(out, Double.NaN);
        if (a.length < p) return out;
        double sum = 0;
        for (int i = 0; i < p; i++) sum += a[i];
        double v = sum / p;
        out[p - 1] = v;
        double k = 2.0 / (p + 1.0);
        for (int i = p; i < a.length; i++) {
            v = a[i] * k + v * (1.0 - k);
            out[i] = v;
        }
        return out;
    }

    private static double[] rsi(double[] a, int p) {
        double[] out = new double[a.length];
        java.util.Arrays.fill(out, Double.NaN);
        if (a.length <= p) return out;
        double g = 0, l = 0;
        for (int i = 1; i <= p; i++) {
            double d = a[i] - a[i - 1];
            if (d >= 0) g += d; else l -= d;
        }
        double ag = g / p, al = l / p;
        out[p] = al == 0 ? 100 : 100 - 100 / (1 + ag / al);
        for (int i = p + 1; i < a.length; i++) {
            double d = a[i] - a[i - 1];
            ag = (ag * (p - 1) + Math.max(d, 0)) / p;
            al = (al * (p - 1) + Math.max(-d, 0)) / p;
            out[i] = al == 0 ? 100 : 100 - 100 / (1 + ag / al);
        }
        return out;
    }

    private static double[] atr(List<Candle> c, int p) {
        double[] out = new double[c.size()];
        java.util.Arrays.fill(out, Double.NaN);
        if (c.size() < p) return out;
        double[] tr = new double[c.size()];
        for (int i = 0; i < c.size(); i++) {
            Candle x = c.get(i);
            if (i == 0) tr[i] = x.h - x.l;
            else {
                double pc = c.get(i - 1).c;
                tr[i] = Math.max(x.h - x.l, Math.max(Math.abs(x.h - pc), Math.abs(x.l - pc)));
            }
        }
        double v = 0;
        for (int i = 0; i < p; i++) v += tr[i];
        v /= p;
        out[p - 1] = v;
        for (int i = p; i < tr.length; i++) {
            v = (v * (p - 1) + tr[i]) / p;
            out[i] = v;
        }
        return out;
    }

    private static double atrLast(List<Candle> c, int p) {
        if (c == null || c.size() < p) return Double.NaN;
        double[] a = atr(c, p);
        return a[a.length - 1];
    }

    private static double[] macdHist(double[] a) {
        double[] e12 = ema(a, 12), e26 = ema(a, 26);
        double[] line = new double[a.length];
        for (int i = 0; i < a.length; i++) line[i] = Double.isFinite(e12[i]) && Double.isFinite(e26[i]) ? e12[i] - e26[i] : 0.0;
        double[] sig = ema(line, 9);
        double[] hist = new double[a.length];
        for (int i = 0; i < a.length; i++) hist[i] = Double.isFinite(sig[i]) ? line[i] - sig[i] : 0.0;
        return hist;
    }

    private static int supertrendDirection(List<Candle> c, int p, double mult) {
        if (c.size() < p + 2) return 0;
        double[] a = atr(c, p);
        double fu = Double.NaN, fl = Double.NaN;
        int trend = 1;
        for (int i = 0; i < c.size(); i++) {
            if (!Double.isFinite(a[i])) continue;
            Candle x = c.get(i);
            double hl = (x.h + x.l) / 2.0;
            double bu = hl + mult * a[i], bl = hl - mult * a[i];
            if (!Double.isFinite(fu)) { fu = bu; fl = bl; }
            else {
                Candle prev = c.get(i - 1);
                fu = (bu < fu || prev.c > fu) ? bu : fu;
                fl = (bl > fl || prev.c < fl) ? bl : fl;
            }
            if (trend == 1 && x.c < fl) trend = -1;
            else if (trend == -1 && x.c > fu) trend = 1;
        }
        return trend;
    }

    private static double smaLast(double[] a, int p) {
        if (a.length < p) return Double.NaN;
        double s = 0;
        for (int i = a.length - p; i < a.length; i++) s += a[i];
        return s / p;
    }

    private static double vwapLast(List<Candle> c) {
        double pv = 0, v = 0;
        for (Candle x : c) {
            if (x.v <= 0) continue;
            double tp = (x.h + x.l + x.c) / 3.0;
            pv += tp * x.v;
            v += x.v;
        }
        return v > 0 ? pv / v : Double.NaN;
    }

    private static int candlePatternScore(Candle c) {
        double body = Math.abs(c.c - c.o);
        double range = Math.max(c.h - c.l, 1e-9);
        double upper = c.h - Math.max(c.o, c.c);
        double lower = Math.min(c.o, c.c) - c.l;
        if (lower > body * 1.8 && lower / range > 0.45) return 1;
        if (upper > body * 1.8 && upper / range > 0.45) return -1;
        if (body / range > 0.68) return c.c > c.o ? 1 : -1;
        return 0;
    }

    private static double maxHigh(List<Candle> c, int from, int toExclusive) {
        if (c.isEmpty()) return Double.NaN;
        int a = Math.max(0, from), b = Math.min(c.size(), Math.max(a + 1, toExclusive));
        double m = -Double.MAX_VALUE;
        for (int i = a; i < b; i++) m = Math.max(m, c.get(i).h);
        return m;
    }

    private static double minLow(List<Candle> c, int from, int toExclusive) {
        if (c.isEmpty()) return Double.NaN;
        int a = Math.max(0, from), b = Math.min(c.size(), Math.max(a + 1, toExclusive));
        double m = Double.MAX_VALUE;
        for (int i = a; i < b; i++) m = Math.min(m, c.get(i).l);
        return m;
    }

    private static boolean nearZone(double price, double lo, double hi, double atr, double mult) {
        double d = atr * mult;
        return price >= lo - d && price <= hi + d;
    }

    private static long tfMillis(String tf) {
        if ("1m".equals(tf)) return 60_000L;
        if ("3m".equals(tf)) return 180_000L;
        if ("5m".equals(tf)) return 300_000L;
        if ("15m".equals(tf)) return 900_000L;
        if ("30m".equals(tf)) return 1_800_000L;
        if ("1h".equals(tf)) return 3_600_000L;
        if ("2h".equals(tf)) return 7_200_000L;
        if ("4h".equals(tf)) return 14_400_000L;
        if ("1d".equals(tf)) return 86_400_000L;
        return 300_000L;
    }

    private static String normalizeSymbol(String s) {
        if (s == null) return "BTCUSDT";
        s = s.toUpperCase(Locale.US).replaceAll("[^A-Z0-9]", "");
        return s.matches("[A-Z0-9]{5,20}") ? s : "BTCUSDT";
    }

    private static String normalizeTf(String s) {
        if (s == null) return "5m";
        return s.matches("(1m|3m|5m|15m|30m|1h|2h|4h|1d)") ? s : "5m";
    }

    private static String formatPrice(double p) {
        if (!Double.isFinite(p)) return "NA";
        if (p >= 1000) return String.format(Locale.US, "%.2f", p);
        if (p >= 100) return String.format(Locale.US, "%.3f", p);
        if (p >= 1) return String.format(Locale.US, "%.4f", p);
        return String.format(Locale.US, "%.6f", p);
    }

    private static String join(List<String> values) {
        StringBuilder b = new StringBuilder();
        for (String s : values) {
            if (b.length() > 0) b.append(" · ");
            b.append(s);
        }
        return b.toString();
    }

    private static final class Candle {
        long t;
        double o, h, l, c, v, tb;
        boolean closed;
        Candle(long t, double o, double h, double l, double c, double v, double tb, boolean closed) {
            this.t = t; this.o = o; this.h = h; this.l = l; this.c = c; this.v = v; this.tb = tb; this.closed = closed;
        }
        Candle copy() { return new Candle(t, o, h, l, c, v, tb, closed); }
    }

    private static final class FlowTrade {
        final long time;
        final double qty;
        final boolean buy;
        FlowTrade(long time, double qty, boolean buy) { this.time = time; this.qty = qty; this.buy = buy; }
    }

    private static final class Turning {
        final String state;
        final int dir;
        final int score;
        final boolean trigger;
        final String location;
        final double flow;
        final String reason;
        final double level;
        Turning(String state, int dir, int score, boolean trigger, String location, double flow, String reason, double level) {
            this.state = state; this.dir = dir; this.score = score; this.trigger = trigger; this.location = location; this.flow = flow; this.reason = reason; this.level = level;
        }
        static Turning monitoring() { return new Turning("MONITORING", 0, 0, false, "NA", 0, "Waiting for micro data", Double.NaN); }
    }

    private static final class Plan {
        final double entry, sl, t1, t2, t3;
        Plan(double entry, double sl, double t1, double t2, double t3) { this.entry = entry; this.sl = sl; this.t1 = t1; this.t2 = t2; this.t3 = t3; }
    }
}
