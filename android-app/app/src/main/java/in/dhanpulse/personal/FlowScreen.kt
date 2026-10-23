package `in`.dhanpulse.personal

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
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

data class FlowInstrument(val token:String, val exchange:String, val symbol:String, val kind:String,
    val underlying:String="",val expiry:String="",val strike:Double?=null)
data class FlowCatalog(val items:List<FlowInstrument> = emptyList(),val roots:List<String> = emptyList(),
    val kinds:List<String> = emptyList(),val expiries:List<String> = emptyList(),
    val total:Int=0,val hasMore:Boolean=false)
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
    val keyboard=LocalSoftwareKeyboardController.current
    var query by remember { mutableStateOf("") }
    var underlying by remember { mutableStateOf("") }
    var kind by remember { mutableStateOf("") }
    var expiry by remember { mutableStateOf("") }
    var page by remember { mutableIntStateOf(0) }
    var rootsShown by remember { mutableIntStateOf(40) }
    var catalogue by remember { mutableStateOf(FlowCatalog()) }
    var retryCatalogue by remember { mutableIntStateOf(0) }
    var recent by remember { mutableStateOf(emptyList<String>()) }
    var choices by remember { mutableStateOf(emptyList<FlowInstrument>()) }
    var selected by remember { mutableStateOf<FlowInstrument?>(null) }
    var minutes by remember { mutableIntStateOf(5) }
    var restart by remember { mutableIntStateOf(0) }
    var snapshot by remember { mutableStateOf<FlowSnapshot?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var catalogError by remember { mutableStateOf<String?>(null) }
    var searching by remember { mutableStateOf(false) }
    var showContracts by remember { mutableStateOf(true) }
    val listState=rememberLazyListState()
    LaunchedEffect(underlying,page,showContracts) { listState.scrollToItem(0) }
    LaunchedEffect(group,query,underlying,kind,expiry,page,retryCatalogue,sessionId) {
        searching=true;catalogError=null;choices=emptyList();delay(300)
        try { catalogue=api.flowCatalog(sessionId,group,query,underlying=underlying,kind=kind,expiry=expiry,offset=page*40);choices=catalogue.items }
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
    LazyColumn(Modifier.fillMaxSize(),state=listState,contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        item { Text("Footprint & Order Flow",style=MaterialTheme.typography.headlineSmall) }
        item { Text("Choose a market, then a name and contract. Index flow uses traded futures or options. Quick choices are navigation shortcuts, not trade recommendations.",style=MaterialTheme.typography.bodySmall) }
        item { Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
            listOf("INDEX" to "Indices","STOCKS" to "Shares","STOCK_OPTIONS" to "Stock options","MCX" to "MCX").forEach { (key,label) ->
                FilterChip(selected=group==key,onClick={group=key;selected=null;snapshot=null;showContracts=true;
                    query="";underlying="";kind="";expiry="";page=0;rootsShown=40;catalogue=FlowCatalog()},label={Text(label)})
            }
        } }
        if(selected!=null) item { OutlinedButton(onClick={showContracts=!showContracts},modifier=Modifier.fillMaxWidth()) {
            Text(if(showContracts) "Back to monitor: ${selected!!.symbol}" else "Change instrument or contract")
        } }
        if(showContracts) {
            if(underlying.isNotBlank()) item { Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                Text(underlying,style=MaterialTheme.typography.titleMedium)
                TextButton(onClick={underlying="";query="";kind="";expiry="";page=0}) { Text("Change name") }
            } }
            item { OutlinedTextField(value=query,onValueChange={query=it;page=0;rootsShown=40},
                label={Text(if(underlying.isBlank()) "Search stock or index name" else "Search strike or contract")},
                placeholder={Text(if(underlying.isBlank()) "Example: SENSEX, INFY, CRUDEOIL" else "Type the strike price")},
                trailingIcon={if(query.isNotEmpty()) TextButton(onClick={query="";page=0;rootsShown=40}){Text("Clear")}},
                singleLine=true,modifier=Modifier.fillMaxWidth()) }
            if(searching) item { LinearProgressIndicator(Modifier.fillMaxWidth()) }
            catalogError?.let { message -> item { Text(message,color=MaterialTheme.colorScheme.error)
                OutlinedButton(onClick={retryCatalogue++}){Text("Retry search")} } }
            if(!searching && catalogError==null && underlying.isBlank()) {
                val quick=(recent+when(group){
                    "INDEX"->listOf("NIFTY","BANKNIFTY","SENSEX","FINNIFTY","MIDCPNIFTY")
                    "MCX"->listOf("CRUDEOIL","NATURALGAS","GOLD","SILVER")
                    else->listOf("RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK")
                }).distinct().filter { it in catalogue.roots }
                if(query.isBlank()) {
                    item { Text("Quick choices",style=MaterialTheme.typography.titleSmall) }
                    items(quick.chunked(2)) { names -> Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                        names.forEach { name -> OutlinedButton(onClick={underlying=name;query="";kind="";expiry="";page=0;keyboard?.hide()},modifier=Modifier.weight(1f).heightIn(min=48.dp)) {Text(name)} }
                    } }
                }
                item { Text("${catalogue.roots.size} available names. Tap one to see its contracts.") }
                if(catalogue.roots.isEmpty()) item { Text("No names found. Try a shorter symbol or choose another market.") }
                items(catalogue.roots.take(rootsShown),key={"root:$it"}) { name ->
                    OutlinedButton(onClick={underlying=name;query="";kind="";expiry="";page=0;keyboard?.hide()},modifier=Modifier.fillMaxWidth().heightIn(min=48.dp)) {Text(name)}
                }
                if(rootsShown<catalogue.roots.size) item { OutlinedButton(onClick={rootsShown+=40},modifier=Modifier.fillMaxWidth()){Text("Show more names")} }
            }
            if(underlying.isNotBlank()) {
                item { Text("Contract type",style=MaterialTheme.typography.titleSmall)
                    Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                        (listOf("")+catalogue.kinds).forEach { type -> FilterChip(selected=kind==type,onClick={kind=type;expiry="";page=0},label={Text(when(type){"FUT"->"Futures";"CE"->"Call CE";"PE"->"Put PE";"CASH"->"Shares";else->"All"})}) }
                    }
                }
                if(catalogue.expiries.isNotEmpty()) item { Text("Expiry",style=MaterialTheme.typography.titleSmall)
                    Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                        (listOf("")+catalogue.expiries).forEach { date -> FilterChip(selected=expiry==date,onClick={expiry=date;page=0},label={Text(date.ifBlank { "All expiries" })}) }
                    }
                }
                if(!searching && catalogError==null) item { Text(if(choices.isEmpty()) "No matching contracts. Clear the search or change the filters." else "${catalogue.total} contracts. Showing ${page*40+1} to ${page*40+choices.size}. Tap to monitor.") }
            }
            items(choices,key={it.exchange+it.token}) { instrument ->
                OutlinedButton(onClick={selected=instrument;showContracts=false;keyboard?.hide();recent=(listOf(underlying)+recent).distinct().take(6)},modifier=Modifier.fillMaxWidth().heightIn(min=56.dp)) {
                    Column(Modifier.fillMaxWidth()) {
                        Text(instrument.symbol,style=MaterialTheme.typography.titleSmall)
                        Text("${instrument.exchange} • ${instrument.kind}"+if(instrument.expiry.isNotBlank()) " • ${instrument.expiry}" else "",style=MaterialTheme.typography.bodySmall)
                        instrument.strike?.let { Text("Strike ${flowNumber(it)}",style=MaterialTheme.typography.bodySmall) }
                    }
                }
            }
            if(underlying.isNotBlank() && !searching && catalogError==null) item { Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                OutlinedButton(onClick={page--},enabled=page>0){Text("Previous")}
                OutlinedButton(onClick={page++},enabled=catalogue.hasMore){Text("Next contracts")}
            } }
        }
        if(selected!=null && !showContracts) {
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
