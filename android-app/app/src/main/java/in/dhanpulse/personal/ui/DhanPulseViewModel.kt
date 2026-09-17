package `in`.dhanpulse.personal.ui

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import `in`.dhanpulse.personal.data.ApiFactory
import `in`.dhanpulse.personal.data.DhanPulseApi
import `in`.dhanpulse.personal.data.SecurePrefs
import `in`.dhanpulse.personal.model.*
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class DhanPulseViewModel(app: Application) : AndroidViewModel(app) {
    private val prefs = SecurePrefs(app)

    var backendUrl by mutableStateOf(prefs.backendUrl)
    var clientCode by mutableStateOf(prefs.clientCode)
    var apiKey by mutableStateOf(prefs.apiKey)
    var sessionId by mutableStateOf<String?>(null)
    var profile by mutableStateOf<UserProfile?>(null)
    var selectedSymbol by mutableStateOf("NIFTY")
    var analysis by mutableStateOf<AnalysisResponse?>(null)
    var loading by mutableStateOf(false)
    var error by mutableStateOf<String?>(null)
    private var api: DhanPulseApi? = null
    private var refreshJob: Job? = null

    private fun client(): DhanPulseApi {
        val existing = api
        if (existing != null) return existing
        return ApiFactory.create(backendUrl).also { api = it }
    }

    fun login(pin: String, totp: String, onDone: () -> Unit) {
        error = null
        if (!backendUrl.startsWith("https://")) { error = "Backend URL must use HTTPS"; onDone(); return }
        if (apiKey.isBlank() || clientCode.isBlank() || pin.isBlank() || totp.isBlank()) { error = "Complete all login fields"; onDone(); return }
        loading = true
        api = null
        viewModelScope.launch {
            try {
                val r = client().login(LoginRequest(apiKey.trim(), clientCode.trim(), pin, totp.trim()))
                sessionId = r.sessionId
                profile = r.profile
                prefs.backendUrl = backendUrl.trim()
                prefs.clientCode = clientCode.trim()
                prefs.apiKey = apiKey.trim()
                fetchAnalysis()
            } catch (e: Exception) { error = e.message ?: "Login failed" }
            loading = false
            onDone()
        }
    }

    fun fetchAnalysis() {
        val s = sessionId ?: return
        loading = analysis == null
        viewModelScope.launch {
            try { analysis = client().analysis(s, selectedSymbol, "FIVE_MINUTE"); error = null }
            catch (e: Exception) { error = e.message ?: "Analysis failed" }
            loading = false
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
            while (isActive && sessionId != null) { delay(15_000); fetchAnalysis() }
        }
    }

    fun stopAutoRefresh() { refreshJob?.cancel(); refreshJob = null }

    fun logout() {
        stopAutoRefresh(); sessionId = null; profile = null; analysis = null; error = null
    }
}
