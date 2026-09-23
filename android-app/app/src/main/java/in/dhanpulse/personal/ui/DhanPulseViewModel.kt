package `in`.dhanpulse.personal.ui

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import `in`.dhanpulse.personal.data.ApiFactory
import `in`.dhanpulse.personal.data.DhanPulseApi
import `in`.dhanpulse.personal.model.*
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class DhanPulseViewModel(app: Application) : AndroidViewModel(app) {
    private val backendUrl = "https://dhanpulse-personal-api.onrender.com"

    var sessionId by mutableStateOf<String?>(null)
    var profile by mutableStateOf<UserProfile?>(null)
    var selectedSymbol by mutableStateOf("NIFTY")
    var analysis by mutableStateOf<AnalysisResponse?>(null)
    var loading by mutableStateOf(false)
    var error by mutableStateOf<String?>(null)
    var refreshWarning by mutableStateOf<String?>(null)
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
            } catch (e: Exception) {
                error = e.message ?: "Login failed"
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
                    error = e.message ?: "Analysis failed"
                }
            }
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
            while (isActive && sessionId != null) {
                delay(60_000)
                fetchAnalysis()
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
        error = null
        refreshWarning = null
    }
}
