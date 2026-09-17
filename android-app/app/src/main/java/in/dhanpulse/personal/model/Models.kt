package `in`.dhanpulse.personal.model

data class LoginRequest(val apiKey: String, val clientCode: String, val pin: String, val totp: String)
data class UserProfile(val clientcode: String? = null, val name: String? = null)
data class LoginResponse(val sessionId: String, val expiresAt: String? = null, val profile: UserProfile? = null)

data class RuleScore(val bullish: Int = 0, val bearish: Int = 0, val considered: Int = 0)
data class SupertrendValue(val direction: String? = null, val value: Double? = null)
data class MarketMetrics(val ltp: Double? = null, val ema9: Double? = null, val ema15: Double? = null, val vwap: Double? = null, val vwapSource: String? = null, val rsi: Double? = null, val macdHistogram: Double? = null, val supertrend: SupertrendValue? = null, val atr: Double? = null)
data class OptionContract(val token: String? = null, val tradingSymbol: String? = null, val strike: Double? = null, val optionType: String? = null, val ltp: Double? = null, val oi: Double? = null, val lotSize: Int? = null)
data class OptionChainSummary(val expiry: String? = null, val atm: Double? = null, val nearAtmPcr: Double? = null, val totalCeOi: Double? = null, val totalPeOi: Double? = null, val support: Double? = null, val resistance: Double? = null, val contracts: List<OptionContract> = emptyList())
data class Levels(val underlyingEntry: Double? = null, val stop: Double? = null, val target1: Double? = null, val target2: Double? = null, val basis: String? = null)
data class SignalRule(val name: String, val state: String, val detail: String? = null)
data class AnalysisResponse(val symbol: String, val timestamp: String? = null, val timeframe: String? = null, val signal: String = "WAIT", val ruleScore: RuleScore = RuleScore(), val market: MarketMetrics = MarketMetrics(), val optionChain: OptionChainSummary = OptionChainSummary(), val suggestedContract: OptionContract? = null, val levels: Levels? = null, val rules: List<SignalRule> = emptyList(), val notes: List<String> = emptyList())
data class ErrorResponse(val error: String? = null)
