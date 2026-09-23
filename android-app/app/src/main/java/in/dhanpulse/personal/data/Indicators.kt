package `in`.dhanpulse.personal.data

import kotlin.math.abs
import kotlin.math.max

data class Candle(val timestamp: String, val open: Double, val high: Double, val low: Double, val close: Double, val volume: Double)
data class MacdValue(val line: Double, val signal: Double, val histogram: Double)
data class SupertrendCalc(val value: Double, val direction: String)

object Indicators {
    fun ema(values: List<Double>, period: Int): Double? {
        if (values.size < period) return null
        val k = 2.0 / (period + 1)
        var current = values.take(period).average()
        for (i in period until values.size) current = values[i] * k + current * (1 - k)
        return current
    }

    private fun emaSeries(values: List<Double>, period: Int): List<Double?> {
        val out = MutableList<Double?>(values.size) { null }
        if (values.size < period) return out
        val k = 2.0 / (period + 1)
        var current = values.take(period).average()
        out[period - 1] = current
        for (i in period until values.size) {
            current = values[i] * k + current * (1 - k)
            out[i] = current
        }
        return out
    }

    fun rsi(values: List<Double>, period: Int = 14): Double? {
        if (values.size <= period) return null
        var gains = 0.0
        var losses = 0.0
        for (i in 1..period) {
            val d = values[i] - values[i - 1]
            if (d >= 0) gains += d else losses -= d
        }
        var avgGain = gains / period
        var avgLoss = losses / period
        for (i in period + 1 until values.size) {
            val d = values[i] - values[i - 1]
            val gain = max(d, 0.0)
            val loss = max(-d, 0.0)
            avgGain = (avgGain * (period - 1) + gain) / period
            avgLoss = (avgLoss * (period - 1) + loss) / period
        }
        if (avgLoss == 0.0) return 100.0
        val rs = avgGain / avgLoss
        return 100.0 - 100.0 / (1.0 + rs)
    }

    fun macd(values: List<Double>, fast: Int = 12, slow: Int = 26, signalPeriod: Int = 9): MacdValue? {
        if (values.size < slow + signalPeriod) return null
        val fastS = emaSeries(values, fast)
        val slowS = emaSeries(values, slow)
        val line = values.indices.map { i -> if (fastS[i] != null && slowS[i] != null) fastS[i]!! - slowS[i]!! else null }
        val valid = line.filterNotNull()
        if (valid.size < signalPeriod) return null
        val signal = ema(valid, signalPeriod) ?: return null
        val last = valid.last()
        return MacdValue(last, signal, last - signal)
    }

    fun atr(candles: List<Candle>, period: Int = 14): Double? {
        if (candles.size <= period) return null
        val trs = mutableListOf<Double>()
        for (i in 1 until candles.size) {
            val c = candles[i]
            val p = candles[i - 1]
            trs += max(c.high - c.low, max(abs(c.high - p.close), abs(c.low - p.close)))
        }
        var current = trs.take(period).average()
        for (i in period until trs.size) current = (current * (period - 1) + trs[i]) / period
        return current
    }

    fun supertrend(candles: List<Candle>, period: Int = 10, multiplier: Double = 3.0): SupertrendCalc? {
        if (candles.size < period + 2) return null
        val tr = MutableList(candles.size) { 0.0 }
        for (i in 1 until candles.size) {
            val c = candles[i]
            val p = candles[i - 1]
            tr[i] = max(c.high - c.low, max(abs(c.high - p.close), abs(c.low - p.close)))
        }
        val atrs = MutableList<Double?>(candles.size) { null }
        var a = tr.subList(1, period + 1).average()
        atrs[period] = a
        for (i in period + 1 until candles.size) {
            a = (a * (period - 1) + tr[i]) / period
            atrs[i] = a
        }
        val finalUpper = MutableList<Double?>(candles.size) { null }
        val finalLower = MutableList<Double?>(candles.size) { null }
        val st = MutableList<Double?>(candles.size) { null }
        val dir = MutableList<Int?>(candles.size) { null }

        for (i in period until candles.size) {
            val ai = atrs[i] ?: continue
            val hl2 = (candles[i].high + candles[i].low) / 2.0
            val upper = hl2 + multiplier * ai
            val lower = hl2 - multiplier * ai
            if (i == period) {
                finalUpper[i] = upper
                finalLower[i] = lower
                st[i] = if (candles[i].close <= upper) upper else lower
                dir[i] = if (candles[i].close > st[i]!!) 1 else -1
                continue
            }
            val pfu = finalUpper[i - 1] ?: upper
            val pfl = finalLower[i - 1] ?: lower
            finalUpper[i] = if (upper < pfu || candles[i - 1].close > pfu) upper else pfu
            finalLower[i] = if (lower > pfl || candles[i - 1].close < pfl) lower else pfl
            st[i] = if (st[i - 1] == pfu) {
                if (candles[i].close <= finalUpper[i]!!) finalUpper[i] else finalLower[i]
            } else {
                if (candles[i].close >= finalLower[i]!!) finalLower[i] else finalUpper[i]
            }
            dir[i] = if (candles[i].close > st[i]!!) 1 else -1
        }
        val i = candles.lastIndex
        val value = st[i] ?: return null
        return SupertrendCalc(value, if (dir[i] == 1) "BULLISH" else "BEARISH")
    }

    fun vwap(candles: List<Candle>): Double? {
        var pv = 0.0
        var vol = 0.0
        candles.forEach { c ->
            if (c.volume > 0) {
                val typical = (c.high + c.low + c.close) / 3.0
                pv += typical * c.volume
                vol += c.volume
            }
        }
        return if (vol > 0) pv / vol else null
    }
}
