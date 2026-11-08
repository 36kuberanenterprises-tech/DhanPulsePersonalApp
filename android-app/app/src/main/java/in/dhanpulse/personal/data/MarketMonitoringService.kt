package `in`.dhanpulse.personal.data

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import `in`.dhanpulse.personal.MainActivity
import `in`.dhanpulse.personal.model.AnalysisResponse
import `in`.dhanpulse.personal.model.LiveMoverStock
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeout
import retrofit2.HttpException
import java.time.Instant
import java.time.LocalTime
import java.time.ZoneId

/**
 * User started native market monitor. No order endpoint is ever called here.
 * Android 15 dataSync foreground services have a 6h/24h background budget.
 */
class MarketMonitoringService : Service() {
    companion object {
        const val ACTION_START = "in.dhanpulse.personal.monitor.START"
        const val ACTION_STOP = "in.dhanpulse.personal.monitor.STOP"
        private const val STATUS_CHANNEL = "dhanpulse_market_status"
        private const val ALERT_CHANNEL = "dhanpulse_market_alerts"
        private const val STATUS_ID = 7301
        private const val SIGNAL_ID = 7302
        private const val MAX_RUNTIME = 5L * 60L * 60_000L + 40L * 60_000L
        private const val SERVER = "https://dhanpulse-personal-api.onrender.com"
        private val IST = ZoneId.of("Asia/Kolkata")
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private lateinit var monitorState: MarketMonitorStore
    private lateinit var manager: NotificationManager
    private var feedJob: Job? = null
    private var scanJob: Job? = null
    private var startedAt = 0L
    private var lastNoticeAt = 0L
    private var lastAlertAt = 0L
    private var lastAlertKey = ""
    private var noHistoryUntil = 0L

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        monitorState = MarketMonitorStore(this)
        manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel(
            STATUS_CHANNEL, "DhanPulse market monitoring", NotificationManager.IMPORTANCE_LOW
        ))
        manager.createNotificationChannel(NotificationChannel(
            ALERT_CHANNEL, "DhanPulse market alerts", NotificationManager.IMPORTANCE_HIGH
        ))
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopMonitor("Monitoring stopped by user", true)
            return START_NOT_STICKY
        }
        if (intent?.action != ACTION_START && !monitorState.requested) {
            stopSelf()
            return START_NOT_STICKY
        }
        val secure = runCatching { SecurePrefs(this) }.getOrNull()
        if (secure?.sessionId.isNullOrBlank() || (secure?.sessionExpiry ?: 0L) <= System.currentTimeMillis()) {
            monitorState.stop("Login required for monitoring", false)
            stopSelf()
            return START_NOT_STICKY
        }
        if (scanJob?.isActive == true) return START_STICKY
        monitorState.requested = true
        monitorState.running = true
        monitorState.status = "STARTING"
        startedAt = System.currentTimeMillis()
        try {
            ServiceCompat.startForeground(this, STATUS_ID,
                notification("DhanPulse • monitoring", "NSE and MCX background monitoring enabled"),
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } catch (e: Exception) {
            monitorState.stop("Android blocked background service", false)
            stopSelf()
            return START_NOT_STICKY
        }
        scanJob = scope.launch { pollingLoop(secure!!) }
        feedJob = scope.launch { liveFeedLoop(secure!!) }
        return START_STICKY
    }

    private fun activityIntent(): PendingIntent =
        PendingIntent.getActivity(this, 73,
            Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)

    private fun stopIntent(): PendingIntent =
        PendingIntent.getService(this, 74,
            Intent(this, MarketMonitoringService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)

    private fun notification(title: String, message: String): Notification =
        NotificationCompat.Builder(this, STATUS_CHANNEL)
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setContentTitle(title)
            .setContentText(message)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))
            .setContentIntent(activityIntent())
            .setOngoing(true)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setOnlyAlertOnce(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Stop", stopIntent())
            .build()

    private fun status(label: String, detail: String) {
        monitorState.status = label
        val now = System.currentTimeMillis()
        if (now - lastNoticeAt >= 15_000L) {
            lastNoticeAt = now
            manager.notify(STATUS_ID, notification("DhanPulse • " + label, detail))
        }
    }

    private fun alert(key: String, title: String, detail: String) {
        val now = System.currentTimeMillis()
        if (key == lastAlertKey && now - lastAlertAt < 20 * 60_000L) return
        lastAlertKey = key
        lastAlertAt = now
        manager.notify(SIGNAL_ID, NotificationCompat.Builder(this, ALERT_CHANNEL)
            .setSmallIcon(android.R.drawable.stat_notify_chat)
            .setContentTitle(title)
            .setContentText(detail)
            .setStyle(NotificationCompat.BigTextStyle().bigText(detail))
            .setContentIntent(activityIntent())
            .setAutoCancel(true)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build())
    }

    private fun isRecent(raw: String?, maxAgeMs: Long = 60_000L): Boolean {
        val timestamp = runCatching { Instant.parse(raw ?: "").toEpochMilli() }.getOrNull() ?: return false
        val delta = System.currentTimeMillis() - timestamp
        return delta in 0L..maxAgeMs
    }

    private fun marketHours(): Pair<Boolean, Boolean> {
        val local = Instant.now().atZone(IST)
        if (local.dayOfWeek.value !in 1..5) return false to false
        val time = local.toLocalTime()
        val equity = !time.isBefore(LocalTime.of(9,15)) && time.isBefore(LocalTime.of(15,30))
        val mcx = !time.isBefore(LocalTime.of(9,0)) && time.isBefore(LocalTime.of(23,30))
        return equity to mcx
    }

    private fun validSession(secure: SecurePrefs): String? {
        if (!monitorState.requested || secure.sessionExpiry <= System.currentTimeMillis()) return null
        return secure.sessionId?.takeIf { it.isNotBlank() }
    }

    private suspend fun pollingLoop(secure: SecurePrefs) {
        val api = ApiFactory.create(SERVER)
        var tick = 0
        var failures = 0
        while (scope.isActive && monitorState.requested) {
            try {
                val now = System.currentTimeMillis()
                if (now - startedAt >= MAX_RUNTIME) {
                    alert("monitor_time_limit", "Monitoring paused",
                        "Android limits continuous background monitoring. Reopen DhanPulse to restart.")
                    stopMonitor("Android foreground monitoring limit", false)
                    break
                }
                val session = validSession(secure)
                if (session == null) {
                    stopMonitor("Session expired • login required", false)
                    break
                }
                val (nse,mcx) = marketHours()
                if (!nse && !mcx) {
                    status("MARKET CLOSED", "NSE and MCX regular monitoring windows are closed.")
                    delay(60_000L)
                    continue
                }
                if (monitorState.hasVisibleApp()) {
                    status("ACTIVE", "Monitoring is handed to the visible app.")
                    delay(10_000L)
                    continue
                }
                val checks = mutableListOf<String>()
                if (nse) checks.addAll(listOf("NIFTY", "BANKNIFTY", "MOVERS", "STOCKS"))
                if (mcx) checks.add(monitorState.selectedSymbol.takeIf {
                    it !in setOf("NIFTY","BANKNIFTY","SENSEX") && it.isNotBlank()
                } ?: "MCXBULLDEX")
                val choice = checks[tick++ % checks.size]
                monitorState.lastCheckAt = now
                try {
                    when (choice) {
                        "MOVERS" -> {
                            val movers = withTimeout(28_000L) { api.liveMovers(session) }
                            val top = if (isRecent(movers.updatedAt)) movers.movers.firstOrNull {
                                it.status == "LIVE_MOVER" && it.ageSeconds != null &&
                                it.ageSeconds in 0.0..15.0 && (it.price ?: 0.0) > 0
                            } else null
                            if (top != null) {
                                monitorState.lastMarketDataAt = System.currentTimeMillis()
                                status("LIVE MOVERS", top.symbol + " • quote screened, not a confirmed trade")
                                alertMover(top)
                            } else status("SCANNING", "No verified fresh live mover quote at this check.")
                        }
                        "STOCKS" -> {
                            val result = withTimeout(28_000L) { api.stockScanner(session) }
                            val ready = result.candidates.firstOrNull { it.status == "READY" &&
                                it.plan != null && it.side in setOf("BUY","SELL") }
                            if (result.marketStatus == "SCANNING" && isRecent(result.timestamp) &&
                                ready != null) {
                                monitorState.lastMarketDataAt = System.currentTimeMillis()
                                status("STOCK SETUP", ready.symbol + " " + ready.side + " • review in app")
                                alert("stock:" + ready.symbol + ":" + ready.side + ":" + ready.setup,
                                    "DhanPulse stock setup: " + ready.symbol,
                                    ready.side + " candidate. Review checks. No order placed.")
                            } else status("SCANNING", "Stock scanner active • no verified entry candidate")
                        }
                        else -> {
                            if (now < noHistoryUntil) {
                                status("CANDLE PAUSE", "History access restricted; no confirmed call.")
                            } else processAnalysis(withTimeout(28_000L) { api.analysis(session, choice) })
                        }
                    }
                    failures = 0
                    if (monitorState.hasLiveMonitoring()) secure.lastUserActivity = System.currentTimeMillis()
                } catch (e: Exception) {
                    // One timed-out broker request must not terminate the
                    // entire native market monitor; only actual job cancellation does.
                    if (e is CancellationException && e !is TimeoutCancellationException) throw e
                    if (e is HttpException && e.code() == 401) {
                        stopMonitor("Session invalid • sign in again", false)
                        break
                    }
                    failures++
                    val reason = (e.message ?: e.javaClass.simpleName).take(120)
                    if (reason.contains("403") || reason.contains("historical", true) ||
                        reason.contains("cooldown", true)) noHistoryUntil = now + 15 * 60_000L
                    status("DATA DELAYED", "Broker or backend unavailable; no signal inferred. " + reason.take(55))
                    delay((4_000L * failures).coerceAtMost(30_000L))
                }
                delay(30_000L)
            } catch (_: CancellationException) {
                break
            }
        }
    }

    private fun processAnalysis(result: AnalysisResponse) {
        val side = result.tradeDecision.direction.uppercase()
        if (result.dataFresh == true && isRecent(result.timestamp) &&
            result.tradeDecision.setupAllowed &&
            side in setOf("BUY","SELL","CE","PE")) {
            monitorState.lastMarketDataAt = System.currentTimeMillis()
            status("SETUP READY", result.symbol + " " + side + " • review")
            alert("index:" + result.symbol + ":" + side + ":" + result.tradeDecision.strategyFamily,
                "DhanPulse " + result.symbol + " " + side,
                "Confirmed with fresh broker data. Review the app; no order placed.")
        } else if (result.dataFresh == true && isRecent(result.timestamp) &&
            (result.market.ltp ?: 0.0) > 0) {
            monitorState.lastMarketDataAt = System.currentTimeMillis()
            status("LIVE", result.symbol + " price feed active • no trade setup")
        } else status("DATA NEEDED", result.symbol + " historical confirmation unavailable")
    }

    private fun alertMover(item: LiveMoverStock) {
        val pct = item.changePct ?: return
        if (kotlin.math.abs(pct) < 1.0) return
        val direction = if (pct > 0) "UP" else "DOWN"
        alert("mover:" + item.symbol + ":" + direction,
            "DhanPulse watch: " + item.symbol,
            "Live quote move " + "%.2f".format(java.util.Locale.US, pct) +
                "%. Watch only; not a BUY or SELL signal.")
    }

    private suspend fun liveFeedLoop(secure: SecurePrefs) {
        val feed = LivePriceStream(SERVER)
        while (scope.isActive && monitorState.requested) {
            if (monitorState.hasVisibleApp() || validSession(secure) == null) {
                delay(3_000L)
                continue
            }
            val (nse,mcx) = marketHours()
            val symbol = monitorState.selectedSymbol
            val open = if (symbol in setOf("NIFTY","BANKNIFTY","SENSEX")) nse else mcx
            if (!open) {
                delay(30_000L)
                continue
            }
            try {
                feed.collect(validSession(secure) ?: break, symbol) { price ->
                    if (monitorState.hasVisibleApp() || !monitorState.requested ||
                        monitorState.selectedSymbol != symbol)
                        throw CancellationException("Visible app or symbol change")
                    if (price.status == "LIVE" && (price.price ?: 0.0) > 0) {
                        monitorState.lastMarketDataAt = System.currentTimeMillis()
                        if (System.currentTimeMillis() - lastNoticeAt > 20_000L)
                            status("STREAM LIVE", symbol + " • " +
                                "%.2f".format(java.util.Locale.US, price.price) + " • read only")
                    }
                }
            } catch (_: CancellationException) {
                // The app resumed or the watched symbol changed.
            } catch (e: Exception) {
                if (!monitorState.hasVisibleApp())
                    status("RECONNECTING", symbol + " broker stream interrupted")
            }
            delay(5_000L)
        }
    }

    private fun stopMonitor(message: String, byUser: Boolean) {
        monitorState.stop(message, clearRequest = byUser)
        scanJob?.cancel()
        feedJob?.cancel()
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onTimeout(startId: Int, fgsType: Int) {
        stopMonitor("Android service time budget reached", false)
    }

    override fun onDestroy() {
        scanJob?.cancel()
        feedJob?.cancel()
        monitorState.running = false
        super.onDestroy()
    }
}
