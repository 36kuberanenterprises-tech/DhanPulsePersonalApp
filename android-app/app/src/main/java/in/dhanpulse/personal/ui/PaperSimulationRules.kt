package `in`.dhanpulse.personal.ui

import `in`.dhanpulse.personal.model.PaperStockTrade
import `in`.dhanpulse.personal.model.StockCandidate
import `in`.dhanpulse.personal.model.StockQuote
import `in`.dhanpulse.personal.model.StockScanResponse
import java.time.Instant
import java.time.LocalTime
import java.time.ZoneId
import kotlin.math.abs

/**
 * Research only. A qualifying signal is not a broker fill.
 * Auto paper records the latest observed quote, never a better theoretical price.
 */
internal object PaperSimulationRules {
    private val india = ZoneId.of("Asia/Kolkata")
    private fun scanRecent(scan: StockScanResponse, now: Long): Boolean {
        val at = runCatching { Instant.parse(scan.timestamp).toEpochMilli() }.getOrNull() ?: return false
        return now - at in 0L..45_000L
    }

    fun selectAutoEntry(
        scan: StockScanResponse,
        now: Long,
        tradedToday: Set<String>
    ): StockCandidate? {
        val at = Instant.ofEpochMilli(now).atZone(india)
        val time = at.toLocalTime()
        if (at.dayOfWeek.value !in 1..5 ||
            time.isBefore(LocalTime.of(9, 30)) ||
            !time.isBefore(LocalTime.of(14, 45)) ||
            scan.marketStatus != "SCANNING" || !scanRecent(scan, now)) return null

        return scan.candidates.firstOrNull { candidate ->
            val plan = candidate.plan
            val price = candidate.price
            candidate.status == "READY" &&
                candidate.side in setOf("BUY", "SELL") &&
                candidate.token.matches(Regex("\\d{1,12}")) &&
                candidate.symbol.isNotBlank() &&
                "${candidate.symbol}|${candidate.side}" !in tradedToday &&
                plan != null && price != null &&
                price.isFinite() && price > 0 &&
                plan.entry.isFinite() && plan.entry > 0 &&
                plan.stop.isFinite() && plan.stop > 0 &&
                plan.quantity > 0 &&
                plan.estimatedLoss.isFinite() && plan.estimatedLoss > 0 &&
                ((candidate.side == "BUY" && price >= plan.entry && plan.stop < price) ||
                    (candidate.side == "SELL" && price <= plan.entry && plan.stop > price)) &&
                abs(price - plan.entry) / plan.entry <= 0.0025
        }
    }

    fun autoExitAtObservedQuote(
        open: PaperStockTrade,
        quote: StockQuote?,
        scan: StockScanResponse,
        now: Long
    ): Pair<Double, String>? {
        if (!scanRecent(scan, now) || quote?.fresh != true ||
            quote.token != open.token || quote.price <= 0 ||
            !quote.price.isFinite()) return null
        val price = quote.price
        val hitStop = if (open.side == "BUY") price <= open.stop else price >= open.stop
        val hitTarget = if (open.side == "BUY") price >= open.target2 else price <= open.target2
        return when {
            hitStop -> price to "Stop crossed on sampled quote"
            hitTarget -> price to "Target 2 crossed on sampled quote"
            else -> null
        }
    }
}
