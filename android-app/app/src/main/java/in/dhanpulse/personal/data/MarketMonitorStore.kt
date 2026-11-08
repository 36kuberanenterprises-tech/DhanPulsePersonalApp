package `in`.dhanpulse.personal.data

import android.content.Context

/**
 * Non-secret state only. Authenticated sessions stay in SecurePrefs.
 * A user-initiated foreground service owns actual background monitoring.
 */
class MarketMonitorStore(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences("dhanpulse_market_monitor", Context.MODE_PRIVATE)

    var requested: Boolean
        get() = prefs.getBoolean("requested", false)
        set(value) = prefs.edit().putBoolean("requested", value).apply()

    var running: Boolean
        get() = prefs.getBoolean("running", false)
        set(value) = prefs.edit().putBoolean("running", value).apply()

    var uiVisible: Boolean
        get() = prefs.getBoolean("ui_visible", false)
        set(value) = prefs.edit().putBoolean("ui_visible", value).apply()

    var uiHeartbeatAt: Long
        get() = prefs.getLong("ui_heartbeat_at", 0L)
        set(value) = prefs.edit().putLong("ui_heartbeat_at", value).apply()

    // Do not let a stale UI flag hold the native service idle after a crash.
    fun hasVisibleApp(now: Long = System.currentTimeMillis()): Boolean =
        uiVisible && uiHeartbeatAt in (now - 90_000L)..now

    var status: String
        get() = prefs.getString("status", "OFF") ?: "OFF"
        set(value) = prefs.edit().putString("status", value.take(120)).apply()

    var lastMarketDataAt: Long
        get() = prefs.getLong("market_data_at", 0L)
        set(value) = prefs.edit().putLong("market_data_at", value).apply()

    var lastCheckAt: Long
        get() = prefs.getLong("last_check_at", 0L)
        set(value) = prefs.edit().putLong("last_check_at", value).apply()

    var selectedSymbol: String
        get() = prefs.getString("selected_symbol", "NIFTY") ?: "NIFTY"
        set(value) {
            val clean = value.uppercase().filter { it.isLetterOrDigit() || it == '_' }.take(25)
            prefs.edit().putString("selected_symbol", clean.ifBlank { "NIFTY" }).apply()
        }

    fun hasLiveMonitoring(now: Long = System.currentTimeMillis()): Boolean =
        requested && running && lastMarketDataAt in (now - 150_000L)..now

    fun stop(statusText: String, clearRequest: Boolean) {
        prefs.edit()
            .putBoolean("running", false)
            .putString("status", statusText.take(120))
            .apply {
                if (clearRequest) putBoolean("requested", false)
            }
            .apply()
    }
}
