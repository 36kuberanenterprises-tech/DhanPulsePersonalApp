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

    // Latest selected underlying quote for the ongoing user-initiated notification.
    // The receipt time is local; an old value is never labelled LIVE.
    val selectedPrice: Double
        get() = java.lang.Double.longBitsToDouble(prefs.getLong("selected_price_bits", 0L))

    val selectedPriceAt: Long
        get() = prefs.getLong("selected_price_at", 0L)

    val selectedPriceSymbol: String
        get() = prefs.getString("selected_price_symbol", "") ?: ""

    val selectedFeedStatus: String
        get() = prefs.getString("selected_feed_status", "WAITING") ?: "WAITING"

    fun recordSelectedQuote(symbol: String, status: String, price: Double?, receivedAt: Long = System.currentTimeMillis()) {
        val clean = symbol.uppercase().filter { it.isLetterOrDigit() || it == '_' }.take(25)
        if (clean != selectedSymbol) return
        val editor = prefs.edit().putString("selected_feed_status", status.take(32))
        if (status == "LIVE" && price != null && price.isFinite() && price > 0.0) {
            editor.putString("selected_price_symbol", clean)
                .putLong("selected_price_bits", java.lang.Double.doubleToRawLongBits(price))
                .putLong("selected_price_at", receivedAt)
                .putLong("market_data_at", receivedAt)
        }
        editor.apply()
    }

    fun clearSelectedQuote(symbol: String) {
        val clean = symbol.uppercase().filter { it.isLetterOrDigit() || it == '_' }.take(25)
        prefs.edit().putString("selected_symbol", clean.ifBlank { "NIFTY" })
            .putString("selected_price_symbol", "")
            .putLong("selected_price_bits", 0L)
            .putLong("selected_price_at", 0L)
            .putString("selected_feed_status", "CONNECTING")
            .apply()
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
