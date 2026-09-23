package `in`.dhanpulse.personal

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
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
                Text("DhanPulse", color = Ink, fontSize = 34.sp, fontWeight = FontWeight.ExtraBold)
                Spacer(Modifier.width(10.dp))
                StatusPill("LIVE", Green)
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
                        Text("DhanPulse", color = Ink, fontSize = 28.sp, fontWeight = FontWeight.ExtraBold)
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
            item { Text("AUTO REFRESH 60 SEC  •  ANALYSIS ONLY  •  NO AUTO ORDER", color = Muted, style = MaterialTheme.typography.labelSmall, modifier = Modifier.padding(top = 4.dp)) }
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