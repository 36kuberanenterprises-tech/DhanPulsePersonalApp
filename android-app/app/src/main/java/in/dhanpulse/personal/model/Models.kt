package `in`.dhanpulse.personal.model

data class LoginRequest(val apiKey: String, val clientCode: String, val pin: String, val totp: String)
data class UserProfile(val clientcode: String? = null, val name: String? = null)
data class LoginResponse(val sessionId: String, val expiresAt: String? = null, val profile: UserProfile? = null)

data class RuleScore(val bullish: Int = 0, val bearish: Int = 0, val considered: Int = 0)
data class SupertrendValue(val direction: String? = null, val value: Double? = null)
data class MarketMetrics(val ltp: Double? = null, val feedTime: String? = null, val lastCandleTime: String? = null, val ema9: Double? = null, val ema15: Double? = null, val vwap: Double? = null, val vwapSource: String? = null, val rsi: Double? = null, val macdHistogram: Double? = null, val supertrend: SupertrendValue? = null, val atr: Double? = null)
data class OptionContract(val token: String? = null, val tradingSymbol: String? = null, val exchange: String? = null, val strike: Double? = null, val optionType: String? = null, val ltp: Double? = null, val oi: Double? = null, val lotSize: Int? = null)
data class OptionChainSummary(val expiry: String? = null, val atm: Double? = null, val nearAtmPcr: Double? = null, val pcrCoverage: String? = null, val totalCeOi: Double? = null, val totalPeOi: Double? = null, val support: Double? = null, val resistance: Double? = null, val contracts: List<OptionContract> = emptyList())
data class Levels(val underlyingEntry: Double? = null, val stop: Double? = null, val target1: Double? = null, val target2: Double? = null, val basis: String? = null)
data class SignalRule(val name: String, val state: String, val detail: String? = null)
data class StrategyVote(
    val name: String = "",
    val vote: String = "WAIT",
    val detail: String? = null
)

data class TradeDecision(
    val direction: String = "WAIT",
    val status: String = "WATCHING",
    val setupAllowed: Boolean = false,
    val supportingVotes: Int = 0,
    val totalVotes: Int = 0,
    val alignmentPct: Double = 0.0,
    val regime: String = "UNKNOWN",
    val regimeSuitable: Boolean = false,
    val strategyVotes: List<StrategyVote> = emptyList(),
    val conflicts: List<String> = emptyList(),
    val selectedContractReason: String? = null,
    val selectedContractScore: Double? = null,
    val message: String = ""
)

data class AnalysisResponse(val symbol: String, val timestamp: String? = null, val timeframe: String? = null, val signal: String = "WAIT", val dataFresh: Boolean? = null, val ruleScore: RuleScore = RuleScore(), val market: MarketMetrics = MarketMetrics(), val optionChain: OptionChainSummary = OptionChainSummary(), val suggestedContract: OptionContract? = null, val trackedContract: OptionContract? = null, val tradeDecision: TradeDecision = TradeDecision(), val levels: Levels? = null, val rules: List<SignalRule> = emptyList(), val notes: List<String> = emptyList())
data class ErrorResponse(val error: String? = null)

data class PremiumTradePlan(
    val signal: String = "WAIT",
    val contract: OptionContract? = null,
    val referencePremium: Double? = null,
    val entry: Double? = null,
    val stopLoss: Double? = null,
    val target1: Double? = null,
    val target2: Double? = null,
    val target3: Double? = null,
    val status: String = "WAIT",
    val stage: String = "WATCHING",
    val confirmationCount: Int = 0,
    val confirmationRequired: Int = 2,
    val decisionNote: String? = null,
    val callId: String? = null
)

data class SignalCall(
    val id: String,
    val symbol: String,
    val timeframe: String,
    val side: String,
    val token: String,
    val tradingSymbol: String,
    val strike: Double? = null,
    val exchange: String? = null,
    val generatedAt: Long,
    val sessionDate: String,
    val referencePremium: Double,
    val entry: Double,
    val stopLoss: Double,
    val target1: Double,
    val target2: Double,
    val target3: Double,
    val entryHitAt: Long? = null,
    val t1HitAt: Long? = null,
    val t2HitAt: Long? = null,
    val t3HitAt: Long? = null,
    val slHitAt: Long? = null,
    val cancelledAt: Long? = null,
    val lastPremium: Double? = null,
    val lastTrackedAt: Long? = null,
    val status: String = "WAITING_ENTRY"
)

data class SignalStats(
    val generated: Int = 0,
    val entered: Int = 0,
    val target1Hits: Int = 0,
    val target2Hits: Int = 0,
    val target3Hits: Int = 0,
    val stopLossHits: Int = 0,
    val cancelled: Int = 0,
    val open: Int = 0,
    val unresolved: Int = 0
)


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
    val traceId: String? = null,
    val side: String? = null,
    val lots: Int = 0,
    val quantity: Int = 0,
    val lotSize: Int = 0,
    val tradingSymbol: String? = null,
    val orderId: String? = null,
    val uniqueOrderId: String? = null,
    val orderStatus: String? = null,
    val averagePrice: Double? = null,
    val filledShares: Double? = null,
    val rejectionReason: String? = null,
    val message: String? = null,
    val account: AccountSummary? = null
)

data class OrderGatewayDiagnostics(
    val backendReached: Boolean = false,
    val brokerSessionOk: Boolean = false,
    val brokerMessage: String? = null,
    val registeredPublicIp: String? = null,
    val actualEgressIp: String? = null,
    val relayConfigured: Boolean = false,
    val relayHost: String? = null,
    val executionReady: Boolean = false,
    val status: String = "UNKNOWN",
    val message: String = ""
)


data class BacktestRequest(
    val symbol: String,
    val interval: String,
    val years: Int = 3,
    val capital: Double = 20000.0
)

data class BacktestSlice(
    val label: String = "",
    val trades: Int = 0,
    val winRate: Double = 0.0,
    val profitFactor: Double? = null,
    val expectancyR: Double = 0.0,
    val netR: Double = 0.0
)

data class BacktestDiagnostics(
    val sides: List<BacktestSlice> = emptyList(),
    val times: List<BacktestSlice> = emptyList(),
    val weekdays: List<BacktestSlice> = emptyList(),
    val regimes: List<BacktestSlice> = emptyList(),
    val volatility: List<BacktestSlice> = emptyList(),
    val exits: List<BacktestSlice> = emptyList(),
    val phases: List<BacktestSlice> = emptyList(),
    val years: List<BacktestSlice> = emptyList()
)

data class EquityPoint(
    val date: String = "",
    val equity: Double = 0.0
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
    val startingCapital: Double = 0.0,
    val endingCapital: Double = 0.0,
    val modelPnl: Double = 0.0,
    val modelReturnPct: Double = 0.0,
    val maxDrawdownPct: Double = 0.0,
    val maxConsecutiveLosses: Int = 0,
    val avgWinR: Double = 0.0,
    val avgLossR: Double = 0.0,
    val diagnostics: BacktestDiagnostics = BacktestDiagnostics(),
    val equityCurve: List<EquityPoint> = emptyList()
)

data class RobustnessRow(
    val ema: String = "",
    val stopAtr: Double = 0.0,
    val profitFactor: Double? = null,
    val expectancyR: Double = 0.0,
    val netR: Double = 0.0,
    val trades: Int = 0
)

data class RobustnessSummary(
    val combinations: Int = 0,
    val profitableCombinations: Int = 0,
    val profitablePct: Double = 0.0,
    val minProfitFactor: Double? = null,
    val maxProfitFactor: Double? = null,
    val medianProfitFactor: Double? = null,
    val best: RobustnessRow? = null,
    val rows: List<RobustnessRow> = emptyList()
)


data class AdaptivePhase(
    val label: String = "",
    val trades: Int = 0,
    val winRate: Double = 0.0,
    val profitFactor: Double? = null,
    val expectancyR: Double = 0.0,
    val netR: Double = 0.0
)

data class AdaptiveCombined(
    val totalTrades: Int = 0,
    val winRate: Double = 0.0,
    val profitFactor: Double? = null,
    val expectancyR: Double = 0.0,
    val netR: Double = 0.0,
    val modelPnl: Double = 0.0,
    val modelReturnPct: Double = 0.0,
    val maxDrawdownPct: Double = 0.0
)

data class AdaptiveResearch(
    val status: String = "",
    val gatePassed: Boolean = false,
    val message: String = "",
    val searchedConfigs: Int = 0,
    val candidates: Int = 0,
    val configName: String? = null,
    val ruleText: String? = null,
    val development: AdaptivePhase? = null,
    val validation: AdaptivePhase? = null,
    val outOfSample: AdaptivePhase? = null,
    val combined: AdaptiveCombined? = null
)

data class BacktestDataQuality(
    val rawCandles: Int = 0,
    val usedCandles: Int = 0,
    val weekendOrSpecialCandlesExcluded: Int = 0,
    val higherTimeframeExcluded: Int = 0,
    val note: String = ""
)


data class BacktestInterpretation(
    val verdict: String = "",
    val reason: String = "",
    val focus: List<String> = emptyList(),
    val ignoreForDecision: List<String> = emptyList()
)

data class BacktestPeriod(
    val from: String? = null,
    val to: String? = null
)

data class BacktestReport(
    val version: String? = null,
    val symbol: String = "",
    val interval: String = "",
    val years: Int = 0,
    val capital: Double = 0.0,
    val period: BacktestPeriod = BacktestPeriod(),
    val candles: Int = 0,
    val higherTimeframe: String = "",
    val dataQuality: BacktestDataQuality = BacktestDataQuality(),
    val strategies: List<BacktestStrategy> = emptyList(),
    val robustness: RobustnessSummary = RobustnessSummary(),
    val adaptive: AdaptiveResearch = AdaptiveResearch(),
    val interpretation: BacktestInterpretation = BacktestInterpretation(),
    val limitations: List<String> = emptyList(),
    val generatedAt: String? = null
)
