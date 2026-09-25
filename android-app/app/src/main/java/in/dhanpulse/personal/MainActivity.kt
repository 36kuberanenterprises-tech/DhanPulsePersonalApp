package `in`.dhanpulse.personal

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import `in`.dhanpulse.personal.model.AnalysisResponse
import `in`.dhanpulse.personal.model.AccountSummary
import `in`.dhanpulse.personal.model.BacktestSlice
import `in`.dhanpulse.personal.model.BacktestStrategy
import `in`.dhanpulse.personal.model.AdaptivePhase
import `in`.dhanpulse.personal.ui.DhanPulseViewModel
import kotlin.math.abs


private val AppBg = Color(0xFF08101C)
private val Panel = Color(0xFF101A29)
private val Panel2 = Color(0xFF162235)
private val Line = Color(0xFF25354A)
private val Ink = Color(0xFFF5F8FC)
private val Muted = Color(0xFF8FA3BA)
private val Purple = Color(0xFF7A5AF8)
private val Blue = Color(0xFF4B9BFF)
private val Green = Color(0xFF25D39A)
private val Red = Color(0xFFFF6474)
private val Amber = Color(0xFFFFBD5C)

private val AppColors = darkColorScheme(
    primary = Purple,
    secondary = Blue,
    background = AppBg,
    surface = Panel,
    surfaceVariant = Panel2,
    outline = Line,
    onBackground = Ink,
    onSurface = Ink,
    onSurfaceVariant = Muted,
    error = Red,
    tertiary = Amber
)
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme(colorScheme = AppColors) { Surface(Modifier.fillMaxSize(), color = AppBg) { DhanPulseApp() } } }
    }
}

@Composable
fun DhanPulseApp(vm: DhanPulseViewModel = viewModel()) {
    if (vm.sessionId == null) LoginScreen(vm) else DashboardScreen(vm)
}

@Composable
fun LoginScreen(vm: DhanPulseViewModel) {
    var pin by remember { mutableStateOf("") }
    var totp by remember { mutableStateOf("") }

    Box(
        Modifier
            .fillMaxSize()
            .background(Brush.verticalGradient(listOf(Color(0xFF0B1424), AppBg)))
            .statusBarsPadding()
            .navigationBarsPadding()
            .padding(horizontal = 22.dp)
    ) {
        Column(
            Modifier.fillMaxWidth().align(Alignment.Center),
            verticalArrangement = Arrangement.spacedBy(18.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Image(
                    painter = painterResource(R.mipmap.ic_launcher),
                    contentDescription = "DhanPulse logo",
                    modifier = Modifier.size(64.dp).clip(RoundedCornerShape(16.dp)),
                    contentScale = ContentScale.Fit
                )
                Spacer(Modifier.width(14.dp))
                Column {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("DhanPulse", color = Ink, fontSize = 30.sp, fontWeight = FontWeight.ExtraBold)
                        Spacer(Modifier.width(8.dp))
                        StatusPill("LIVE", Green)
                    }
                    Text("Trading & Investment", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
            }
            Text("Angel One market intelligence", color = Muted, style = MaterialTheme.typography.bodyLarge)

            Card(
                colors = CardDefaults.cardColors(containerColor = Panel),
                shape = RoundedCornerShape(24.dp),
                border = BorderStroke(1.dp, Line)
            ) {
                Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                    Text("Secure sign in", color = Ink, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Text("Backend and SmartAPI are already configured. Enter only your current Angel One login details.", color = Muted, style = MaterialTheme.typography.bodySmall)

                    OutlinedTextField(
                        pin, { pin = it },
                        label = { Text("Angel One PIN") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        shape = RoundedCornerShape(16.dp),
                        visualTransformation = PasswordVisualTransformation(),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword)
                    )
                    OutlinedTextField(
                        totp, { totp = it },
                        label = { Text("Current 6 digit TOTP") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        shape = RoundedCornerShape(16.dp),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                    )

                    vm.error?.let { ErrorStrip(it) }

                    Button(
                        onClick = { vm.login(pin, totp) { pin = ""; totp = "" } },
                        enabled = !vm.loading,
                        modifier = Modifier.fillMaxWidth().height(54.dp),
                        shape = RoundedCornerShape(16.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Purple, contentColor = Color.White)
                    ) {
                        if (vm.loading) CircularProgressIndicator(Modifier.size(22.dp), strokeWidth = 2.dp, color = Color.White)
                        else Text("Connect securely", fontWeight = FontWeight.Bold)
                    }

                    Text("PIN and TOTP are used only for this login and are not saved on the phone.", color = Muted, style = MaterialTheme.typography.labelSmall)
                }
            }
        }
    }
}

@Composable
fun DashboardScreen(vm: DhanPulseViewModel) {
    DisposableEffect(Unit) {
        vm.startAutoRefresh()
        onDispose { vm.stopAutoRefresh() }
    }
    var section by remember { mutableStateOf("MARKET") }

    Scaffold(
        containerColor = AppBg,
        bottomBar = { TraderBottomNav(section) { section = it } }
    ) { inner ->
        Column(
            Modifier.fillMaxSize().background(AppBg).padding(inner).statusBarsPadding()
        ) {
            TraderHeader(vm)
            when (section) {
                "TRADE" -> TradeSection(vm)
                "POSITIONS" -> PositionsSection(vm)
                "RESEARCH" -> ResearchSection(vm)
                "ACCOUNT" -> AccountSection(vm)
                else -> MarketSection(vm)
            }
        }
    }
}

@Composable
private fun TraderHeader(vm: DhanPulseViewModel) {
    Column(Modifier.fillMaxWidth().background(Panel).padding(horizontal = 16.dp, vertical = 10.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Image(
                    painter = painterResource(R.mipmap.ic_launcher),
                    contentDescription = null,
                    modifier = Modifier.size(34.dp).clip(RoundedCornerShape(9.dp)),
                    contentScale = ContentScale.Fit
                )
                Spacer(Modifier.width(9.dp))
                Column {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("DhanPulse Trader", color = Ink, fontSize = 18.sp, fontWeight = FontWeight.ExtraBold)
                        Spacer(Modifier.width(7.dp))
                        StatusPill("LIVE", Green)
                    }
                    Text(vm.profile?.name ?: "Angel One connected", color = Muted, fontSize = 10.sp)
                }
            }
            Surface(onClick = { vm.fetchAnalysis(); vm.fetchAccount() }, color = Panel2, shape = RoundedCornerShape(12.dp)) {
                Text("Refresh", color = Ink, fontSize = 11.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp))
            }
        }
    }
}

@Composable
private fun TraderBottomNav(selected: String, onSelect: (String) -> Unit) {
    val tabs = listOf(
        "MARKET" to "Market",
        "TRADE" to "Trade",
        "POSITIONS" to "Positions",
        "RESEARCH" to "Research",
        "ACCOUNT" to "Account"
    )
    NavigationBar(containerColor = Panel, tonalElevation = 8.dp) {
        tabs.forEach { (key, label) ->
            NavigationBarItem(
                selected = selected == key,
                onClick = { onSelect(key) },
                icon = {
                    Box(
                        Modifier.size(7.dp).clip(RoundedCornerShape(50)).background(if (selected == key) Purple else Color.Transparent)
                    )
                },
                label = { Text(label, fontSize = 10.sp, fontWeight = if (selected == key) FontWeight.ExtraBold else FontWeight.Medium) },
                colors = NavigationBarItemDefaults.colors(
                    selectedTextColor = Ink,
                    unselectedTextColor = Muted,
                    indicatorColor = Purple.copy(alpha = 0.12f)
                )
            )
        }
    }
}

@Composable
private fun TradingContextBar(vm: DhanPulseViewModel) {
    var symbolOpen by remember { mutableStateOf(false) }
    var tfOpen by remember { mutableStateOf(false) }
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Box(Modifier.weight(1f)) {
            Surface(
                onClick = { symbolOpen = true },
                color = Panel,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, Line)
            ) {
                Column(Modifier.fillMaxWidth().padding(horizontal = 13.dp, vertical = 10.dp)) {
                    Text("SYMBOL", color = Muted, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                    Text(vm.selectedSymbol.replace("BANKNIFTY", "BANK NIFTY"), color = Ink, fontSize = 14.sp, fontWeight = FontWeight.ExtraBold)
                }
            }
            DropdownMenu(expanded = symbolOpen, onDismissRequest = { symbolOpen = false }) {
                listOf("NIFTY" to "NIFTY", "BANKNIFTY" to "BANK NIFTY", "SENSEX" to "SENSEX").forEach { (key, label) ->
                    DropdownMenuItem(
                        text = { Text(label) },
                        onClick = { vm.selectSymbol(key); symbolOpen = false }
                    )
                }
            }
        }
        Box(Modifier.weight(1f)) {
            Surface(
                onClick = { tfOpen = true },
                color = Panel,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, Line)
            ) {
                Column(Modifier.fillMaxWidth().padding(horizontal = 13.dp, vertical = 10.dp)) {
                    Text("TIMEFRAME", color = Muted, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                    Text(timeframeShort(vm.selectedTimeframe), color = Ink, fontSize = 14.sp, fontWeight = FontWeight.ExtraBold)
                }
            }
            DropdownMenu(expanded = tfOpen, onDismissRequest = { tfOpen = false }) {
                listOf(
                    "ONE_MINUTE" to "1 minute",
                    "THREE_MINUTE" to "3 minutes",
                    "FIVE_MINUTE" to "5 minutes",
                    "TEN_MINUTE" to "10 minutes",
                    "FIFTEEN_MINUTE" to "15 minutes"
                ).forEach { (key, label) ->
                    DropdownMenuItem(text = { Text(label) }, onClick = { vm.selectTimeframe(key); tfOpen = false })
                }
            }
        }
    }
}

@Composable
private fun MarketSection(vm: DhanPulseViewModel) {
    val a = vm.analysis
    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 16.dp),
        contentPadding = PaddingValues(top = 12.dp, bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item { TradingContextBar(vm) }
        vm.error?.let { item { ErrorStrip(it) } }
        vm.refreshWarning?.let { item { InfoStrip("Live refresh delayed", "Showing the latest successful analysis. Automatic retry is active.") } }
        if (vm.loading && a == null) item { LoadingMarketCard() }
        if (a != null) {
            item { SignalCard(a, vm::fetchAnalysis) }
            item { MarketCard(a) }
            item { OptionCard(a) }
            item { SignalRulesPanel(a) }
        }
    }
}

@Composable
private fun TradeSection(vm: DhanPulseViewModel) {
    val a = vm.analysis
    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 16.dp),
        contentPadding = PaddingValues(top = 12.dp, bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item { TradingContextBar(vm) }
        if (a != null) {
            item { TradeDeskHero(a, vm) }
            item { DecisionPipelineCard(a, vm) }
            item { PremiumDecisionCard(vm) }
            vm.signalHistory.firstOrNull()?.let { latest ->
                item { LatestCallRecordCard(latest) }
            }
            item { SignalPerformanceCard(vm) }
        } else item { LoadingMarketCard() }
    }
}

@Composable
private fun DecisionPipelineCard(a: AnalysisResponse, vm: DhanPulseViewModel) {
    val d = a.tradeDecision
    val p = vm.premiumTradePlan
    val directionColor = when (d.direction) { "CE" -> Green; "PE" -> Red; else -> Amber }
    val stageText = when {
        p.callId != null && p.stage == "WAITING_ENTRY" -> "CALL RECORDED • WAITING ENTRY"
        p.callId != null && p.stage == "ENTRY_ACTIVE" -> "ENTRY ACTIVE"
        p.callId != null && p.stage.startsWith("TARGET_") -> p.stage.replace("_", " ")
        p.callId != null && p.stage == "STOP_LOSS_HIT" -> "STOP LOSS HIT"
        d.direction == "WAIT" -> "WATCHING"
        !d.setupAllowed && d.status == "REJECTED_CONFLICT" -> "REJECTED • CONFLICT"
        !d.setupAllowed -> "SETUP FORMING"
        p.confirmationCount <= 0 -> "SETUP PASSED • SCAN 0/2"
        p.confirmationCount == 1 -> "CONFIRMING • SCAN 1/2"
        else -> "PREMIUM CONFIRMATION"
    }
    val stageColor = when {
        p.callId != null && p.stage == "STOP_LOSS_HIT" -> Red
        p.callId != null && p.stage.startsWith("TARGET_") -> Green
        d.setupAllowed -> Blue
        d.status == "REJECTED_CONFLICT" -> Red
        else -> Amber
    }

    Card(
        colors = CardDefaults.cardColors(containerColor = Panel),
        shape = RoundedCornerShape(22.dp),
        border = BorderStroke(1.dp, stageColor.copy(alpha = 0.28f))
    ) {
        Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(13.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Trade Decision", color = Ink, fontWeight = FontWeight.ExtraBold, fontSize = 19.sp)
                    Text("One final direction after market evidence and strategy filters", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
                StatusPill(d.direction, directionColor)
            }

            Surface(color = stageColor.copy(alpha = 0.09f), shape = RoundedCornerShape(14.dp), border = BorderStroke(1.dp, stageColor.copy(alpha = 0.22f))) {
                Column(Modifier.fillMaxWidth().padding(13.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    Text(stageText, color = stageColor, fontWeight = FontWeight.ExtraBold, fontSize = 15.sp)
                    Text(
                        if (d.message.isNotBlank()) d.message else "Waiting for confirmation.",
                        color = Muted,
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }

            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                DecisionMetric("ALIGNMENT", "${d.supportingVotes}/${d.totalVotes}", if (d.setupAllowed) Green else Amber, Modifier.weight(1f))
                DecisionMetric("REGIME", d.regime, if (d.regimeSuitable) Green else Red, Modifier.weight(1f))
                DecisionMetric("SCAN", "${p.confirmationCount}/${p.confirmationRequired}", Blue, Modifier.weight(1f))
            }

            Text("STRATEGY CONSENSUS", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
            d.strategyVotes.forEach { vote ->
                val vc = when (vote.vote) { "CE" -> Green; "PE" -> Red; else -> Muted }
                Surface(color = Panel2, shape = RoundedCornerShape(12.dp)) {
                    Row(
                        Modifier.fillMaxWidth().padding(horizontal = 11.dp, vertical = 9.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(Modifier.weight(1f)) {
                            Text(vote.name, color = Ink, fontWeight = FontWeight.Bold, fontSize = 11.sp)
                            vote.detail?.let { Text(it, color = Muted, fontSize = 8.sp) }
                        }
                        StatusPill(vote.vote, vc)
                    }
                }
            }

            if (d.conflicts.isNotEmpty()) {
                Surface(color = Red.copy(alpha = 0.08f), shape = RoundedCornerShape(12.dp), border = BorderStroke(1.dp, Red.copy(alpha = 0.18f))) {
                    Column(Modifier.fillMaxWidth().padding(11.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("WHY NO CALL", color = Red, fontWeight = FontWeight.ExtraBold, fontSize = 9.sp)
                        d.conflicts.forEach { Text("• $it", color = Muted, fontSize = 9.sp) }
                    }
                }
            }

            a.suggestedContract?.let { contract ->
                Surface(color = Panel2, shape = RoundedCornerShape(12.dp)) {
                    Column(Modifier.fillMaxWidth().padding(11.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("SELECTED CANDIDATE", color = Muted, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                        Text(contract.tradingSymbol ?: "Option", color = Ink, fontWeight = FontWeight.ExtraBold)
                        Text(d.selectedContractReason ?: "Near-ATM contract selected.", color = Muted, fontSize = 9.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun DecisionMetric(label: String, value: String, color: Color, modifier: Modifier = Modifier) {
    Column(modifier.clip(RoundedCornerShape(12.dp)).background(color.copy(alpha = 0.08f)).padding(10.dp)) {
        Text(label, color = Muted, fontSize = 8.sp, fontWeight = FontWeight.Bold)
        Text(value, color = color, fontSize = 13.sp, fontWeight = FontWeight.ExtraBold)
    }
}

@Composable
private fun PremiumDecisionCard(vm: DhanPulseViewModel) {
    val p = vm.premiumTradePlan
    val contract = p.contract
    val actionColor = when (p.signal) { "CE" -> Green; "PE" -> Red; else -> Amber }

    Card(
        colors = CardDefaults.cardColors(containerColor = Panel),
        shape = RoundedCornerShape(22.dp),
        border = BorderStroke(1.dp, actionColor.copy(alpha = 0.35f))
    ) {
        Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Premium Trade Plan", color = Ink, fontWeight = FontWeight.ExtraBold, fontSize = 19.sp)
                    Text("Only the final selected direction appears here", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
                StatusPill(p.signal, actionColor)
            }

            if (p.signal == "WAIT" || contract == null) {
                Surface(color = Amber.copy(alpha = 0.10f), shape = RoundedCornerShape(14.dp), border = BorderStroke(1.dp, Amber.copy(alpha = 0.25f))) {
                    Column(Modifier.fillMaxWidth().padding(14.dp)) {
                        Text("WATCHING", color = Amber, fontSize = 24.sp, fontWeight = FontWeight.ExtraBold)
                        Text(p.decisionNote ?: "No confirmed directional setup.", color = Muted, style = MaterialTheme.typography.bodySmall)
                    }
                }
                return@Column
            }

            Surface(color = Panel2, shape = RoundedCornerShape(16.dp)) {
                Row(Modifier.fillMaxWidth().padding(14.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text(if (p.callId == null) "CANDIDATE STRIKE" else "RECORDED CALL", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                        Text(contract.tradingSymbol ?: "Option", color = Ink, fontWeight = FontWeight.ExtraBold, fontSize = 16.sp)
                        Text("Strike ${n(contract.strike)} • ${contract.optionType ?: p.signal}", color = Muted, fontSize = 10.sp)
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text("LIVE PREMIUM", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                        Text(n(contract.ltp), color = actionColor, fontWeight = FontWeight.ExtraBold, fontSize = 22.sp)
                    }
                }
            }

            if (p.status == "FILTERED") {
                Surface(color = Red.copy(alpha = 0.08f), shape = RoundedCornerShape(14.dp), border = BorderStroke(1.dp, Red.copy(alpha = 0.20f))) {
                    Column(Modifier.fillMaxWidth().padding(13.dp)) {
                        Text("NO TRADE CALL YET", color = Red, fontWeight = FontWeight.ExtraBold)
                        Text(p.decisionNote ?: "The market bias exists, but the meta filters rejected the setup.", color = Muted, style = MaterialTheme.typography.bodySmall)
                    }
                }
                return@Column
            }

            val statusLabel = when (p.status) {
                "WAITING_ENTRY" -> "BUY ABOVE"
                "ENTERED" -> "ENTRY ACTIVE"
                "T1_HIT" -> "T1 HIT"
                "T2_HIT" -> "T2 HIT"
                "T3_HIT" -> "T3 HIT"
                "SL_HIT" -> "SL HIT"
                else -> "BUY ABOVE"
            }

            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                PremiumLevelBox(statusLabel, p.entry, Blue, Modifier.weight(1f))
                PremiumLevelBox("STOP LOSS", p.stopLoss, Red, Modifier.weight(1f))
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                PremiumLevelBox("TARGET 1", p.target1, Green, Modifier.weight(1f))
                PremiumLevelBox("TARGET 2", p.target2, Green, Modifier.weight(1f))
                PremiumLevelBox("TARGET 3", p.target3, Green, Modifier.weight(1f))
            }

            val progress = p.confirmationCount.coerceIn(0, p.confirmationRequired)
            LinearProgressIndicator(
                progress = { if (p.confirmationRequired > 0) progress.toFloat() / p.confirmationRequired.toFloat() else 0f },
                modifier = Modifier.fillMaxWidth().height(6.dp).clip(RoundedCornerShape(6.dp)),
                color = Blue,
                trackColor = Panel2
            )
            Text(
                when {
                    p.callId != null && p.status == "WAITING_ENTRY" -> "CALL CONFIRMED • Levels locked • waiting for premium to cross Buy Above."
                    p.callId != null -> "CALL ACTIVE • Original levels are locked and being tracked."
                    progress == 0 -> "Meta setup passed. Waiting for the first matching live confirmation."
                    progress == 1 -> "Confirmation 1/2 complete. Same direction and strike must remain valid on the next scan."
                    else -> "Premium confirmation complete."
                },
                color = Muted,
                style = MaterialTheme.typography.labelSmall
            )
        }
    }
}

@Composable
private fun PremiumLevelBox(label: String, value: Double?, color: Color, modifier: Modifier = Modifier) {
    Surface(modifier = modifier, color = color.copy(alpha = 0.08f), shape = RoundedCornerShape(13.dp), border = BorderStroke(1.dp, color.copy(alpha = 0.20f))) {
        Column(Modifier.padding(horizontal = 10.dp, vertical = 11.dp)) {
            Text(label, color = Muted, fontSize = 8.sp, fontWeight = FontWeight.Bold)
            Text(n(value), color = color, fontSize = 17.sp, fontWeight = FontWeight.ExtraBold)
        }
    }
}

@Composable
private fun LatestCallRecordCard(call: `in`.dhanpulse.personal.model.SignalCall) {
    var open by remember(call.id) { mutableStateOf(false) }
    val resultColor = callResultColor(call.status)
    Card(
        colors = CardDefaults.cardColors(containerColor = Panel),
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, resultColor.copy(alpha = 0.25f))
    ) {
        Column(Modifier.fillMaxWidth()) {
            Row(
                Modifier.fillMaxWidth().clickable { open = !open }.padding(16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(Modifier.weight(1f)) {
                    Text("Latest Recorded Call", color = Ink, fontWeight = FontWeight.ExtraBold, fontSize = 17.sp)
                    Text(call.tradingSymbol, color = Ink, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                    Text(
                        "${call.side} • ${timeframeShort(call.timeframe)} • Generated ${formatCallTime(call.generatedAt)}",
                        color = Muted,
                        fontSize = 9.sp
                    )
                }
                Column(horizontalAlignment = Alignment.End) {
                    StatusPill(call.status.replace("_", " "), resultColor)
                    Spacer(Modifier.height(5.dp))
                    Text(if (open) "Hide details" else "View details", color = Blue, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                }
            }
            if (open) {
                HorizontalDivider(color = Line)
                CallRecordDetails(call, compact = true)
            }
        }
    }
}

@Composable
private fun FullCallRecordCard(call: `in`.dhanpulse.personal.model.SignalCall) {
    val resultColor = callResultColor(call.status)
    Card(
        colors = CardDefaults.cardColors(containerColor = Panel),
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, resultColor.copy(alpha = 0.25f))
    ) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(11.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                Column(Modifier.weight(1f)) {
                    Text(call.tradingSymbol, color = Ink, fontWeight = FontWeight.ExtraBold, fontSize = 16.sp)
                    Text(
                        "Strike ${n(call.strike)} • ${call.side} • ${timeframeShort(call.timeframe)}",
                        color = Muted,
                        fontSize = 10.sp
                    )
                    Text("Generated ${formatCallDateTime(call.generatedAt)}", color = Muted, fontSize = 9.sp)
                }
                StatusPill(call.status.replace("_", " "), resultColor)
            }
            CallRecordDetails(call, compact = false)
        }
    }
}

@Composable
private fun CallRecordDetails(call: `in`.dhanpulse.personal.model.SignalCall, compact: Boolean) {
    Column(
        Modifier.fillMaxWidth().padding(if (compact) 14.dp else 0.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Surface(color = Panel2, shape = RoundedCornerShape(14.dp)) {
            Row(
                Modifier.fillMaxWidth().padding(12.dp),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column {
                    Text("PREMIUM WHEN CALL GENERATED", color = Muted, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                    Text(n(call.referencePremium), color = Ink, fontSize = 18.sp, fontWeight = FontWeight.ExtraBold)
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text("LAST TRACKED PREMIUM", color = Muted, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                    Text(n(call.lastPremium), color = callResultColor(call.status), fontSize = 18.sp, fontWeight = FontWeight.ExtraBold)
                }
            }
        }

        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            PremiumLevelBox("BUY ABOVE", call.entry, Blue, Modifier.weight(1f))
            PremiumLevelBox("STOP LOSS", call.stopLoss, Red, Modifier.weight(1f))
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            PremiumLevelBox("TARGET 1", call.target1, Green, Modifier.weight(1f))
            PremiumLevelBox("TARGET 2", call.target2, Green, Modifier.weight(1f))
            PremiumLevelBox("TARGET 3", call.target3, Green, Modifier.weight(1f))
        }

        HorizontalDivider(color = Line)
        CallMilestoneRow("Entry", call.entryHitAt, Blue)
        CallMilestoneRow("Target 1", call.t1HitAt, Green)
        CallMilestoneRow("Target 2", call.t2HitAt, Green)
        CallMilestoneRow("Target 3", call.t3HitAt, Green)
        CallMilestoneRow("Stop Loss", call.slHitAt, Red)
        CallMilestoneRow("Cancelled", call.cancelledAt, Muted)

        Text("Call ID: ${call.id}", color = Muted, fontSize = 8.sp)
    }
}

@Composable
private fun CallMilestoneRow(label: String, hitAt: Long?, color: Color) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = Muted, fontSize = 10.sp)
        Text(
            if (hitAt != null) "HIT • ${formatCallTime(hitAt)}" else "Not hit",
            color = if (hitAt != null) color else Muted,
            fontSize = 10.sp,
            fontWeight = if (hitAt != null) FontWeight.Bold else FontWeight.Normal
        )
    }
}

private fun callResultColor(status: String): Color = when (status) {
    "T3_HIT", "T2_HIT", "T1_HIT" -> Green
    "SL_HIT" -> Red
    "UNRESOLVED", "CANCELLED" -> Muted
    "ENTERED", "WAITING_ENTRY" -> Amber
    else -> Blue
}

private fun formatCallTime(ms: Long): String =
    java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.US).format(java.util.Date(ms))

private fun formatCallDateTime(ms: Long): String =
    java.text.SimpleDateFormat("dd MMM yyyy • HH:mm:ss", java.util.Locale.US).format(java.util.Date(ms))

@Composable
private fun SignalPerformanceCard(vm: DhanPulseViewModel, showRecent: Boolean = false) {
    val s = vm.signalStats
    Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(22.dp), border = BorderStroke(1.dp, Line)) {
        Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column {
                    Text("Call Performance", color = Ink, fontWeight = FontWeight.ExtraBold, fontSize = 18.sp)
                    Text("All generated premium calls stored on this phone", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
                StatusPill("${s.generated} CALLS", Blue)
            }

            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatTile("GENERATED", s.generated.toString(), Blue, Modifier.weight(1f))
                StatTile("ENTERED", s.entered.toString(), Ink, Modifier.weight(1f))
                StatTile("OPEN", s.open.toString(), Amber, Modifier.weight(1f))
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatTile("CANCELLED", s.cancelled.toString(), Muted, Modifier.weight(1f))
                StatTile("UNRESOLVED", s.unresolved.toString(), Muted, Modifier.weight(1f))
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatTile("T1 HIT", s.target1Hits.toString(), Green, Modifier.weight(1f))
                StatTile("T2 HIT", s.target2Hits.toString(), Green, Modifier.weight(1f))
                StatTile("T3 HIT", s.target3Hits.toString(), Green, Modifier.weight(1f))
                StatTile("SL HIT", s.stopLossHits.toString(), Red, Modifier.weight(1f))
            }

            if (s.entered > 0) {
                val t1Rate = 100.0 * s.target1Hits / s.entered
                val t2Rate = 100.0 * s.target2Hits / s.entered
                val t3Rate = 100.0 * s.target3Hits / s.entered
                Text("Hit rate from entered calls: T1 ${String.format("%.1f", t1Rate)}% • T2 ${String.format("%.1f", t2Rate)}% • T3 ${String.format("%.1f", t3Rate)}%", color = Muted, style = MaterialTheme.typography.labelSmall)
            }

            if (showRecent && vm.signalHistory.isNotEmpty()) {
                HorizontalDivider(color = Line)
                Text("RECENT CALLS", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                vm.signalHistory.take(12).forEach { call -> SignalHistoryRow(call) }
            }

            Text("Every generated call is stored with strike, premium, entry, SL, T1, T2, T3 and final status. Open Research → Call Book to see the full record.", color = Muted, style = MaterialTheme.typography.labelSmall)
        }
    }
}

@Composable
private fun StatTile(label: String, value: String, color: Color, modifier: Modifier = Modifier) {
    Column(modifier.clip(RoundedCornerShape(12.dp)).background(Panel2).padding(9.dp)) {
        Text(label, color = Muted, fontSize = 7.sp, fontWeight = FontWeight.Bold)
        Text(value, color = color, fontSize = 17.sp, fontWeight = FontWeight.ExtraBold)
    }
}

@Composable
private fun SignalHistoryRow(call: `in`.dhanpulse.personal.model.SignalCall) {
    val color = when (call.status) {
        "T3_HIT", "T2_HIT", "T1_HIT" -> Green
        "SL_HIT" -> Red
        "UNRESOLVED", "CANCELLED" -> Muted
        else -> Amber
    }
    Surface(color = Panel2, shape = RoundedCornerShape(12.dp)) {
        Row(Modifier.fillMaxWidth().padding(10.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(call.tradingSymbol, color = Ink, fontWeight = FontWeight.Bold, fontSize = 11.sp)
                Text("${call.side} • Entry ${n(call.entry)} • SL ${n(call.stopLoss)}", color = Muted, fontSize = 9.sp)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(call.status.replace("_", " "), color = color, fontWeight = FontWeight.ExtraBold, fontSize = 10.sp)
                Text("LTP ${n(call.lastPremium)}", color = Muted, fontSize = 9.sp)
            }
        }
    }
}

@Composable
private fun OrderGatewayCard(vm: DhanPulseViewModel) {
    val g = vm.orderGateway
    val ready = g?.executionReady == true
    val color = if (ready) Green else if (vm.orderGatewayBusy) Amber else Red
    Card(
        colors = CardDefaults.cardColors(containerColor = Panel),
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, color.copy(alpha = 0.28f))
    ) {
        Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Real Order Gateway", color = Ink, fontWeight = FontWeight.ExtraBold)
                    Text("Android → Backend → Angel One", color = Muted, style = MaterialTheme.typography.labelSmall)
                }
                StatusPill(if (vm.orderGatewayBusy) "CHECKING" else if (ready) "READY" else "BLOCKED", color)
            }
            if (g == null) {
                Text("Checking broker session and static-IP order route.", color = Muted, style = MaterialTheme.typography.bodySmall)
            } else {
                Text(g.message, color = if (ready) Green else Red, style = MaterialTheme.typography.bodySmall)
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("Registered IP", color = Muted, fontSize = 10.sp)
                    Text(g.registeredPublicIp ?: "NA", color = Ink, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(if (g.relayConfigured) "Relay" else "Backend egress", color = Muted, fontSize = 10.sp)
                    Text(g.relayHost ?: g.actualEgressIp ?: "Unknown", color = Ink, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("SmartAPI session", color = Muted, fontSize = 10.sp)
                    Text(if (g.brokerSessionOk) "ACTIVE" else "CHECK LOGIN", color = if (g.brokerSessionOk) Green else Red, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                }
            }
            FilledTonalButton(
                onClick = vm::fetchOrderDiagnostics,
                enabled = !vm.orderGatewayBusy,
                modifier = Modifier.fillMaxWidth()
            ) { Text("CHECK ORDER ROUTE", fontWeight = FontWeight.Bold) }
        }
    }
}

@Composable
private fun PositionsSection(vm: DhanPulseViewModel) {
    val account = vm.account
    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 16.dp),
        contentPadding = PaddingValues(top = 12.dp, bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            SectionTitle("Positions", "Live Angel One positions and P&L")
        }
        if (account == null) {
            item { InfoStrip("Position data", "Account data is loading. Tap Refresh at the top if needed.") }
        } else {
            item { AccountCard(account, vm::fetchAccount) }
            val open = account.positions.filter { it.netQty != 0.0 }
            if (open.isEmpty()) item { EmptyStateCard("No open positions", "Your open F&O positions will appear here with live P&L.") }
            items(open) { pos -> PositionCard(pos) }
        }
    }
}

@Composable
private fun ResearchSection(vm: DhanPulseViewModel) {
    var researchTab by remember { mutableStateOf("CALLS") }

    Column(Modifier.fillMaxSize()) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            listOf("CALLS" to "Call Book", "BACKTEST" to "Backtest").forEach { (key, label) ->
                val selected = researchTab == key
                Surface(
                    onClick = { researchTab = key },
                    modifier = Modifier.weight(1f),
                    color = if (selected) Purple.copy(alpha = 0.18f) else Panel,
                    shape = RoundedCornerShape(14.dp),
                    border = BorderStroke(1.dp, if (selected) Purple.copy(alpha = 0.45f) else Line)
                ) {
                    Text(
                        label,
                        color = if (selected) Ink else Muted,
                        fontWeight = if (selected) FontWeight.ExtraBold else FontWeight.Medium,
                        modifier = Modifier.padding(vertical = 12.dp),
                        textAlign = TextAlign.Center
                    )
                }
            }
        }

        if (researchTab == "CALLS") {
            LazyColumn(
                Modifier.fillMaxSize().padding(horizontal = 16.dp),
                contentPadding = PaddingValues(bottom = 24.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                item { SectionTitle("Call Book", "Every generated premium call with strike, entry, SL, targets and result") }
                item { SignalPerformanceCard(vm) }
                if (vm.signalHistory.isEmpty()) {
                    item { EmptyStateCard("No calls recorded yet", "A call will be added after the same CE/PE setup is confirmed on two live scans.") }
                } else {
                    items(vm.signalHistory, key = { it.id }) { call ->
                        FullCallRecordCard(call)
                    }
                }
            }
        } else {
            LazyColumn(
                Modifier.fillMaxSize().padding(horizontal = 16.dp),
                contentPadding = PaddingValues(bottom = 24.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                item { SectionTitle("Backtest Lab", "Historical strategy validation and robustness") }
                item { TradingContextBar(vm) }
                item { BacktestLabCard(vm) }
            }
        }
    }
}

@Composable
private fun AccountSection(vm: DhanPulseViewModel) {
    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 16.dp),
        contentPadding = PaddingValues(top = 12.dp, bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item { SectionTitle("Account", "Connection, funds and safety controls") }
        vm.account?.let { item { AccountCard(it, vm::fetchAccount) } }
        item {
            Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(20.dp), border = BorderStroke(1.dp, Line)) {
                Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("Trading controls", color = Ink, fontWeight = FontWeight.ExtraBold)
                    AccountSettingRow("Broker", "Angel One SmartAPI")
                    AccountSettingRow("Auto Trade", if (vm.autoTradeEnabled) "ON" else "OFF")
                    AccountSettingRow("Auto lots", vm.autoLots.toString())
                    AccountSettingRow("Account / P&L refresh", "Every 15 seconds")
                    AccountSettingRow("Live analysis refresh", "Every 3 seconds")
                    AccountSettingRow("Order gateway", if (vm.orderGateway?.executionReady == true) "READY" else "BLOCKED")
                    HorizontalDivider(color = Line)
                    Text("Manual trading stays available even when Auto Trade is blocked by the research gate.", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
            }
        }
        item {
            Button(
                onClick = vm::logout,
                modifier = Modifier.fillMaxWidth().height(50.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Red.copy(alpha = 0.16f), contentColor = Red),
                shape = RoundedCornerShape(14.dp)
            ) { Text("Logout", fontWeight = FontWeight.ExtraBold) }
        }
    }
}

@Composable
private fun SectionTitle(title: String, subtitle: String) {
    Column {
        Text(title, color = Ink, fontSize = 22.sp, fontWeight = FontWeight.ExtraBold)
        Text(subtitle, color = Muted, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun LoadingMarketCard() {
    Box(Modifier.fillMaxWidth().height(150.dp).clip(RoundedCornerShape(20.dp)).background(Panel), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            CircularProgressIndicator(color = Purple)
            Spacer(Modifier.height(10.dp))
            Text("Reading live market data...", color = Muted)
        }
    }
}

@Composable
private fun TradeDeskHero(a: AnalysisResponse, vm: DhanPulseViewModel) {
    val c = when (a.signal) { "CE" -> Green; "PE" -> Red; else -> Amber }
    Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(20.dp), border = BorderStroke(1.dp, c.copy(alpha = 0.30f))) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column {
                    Text("Trader Desk", color = Ink, fontWeight = FontWeight.ExtraBold, fontSize = 18.sp)
                    Text("Signal, execution and risk • live scan every 3 sec", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
                StatusPill(a.signal, c)
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("Index ${n(a.market.ltp)}", color = Ink, fontWeight = FontWeight.Bold)
                val d = a.tradeDecision
                val heroText = when {
                    d.direction == "WAIT" -> "WATCHING"
                    d.setupAllowed -> "SETUP PASSED"
                    d.status == "REJECTED_CONFLICT" -> "FILTERED"
                    else -> "CONFIRMING"
                }
                val heroColor = when {
                    d.direction == "WAIT" -> Amber
                    d.setupAllowed -> Green
                    d.status == "REJECTED_CONFLICT" -> Red
                    else -> Blue
                }
                Text(heroText, color = heroColor, fontWeight = FontWeight.ExtraBold)
            }
        }
    }
}

@Composable
private fun SignalRulesPanel(a: AnalysisResponse) {
    var open by remember(a.symbol, a.timeframe) { mutableStateOf(false) }
    Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(18.dp), border = BorderStroke(1.dp, Line)) {
        Column(Modifier.fillMaxWidth()) {
            Row(
                Modifier.fillMaxWidth().clickable { open = !open }.padding(14.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text("Signal checks", color = Ink, fontWeight = FontWeight.ExtraBold)
                    Text("${a.rules.size} engine conditions", color = Muted, fontSize = 10.sp)
                }
                Text(if (open) "Hide" else "View", color = Blue, fontWeight = FontWeight.Bold)
            }
            if (open) {
                HorizontalDivider(color = Line)
                a.rules.forEach { rule ->
                    val stateColor = when (rule.state.uppercase()) { "BULLISH" -> Green; "BEARISH" -> Red; "NEUTRAL" -> Amber; else -> Muted }
                    Row(Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
                        Box(Modifier.width(4.dp).height(34.dp).clip(RoundedCornerShape(4.dp)).background(stateColor))
                        Spacer(Modifier.width(10.dp))
                        Column(Modifier.weight(1f)) {
                            Text(rule.name, color = Ink, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                            rule.detail?.let { Text(it, color = Muted, fontSize = 9.sp) }
                        }
                        StatusPill(rule.state.uppercase(), stateColor)
                    }
                }
            }
        }
    }
}

@Composable
private fun PositionCard(pos: `in`.dhanpulse.personal.model.PositionSummary) {
    val pnlColor = if (pos.pnl >= 0) Green else Red
    Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(18.dp), border = BorderStroke(1.dp, Line)) {
        Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column(Modifier.weight(1f)) {
                    Text(pos.tradingSymbol ?: "Position", color = Ink, fontWeight = FontWeight.ExtraBold)
                    Text("${pos.exchange ?: ""} • ${pos.netQty.toInt()} qty • ${pos.productType ?: ""}", color = Muted, fontSize = 10.sp)
                }
                Text(money(pos.pnl), color = pnlColor, fontWeight = FontWeight.ExtraBold, fontSize = 18.sp)
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("Avg ${n(if (pos.netQty >= 0) pos.buyAvgPrice else pos.sellAvgPrice)}", color = Muted, fontSize = 10.sp)
                Text("LTP ${n(pos.ltp)}", color = Ink, fontSize = 10.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun EmptyStateCard(title: String, body: String) {
    Surface(color = Panel, shape = RoundedCornerShape(18.dp), border = BorderStroke(1.dp, Line)) {
        Column(Modifier.fillMaxWidth().padding(18.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text(title, color = Ink, fontWeight = FontWeight.ExtraBold)
            Spacer(Modifier.height(5.dp))
            Text(body, color = Muted, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun AccountSettingRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = Muted, style = MaterialTheme.typography.bodySmall)
        Text(value, color = Ink, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
    }
}

@Composable
fun SignalCard(a: AnalysisResponse, refresh: () -> Unit) {
    val color = when (a.signal.uppercase()) { "CE" -> Green; "PE" -> Red; else -> Amber }
    Box(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(24.dp))
            .background(Brush.linearGradient(listOf(color.copy(alpha = 0.20f), Panel2, Panel)))
            .border(1.dp, color.copy(alpha = 0.35f), RoundedCornerShape(24.dp)).padding(20.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                Column {
                    Text(a.symbol.replace("BANKNIFTY", "BANK NIFTY"), color = Muted, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold)
                    Text("CURRENT MARKET BIAS", color = Muted, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                }
                Surface(onClick = refresh, color = Panel2, shape = RoundedCornerShape(12.dp), border = BorderStroke(1.dp, Line)) {
                    Text("Refresh", color = Ink, modifier = Modifier.padding(horizontal = 14.dp, vertical = 9.dp), fontWeight = FontWeight.Bold)
                }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Bottom) {
                Column {
                    Text(a.signal, color = color, fontSize = 54.sp, fontWeight = FontWeight.Black)
                    Text(if (a.signal == "WAIT") "Market bias only • no trade call" else if (a.signal == "CE") "Bullish market bias • not yet a trade call" else "Bearish market bias • not yet a trade call", color = Muted)
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text("INDEX LTP", color = Muted, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    Text(n(a.market.ltp), color = Ink, fontSize = 22.sp, fontWeight = FontWeight.ExtraBold)
                }
            }
            HorizontalDivider(color = Line)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                ScoreMetric("BULL", a.ruleScore.bullish.toString(), Green)
                ScoreMetric("BEAR", a.ruleScore.bearish.toString(), Red)
                ScoreMetric("CHECKS", a.ruleScore.considered.toString(), Blue)
            }
            a.suggestedContract?.let {
                Surface(color = color.copy(alpha = 0.10f), shape = RoundedCornerShape(14.dp), border = BorderStroke(1.dp, color.copy(alpha = 0.25f))) {
                    Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column {
                            Text("CANDIDATE STRIKE • NOT A CALL", color = Muted, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                            Text(it.tradingSymbol ?: "Candidate contract", color = Ink, fontWeight = FontWeight.Bold)
                        }
                        Text("LTP ${n(it.ltp)}", color = color, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}

@Composable
fun TradePlanCard(a: AnalysisResponse, vm: DhanPulseViewModel) {
    val levels = a.levels
    val contract = a.suggestedContract
    val active = a.signal == "CE" || a.signal == "PE"
    val actionColor = when (a.signal) { "CE" -> Green; "PE" -> Red; else -> Amber }
    var lots by remember(contract?.token) { mutableStateOf(1) }
    var pendingSide by remember { mutableStateOf<String?>(null) }
    val currentLongQty = vm.account?.positions?.firstOrNull { it.token == contract?.token }?.netQty ?: 0.0
    val gatewayReady = vm.orderGateway?.executionReady == true
    val canExit = currentLongQty > 0.0 && gatewayReady

    pendingSide?.let { side ->
        AlertDialog(
            onDismissRequest = { if (!vm.orderBusy) pendingSide = null },
            title = { Text(if (side == "BUY") "Confirm BUY" else "Confirm SELL / EXIT") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(contract?.tradingSymbol ?: "Selected option")
                    Text("Lots: $lots   Quantity: ${(contract?.lotSize ?: 0) * lots}")
                    Text("Order type: MARKET • Product: INTRADAY")
                    if (side == "SELL") Text("SELL is restricted to your existing long quantity. Naked option selling is blocked.", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
            },
            confirmButton = {
                Button(
                    onClick = { contract?.let { vm.placeOrder(side, it, lots) }; pendingSide = null },
                    enabled = !vm.orderBusy,
                    colors = ButtonDefaults.buttonColors(containerColor = if (side == "BUY") Green else Red)
                ) { Text(if (side == "BUY") "Confirm BUY" else "Confirm EXIT", color = Color.White, fontWeight = FontWeight.Bold) }
            },
            dismissButton = { TextButton(onClick = { pendingSide = null }, enabled = !vm.orderBusy) { Text("Cancel") } }
        )
    }

    Card(
        colors = CardDefaults.cardColors(containerColor = Panel),
        shape = RoundedCornerShape(22.dp),
        border = BorderStroke(1.dp, if (active) actionColor.copy(alpha = 0.35f) else Line)
    ) {
        Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column {
                    Text("Trade plan", color = Ink, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold)
                    Text("Entry, stop, targets and manual execution", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
                StatusPill(a.signal, actionColor)
            }

            if (!active || levels == null || contract == null) {
                Surface(color = Amber.copy(alpha = 0.10f), shape = RoundedCornerShape(14.dp), border = BorderStroke(1.dp, Amber.copy(alpha = 0.25f))) {
                    Column(Modifier.fillMaxWidth().padding(14.dp)) {
                        Text("WAIT", color = Amber, fontSize = 24.sp, fontWeight = FontWeight.ExtraBold)
                        Text("No fresh entry until the confirmation rules produce a CE or PE signal.", color = Muted, style = MaterialTheme.typography.bodySmall)
                    }
                }
            } else {
                Surface(color = actionColor.copy(alpha = 0.08f), shape = RoundedCornerShape(14.dp)) {
                    Row(Modifier.fillMaxWidth().padding(14.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text("OPTION CONTRACT", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                            Text(contract.tradingSymbol ?: "Selected near ATM contract", color = Ink, fontWeight = FontWeight.ExtraBold)
                            Text("Lot size ${contract.lotSize ?: 0}", color = Muted, style = MaterialTheme.typography.labelSmall)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text("OPTION ENTRY", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                            Text(n(contract.ltp), color = actionColor, fontSize = 20.sp, fontWeight = FontWeight.ExtraBold)
                        }
                    }
                }

                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    LevelTile("INDEX ENTRY", n(levels.underlyingEntry), Blue, Modifier.weight(1f))
                    LevelTile("STOP LOSS", n(levels.stop), Red, Modifier.weight(1f))
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    LevelTile("TARGET 1", n(levels.target1), Green, Modifier.weight(1f))
                    LevelTile("TARGET 2", n(levels.target2), Green, Modifier.weight(1f))
                }

                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Column {
                        Text("ORDER SIZE", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                        Text("${(contract.lotSize ?: 0) * lots} qty", color = Ink, fontWeight = FontWeight.ExtraBold)
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        FilledTonalButton(onClick = { if (lots > 1) lots-- }, enabled = !vm.orderBusy) { Text("−") }
                        Text(lots.toString(), color = Ink, fontSize = 18.sp, fontWeight = FontWeight.ExtraBold, modifier = Modifier.padding(horizontal = 12.dp))
                        FilledTonalButton(onClick = { if (lots < 20) lots++ }, enabled = !vm.orderBusy) { Text("+") }
                    }
                }

                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Button(
                        onClick = { pendingSide = "BUY" },
                        enabled = gatewayReady && !vm.orderBusy,
                        modifier = Modifier.weight(1f).height(52.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Green, disabledContainerColor = Panel2),
                        shape = RoundedCornerShape(14.dp)
                    ) { Text("BUY ${a.signal}", color = Color.White, fontWeight = FontWeight.ExtraBold) }

                    Button(
                        onClick = { pendingSide = "SELL" },
                        enabled = canExit && !vm.orderBusy,
                        modifier = Modifier.weight(1f).height(52.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Red, disabledContainerColor = Panel2),
                        shape = RoundedCornerShape(14.dp)
                    ) { Text(if (canExit) "SELL / EXIT" else "NO POSITION", color = if (canExit) Color.White else Muted, fontWeight = FontWeight.ExtraBold) }
                }

                if (currentLongQty > 0) Text("Current long position: ${currentLongQty.toInt()} qty", color = Green, style = MaterialTheme.typography.bodySmall)
                vm.orderMessage?.let { InfoStrip("Order status", it) }

                Text(levels.basis ?: "Targets are based on the underlying index.", color = Muted, style = MaterialTheme.typography.labelSmall)
                Text("Option entry is the live contract premium. Stop and targets shown here are underlying index levels.", color = Muted, style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}

@Composable
fun TimeframeSelector(vm: DhanPulseViewModel) {
    val frames = listOf(
        "ONE_MINUTE" to "1m",
        "THREE_MINUTE" to "3m",
        "FIVE_MINUTE" to "5m",
        "TEN_MINUTE" to "10m",
        "FIFTEEN_MINUTE" to "15m"
    )
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("TIME FRAME", color = Muted, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.8.sp)
        Row(
            Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(Panel).border(1.dp, Line, RoundedCornerShape(14.dp)).padding(4.dp),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            frames.forEach { pair ->
                val selected = vm.selectedTimeframe == pair.first
                Box(
                    Modifier.weight(1f).clip(RoundedCornerShape(10.dp)).background(if (selected) Blue else Color.Transparent)
                        .clickable { vm.selectTimeframe(pair.first) }.padding(vertical = 10.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(pair.second, color = if (selected) Color.White else Muted, fontSize = 12.sp, fontWeight = FontWeight.ExtraBold)
                }
            }
        }
    }
}

@Composable
fun ManualTradeCard(a: AnalysisResponse, vm: DhanPulseViewModel) {
    var manualType by remember(a.symbol, a.timeframe) { mutableStateOf(if (a.signal == "PE") "PE" else "CE") }
    var lots by remember(a.symbol, a.timeframe, manualType) { mutableStateOf(1) }
    var pendingSide by remember { mutableStateOf<String?>(null) }
    val atm = a.optionChain.atm ?: a.market.ltp ?: 0.0
    val contract = a.optionChain.contracts
        .filter { it.optionType == manualType }
        .minByOrNull { abs((it.strike ?: atm) - atm) }
    val currentLongQty = vm.account?.positions?.firstOrNull { it.token == contract?.token }?.netQty ?: 0.0
    val gatewayReady = vm.orderGateway?.executionReady == true
    val canExit = currentLongQty > 0.0 && gatewayReady

    pendingSide?.let { side ->
        AlertDialog(
            onDismissRequest = { if (!vm.orderBusy) pendingSide = null },
            title = { Text(if (side == "BUY") "Confirm Manual BUY" else "Confirm Manual EXIT") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(contract?.tradingSymbol ?: "Selected option")
                    Text("Side: $side   Lots: $lots   Qty: ${(contract?.lotSize ?: 0) * lots}")
                    Text("MARKET • INTRADAY", color = Muted, style = MaterialTheme.typography.bodySmall)
                    if (vm.autoTradeEnabled) Text("Manual order will switch Auto Trade OFF to avoid duplicate orders.", color = Amber, style = MaterialTheme.typography.bodySmall)
                }
            },
            confirmButton = {
                Button(
                    onClick = { contract?.let { vm.placeOrder(side, it, lots) }; pendingSide = null },
                    enabled = !vm.orderBusy,
                    colors = ButtonDefaults.buttonColors(containerColor = if (side == "BUY") Green else Red)
                ) { Text(if (side == "BUY") "BUY NOW" else "EXIT NOW", color = Color.White, fontWeight = FontWeight.ExtraBold) }
            },
            dismissButton = { TextButton(onClick = { pendingSide = null }) { Text("Cancel") } }
        )
    }

    Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(22.dp), border = BorderStroke(1.dp, Purple.copy(alpha = 0.32f))) {
        Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column {
                    Text("Manual Trade", color = Ink, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold)
                    Text("Choose CE or PE and place your own order", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
                StatusPill(a.timeframe ?: vm.selectedTimeframe, Blue)
            }

            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("CE", "PE").forEach { type ->
                    val selected = manualType == type
                    Button(
                        onClick = { manualType = type },
                        modifier = Modifier.weight(1f),
                        colors = ButtonDefaults.buttonColors(containerColor = if (selected) (if (type == "CE") Green else Red) else Panel2),
                        shape = RoundedCornerShape(14.dp)
                    ) { Text(type, color = if (selected) Color.White else Muted, fontWeight = FontWeight.ExtraBold) }
                }
            }

            if (contract == null) {
                InfoStrip("Manual contract unavailable", "Refresh analysis to load the near ATM option contracts.")
            } else {
                Surface(color = Panel2, shape = RoundedCornerShape(14.dp)) {
                    Row(Modifier.fillMaxWidth().padding(14.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text("SELECTED CONTRACT", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                            Text(contract.tradingSymbol ?: "Option contract", color = Ink, fontWeight = FontWeight.ExtraBold)
                            Text("Strike ${n(contract.strike)} • Lot ${contract.lotSize ?: 0}", color = Muted, style = MaterialTheme.typography.labelSmall)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text("PREMIUM", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                            Text(n(contract.ltp), color = if (manualType == "CE") Green else Red, fontSize = 20.sp, fontWeight = FontWeight.ExtraBold)
                        }
                    }
                }

                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Column {
                        Text("LOTS", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                        Text("$lots  •  ${(contract.lotSize ?: 0) * lots} qty", color = Ink, fontWeight = FontWeight.ExtraBold)
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        FilledTonalButton(onClick = { if (lots > 1) lots-- }, enabled = !vm.orderBusy) { Text("−") }
                        Spacer(Modifier.width(8.dp))
                        FilledTonalButton(onClick = { if (lots < 20) lots++ }, enabled = !vm.orderBusy) { Text("+") }
                    }
                }

                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Button(
                        onClick = { pendingSide = "BUY" },
                        enabled = gatewayReady && !vm.orderBusy,
                        modifier = Modifier.weight(1f).height(52.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Green, disabledContainerColor = Panel2),
                        shape = RoundedCornerShape(14.dp)
                    ) { Text(if (gatewayReady) "BUY $manualType" else "ORDER BLOCKED", color = if (gatewayReady) Color.White else Muted, fontWeight = FontWeight.ExtraBold) }

                    Button(
                        onClick = { pendingSide = "SELL" },
                        enabled = canExit && !vm.orderBusy,
                        modifier = Modifier.weight(1f).height(52.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Red, disabledContainerColor = Panel2),
                        shape = RoundedCornerShape(14.dp)
                    ) { Text(if (canExit) "SELL / EXIT" else "NO POSITION", color = if (canExit) Color.White else Muted, fontWeight = FontWeight.ExtraBold) }
                }
                if (!gatewayReady) {
                    InfoStrip("Live order route blocked", vm.orderGateway?.message ?: "Check Real Order Gateway before placing a live order.")
                } else if (currentLongQty > 0) {
                    Text("Open position: ${currentLongQty.toInt()} qty", color = Green, style = MaterialTheme.typography.bodySmall)
                }
                vm.orderMessage?.let { InfoStrip("Manual order status", it) }
            }
        }
    }
}

@Composable
fun AutoTradeCard(vm: DhanPulseViewModel) {
    var confirmEnable by remember { mutableStateOf(false) }
    if (confirmEnable) {
        AlertDialog(
            onDismissRequest = { confirmEnable = false },
            title = { Text("Enable Auto Trade?") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    val gatewayReady = vm.orderGateway?.executionReady == true
                    val researchPassed = vm.backtestReport?.adaptive?.gatePassed == true
                    Text("DhanPulse will place real BUY orders automatically when the same CE or PE signal is confirmed on two refreshes.")
                    Text("Order route: " + if (gatewayReady) "READY" else "BLOCKED", color = if (gatewayReady) Green else Red, fontWeight = FontWeight.Bold)
                    Text("Research validation: " + if (researchPassed) "PASSED" else "NOT PASSED — experimental live use", color = if (researchPassed) Green else Amber, style = MaterialTheme.typography.bodySmall)
                    Text("It will auto EXIT only the position opened by this auto session when Target 1, stop loss or the opposite signal is reached.", color = Muted, style = MaterialTheme.typography.bodySmall)
                    Text("Auto Trade works only while this app is open and logged in.", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
            },
            confirmButton = {
                Button(
                    onClick = { vm.updateAutoTradeEnabled(true); confirmEnable = false },
                    enabled = vm.orderGateway?.executionReady == true,
                    colors = ButtonDefaults.buttonColors(containerColor = Green, disabledContainerColor = Panel2)
                ) {
                    Text("Enable Auto Trade", color = Color.White, fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = { TextButton(onClick = { confirmEnable = false }) { Text("Cancel") } }
        )
    }

    val researchPassed = vm.backtestReport?.adaptive?.gatePassed == true
    val gatewayReady = vm.orderGateway?.executionReady == true
    val activeColor = when {
        vm.autoTradeEnabled && researchPassed -> Green
        vm.autoTradeEnabled -> Amber
        !gatewayReady -> Red
        else -> Muted
    }
    Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(22.dp), border = BorderStroke(1.dp, if (vm.autoTradeEnabled) Green.copy(alpha = 0.30f) else Line)) {
        Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column {
                    Text("Auto Trade", color = Ink, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold)
                    Text("Automatic CE / PE entry and protected exit", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
                Switch(
                    checked = vm.autoTradeEnabled,
                    enabled = gatewayReady || vm.autoTradeEnabled,
                    onCheckedChange = { enabled -> if (enabled) confirmEnable = true else vm.updateAutoTradeEnabled(false) }
                )
            }

            Surface(color = activeColor.copy(alpha = 0.10f), shape = RoundedCornerShape(14.dp), border = BorderStroke(1.dp, activeColor.copy(alpha = 0.22f))) {
                Text(vm.autoStatus, color = activeColor, modifier = Modifier.fillMaxWidth().padding(12.dp), style = MaterialTheme.typography.bodySmall)
            }
            AccountSettingRow("Order route", if (gatewayReady) "READY" else "BLOCKED")
            AccountSettingRow("Research gate", if (researchPassed) "PASSED" else "WARNING ONLY")
            if (!gatewayReady) {
                Text(
                    "Live Auto cannot be enabled until Angel order traffic actually exits from the registered static IP. This is a network route requirement, not a signal-setting issue.",
                    color = Red,
                    style = MaterialTheme.typography.labelSmall
                )
            }

            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column {
                    Text("AUTO LOTS", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                    Text(vm.autoLots.toString(), color = Ink, fontSize = 20.sp, fontWeight = FontWeight.ExtraBold)
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    FilledTonalButton(onClick = { vm.updateAutoLots(vm.autoLots - 1) }, enabled = !vm.autoTradeEnabled && vm.autoLots > 1) { Text("−") }
                    Spacer(Modifier.width(8.dp))
                    FilledTonalButton(onClick = { vm.updateAutoLots(vm.autoLots + 1) }, enabled = !vm.autoTradeEnabled && vm.autoLots < 5) { Text("+") }
                }
            }

            Text("Safety: maximum 5 lots, no naked option selling, one auto position at a time, two matching signal confirmations required.", color = Muted, style = MaterialTheme.typography.labelSmall)
        }
    }
}

@Composable
fun BacktestLabCard(vm: DhanPulseViewModel) {
    val report = vm.backtestReport
    var resultTab by remember(report?.generatedAt) { mutableStateOf("SUMMARY") }
    Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(22.dp), border = BorderStroke(1.dp, Blue.copy(alpha = 0.30f))) {
        Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Backtest Lab", color = Ink, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold)
                    Text("Clarity v1.2 • research only • no real orders", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
                StatusPill(if (vm.backtestBusy) "RUNNING" else "HISTORICAL", if (vm.backtestBusy) Amber else Blue)
            }

            Surface(color = Panel2, shape = RoundedCornerShape(14.dp)) {
                Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("TEST SETUP", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                    Text("${vm.selectedSymbol.replace("BANKNIFTY", "BANK NIFTY")} • ${timeframeShort(vm.selectedTimeframe)} entry • 15m trend", color = Ink, fontWeight = FontWeight.ExtraBold)
                    Text("Model capital ${money(vm.backtestCapital)} • 1% current-equity risk model", color = Muted, style = MaterialTheme.typography.labelSmall)
                }
            }

            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("HISTORY PERIOD", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf(1 to "1Y", 3 to "3Y", 5 to "5Y").forEach { pair ->
                        val selected = vm.backtestYears == pair.first
                        FilledTonalButton(
                            onClick = { vm.updateBacktestYears(pair.first) },
                            enabled = !vm.backtestBusy,
                            modifier = Modifier.weight(1f),
                            colors = ButtonDefaults.filledTonalButtonColors(containerColor = if (selected) Blue.copy(alpha = 0.25f) else Panel2, contentColor = if (selected) Blue else Muted)
                        ) { Text(pair.second, fontWeight = FontWeight.ExtraBold) }
                    }
                }
            }

            Button(
                onClick = vm::runBacktest,
                enabled = !vm.backtestBusy && !vm.autoTradeEnabled,
                modifier = Modifier.fillMaxWidth().height(52.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Blue)
            ) {
                if (vm.backtestBusy) {
                    CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp, color = Color.White)
                    Spacer(Modifier.width(10.dp))
                    Text("Pulling & testing history…", color = Color.White, fontWeight = FontWeight.Bold)
                } else Text("RUN HISTORICAL BACKTEST", color = Color.White, fontWeight = FontWeight.ExtraBold)
            }

            if (vm.autoTradeEnabled) InfoStrip("Backtest locked", "Switch Auto Trade OFF before historical testing.")
            vm.backtestError?.let { ErrorStrip(it) }

            if (report != null) {
                HorizontalDivider(color = Line)
                Text("${report.candles} weekday candles • ${report.years}Y • ${report.period.from?.take(10) ?: ""} to ${report.period.to?.take(10) ?: ""}", color = Muted, style = MaterialTheme.typography.labelSmall)

                if (report.dataQuality.weekendOrSpecialCandlesExcluded > 0) {
                    InfoStrip(
                        "Data cleaned",
                        "${report.dataQuality.weekendOrSpecialCandlesExcluded} weekend/special-session candles were excluded from normal strategy and weekday statistics. Weekday analysis now uses Monday to Friday only."
                    )
                }

                val adaptive = report.adaptive
                val decisionColor = if (adaptive.gatePassed) Green else Red
                Surface(color = decisionColor.copy(alpha = 0.08f), shape = RoundedCornerShape(16.dp), border = BorderStroke(1.dp, decisionColor.copy(alpha = 0.22f))) {
                    Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("WHAT SHOULD I CONSIDER?", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                        Text(report.interpretation.verdict.ifBlank { if (adaptive.gatePassed) "PAPER TEST" else "NOT READY" }, color = decisionColor, fontWeight = FontWeight.ExtraBold, fontSize = 17.sp)
                        Text(report.interpretation.reason.ifBlank { adaptive.message }, color = Muted, style = MaterialTheme.typography.bodySmall)
                        if (report.interpretation.focus.isNotEmpty()) {
                            Text("Main things to check: " + report.interpretation.focus.take(3).joinToString(" • "), color = Ink, style = MaterialTheme.typography.labelSmall)
                        }
                    }
                }

                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    BacktestTab("Summary", "SUMMARY", resultTab, Modifier.weight(1f)) { resultTab = "SUMMARY" }
                    BacktestTab("Adaptive", "ADAPTIVE", resultTab, Modifier.weight(1f)) { resultTab = "ADAPTIVE" }
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    BacktestTab("Diagnostics", "DIAGNOSTICS", resultTab, Modifier.weight(1f)) { resultTab = "DIAGNOSTICS" }
                    BacktestTab("Robustness", "ROBUSTNESS", resultTab, Modifier.weight(1f)) { resultTab = "ROBUSTNESS" }
                }

                when (resultTab) {
                    "ADAPTIVE" -> {
                        val gateColor = if (adaptive.gatePassed) Green else Red
                        Surface(color = gateColor.copy(alpha = 0.08f), shape = RoundedCornerShape(16.dp), border = BorderStroke(1.dp, gateColor.copy(alpha = 0.22f))) {
                            Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                    Column(Modifier.weight(1f)) {
                                        Text("Adaptive Intelligence", color = Ink, fontWeight = FontWeight.ExtraBold)
                                        Text("Develop → validate → untouched unseen test", color = Muted, style = MaterialTheme.typography.labelSmall)
                                    }
                                    StatusPill(if (adaptive.gatePassed) "PAPER ELIGIBLE" else "LIVE BLOCKED", gateColor)
                                }
                                Text(adaptive.message, color = if (adaptive.gatePassed) Green else Muted, style = MaterialTheme.typography.bodySmall)
                                adaptive.configName?.takeIf { it.isNotBlank() }?.let { Text(it, color = Blue, fontWeight = FontWeight.Bold) }
                                adaptive.ruleText?.takeIf { it.isNotBlank() }?.let { rule ->
                                    Surface(color = Panel2, shape = RoundedCornerShape(12.dp)) { Text(rule, color = Ink, modifier = Modifier.fillMaxWidth().padding(10.dp), style = MaterialTheme.typography.bodySmall) }
                                }
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    BacktestMetric("CONFIGS", adaptive.searchedConfigs.toString(), Modifier.weight(1f))
                                    BacktestMetric("CANDIDATES", adaptive.candidates.toString(), Modifier.weight(1f))
                                    BacktestMetric("GATE", if (adaptive.gatePassed) "PASS" else "FAIL", Modifier.weight(1f))
                                }
                                adaptive.development?.let { AdaptivePhaseRow("1. DEVELOPMENT", it) }
                                adaptive.validation?.let { AdaptivePhaseRow("2. VALIDATION", it) }
                                adaptive.outOfSample?.let { AdaptivePhaseRow("3. UNSEEN", it) }
                                adaptive.combined?.let { x ->
                                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                        BacktestMetric("FILTERED PF", x.profitFactor?.let { String.format("%.2f", it) } ?: "NA", Modifier.weight(1f))
                                        BacktestMetric("EXP", String.format("%.3fR", x.expectancyR), Modifier.weight(1f))
                                        BacktestMetric("MAX DD", String.format("%.1f%%", x.maxDrawdownPct), Modifier.weight(1f))
                                    }
                                }
                            }
                        }
                    }

                    "DIAGNOSTICS" -> {
                        val trend = report.strategies.firstOrNull { it.strategy == "TREND_PRO" }
                        if (trend != null) {
                            Text("Trend Pro diagnostics", color = Ink, fontWeight = FontWeight.ExtraBold)
                            Text("These explain the past. Do not choose a live rule from one green box alone.", color = Muted, style = MaterialTheme.typography.bodySmall)
                            ExpandableDiagnostic("CE vs PE", trend.diagnostics.sides, false)
                            ExpandableDiagnostic("Time windows", trend.diagnostics.times, false)
                            ExpandableDiagnostic("Weekdays — Monday to Friday", trend.diagnostics.weekdays, false)
                            ExpandableDiagnostic("Market regime", trend.diagnostics.regimes, false)
                            ExpandableDiagnostic("Volatility", trend.diagnostics.volatility, false)
                            ExpandableDiagnostic("Exit outcomes", trend.diagnostics.exits, false)
                            ExpandableDiagnostic("Development / validation / unseen", trend.diagnostics.phases, false)
                            ExpandableDiagnostic("Year by year", trend.diagnostics.years, false)
                        }
                    }

                    "ROBUSTNESS" -> {
                        val rb = report.robustness
                        Surface(color = Blue.copy(alpha = 0.08f), shape = RoundedCornerShape(16.dp), border = BorderStroke(1.dp, Blue.copy(alpha = 0.20f))) {
                            Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                Text("Parameter robustness", color = Ink, fontWeight = FontWeight.ExtraBold)
                                Text("If nearby settings also work, the strategy is more believable. One lucky setting is not enough.", color = Muted, style = MaterialTheme.typography.bodySmall)
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    BacktestMetric("TESTED", rb.combinations.toString(), Modifier.weight(1f))
                                    BacktestMetric("PROFITABLE", rb.profitableCombinations.toString(), Modifier.weight(1f))
                                    BacktestMetric("STABLE %", String.format("%.1f%%", rb.profitablePct), Modifier.weight(1f))
                                }
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    BacktestMetric("MEDIAN PF", rb.medianProfitFactor?.let { String.format("%.2f", it) } ?: "NA", Modifier.weight(1f))
                                    BacktestMetric("MIN PF", rb.minProfitFactor?.let { String.format("%.2f", it) } ?: "NA", Modifier.weight(1f))
                                    BacktestMetric("MAX PF", rb.maxProfitFactor?.let { String.format("%.2f", it) } ?: "NA", Modifier.weight(1f))
                                }
                                rb.best?.let { b -> Text("Strongest nearby setting: EMA ${b.ema}, Stop ${String.format("%.1f", b.stopAtr)} ATR • PF ${b.profitFactor?.let { String.format("%.2f", it) } ?: "NA"} • ${String.format("%.3f", b.expectancyR)}R/trade", color = Blue, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold) }
                            }
                        }
                        InfoStrip("Data quality", report.dataQuality.note)
                    }

                    else -> {
                        Text("Strategy summary", color = Ink, fontWeight = FontWeight.ExtraBold)
                        report.strategies.forEach { CompactStrategyRow(it) }
                        Surface(color = Panel2, shape = RoundedCornerShape(14.dp)) {
                            Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                                Text("HOW TO READ", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                                Text("PF above 1.00 = gross winning R is greater than losing R.", color = Ink, style = MaterialTheme.typography.bodySmall)
                                Text("Expectancy above 0 = average trade is positive after the model friction.", color = Ink, style = MaterialTheme.typography.bodySmall)
                                Text("1R = the amount risked on one trade. With Rs. 20,000 and 1% risk, the first 1R is about Rs. 200.", color = Ink, style = MaterialTheme.typography.bodySmall)
                                Text("Max DD = biggest peak-to-trough fall in the model equity.", color = Ink, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }

                InfoStrip("Important", "Green historical numbers are not a guarantee. The main decision is the Adaptive gate; Live Auto should remain blocked until a rule passes unseen-data testing and later option-premium validation.")
            } else {
                Text("Run a backtest. The app will show one clear decision first, then you can open Summary, Adaptive, Diagnostics or Robustness separately.", color = Muted, style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}

@Composable
private fun BacktestTab(label: String, key: String, selected: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    val active = key == selected
    FilledTonalButton(
        onClick = onClick,
        modifier = modifier,
        colors = ButtonDefaults.filledTonalButtonColors(containerColor = if (active) Blue.copy(alpha = 0.25f) else Panel2, contentColor = if (active) Blue else Muted)
    ) { Text(label, fontSize = 11.sp, fontWeight = FontWeight.Bold) }
}

@Composable
private fun CompactStrategyRow(s: BacktestStrategy) {
    val rc = if (s.expectancyR > 0 && (s.profitFactor ?: 0.0) > 1.0) Green else Red
    Surface(color = rc.copy(alpha = 0.06f), shape = RoundedCornerShape(14.dp), border = BorderStroke(1.dp, rc.copy(alpha = 0.16f))) {
        Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(s.label, color = Ink, fontWeight = FontWeight.ExtraBold)
                Text("${if (s.netR >= 0) "+" else ""}${String.format("%.2f", s.netR)}R", color = rc, fontWeight = FontWeight.ExtraBold)
            }
            Text("${s.totalTrades} trades • WR ${String.format("%.1f", s.winRate)}% • PF ${s.profitFactor?.let { String.format("%.2f", it) } ?: "NA"} • Exp ${String.format("%.3f", s.expectancyR)}R • DD ${String.format("%.1f", s.maxDrawdownPct)}%", color = Muted, style = MaterialTheme.typography.labelSmall)
        }
    }
}

@Composable
private fun ExpandableDiagnostic(title: String, rows: List<BacktestSlice>, initiallyOpen: Boolean) {
    if (rows.isEmpty()) return
    var open by remember(title) { mutableStateOf(initiallyOpen) }
    Surface(color = Panel2, shape = RoundedCornerShape(14.dp)) {
        Column(Modifier.fillMaxWidth()) {
            Row(
                Modifier.fillMaxWidth().clickable { open = !open }.padding(horizontal = 12.dp, vertical = 11.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(title, color = Ink, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                Text(if (open) "▲" else "▼", color = Blue, fontWeight = FontWeight.Bold)
            }
            if (open) {
                Column(Modifier.padding(horizontal = 10.dp, vertical = 6.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                    DiagnosticSliceGroup("", rows)
                }
            }
        }
    }
}

@Composable
private fun AdaptivePhaseRow(title: String, x: AdaptivePhase) {
    val positive = x.expectancyR > 0 && (x.profitFactor ?: 0.0) > 1.0
    val rc = if (positive) Green else Red
    Surface(color = Panel2, shape = RoundedCornerShape(12.dp)) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 11.dp, vertical = 9.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(Modifier.weight(1f)) {
                Text(title, color = Ink, fontWeight = FontWeight.Bold, fontSize = 11.sp)
                Text("${x.trades} trades • WR ${String.format("%.1f", x.winRate)}%", color = Muted, fontSize = 9.sp)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text("${if (x.netR >= 0) "+" else ""}${String.format("%.2f", x.netR)}R", color = rc, fontWeight = FontWeight.ExtraBold)
                Text("PF ${x.profitFactor?.let { String.format("%.2f", it) } ?: "NA"} • ${String.format("%.3f", x.expectancyR)}R", color = Muted, fontSize = 9.sp)
            }
        }
    }
}

@Composable
private fun DiagnosticSliceGroup(title: String, rows: List<BacktestSlice>) {
    if (rows.isEmpty()) return
    Column(verticalArrangement = Arrangement.spacedBy(7.dp)) {
        if (title.isNotBlank()) Text(title.uppercase(), color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
        rows.forEach { row ->
            val positive = row.expectancyR > 0.0
            val rc = if (positive) Green else Red
            Surface(color = Panel2, shape = RoundedCornerShape(12.dp)) {
                Row(
                    Modifier.fillMaxWidth().padding(horizontal = 11.dp, vertical = 9.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(row.label, color = Ink, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                        Text("${row.trades} trades • WR ${String.format("%.1f", row.winRate)}%", color = Muted, fontSize = 9.sp)
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text("${if (row.netR >= 0) "+" else ""}${String.format("%.2f", row.netR)}R", color = rc, fontWeight = FontWeight.ExtraBold)
                        Text("PF ${row.profitFactor?.let { String.format("%.2f", it) } ?: "NA"} • ${String.format("%.3f", row.expectancyR)}R", color = Muted, fontSize = 9.sp)
                    }
                }
            }
        }
    }
}
@Composable
private fun BacktestMetric(label: String, value: String, modifier: Modifier = Modifier) {
    Column(modifier.clip(RoundedCornerShape(12.dp)).background(Panel2).padding(9.dp)) {
        Text(label, color = Muted, fontSize = 8.sp, fontWeight = FontWeight.Bold)
        Text(value, color = Ink, fontSize = 14.sp, fontWeight = FontWeight.ExtraBold)
    }
}

private fun timeframeShort(interval: String): String = when (interval) {
    "ONE_MINUTE" -> "1m"
    "THREE_MINUTE" -> "3m"
    "TEN_MINUTE" -> "10m"
    "FIFTEEN_MINUTE" -> "15m"
    else -> "5m"
}

@Composable
fun AccountCard(account: AccountSummary, refresh: () -> Unit) {
    val pnlColor = if (account.totalPnl >= 0) Green else Red
    Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(22.dp), border = BorderStroke(1.dp, Line)) {
        Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column {
                    Text("Account", color = Ink, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold)
                    Text("Angel One funds and live P&L", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
                TextButton(onClick = refresh) { Text("Refresh") }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                AccountMetric("AVAILABLE CASH", money(account.availableCash), Ink, Modifier.weight(1f))
                AccountMetric("RMS NET", money(account.net), Blue, Modifier.weight(1f))
            }
            Surface(color = pnlColor.copy(alpha = 0.10f), shape = RoundedCornerShape(16.dp), border = BorderStroke(1.dp, pnlColor.copy(alpha = 0.22f))) {
                Column(Modifier.fillMaxWidth().padding(14.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("TODAY P&L", color = Muted, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                        Text(money(account.totalPnl), color = pnlColor, fontSize = 24.sp, fontWeight = FontWeight.ExtraBold)
                    }
                    Spacer(Modifier.height(8.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("Realized ${money(account.realizedPnl)}", color = Muted, style = MaterialTheme.typography.bodySmall)
                        Text("Unrealized ${money(account.unrealizedPnl)}", color = Muted, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
            Text("Open positions ${account.positions.count { it.netQty != 0.0 }}   •   Used margin ${money(account.utilizedDebits)}", color = Muted, style = MaterialTheme.typography.labelSmall)
        }
    }
}

@Composable
private fun AccountMetric(label: String, value: String, color: Color, modifier: Modifier = Modifier) {
    Column(modifier.clip(RoundedCornerShape(14.dp)).background(Panel2).padding(12.dp)) {
        Text(label, color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
        Text(value, color = color, fontSize = 17.sp, fontWeight = FontWeight.ExtraBold)
    }
}

@Composable
fun MarketCard(a: AnalysisResponse) {
    val m = a.market
    Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(22.dp), border = BorderStroke(1.dp, Line)) {
        Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Market structure", color = Ink, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold)
            Text("Price trend and momentum", color = Muted, style = MaterialTheme.typography.bodySmall)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                MetricTile("LTP", n(m.ltp), Modifier.weight(1f))
                MetricTile("VWAP", n(m.vwap), Modifier.weight(1f))
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                MetricTile("EMA 9", n(m.ema9), Modifier.weight(1f))
                MetricTile("EMA 15", n(m.ema15), Modifier.weight(1f))
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                MetricTile("RSI", n(m.rsi), Modifier.weight(1f))
                MetricTile("MACD", n(m.macdHistogram), Modifier.weight(1f))
                MetricTile("ATR", n(m.atr), Modifier.weight(1f))
            }
            val stBull = m.supertrend?.direction == "BULLISH"
            Surface(color = if (stBull) Green.copy(alpha = 0.10f) else Red.copy(alpha = 0.10f), shape = RoundedCornerShape(14.dp)) {
                Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("SUPERTREND", color = Muted, style = MaterialTheme.typography.labelSmall)
                    Text(m.supertrend?.direction ?: "NA", color = if (stBull) Green else Red, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
fun OptionCard(a: AnalysisResponse) {
    val o = a.optionChain
    Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(22.dp), border = BorderStroke(1.dp, Line)) {
        Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column {
                    Text("Option intelligence", color = Ink, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold)
                    Text("Market evidence only • CE and PE OI are not trade calls", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text("EXPIRY", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                    Text(o.expiry ?: "NA", color = Ink, fontWeight = FontWeight.Bold)
                }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                LevelTile("SUPPORT", n(o.support), Green, Modifier.weight(1f))
                LevelTile("ATM", n(o.atm), Blue, Modifier.weight(1f))
                LevelTile("RESISTANCE", n(o.resistance), Red, Modifier.weight(1f))
            }
            HorizontalDivider(color = Line)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                OiMetric("CALL OI", compact(o.totalCeOi), Red, Alignment.Start)
                OiMetric("PCR", n(o.nearAtmPcr), Ink, Alignment.CenterHorizontally)
                OiMetric("PUT OI", compact(o.totalPeOi), Green, Alignment.End)
            }
        }
    }
}

@Composable
private fun StatusPill(text: String, color: Color) {
    Surface(color = color.copy(alpha = 0.12f), shape = RoundedCornerShape(50), border = BorderStroke(1.dp, color.copy(alpha = 0.25f))) {
        Text(text, color = color, fontSize = 9.sp, fontWeight = FontWeight.ExtraBold, modifier = Modifier.padding(horizontal = 9.dp, vertical = 5.dp))
    }
}

@Composable
private fun ErrorStrip(message: String) {
    Surface(color = Red.copy(alpha = 0.10f), shape = RoundedCornerShape(14.dp), border = BorderStroke(1.dp, Red.copy(alpha = 0.25f))) {
        Column(Modifier.fillMaxWidth().padding(12.dp)) {
            Text("Connection issue", color = Red, fontWeight = FontWeight.Bold)
            Text(message, color = Muted, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun InfoStrip(title: String, body: String) {
    Surface(color = Amber.copy(alpha = 0.10f), shape = RoundedCornerShape(14.dp), border = BorderStroke(1.dp, Amber.copy(alpha = 0.25f))) {
        Column(Modifier.fillMaxWidth().padding(12.dp)) {
            Text(title, color = Amber, fontWeight = FontWeight.Bold)
            Text(body, color = Muted, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun ScoreMetric(label: String, value: String, color: Color) {
    Column {
        Text(label, color = Muted, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        Text(value, color = color, fontSize = 21.sp, fontWeight = FontWeight.ExtraBold)
    }
}

@Composable
private fun MetricTile(label: String, value: String, modifier: Modifier = Modifier) {
    Column(modifier.clip(RoundedCornerShape(14.dp)).background(Panel2).padding(12.dp)) {
        Text(label, color = Muted, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        Text(value, color = Ink, fontSize = 17.sp, fontWeight = FontWeight.ExtraBold)
    }
}

@Composable
private fun LevelTile(label: String, value: String, color: Color, modifier: Modifier = Modifier) {
    Column(modifier.clip(RoundedCornerShape(14.dp)).background(color.copy(alpha = 0.08f)).border(1.dp, color.copy(alpha = 0.18f), RoundedCornerShape(14.dp)).padding(12.dp)) {
        Text(label, color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
        Text(value, color = color, fontSize = 14.sp, fontWeight = FontWeight.ExtraBold)
    }
}

@Composable
private fun OiMetric(label: String, value: String, color: Color, alignment: Alignment.Horizontal) {
    Column(horizontalAlignment = alignment) {
        Text(label, color = Muted, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        Text(value, color = color, fontSize = 18.sp, fontWeight = FontWeight.ExtraBold)
    }
}

private fun compact(v: Number?): String {
    val x = v?.toDouble() ?: return "NA"
    return when {
        x >= 10_000_000 -> String.format("%.2f Cr", x / 10_000_000.0)
        x >= 100_000 -> String.format("%.2f L", x / 100_000.0)
        x >= 1_000 -> String.format("%.1f K", x / 1_000.0)
        else -> String.format("%.0f", x)
    }
}

private fun n(v: Number?): String = if (v == null) "NA" else String.format("%,.2f", v.toDouble())
private fun money(v: Number?): String = if (v == null) "₹0.00" else "₹" + String.format("%,.2f", v.toDouble())