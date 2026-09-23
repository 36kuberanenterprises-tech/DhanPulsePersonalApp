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
    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column {
                    Text("DhanPulse Live", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                    Text(vm.profile?.name ?: vm.profile?.clientcode ?: "Connected")
                }
                TextButton(onClick = vm::logout) { Text("Logout") }
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("NIFTY", "BANKNIFTY", "SENSEX").forEach { symbol ->
                    FilterChip(selected = vm.selectedSymbol == symbol, onClick = { vm.selectSymbol(symbol) }, label = { Text(symbol) })
                }
            }
        }
        vm.error?.let { item { Text(it, color = MaterialTheme.colorScheme.error) } }
        vm.refreshWarning?.let { item { Text(it, color = MaterialTheme.colorScheme.tertiary) } }
        if (vm.loading && a == null) item { CircularProgressIndicator() }
        if (a != null) {
            item { SignalCard(a, vm::fetchAnalysis) }
            item { MarketCard(a) }
            item { OptionCard(a) }
            item { Text("Signal checks", fontWeight = FontWeight.Bold) }
            items(a.rules) { rule ->
                Card { Column(Modifier.fillMaxWidth().padding(12.dp)) { Text("${rule.name}: ${rule.state}", fontWeight = FontWeight.SemiBold); rule.detail?.let { Text(it, style = MaterialTheme.typography.bodySmall) } } }
            }
        }
    }
}

@Composable
fun SignalCard(a: AnalysisResponse, refresh: () -> Unit) {
    Card { Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(a.symbol, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            TextButton(onClick = refresh) { Text("Refresh") }
        }
        Text(a.signal, style = MaterialTheme.typography.displayMedium, fontWeight = FontWeight.ExtraBold)
        Text("Bull ${a.ruleScore.bullish}   Bear ${a.ruleScore.bearish}   Considered ${a.ruleScore.considered}")
        a.suggestedContract?.let { Text("Contract ${it.tradingSymbol ?: ""}   LTP ${n(it.ltp)}") }
    } }
}

@Composable
fun MarketCard(a: AnalysisResponse) {
    val m = a.market
    Card { Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text("Market structure", fontWeight = FontWeight.Bold)
        Text("LTP ${n(m.ltp)}")
        Text("EMA 9 ${n(m.ema9)}   EMA 15 ${n(m.ema15)}")
        Text("VWAP ${n(m.vwap)}")
        Text("RSI ${n(m.rsi)}   MACD ${n(m.macdHistogram)}")
        Text("Supertrend ${m.supertrend?.direction ?: "NA"}   ATR ${n(m.atr)}")
    } }
}

@Composable
fun OptionCard(a: AnalysisResponse) {
    val o = a.optionChain
    Card { Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text("Option chain", fontWeight = FontWeight.Bold)
        Text("Expiry ${o.expiry ?: "NA"}   ATM ${n(o.atm)}")
        Text("PCR ${n(o.nearAtmPcr)}")
        Text("Support ${n(o.support)}   Resistance ${n(o.resistance)}")
        Text("CE OI ${n(o.totalCeOi)}   PE OI ${n(o.totalPeOi)}")
    } }
}

private fun n(v: Number?): String = if (v == null) "NA" else String.format("%.2f", v.toDouble())
