package `in`.dhanpulse.personal.ui

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.google.gson.Gson
import `in`.dhanpulse.personal.data.ApiFactory
import `in`.dhanpulse.personal.data.DhanPulseApi
import `in`.dhanpulse.personal.model.*
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import retrofit2.HttpException
import kotlin.math.floor

class DhanPulseViewModel(app: Application) : AndroidViewModel(app) {
    private val backendUrl = "https://dhanpulse-personal-api.onrender.com"

    var sessionId by mutableStateOf<String?>(null)
    var profile by mutableStateOf<UserProfile?>(null)
    var selectedSymbol by mutableStateOf("NIFTY")
    var analysis by mutableStateOf<AnalysisResponse?>(null)
    var account by mutableStateOf<AccountSummary?>(null)
    var loading by mutableStateOf(false)
    var error by mutableStateOf<String?>(null)
    var refreshWarning by mutableStateOf<String?>(null)
    var orderBusy by mutableStateOf(false)
    var orderMessage by mutableStateOf<String?>(null)

    var autoTradeEnabled by mutableStateOf(false)
        private set
    var autoLots by mutableStateOf(1)
        private set
    var autoStatus by mutableStateOf("Auto Trade is OFF")
        private set

    private var autoPositionContract: OptionContract? = null
    private var autoPositionSignal: String? = null
    private var autoStop: Double? = null
    private var autoTarget: Double? = null
    private var blockedSignal: String? = null
    private var pendingSignalKey: String? = null
    private var pendingSignalCount = 0
    private var autoEvaluating = false

    private var api: DhanPulseApi? = null
    private var refreshJob: Job? = null

    private fun client(): DhanPulseApi {
        val existing = api
        if (existing != null) return existing
        return ApiFactory.create(backendUrl).also { api = it }
    }

    fun login(pin: String, totp: String, onDone: () -> Unit) {
        error = null
        if (pin.isBlank() || totp.isBlank()) {
            error = "Enter PIN and current TOTP"
            onDone()
            return
        }
        loading = true
        api = null
        viewModelScope.launch {
            try {
                val r = client().login(LoginRequest("", "", pin.trim(), totp.trim()))
                sessionId = r.sessionId
                profile = r.profile
                fetchAnalysis()
                fetchAccount()
            } catch (e: Exception) {
                error = friendlyError(e, "Login failed")
            }
            loading = false
            onDone()
        }
    }

    fun fetchAnalysis() {
        val s = sessionId ?: return
        loading = analysis == null
        viewModelScope.launch {
            try {
                val result = client().analysis(s, selectedSymbol, "FIVE_MINUTE")
                analysis = result
                error = null
                refreshWarning = null
                if (autoTradeEnabled) evaluateAutoTrade(result)
            } catch (e: Exception) {
                if (analysis != null) {
                    error = null
                    refreshWarning = "Live refresh delayed. Retrying automatically."
                    if (autoTradeEnabled) autoStatus = "Auto Trade paused until live analysis refresh succeeds."
                } else {
                    error = friendlyError(e, "Analysis failed")
                }
            }
            loading = false
        }
    }

    fun fetchAccount() {
        val s = sessionId ?: return
        viewModelScope.launch {
            try {
                account = client().account(s)
            } catch (_: Exception) { }
        }
    }

    fun updateAutoTradeEnabled(enabled: Boolean) {
        autoTradeEnabled = enabled
        pendingSignalKey = null
        pendingSignalCount = 0
        autoStatus = if (enabled) "Auto Trade armed. Waiting for 2 matching CE/PE confirmations." else "Auto Trade is OFF. Existing positions are not changed."
    }

    fun updateAutoLots(lots: Int) {
        autoLots = lots.coerceIn(1, 5)
    }

    fun placeOrder(side: String, contract: OptionContract, lots: Int = 1) {
        val s = sessionId ?: return
        val token = contract.token
        val tradingSymbol = contract.tradingSymbol
        val exchange = contract.exchange
        if (token.isNullOrBlank() || tradingSymbol.isNullOrBlank() || exchange.isNullOrBlank()) {
            orderMessage = "Selected option contract is incomplete. Refresh and try again."
            return
        }

        orderBusy = true
        orderMessage = null
        viewModelScope.launch {
            try {
                val result = client().placeOrder(s, OrderRequest(side.uppercase(), token, tradingSymbol, exchange, lots.coerceIn(1, 20)))
                result.account?.let { account = it }
                orderMessage = side.uppercase() + " order submitted" + (result.orderId?.let { " • ID " + it } ?: "")
                fetchAccount()
                fetchAnalysis()
            } catch (e: Exception) {
                orderMessage = friendlyError(e, "Order failed")
            }
            orderBusy = false
        }
    }

    private suspend fun evaluateAutoTrade(result: AnalysisResponse) {
        val s = sessionId ?: return
        if (!autoTradeEnabled || autoEvaluating || orderBusy) return
        autoEvaluating = true
        try {
            val latestAccount = try { client().account(s).also { account = it } } catch (_: Exception) {
                autoStatus = "Auto Trade paused: account/position data unavailable."
                return
            }

            val current = autoPositionContract
            if (current != null) {
                val pos = latestAccount.positions.firstOrNull { it.token == current.token && it.netQty > 0 }
                if (pos == null) {
                    clearAutoPosition()
                } else {
                    val ltp = result.market.ltp
                    val signal = autoPositionSignal
                    val stopHit = when (signal) {
                        "CE" -> ltp != null && autoStop != null && ltp <= autoStop!!
                        "PE" -> ltp != null && autoStop != null && ltp >= autoStop!!
                        else -> false
                    }
                    val targetHit = when (signal) {
                        "CE" -> ltp != null && autoTarget != null && ltp >= autoTarget!!
                        "PE" -> ltp != null && autoTarget != null && ltp <= autoTarget!!
                        else -> false
                    }
                    val reversed = (signal == "CE" && result.signal == "PE") || (signal == "PE" && result.signal == "CE")
                    if (stopHit || targetHit || reversed) {
                        val lotSize = (current.lotSize ?: 1).coerceAtLeast(1)
                        val exitLots = floor(pos.netQty / lotSize.toDouble()).toInt().coerceAtLeast(1)
                        val reason = if (stopHit) "stop loss" else if (targetHit) "target 1" else "opposite signal"
                        val exit = client().placeOrder(s, OrderRequest("SELL", current.token.orEmpty(), current.tradingSymbol.orEmpty(), current.exchange.orEmpty(), exitLots))
                        exit.account?.let { account = it }
                        blockedSignal = signal
                        autoStatus = "AUTO EXIT sent on " + reason + (exit.orderId?.let { " • ID " + it } ?: "")
                        clearAutoPosition(true)
                        pendingSignalKey = null
                        pendingSignalCount = 0
                        return
                    }
                    autoStatus = "AUTO HOLD " + (current.tradingSymbol ?: "") + " • " + pos.netQty.toInt() + " qty"
                    return
                }
            }

            if (result.signal != "CE" && result.signal != "PE") {
                blockedSignal = null
                pendingSignalKey = null
                pendingSignalCount = 0
                autoStatus = "WAIT • No auto entry."
                return
            }

            if (blockedSignal == result.signal) {
                autoStatus = "Auto entry locked until the signal resets after the previous exit."
                return
            }

            val contract = result.suggestedContract
            if (contract?.token.isNullOrBlank() || contract?.tradingSymbol.isNullOrBlank() || contract?.exchange.isNullOrBlank()) {
                autoStatus = "Auto Trade waiting for a valid option contract."
                return
            }

            val existingFno = latestAccount.positions.any { it.netQty != 0.0 && (it.exchange.equals("NFO", true) || it.exchange.equals("BFO", true)) }
            if (existingFno) {
                autoStatus = "Auto entry paused: an existing F&O position is open."
                return
            }

            val signalKey = result.signal + "|" + contract!!.token
            if (pendingSignalKey == signalKey) pendingSignalCount += 1 else { pendingSignalKey = signalKey; pendingSignalCount = 1 }
            if (pendingSignalCount < 2) {
                autoStatus = "AUTO " + result.signal + " confirmation 1/2 • waiting for next refresh."
                return
            }

            val buy = client().placeOrder(s, OrderRequest("BUY", contract.token.orEmpty(), contract.tradingSymbol.orEmpty(), contract.exchange.orEmpty(), autoLots))
            buy.account?.let { account = it }
            autoPositionContract = contract
            autoPositionSignal = result.signal
            autoStop = result.levels?.stop
            autoTarget = result.levels?.target1
            autoStatus = "AUTO BUY " + result.signal + " sent • " + (contract.tradingSymbol ?: "") + (buy.orderId?.let { " • ID " + it } ?: "")
            pendingSignalKey = null
            pendingSignalCount = 0
        } catch (e: Exception) {
            autoStatus = "Auto order not executed: " + friendlyError(e, "Order failed")
        } finally {
            autoEvaluating = false
        }
    }

    private fun clearAutoPosition(keepStatus: Boolean = false) {
        autoPositionContract = null
        autoPositionSignal = null
        autoStop = null
        autoTarget = null
        if (!keepStatus) autoStatus = if (autoTradeEnabled) "Auto Trade armed." else "Auto Trade is OFF"
    }

    fun selectSymbol(symbol: String) {
        selectedSymbol = symbol
        analysis = null
        pendingSignalKey = null
        pendingSignalCount = 0
        if (autoTradeEnabled) autoStatus = "Auto Trade armed for " + symbol + ". Waiting for confirmation."
        fetchAnalysis()
    }

    fun startAutoRefresh() {
        refreshJob?.cancel()
        refreshJob = viewModelScope.launch {
            while (isActive && sessionId != null) {
                delay(60_000)
                fetchAnalysis()
                fetchAccount()
            }
        }
    }

    fun stopAutoRefresh() {
        refreshJob?.cancel()
        refreshJob = null
    }

    fun logout() {
        stopAutoRefresh()
        autoTradeEnabled = false
        clearAutoPosition()
        blockedSignal = null
        pendingSignalKey = null
        pendingSignalCount = 0
        sessionId = null
        profile = null
        analysis = null
        account = null
        orderMessage = null
        orderBusy = false
        error = null
        refreshWarning = null
    }

    private fun friendlyError(e: Exception, fallback: String): String {
        if (e is HttpException) {
            val raw = runCatching { e.response()?.errorBody()?.string() }.getOrNull()
            val parsed = raw?.let { body -> runCatching { Gson().fromJson(body, ErrorResponse::class.java)?.error }.getOrNull() }
            if (!parsed.isNullOrBlank()) return parsed
            return "HTTP " + e.code()
        }
        return e.message ?: fallback
    }
}
