package `in`.dhanpulse.personal

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import `in`.dhanpulse.personal.model.AnalysisResponse
import `in`.dhanpulse.personal.ui.DhanPulseViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme(colorScheme = darkColorScheme()) { DhanPulseApp() } }
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

    Column(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Spacer(Modifier.height(20.dp))
        Text("DhanPulse Personal", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text("Angel One live market analysis")
        Text("Backend connection is already configured.", style = MaterialTheme.typography.bodySmall)
        OutlinedTextField(
            pin,
            { pin = it },
            label = { Text("PIN") },
            modifier = Modifier.fillMaxWidth(),
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword)
        )
        OutlinedTextField(
            totp,
            { totp = it },
            label = { Text("Current TOTP") },
            modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
        )
        vm.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Button(
            onClick = { vm.login(pin, totp) { pin = ""; totp = "" } },
            enabled = !vm.loading,
            modifier = Modifier.fillMaxWidth()
        ) {
            if (vm.loading) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp) else Text("Connect to Angel One")
        }
        Text("Only PIN and TOTP are entered here. They are not saved on the phone.", style = MaterialTheme.typography.bodySmall)
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
