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
import kotlin.math.round

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

    var premiumTradePlan by mutableStateOf(PremiumTradePlan())
        private set
    var signalHistory by mutableStateOf<List<SignalCall>>(emptyList())
        private set
    var signalStats by mutableStateOf(SignalStats())
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

    private val signalPrefs = app.getSharedPreferences("dhanpulse_signal_tracker", 0)
    private var callPendingKey: String? = null
    private var callPendingCount = 0
    private var blockedCallBias: String? = null
    private val pendingCancelCounts = mutableMapOf<String, Int>()

    init {
        loadSignalHistory()
    }

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
                updateSignalTracker(result)
                updatePremiumDecision(result)
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


    private fun tick(value: Double): Double = round(value / 0.05) * 0.05

    private fun premiumLevels(reference: Double, timeframe: String): PremiumTradePlan {
        val cfg = when (timeframe) {
            "ONE_MINUTE" -> doubleArrayOf(1.01, 0.94, 1.08, 1.12, 1.18)
            "THREE_MINUTE" -> doubleArrayOf(1.015, 0.93, 1.10, 1.16, 1.23)
            "TEN_MINUTE" -> doubleArrayOf(1.025, 0.90, 1.15, 1.25, 1.35)
            "FIFTEEN_MINUTE" -> doubleArrayOf(1.03, 0.88, 1.18, 1.30, 1.45)
            else -> doubleArrayOf(1.02, 0.92, 1.12, 1.20, 1.30)
        }
        val entry = tick(reference * cfg[0])
        return PremiumTradePlan(
            referencePremium = tick(reference),
            entry = entry,
            stopLoss = tick(entry * cfg[1]),
            target1 = tick(entry * cfg[2]),
            target2 = tick(entry * cfg[3]),
            target3 = tick(entry * cfg[4])
        )
    }

    private fun activeTrackedCall(a: AnalysisResponse): SignalCall? =
        signalHistory.firstOrNull {
            it.symbol == a.symbol &&
            it.timeframe == (a.timeframe ?: selectedTimeframe) &&
            it.status !in setOf("T3_HIT", "SL_HIT", "UNRESOLVED", "CANCELLED")
        }

    private fun updatePremiumDecision(a: AnalysisResponse) {
        val tracked = activeTrackedCall(a)
        if (tracked != null) {
            val stage = when (tracked.status) {
                "WAITING_ENTRY" -> "WAITING_ENTRY"
                "ENTERED" -> "ENTRY_ACTIVE"
                "T1_HIT" -> "TARGET_1_HIT"
                "T2_HIT" -> "TARGET_2_HIT"
                "T3_HIT" -> "TARGET_3_HIT"
                "SL_HIT" -> "STOP_LOSS_HIT"
                "CANCELLED" -> "CANCELLED"
                else -> tracked.status
            }
            premiumTradePlan = PremiumTradePlan(
                signal = tracked.side,
                contract = a.optionChain.contracts.firstOrNull { it.token == tracked.token } ?: a.suggestedContract,
                referencePremium = tracked.referencePremium,
                entry = tracked.entry,
                stopLoss = tracked.stopLoss,
                target1 = tracked.target1,
                target2 = tracked.target2,
                target3 = tracked.target3,
                status = tracked.status,
                stage = stage,
                confirmationCount = 2,
                confirmationRequired = 2,
                decisionNote = "Recorded call is locked. Live premium is being tracked against the original levels.",
                callId = tracked.id
            )
            return
        }

        val decision = a.tradeDecision
        val contract = a.suggestedContract
        val premium = contract?.ltp

        if (decision.direction !in setOf("CE", "PE") || contract == null || premium == null || premium <= 0) {
            premiumTradePlan = PremiumTradePlan(
                signal = "WAIT",
                contract = contract,
                status = "WAIT",
                stage = "WATCHING",
                confirmationCount = 0,
                confirmationRequired = 2,
                decisionNote = decision.message.ifBlank { "Waiting for a directional setup." }
            )
            return
        }

        if (!decision.setupAllowed) {
            premiumTradePlan = PremiumTradePlan(
                signal = decision.direction,
                contract = contract,
                referencePremium = tick(premium),
                status = "FILTERED",
                stage = decision.status,
                confirmationCount = 0,
                confirmationRequired = 2,
                decisionNote = decision.message
            )
            return
        }

        val lv = premiumLevels(premium, a.timeframe ?: selectedTimeframe)
        premiumTradePlan = lv.copy(
            signal = decision.direction,
            contract = contract,
            status = "BUY_ABOVE",
            stage = if (callPendingCount <= 0) "SETUP_FORMING" else "CONFIRMING",
            confirmationCount = callPendingCount.coerceAtMost(2),
            confirmationRequired = 2,
            decisionNote = "Meta decision passed. Confirming the same direction and strike on two live scans before the call is recorded."
        )
    }

    private fun updateSignalTracker(a: AnalysisResponse) {
        val now = System.currentTimeMillis()
        val currentDate = (a.timestamp ?: "").take(10).ifBlank {
            java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.US).format(java.util.Date(now))
        }

        var changed = false
        val updated = signalHistory.map { call ->
            if (call.status in setOf("T3_HIT", "SL_HIT", "UNRESOLVED", "CANCELLED")) return@map call
            if (call.sessionDate != currentDate) {
                pendingCancelCounts.remove(call.id)
                changed = true
                return@map call.copy(status = "UNRESOLVED")
            }

            if (call.entryHitAt == null) {
                val sameSetup = a.tradeDecision.setupAllowed &&
                    a.tradeDecision.direction == call.side &&
                    a.suggestedContract?.token == call.token
                if (!sameSetup) {
                    val misses = (pendingCancelCounts[call.id] ?: 0) + 1
                    pendingCancelCounts[call.id] = misses
                    if (misses >= 3) {
                        pendingCancelCounts.remove(call.id)
                        changed = true
                        return@map call.copy(cancelledAt = now, status = "CANCELLED")
                    }
                } else {
                    pendingCancelCounts.remove(call.id)
                }
            }

            val currentPremium: Double = (
                a.optionChain.contracts.firstOrNull { it.token == call.token }?.ltp
                    ?: if (a.suggestedContract?.token == call.token) a.suggestedContract?.ltp else null
                ) ?: return@map call

            var x = call.copy(lastPremium = tick(currentPremium))
            if (x.entryHitAt == null && currentPremium >= x.entry) {
                x = x.copy(entryHitAt = now, status = "ENTERED")
                changed = true
            }
            if (x.entryHitAt != null) {
                if (x.t1HitAt == null && currentPremium >= x.target1) {
                    x = x.copy(t1HitAt = now, status = "T1_HIT")
                    changed = true
                }
                if (x.t2HitAt == null && currentPremium >= x.target2) {
                    x = x.copy(t2HitAt = now, status = "T2_HIT")
                    changed = true
                }
                if (x.t3HitAt == null && currentPremium >= x.target3) {
                    x = x.copy(t3HitAt = now, status = "T3_HIT")
                    changed = true
                } else if (x.t3HitAt == null && x.slHitAt == null && currentPremium <= x.stopLoss) {
                    x = x.copy(slHitAt = now, status = "SL_HIT")
                    changed = true
                }
            }
            x
        }.sortedByDescending { it.generatedAt }

        if (changed) {
            signalHistory = updated
            persistSignalHistory()
            refreshSignalStats()
        }

        val decision = a.tradeDecision
        if (!decision.setupAllowed || decision.direction !in setOf("CE", "PE")) {
            blockedCallBias = null
            callPendingKey = null
            callPendingCount = 0
            return
        }

        val contract = a.suggestedContract ?: return
        val premium = contract.ltp ?: return
        if (premium <= 0) return
        if (activeTrackedCall(a) != null) return

        val biasKey = a.symbol + "|" + (a.timeframe ?: selectedTimeframe) + "|" + decision.direction
        if (blockedCallBias == biasKey) return

        val confirmKey = biasKey + "|" + (contract.token ?: contract.tradingSymbol ?: "")
        if (callPendingKey == confirmKey) callPendingCount++ else {
            callPendingKey = confirmKey
            callPendingCount = 1
        }
        if (callPendingCount < 2) return

        val lv = premiumLevels(premium, a.timeframe ?: selectedTimeframe)
        val entry = lv.entry ?: return
        val sl = lv.stopLoss ?: return
        val t1 = lv.target1 ?: return
        val t2 = lv.target2 ?: return
        val t3 = lv.target3 ?: return
        val token = contract.token ?: return
        val symbol = contract.tradingSymbol ?: return

        val call = SignalCall(
            id = "CALL-" + now.toString(),
            symbol = a.symbol,
            timeframe = a.timeframe ?: selectedTimeframe,
            side = decision.direction,
            token = token,
            tradingSymbol = symbol,
            strike = contract.strike,
            exchange = contract.exchange,
            generatedAt = now,
            sessionDate = currentDate,
            referencePremium = tick(premium),
            entry = entry,
            stopLoss = sl,
            target1 = t1,
            target2 = t2,
            target3 = t3,
            lastPremium = tick(premium),
            status = "WAITING_ENTRY"
        )

        signalHistory = (listOf(call) + signalHistory).take(5000)
        blockedCallBias = biasKey
        callPendingKey = null
        callPendingCount = 0
        persistSignalHistory()
        refreshSignalStats()
        premiumTradePlan = PremiumTradePlan(
            signal = call.side,
            contract = contract,
            referencePremium = call.referencePremium,
            entry = call.entry,
            stopLoss = call.stopLoss,
            target1 = call.target1,
            target2 = call.target2,
            target3 = call.target3,
            status = call.status,
            stage = "WAITING_ENTRY",
            confirmationCount = 2,
            confirmationRequired = 2,
            decisionNote = "Confirmed call recorded. Waiting for the option premium to cross the fixed Buy Above level.",
            callId = call.id
        )
    }

    private fun loadSignalHistory() {
        val raw = signalPrefs.getString("history_json", null) ?: return refreshSignalStats()
        signalHistory = runCatching {
            Gson().fromJson(raw, Array<SignalCall>::class.java)?.toList() ?: emptyList()
        }.getOrDefault(emptyList())
        refreshSignalStats()
    }

    private fun persistSignalHistory() {
        signalPrefs.edit().putString("history_json", Gson().toJson(signalHistory.take(5000))).apply()
    }

    private fun refreshSignalStats() {
        val h = signalHistory
        signalStats = SignalStats(
            generated = h.size,
            entered = h.count { it.entryHitAt != null },
            target1Hits = h.count { it.t1HitAt != null },
            target2Hits = h.count { it.t2HitAt != null },
            target3Hits = h.count { it.t3HitAt != null },
            stopLossHits = h.count { it.slHitAt != null },
            cancelled = h.count { it.status == "CANCELLED" },
            open = h.count { it.status !in setOf("T3_HIT", "SL_HIT", "UNRESOLVED", "CANCELLED") },
            unresolved = h.count { it.status == "UNRESOLVED" }
        )
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
