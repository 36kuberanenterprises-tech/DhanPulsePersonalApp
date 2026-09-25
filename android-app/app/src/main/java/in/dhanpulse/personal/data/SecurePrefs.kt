package `in`.dhanpulse.personal.data

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class SecurePrefs(context: Context) {
    private val masterKey = MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
    private val prefs = EncryptedSharedPreferences.create(
        context, "dhanpulse_secure", masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    var backendUrl: String
        get() = prefs.getString("backendUrl", "") ?: ""
        set(v) = prefs.edit().putString("backendUrl", v).apply()
    var clientCode: String
        get() = prefs.getString("clientCode", "") ?: ""
        set(v) = prefs.edit().putString("clientCode", v).apply()
    var apiKey: String
        get() = prefs.getString("apiKey", "") ?: ""
        set(v) = prefs.edit().putString("apiKey", v).apply()

    var sessionId: String?
        get() = prefs.getString("sessionId", null)
        set(v) = prefs.edit().putString("sessionId", v).apply()
    var sessionExpiry: Long
        get() = prefs.getLong("sessionExpiry", 0L)
        set(v) = prefs.edit().putLong("sessionExpiry", v).apply()
    var lastUserActivity: Long
        get() = prefs.getLong("lastUserActivity", 0L)
        set(v) = prefs.edit().putLong("lastUserActivity", v).apply()
    var profileName: String?
        get() = prefs.getString("profileName", null)
        set(v) = prefs.edit().putString("profileName", v).apply()
    var profileCode: String?
        get() = prefs.getString("profileCode", null)
        set(v) = prefs.edit().putString("profileCode", v).apply()

    fun clearSession() {
        prefs.edit().remove("sessionId").remove("sessionExpiry").remove("lastUserActivity")
            .remove("profileName").remove("profileCode").apply()
    }

    fun clear() = prefs.edit().clear().apply()
}
