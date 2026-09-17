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

    fun clear() = prefs.edit().clear().apply()
}
