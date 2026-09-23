package `in`.dhanpulse.personal.model

data class LoginRequest(val apiKey: String, val clientCode: String, val pin: String, val totp: String)
data class UserProfile(val clientcode: String? = null, val name: String? = null)
data class LoginResponse(val sessionId: String, val expiresAt: String? = null, val profile: UserProfile? = null)

data class RuleScore(val bullish: Int = 0, val bearish: Int = 0, val considered: Int = 0)
data class SupertrendValue(val direction: String? = null, val value: Double? = null)
data class MarketMetrics(val ltp: Double? = null, val ema9: Double? = null, val ema15: Double? = null, val vwap: Double? = null, val vwapSource: String? = null, val rsi: Double? = null, val macdHistogram: Double? = null, val supertrend: SupertrendValue? = null, val atr: Double? = null)
data class OptionContract(val token: String? = null, val tradingSymbol: String? = null, val exchange: String? = null, val strike: Double? = null, val optionType: String? = null, val ltp: Double? = null, val oi: Double? = null, val lotSize: Int? = null)
data class OptionChainSummary(val expiry: String? = null, val atm: Double? = null, val nearAtmPcr: Double? = null, val totalCeOi: Double? = null, val totalPeOi: Double? = null, val support: Double? = null, val resistance: Double? = null, val contracts: List<OptionContract> = emptyList())
data class Levels(val underlyingEntry: Double? = null, val stop: Double? = null, val target1: Double? = null, val target2: Double? = null, val basis: String? = null)
data class SignalRule(val name: String, val state: String, val detail: String? = null)
data class AnalysisResponse(val symbol: String, val timestamp: String? = null, val timeframe: String? = null, val signal: String = "WAIT", val ruleScore: RuleScore = RuleScore(), val market: MarketMetrics = MarketMetrics(), val optionChain: OptionChainSummary = OptionChainSummary(), val suggestedContract: OptionContract? = null, val levels: Levels? = null, val rules: List<SignalRule> = emptyList(), val notes: List<String> = emptyList())
data class ErrorResponse(val error: String? = null)

data class PositionSummary(
    val exchange: String? = null,
    val token: String? = null,
    val tradingSymbol: String? = null,
    val productType: String? = null,
    val netQty: Double = 0.0,
    val buyQty: Double = 0.0,
    val sellQty: Double = 0.0,
    val buyAvgPrice: Double = 0.0,
    val sellAvgPrice: Double = 0.0,
    val ltp: Double = 0.0,
    val realizedPnl: Double = 0.0,
    val unrealizedPnl: Double = 0.0,
    val pnl: Double = 0.0
)

data class AccountSummary(
    val availableCash: Double = 0.0,
    val net: Double = 0.0,
    val utilizedDebits: Double = 0.0,
    val availableLimitMargin: Double = 0.0,
    val realizedPnl: Double = 0.0,
    val unrealizedPnl: Double = 0.0,
    val totalPnl: Double = 0.0,
    val positions: List<PositionSummary> = emptyList()
)

data class OrderRequest(
    val side: String,
    val token: String,
    val tradingSymbol: String,
    val exchange: String,
    val lots: Int = 1
)

data class OrderResponse(
    val ok: Boolean = false,
    val side: String? = null,
    val lots: Int = 0,
    val quantity: Int = 0,
    val lotSize: Int = 0,
    val tradingSymbol: String? = null,
    val orderId: String? = null,
    val uniqueOrderId: String? = null,
    val message: String? = null,
    val account: AccountSummary? = null
)


data class BacktestRequest(
    val symbol: String,
    val interval: String,
    val years: Int = 3,
    val capital: Double = 20000.0
)

data class BacktestYear(
    val year: String = "",
    val netR: Double = 0.0,
    val modelPnl: Double = 0.0
)

data class BacktestStrategy(
    val strategy: String = "",
    val label: String = "",
    val totalTrades: Int = 0,
    val wins: Int = 0,
    val losses: Int = 0,
    val winRate: Double = 0.0,
    val profitFactor: Double? = null,
    val expectancyR: Double = 0.0,
    val netR: Double = 0.0,
    val modelPnl: Double = 0.0,
    val modelReturnPct: Double = 0.0,
    val maxDrawdownR: Double = 0.0,
    val maxDrawdownPct: Double = 0.0,
    val maxConsecutiveLosses: Int = 0,
    val avgWinR: Double = 0.0,
    val avgLossR: Double = 0.0,
    val yearly: List<BacktestYear> = emptyList()
)

data class BacktestPeriod(
    val from: String? = null,
    val to: String? = null
)

data class BacktestReport(
    val symbol: String = "",
    val interval: String = "",
    val years: Int = 0,
    val capital: Double = 0.0,
    val period: BacktestPeriod = BacktestPeriod(),
    val candles: Int = 0,
    val higherTimeframe: String = "",
    val strategies: List<BacktestStrategy> = emptyList(),
    val limitations: List<String> = emptyList(),
    val generatedAt: String? = null
)
