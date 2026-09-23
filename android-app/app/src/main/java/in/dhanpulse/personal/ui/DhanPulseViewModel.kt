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
                analysis = client().analysis(s, selectedSymbol, "FIVE_MINUTE")
                error = null
                refreshWarning = null
            } catch (e: Exception) {
                if (analysis != null) {
                    error = null
                    refreshWarning = "Live refresh delayed. Retrying automatically."
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
            } catch (_: Exception) {
                // Keep last successful balance and P&L snapshot.
            }
        }
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
                val result = client().placeOrder(
                    s,
                    OrderRequest(
                        side = side.uppercase(),
                        token = token,
                        tradingSymbol = tradingSymbol,
                        exchange = exchange,
                        lots = lots.coerceIn(1, 20)
                    )
                )
                result.account?.let { account = it }
                orderMessage = buildString {
                    append(side.uppercase())
                    append(" order submitted")
                    result.orderId?.let { append(" • ID "); append(it) }
                }
                fetchAccount()
                fetchAnalysis()
            } catch (e: Exception) {
                orderMessage = friendlyError(e, "Order failed")
            }
            orderBusy = false
        }
    }

    fun selectSymbol(symbol: String) {
        selectedSymbol = symbol
        analysis = null
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
            val parsed = raw?.let { body ->
                runCatching { Gson().fromJson(body, ErrorResponse::class.java)?.error }.getOrNull()
            }
            if (!parsed.isNullOrBlank()) return parsed
            return "HTTP " + e.code()
        }
        return e.message ?: fallback
    }
}
