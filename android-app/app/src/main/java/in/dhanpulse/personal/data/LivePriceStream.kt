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

class LiveStreamHttpException(val httpStatus: Int, details: String) : IOException("Live stream HTTP $httpStatus: $details")

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
        .readTimeout(45, TimeUnit.SECONDS)
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
                    if (!response.isSuccessful) {
                        // The backend can report a missing MCX token, expired session, or unavailable feed.
                        // Limit error-body reads: no private headers or session IDs are logged or displayed.
                        val message = response.body?.string()?.take(240) ?: "No server details"
                        val summary = runCatching { gson.fromJson(message, Map::class.java)["error"]?.toString() }
                            .getOrNull()?.take(160) ?: "Backend rejected the stream request"
                        throw LiveStreamHttpException(response.code, summary)
                    }
                    val source = response.body?.source() ?: throw IOException("Price stream has no data")
                    // Heartbeat/comment traffic can keep HTTP open even when prices have stopped.
                    // Restart only the read-only stream after a bounded interval without a LIVE quote.
                    var lastLiveAt = android.os.SystemClock.elapsedRealtime()
                    while (currentCoroutineContext().isActive) {
                        val line = source.readUtf8Line() ?: break
                        if (line.startsWith("data: ")) {
                            val event = runCatching { gson.fromJson(line.substring(6), LivePriceEvent::class.java) }.getOrNull()
                            if (event != null) {
                                if (event.status == "LIVE" && event.price != null && event.price > 0) {
                                    lastLiveAt = android.os.SystemClock.elapsedRealtime()
                                }
                                onEvent(event)
                            }
                        }
                        if (android.os.SystemClock.elapsedRealtime() - lastLiveAt >= 90_000L) {
                            throw IOException("Live price stream stalled: no LIVE quotes for 90 seconds")
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
