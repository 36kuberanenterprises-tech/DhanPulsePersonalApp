package `in`.dhanpulse.personal

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.repeatOnLifecycle
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import `in`.dhanpulse.personal.data.ApiFactory
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

data class FlowInstrument(val token:String, val exchange:String, val symbol:String, val kind:String)
data class FlowCatalog(val items:List<FlowInstrument> = emptyList())
data class FlowLevel(val price:Double=0.0,val buy:Double=0.0,val sell:Double=0.0,val unknown:Double=0.0)
data class FlowDepth(val price:Double=0.0,val quantity:Double=0.0)
data class FlowBar(val time:String="",val buy:Double=0.0,val sell:Double=0.0,val unknown:Double=0.0,
    val unallocated:Double=0.0,val delta:Double=0.0,val levels:List<FlowLevel> = emptyList())
data class FlowSnapshot(val status:String="WAITING_FOR_FEED",val symbol:String="",val startedAt:String="",
    val lastTickAt:String?=null,val price:Double?=null,val spread:Double?=null,val depthImbalance:Double?=null,
    val oi:Double?=null,val estimatedCvd:Double=0.0,val note:String="",val error:String?=null,
    val bids:List<FlowDepth> = emptyList(),val asks:List<FlowDepth> = emptyList(),val bars:List<FlowBar> = emptyList())

private fun flowNumber(value:Double?)=value?.let { String.format(Locale.US,"%,.2f",it) } ?: "Unavailable"
private fun flowTime(value:String?)=runCatching {
    DateTimeFormatter.ofPattern("dd MMM HH:mm:ss").withZone(ZoneId.of("Asia/Kolkata")).format(Instant.parse(value))
}.getOrDefault("Waiting")

@Composable
fun FlowScreen(sessionId:String) {
    val api=remember { ApiFactory.create("https://dhanpulse-personal-api.onrender.com") }
    val owner=LocalLifecycleOwner.current
    var group by remember { mutableStateOf("INDEX") }
    var query by remember { mutableStateOf("NIFTY") }
    var choices by remember { mutableStateOf(emptyList<FlowInstrument>()) }
    var selected by remember { mutableStateOf<FlowInstrument?>(null) }
    var minutes by remember { mutableIntStateOf(5) }
    var restart by remember { mutableIntStateOf(0) }
    var snapshot by remember { mutableStateOf<FlowSnapshot?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var catalogError by remember { mutableStateOf<String?>(null) }
    var searching by remember { mutableStateOf(false) }
    var showContracts by remember { mutableStateOf(true) }
    LaunchedEffect(group,query,sessionId) {
        searching=true;catalogError=null;choices=emptyList();delay(500)
        try { choices=api.flowCatalog(sessionId,group,query).items }
        catch(e:CancellationException){throw e}
        catch(e:Exception){catalogError="Contract list unavailable. Check connection and search again."}
        finally { searching=false }
    }
    LaunchedEffect(selected,minutes,restart,sessionId,owner) {
        snapshot=null;error=null
        val instrument=selected ?: return@LaunchedEffect
        owner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            var first=true
            while(isActive) {
                try {
                    snapshot=api.flowMonitor(sessionId,instrument.exchange,instrument.token,minutes,first)
                    first=false;error=null
                }catch(e:CancellationException){throw e}
                catch(e:Exception){error="Monitor unavailable. Check login or connection, then tap Restart feed."}
                delay(if(error==null) 1000 else 5000)
            }
        }
    }
    LazyColumn(Modifier.fillMaxSize(),contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        item { Text("Footprint & Order Flow",style=MaterialTheme.typography.headlineSmall) }
        item { Text("Live monitoring only. Select one traded contract. Index monitoring uses futures or options, not the spot index.") }
        item { Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
            listOf("INDEX" to "Indices","STOCKS" to "Shares","STOCK_OPTIONS" to "Stock options","MCX" to "MCX").forEach { (key,label) ->
                FilterChip(selected=group==key,onClick={group=key;selected=null;snapshot=null;showContracts=true;
                    query=when(key){"INDEX"->"NIFTY";"MCX"->"CRUDEOIL";else->""}},label={Text(label)})
            }
        } }
        item { OutlinedTextField(value=query,onValueChange={query=it;showContracts=true},label={Text("Search name, expiry or strike")},singleLine=true,modifier=Modifier.fillMaxWidth()) }
        item { TextButton(onClick={showContracts=!showContracts}) { Text(if(showContracts) "Hide contract list" else "Change contract") } }
        if(showContracts) {
            item { Text(if(searching) "Searching contracts…" else catalogError ?: "${choices.size} matches shown. Refine the search for another expiry or strike.") }
            items(choices,key={it.exchange+it.token}) { instrument ->
                OutlinedButton(onClick={selected=instrument;showContracts=false},modifier=Modifier.fillMaxWidth()) {
                    Text("${instrument.symbol}\n${instrument.exchange} • ${instrument.kind}")
                }
            }
        }
        if(selected!=null) {
            item { Text(selected!!.symbol,style=MaterialTheme.typography.titleMedium) }
            item { Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                listOf(1,3,5,10,15).forEach { m -> FilterChip(selected=minutes==m,onClick={minutes=m},label={Text("${m}m")}) }
            } }
            item { Text("Changing contract or timeframe starts a new observation window. Earlier trades are not reconstructed.") }
            item { OutlinedButton(onClick={restart++}){Text("Restart feed")} }
            error?.let { message -> item { Text(message,color=MaterialTheme.colorScheme.error) } }
            val data=snapshot
            item { Text("${data?.status ?: "CONNECTING"} • Last tick ${flowTime(data?.lastTickAt)} IST") }
            data?.error?.let { message -> item { Text(message,color=MaterialTheme.colorScheme.error) } }
            if(data!=null) {
                item { Card(Modifier.fillMaxWidth()) { Column(Modifier.padding(14.dp),verticalArrangement=Arrangement.spacedBy(6.dp)) {
                    Text("Price ${flowNumber(data.price)} • Spread ${flowNumber(data.spread)}")
                    Text("Open interest ${flowNumber(data.oi)}")
                    Text("Order book imbalance ${data.depthImbalance?.let { flowNumber(it*100)+" percent" } ?: "Unavailable"}")
                    Text("Estimated CVD since connection: ${flowNumber(data.estimatedCvd)}")
                    Text("Started ${flowTime(data.startedAt)} IST. Resting orders are not executed trades.")
                } } }
                item { Text("Five level market depth",style=MaterialTheme.typography.titleMedium) }
                item { Row(Modifier.fillMaxWidth()) { Text("BID / Quantity",Modifier.weight(1f));Text("ASK / Quantity",Modifier.weight(1f)) } }
                items(5) { i ->
                    val bid=data.bids.getOrNull(i);val ask=data.asks.getOrNull(i)
                    Row(Modifier.fillMaxWidth()) {
                        Text(if(bid==null) "Unavailable" else "${flowNumber(bid.price)} / ${flowNumber(bid.quantity)}",Modifier.weight(1f))
                        Text(if(ask==null) "Unavailable" else "${flowNumber(ask.price)} / ${flowNumber(ask.quantity)}",Modifier.weight(1f))
                    }
                }
                item { Text("Observed footprint • estimated sides",style=MaterialTheme.typography.titleMedium) }
                item { Text(data.note) }
                if(data.bars.isEmpty()) item { Text("Waiting for fresh volume changes. Market closure, missing feed or no trades can leave this view empty.") }
                items(data.bars.reversed(),key={it.time}) { bar ->
                    Card(Modifier.fillMaxWidth()) { Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(6.dp)) {
                        Text("${flowTime(bar.time)} IST • Estimated delta ${flowNumber(bar.delta)}",style=MaterialTheme.typography.titleSmall)
                        Text("Buy ${flowNumber(bar.buy)} • Sell ${flowNumber(bar.sell)} • Unknown side ${flowNumber(bar.unknown)}")
                        Text("Unallocated volume ${flowNumber(bar.unallocated)}. This volume has no reliable execution price or side.")
                        Row(Modifier.fillMaxWidth()) { listOf("Price","Sell est.","Buy est.","Unknown").forEach { Text(it,Modifier.weight(1f)) } }
                        bar.levels.take(30).forEach { row -> Row(Modifier.fillMaxWidth()) {
                            listOf(row.price,row.sell,row.buy,row.unknown).forEach { Text(flowNumber(it),Modifier.weight(1f),style=MaterialTheme.typography.bodySmall) }
                        } }
                        if(bar.levels.size>30)Text("Showing highest 30 price levels.")
                    } }
                }
            }
        }
    }
}
