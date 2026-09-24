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
    var selectedTimeframe by mutableStateOf("FIVE_MINUTE")
    var analysis by mutableStateOf<AnalysisResponse?>(null)
    var account by mutableStateOf<AccountSummary?>(null)
    var loading by mutableStateOf(false)
    var error by mutableStateOf<String?>(null)
    var refreshWarning by mutableStateOf<String?>(null)
    var orderBusy by mutableStateOf(false)
    var orderMessage by mutableStateOf<String?>(null)
    var orderGateway by mutableStateOf<OrderGatewayDiagnostics?>(null)
        private set
    var orderGatewayBusy by mutableStateOf(false)
        private set

    var backtestYears by mutableStateOf(3)
        private set
    var backtestCapital by mutableStateOf(20000.0)
        private set
    var backtestBusy by mutableStateOf(false)
        private set
    var backtestReport by mutableStateOf<BacktestReport?>(null)
        private set
    var backtestError by mutableStateOf<String?>(null)
        private set

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
    private var analysisRefreshInFlight = false

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
                fetchOrderDiagnostics()
            } catch (e: Exception) {
                error = friendlyError(e, "Login failed")
            }
            loading = false
            onDone()
        }
    }

    fun fetchAnalysis() {
        val s = sessionId ?: return
        if (analysisRefreshInFlight) return
        analysisRefreshInFlight = true
        loading = analysis == null
        viewModelScope.launch {
            try {
                val result = client().analysis(s, selectedSymbol, selectedTimeframe)
                analysis = result
                error = null
                refreshWarning = null
                if (autoTradeEnabled) evaluateAutoTrade(result)
            } catch (e: Exception) {
                if (e is HttpException && e.code() == 401) {
                    sessionId = null
                    profile = null
                    analysis = null
                    account = null
                    autoTradeEnabled = false
                    error = "Session expired. Please login again."
                } else if (analysis != null) {
                    error = null
                    refreshWarning = "Live refresh delayed. Retrying automatically."
                    if (autoTradeEnabled) autoStatus = "Auto Trade paused until live analysis refresh succeeds."
                } else {
                    val msg = friendlyError(e, "Analysis failed")
                    if (
                        msg.contains("Market history", ignoreCase = true) ||
                        msg.contains("rate-limit", ignoreCase = true) ||
                        msg.contains("rate limit", ignoreCase = true) ||
                        msg.contains("403")
                    ) {
                        error = null
                        refreshWarning = "Preparing prior-session candles. Live quotes will continue automatically."
                    } else {
                        error = msg
                    }
                }
            }
            loading = false
            analysisRefreshInFlight = false
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

    fun fetchOrderDiagnostics() {
        val s = sessionId ?: return
        if (orderGatewayBusy) return
        orderGatewayBusy = true
        viewModelScope.launch {
            try {
                orderGateway = client().orderDiagnostics(s)
            } catch (e: Exception) {
                orderGateway = OrderGatewayDiagnostics(
                    backendReached = false,
                    brokerSessionOk = false,
                    executionReady = false,
                    status = "DIAGNOSTIC_FAILED",
                    message = friendlyError(e, "Unable to verify order gateway")
                )
            }
            orderGatewayBusy = false
        }
    }

    fun updateBacktestYears(years: Int) {
        backtestYears = if (years in setOf(1, 3, 5)) years else 3
        backtestReport = null
        backtestError = null
    }

    fun updateBacktestCapital(capital: Double) {
        backtestCapital = capital.coerceIn(1000.0, 10000000.0)
        backtestReport = null
    }

    fun runBacktest() {
        val s = sessionId ?: return
        if (autoTradeEnabled) {
            backtestError = "Switch Auto Trade OFF before running a historical backtest. This avoids historical API traffic interfering with live automatic trading."
            return
        }
        backtestBusy = true
        backtestError = null
        stopAutoRefresh()
        viewModelScope.launch {
            try {
                backtestReport = client().backtest(
                    s,
                    BacktestRequest(
                        symbol = selectedSymbol,
                        interval = selectedTimeframe,
                        years = backtestYears,
                        capital = backtestCapital
                    )
                )
            } catch (e: Exception) {
                backtestError = friendlyError(e, "Backtest failed")
            }
            backtestBusy = false
            startAutoRefresh()
        }
    }

    fun updateAutoTradeEnabled(enabled: Boolean) {
        pendingSignalKey = null
        pendingSignalCount = 0
        if (!enabled) {
            autoTradeEnabled = false
            autoStatus = "Auto Trade is OFF. Existing positions are not changed."
            return
        }

        val gateway = orderGateway
        if (gateway?.executionReady != true) {
            autoTradeEnabled = false
            autoStatus = gateway?.message ?: "Live Auto blocked: real-order gateway is not ready."
            fetchOrderDiagnostics()
            return
        }

        val researchPassed = backtestReport?.adaptive?.gatePassed == true
        autoTradeEnabled = true
        autoStatus = if (researchPassed) {
            "Order gateway READY and research gate PASSED. Auto Trade armed for 2 matching CE/PE confirmations."
        } else {
            "Order gateway READY. Auto Trade armed with RESEARCH WARNING: this symbol/timeframe has not passed Adaptive validation."
        }
    }

    fun updateAutoLots(lots: Int) {
        autoLots = lots.coerceIn(1, 5)
    }

    fun placeOrder(side: String, contract: OptionContract, lots: Int = 1) {
        val s = sessionId ?: return
        if (autoTradeEnabled) {
            autoTradeEnabled = false
            clearAutoPosition()
            blockedSignal = null
            pendingSignalKey = null
            pendingSignalCount = 0
            autoStatus = "Auto Trade stopped because you used Manual Trade."
        }
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
                val statusText = result.orderStatus?.let { " • " + it.uppercase() } ?: ""
                val fillText = result.filledShares?.takeIf { it > 0 }?.let { " • filled " + it.toInt() } ?: ""
                val traceText = result.traceId?.let { " • trace " + it } ?: ""
                orderMessage = side.uppercase() + " order accepted" +
                    (result.orderId?.let { " • ID " + it } ?: "") + statusText + fillText + traceText
                fetchAccount()
                fetchAnalysis()
                fetchOrderDiagnostics()
            } catch (e: Exception) {
                orderMessage = friendlyError(e, "Order failed")
                fetchOrderDiagnostics()
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

    fun selectTimeframe(interval: String) {
        val allowed = setOf("ONE_MINUTE", "THREE_MINUTE", "FIVE_MINUTE", "TEN_MINUTE", "FIFTEEN_MINUTE")
        if (interval !in allowed) return
        selectedTimeframe = interval
        if (autoTradeEnabled) {
            autoTradeEnabled = false
            autoStatus = "Auto Trade switched OFF because timeframe changed. Re-arm Auto Trade after checking the new setup."
        }
        analysis = null
        backtestReport = null
        backtestError = null
        pendingSignalKey = null
        pendingSignalCount = 0
        if (autoTradeEnabled) autoStatus = "Auto Trade armed on " + timeframeLabel(interval) + ". Waiting for confirmation."
        fetchAnalysis()
    }

    private fun timeframeLabel(interval: String): String = when (interval) {
        "ONE_MINUTE" -> "1 min"
        "THREE_MINUTE" -> "3 min"
        "TEN_MINUTE" -> "10 min"
        "FIFTEEN_MINUTE" -> "15 min"
        else -> "5 min"
    }

    fun selectSymbol(symbol: String) {
        selectedSymbol = symbol
        if (autoTradeEnabled) {
            autoTradeEnabled = false
            autoStatus = "Auto Trade switched OFF because symbol changed. Re-arm Auto Trade after checking the new setup."
        }
        analysis = null
        backtestReport = null
        backtestError = null
        pendingSignalKey = null
        pendingSignalCount = 0
        if (autoTradeEnabled) autoStatus = "Auto Trade armed for " + symbol + ". Waiting for confirmation."
        fetchAnalysis()
    }

    fun startAutoRefresh() {
        refreshJob?.cancel()
        refreshJob = viewModelScope.launch {
            var tick = 0
            while (isActive && sessionId != null) {
                delay(3_000)
                fetchAnalysis()
                tick++
                if (tick % 5 == 0) fetchAccount()
                if (tick % 20 == 0) fetchOrderDiagnostics()
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
        orderGateway = null
        orderGatewayBusy = false
        backtestBusy = false
        backtestReport = null
        backtestError = null
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
