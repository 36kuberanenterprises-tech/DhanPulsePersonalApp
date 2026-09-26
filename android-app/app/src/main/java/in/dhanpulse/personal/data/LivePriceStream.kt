package `in`.dhanpulse.personal.data

import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.isActive
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException
import java.util.concurrent.TimeUnit

data class LivePriceEvent(
    val symbol: String = "",
    val status: String = "CONNECTING",
    val price: Double? = null,
    val exchangeTime: String? = null,
    val receivedAt: String? = null,
    val message: String? = null
)

class LivePriceStream(private val backendUrl: String) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.SECONDS)
        .build()
    private val gson = Gson()

    suspend fun collect(sessionId: String, symbol: String, onEvent: suspend (LivePriceEvent) -> Unit) {
        withContext(Dispatchers.IO) {
            val request = Request.Builder()
                .url(backendUrl.trimEnd('/') + "/api/live/" + symbol + "/stream")
                .header("X-Session-Id", sessionId)
                .header("Accept", "text/event-stream")
                .build()
            val call = client.newCall(request)
            val cancellation = currentCoroutineContext()[Job]?.invokeOnCompletion { call.cancel() }
            try {
                call.execute().use { response ->
                    if (!response.isSuccessful) throw IOException("Price stream HTTP " + response.code)
                    val source = response.body?.source() ?: throw IOException("Price stream has no data")
                    while (currentCoroutineContext().isActive) {
                        val line = source.readUtf8Line() ?: break
                        if (line.startsWith("data: ")) {
                            val event = runCatching { gson.fromJson(line.substring(6), LivePriceEvent::class.java) }.getOrNull()
                            if (event != null) onEvent(event)
                        }
                    }
                }
            } finally {
                cancellation?.dispose()
                call.cancel()
            }
        }
    }
}
