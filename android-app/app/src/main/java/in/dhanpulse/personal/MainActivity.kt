package `in`.dhanpulse.personal

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.BorderStroke
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import `in`.dhanpulse.personal.model.AnalysisResponse
import `in`.dhanpulse.personal.model.AccountSummary
import `in`.dhanpulse.personal.ui.DhanPulseViewModel


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
                Surface(
                    color = Amber.copy(alpha = 0.12f),
                    shape = RoundedCornerShape(16.dp),
                    border = BorderStroke(1.dp, Amber.copy(alpha = 0.28f))
                ) {
                    Text("DP", color = Amber, fontSize = 22.sp, fontWeight = FontWeight.Black, modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp))
                }
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
    val a = vm.analysis
    LazyColumn(
        Modifier.fillMaxSize().background(AppBg).statusBarsPadding().navigationBarsPadding().padding(horizontal = 16.dp),
        contentPadding = PaddingValues(top = 12.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Surface(
                            color = Amber.copy(alpha = 0.12f),
                            shape = RoundedCornerShape(10.dp),
                            border = BorderStroke(1.dp, Amber.copy(alpha = 0.25f))
                        ) {
                            Text("DP", color = Amber, fontSize = 13.sp, fontWeight = FontWeight.Black, modifier = Modifier.padding(horizontal = 8.dp, vertical = 6.dp))
                        }
                        Spacer(Modifier.width(10.dp))
                        Text("DhanPulse", color = Ink, fontSize = 26.sp, fontWeight = FontWeight.ExtraBold)
                        Spacer(Modifier.width(9.dp))
                        StatusPill("LIVE", Green)
                    }
                    Text(vm.profile?.name ?: vm.profile?.clientcode ?: "Angel One connected", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
                TextButton(onClick = vm::logout) { Text("Logout", color = Muted, fontWeight = FontWeight.SemiBold) }
            }
        }
        item {
            Row(
                Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(Panel).border(1.dp, Line, RoundedCornerShape(16.dp)).padding(5.dp),
                horizontalArrangement = Arrangement.spacedBy(5.dp)
            ) {
                listOf("NIFTY" to "NIFTY", "BANKNIFTY" to "BANK NIFTY", "SENSEX" to "SENSEX").forEach { pair ->
                    val selected = vm.selectedSymbol == pair.first
                    Box(
                        Modifier.weight(1f).clip(RoundedCornerShape(12.dp)).background(if (selected) Purple else Color.Transparent).clickable { vm.selectSymbol(pair.first) }.padding(vertical = 12.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(pair.second, color = if (selected) Color.White else Muted, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
        vm.account?.let { account ->
            item { AccountCard(account, vm::fetchAccount) }
        }
        item { AutoTradeCard(vm) }
        vm.error?.let { item { ErrorStrip(it) } }
        vm.refreshWarning?.let { item { InfoStrip("Live refresh delayed", "Showing the latest successful analysis. Automatic retry is active.") } }
        if (vm.loading && a == null) item {
            Box(Modifier.fillMaxWidth().height(180.dp).clip(RoundedCornerShape(22.dp)).background(Panel), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    CircularProgressIndicator(color = Purple)
                    Spacer(Modifier.height(12.dp))
                    Text("Reading live market data...", color = Muted)
                }
            }
        }
        if (a != null) {
            item { SignalCard(a, vm::fetchAnalysis) }
            item { TradePlanCard(a, vm) }
            item { MarketCard(a) }
            item { OptionCard(a) }
            item {
                Column {
                    Text("Signal confirmation", color = Ink, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold)
                    Text("Every rule used by the engine", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
            }
            items(a.rules) { rule ->
                val stateColor = when (rule.state.uppercase()) { "BULLISH" -> Green; "BEARISH" -> Red; "NEUTRAL" -> Amber; else -> Muted }
                Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(18.dp), border = BorderStroke(1.dp, Line)) {
                    Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                        Box(Modifier.width(4.dp).height(42.dp).clip(RoundedCornerShape(4.dp)).background(stateColor))
                        Spacer(Modifier.width(12.dp))
                        Column(Modifier.weight(1f)) {
                            Text(rule.name, color = Ink, fontWeight = FontWeight.Bold)
                            rule.detail?.let { Text(it, color = Muted, style = MaterialTheme.typography.bodySmall) }
                        }
                        StatusPill(rule.state.uppercase(), stateColor)
                    }
                }
            }
            item { Text("AUTO REFRESH 60 SEC  •  AUTO TRADE OPTIONAL  •  LIVE P&L", color = Muted, style = MaterialTheme.typography.labelSmall, modifier = Modifier.padding(top = 4.dp)) }
        }
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
                    Text(if (a.signal == "WAIT") "No trade confirmation" else if (a.signal == "CE") "Bullish confirmation" else "Bearish confirmation", color = Muted)
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
                        Text(it.tradingSymbol ?: "Suggested contract", color = Ink, fontWeight = FontWeight.Bold)
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
    val canExit = currentLongQty > 0.0

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
                        enabled = !vm.orderBusy,
                        modifier = Modifier.weight(1f).height(52.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Green),
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
fun AutoTradeCard(vm: DhanPulseViewModel) {
    var confirmEnable by remember { mutableStateOf(false) }
    if (confirmEnable) {
        AlertDialog(
            onDismissRequest = { confirmEnable = false },
            title = { Text("Enable Auto Trade?") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("DhanPulse will place real BUY orders automatically when the same CE or PE signal is confirmed on two refreshes.")
                    Text("It will auto EXIT only the position opened by this auto session when Target 1, stop loss or the opposite signal is reached.", color = Muted, style = MaterialTheme.typography.bodySmall)
                    Text("Auto Trade works only while this app is open and logged in.", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
            },
            confirmButton = {
                Button(onClick = { vm.setAutoTradeEnabled(true); confirmEnable = false }, colors = ButtonDefaults.buttonColors(containerColor = Green)) {
                    Text("Enable Auto Trade", color = Color.White, fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = { TextButton(onClick = { confirmEnable = false }) { Text("Cancel") } }
        )
    }

    val activeColor = if (vm.autoTradeEnabled) Green else Muted
    Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(22.dp), border = BorderStroke(1.dp, if (vm.autoTradeEnabled) Green.copy(alpha = 0.30f) else Line)) {
        Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column {
                    Text("Auto Trade", color = Ink, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold)
                    Text("Automatic CE / PE entry and protected exit", color = Muted, style = MaterialTheme.typography.bodySmall)
                }
                Switch(
                    checked = vm.autoTradeEnabled,
                    onCheckedChange = { enabled -> if (enabled) confirmEnable = true else vm.setAutoTradeEnabled(false) }
                )
            }

            Surface(color = activeColor.copy(alpha = 0.10f), shape = RoundedCornerShape(14.dp), border = BorderStroke(1.dp, activeColor.copy(alpha = 0.22f))) {
                Text(vm.autoStatus, color = if (vm.autoTradeEnabled) Green else Muted, modifier = Modifier.fillMaxWidth().padding(12.dp), style = MaterialTheme.typography.bodySmall)
            }

            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column {
                    Text("AUTO LOTS", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                    Text(vm.autoLots.toString(), color = Ink, fontSize = 20.sp, fontWeight = FontWeight.ExtraBold)
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    FilledTonalButton(onClick = { vm.setAutoLots(vm.autoLots - 1) }, enabled = !vm.autoTradeEnabled && vm.autoLots > 1) { Text("−") }
                    Spacer(Modifier.width(8.dp))
                    FilledTonalButton(onClick = { vm.setAutoLots(vm.autoLots + 1) }, enabled = !vm.autoTradeEnabled && vm.autoLots < 5) { Text("+") }
                }
            }

            Text("Safety: maximum 5 lots, no naked option selling, one auto position at a time, two matching signal confirmations required.", color = Muted, style = MaterialTheme.typography.labelSmall)
        }
    }
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
                    Text("Near ATM open interest", color = Muted, style = MaterialTheme.typography.bodySmall)
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