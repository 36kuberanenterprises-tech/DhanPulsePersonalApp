package in.qrnumber.app

import android.net.Uri
import java.security.MessageDigest
import java.util.Locale

object QrIdentity {
    data class Parsed(
        val key: String,
        val label: String,
        val rawType: String
    )

    fun parse(raw: String): Parsed {
        val value = raw.trim()
        require(value.isNotEmpty()) { "QR code is empty" }

        if (value.startsWith("upi://pay", ignoreCase = true)) {
            val uri = Uri.parse(value)
            val pa = uri.getQueryParameter("pa")?.trim()?.lowercase(Locale.ROOT)
            val pn = uri.getQueryParameter("pn")?.trim()
            if (!pa.isNullOrBlank()) {
                val stable = "upi:$pa"
                val label = if (!pn.isNullOrBlank()) "$pn  •  $pa" else pa
                return Parsed(
                    key = "K:${sha256(stable)}",
                    label = label,
                    rawType = "UPI QR"
                )
            }
        }

        val digest = sha256("qr:$value")
        val shortLabel = if (value.length <= 64) value else "QR ${digest.take(12).uppercase(Locale.ROOT)}"
        return Parsed(
            key = "K:$digest",
            label = shortLabel,
            rawType = "QR code"
        )
    }

    private fun sha256(text: String): String {
        val bytes = MessageDigest.getInstance("SHA-256").digest(text.toByteArray(Charsets.UTF_8))
        return bytes.joinToString("") { "%02x".format(it) }
    }
}
