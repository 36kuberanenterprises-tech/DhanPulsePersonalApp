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
import `in`.dhanpulse.personal.ui.DhanPulseViewModel
import `in`.dhanpulse.personal.model.AnalysisResponse
import `in`.dhanpulse.personal.model.PremiumTradePlan
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

private fun friendlyName(name:String)=when(name) {
    "NATURALGAS" -> "Natural Gas"; "NATGASMINI" -> "Natural Gas Mini"
    "CRUDEOIL" -> "Crude Oil"; "CRUDEOILM" -> "Crude Oil Mini"
    "NIFTY" -> "Nifty 50"; "BANKNIFTY" -> "Bank Nifty"; "SENSEX" -> "Sensex"
    "FINNIFTY" -> "Fin Nifty"; "MIDCPNIFTY" -> "Midcap Nifty"
    else -> name
}
private fun friendlyExpiry(value:String)=runCatching {
    java.time.LocalDate.parse(value,java.time.format.DateTimeFormatterBuilder().parseCaseInsensitive().appendPattern("ddMMMyyyy").toFormatter(Locale.ENGLISH)).format(DateTimeFormatter.ofPattern("dd MMM yyyy",Locale.ENGLISH))
}.getOrDefault(value)
private fun friendlyContract(i:FlowInstrument):String {
    val type=when { i.symbol.endsWith("CE") -> "Call option"; i.symbol.endsWith("PE") -> "Put option"; i.kind.startsWith("FUT") -> "Futures"; else -> "Shares" }
    return friendlyName(i.underlying.ifBlank { i.symbol })+" • "+type+(i.strike?.let { " • "+flowNumber(it) } ?: "")
}

private fun timeframeLabel(value:String)=when(value) { "ONE_MINUTE"->"1m";"THREE_MINUTE"->"3m";"FIVE_MINUTE"->"5m";"TEN_MINUTE"->"10m";"FIFTEEN_MINUTE"->"15m";else->value }
private fun entryWindowMessage(mcx:Boolean, now:Instant):String? {
    val time=now.atZone(ZoneId.of("Asia/Kolkata")).toLocalTime()
    val start=java.time.LocalTime.of(9,30)
    val end=if(mcx) java.time.LocalTime.of(23,15) else java.time.LocalTime.of(15,30)
    return when {
        time.isBefore(start) -> "New entries start at 09:30 IST, subject to fresh data and strategy confirmation."
        !time.isBefore(end) -> "New entries paused after ${if(mcx) "23:15" else "15:30"} IST by the app's entry rule. Live quotes may continue. Review existing positions separately."
        else -> null
    }
}
private fun analysisRecent(timestamp:String?, now:Instant):Boolean=runCatching {
    val age=java.time.Duration.between(Instant.parse(timestamp),now).seconds
    age in 0..45
}.getOrDefault(false)

internal fun validFlowEntry(a:AnalysisResponse?, plan:PremiumTradePlan, root:String,
    interval:String, supported:Boolean, mcx:Boolean, now:Instant):Boolean {
    if(!supported || a==null || a.symbol!=root || a.timeframe!=interval || a.dataFresh!=true ||
        !analysisRecent(a.timestamp,now) || entryWindowMessage(mcx,now)!=null || !a.tradeDecision.setupAllowed) return false
    val contract=plan.contract ?: return false
    if(contract.token.isNullOrBlank() || contract.exchange.isNullOrBlank() || contract.tradingSymbol.isNullOrBlank() ||
        contract.token!=a.suggestedContract?.token || contract.exchange!=a.suggestedContract?.exchange ||
        plan.status!="WAITING_ENTRY" || plan.signal !in listOf("CE","PE") || plan.signal!=a.tradeDecision.direction) return false
    val entry=plan.entry ?: return false
    val stop=plan.stopLoss ?: return false
    val targets=listOf(plan.target1,plan.target2,plan.target3)
    return entry.isFinite() && entry>0 && stop.isFinite() && stop>0 && stop<entry &&
        targets.all { it!=null && it.isFinite() && it>entry } &&
        targets.zipWithNext().all { (left,right) -> left!!<right!! }
}

@Composable
fun FlowScreen(sessionId:String, vm:DhanPulseViewModel, onOpenPlan:()->Unit, onOpenScanner:()->Unit) {
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
    var choosing by remember { mutableStateOf(false) }
    var chooseRequest by remember { mutableIntStateOf(0) }
    var selectionNote by remember { mutableStateOf<String?>(null) }
    var now by remember { mutableStateOf(Instant.now()) }
    LaunchedEffect(owner) { owner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) { while(isActive) { now=Instant.now();delay(1000) } } }
    val supported=if(group=="INDEX") underlying in setOf("NIFTY","BANKNIFTY","SENSEX") else group=="MCX" &&
        (vm.mcxIndices.any { it.symbol==underlying } || vm.mcxEnergy.any { it.symbol==underlying })
    LaunchedEffect(group,underlying) {
        selected=null;snapshot=null;error=null;showContracts=true
    }
    LaunchedEffect(group,underlying,vm.mcxIndices.size,vm.mcxEnergy.size) {
        selectionNote=null
        if(underlying.isNotBlank() && group in listOf("INDEX","MCX")) {
            vm.showMarket(if(group=="MCX") "MCX" else "EQUITY")
            if(supported) vm.selectSymbol(underlying)
        }
    }
    LaunchedEffect(chooseRequest) {
        if(chooseRequest==0) return@LaunchedEffect
        val root=underlying;val marketGroup=group
        choosing=true;selectionNote=null
        try {
            val a=vm.analysis
            val c=if(vm.selectedSymbol==root && validFlowEntry(a,vm.premiumTradePlan,root,vm.selectedTimeframe,supported,marketGroup=="MCX",Instant.now())) a?.suggestedContract else null
            val result=if(c?.token!=null && c.exchange!=null && c.tradingSymbol!=null)
                FlowInstrument(c.token,c.exchange,c.tradingSymbol,"OPTION",root,a?.optionChain?.expiry ?: "",c.strike)
            else api.flowCatalog(sessionId,marketGroup,"",underlying=root,kind=if(marketGroup=="STOCKS") "CASH" else "FUT").items.firstOrNull()
            if(root==underlying && marketGroup==group) {
                if(result!=null) {selected=result;showContracts=false;keyboard?.hide();selectionNote=if(c!=null) "Showing the option selected by the current analysis." else "Showing the nearest available futures or share contract for observation. This is not a trade call."}
                else selectionNote="No automatic contract available. Choose a contract manually or use the stock scanner."
            }
        } catch(e:CancellationException){throw e}
        catch(e:Exception){selectionNote="Unable to select a contract now. Please try again."}
        finally {choosing=false}
    }
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
        item { Text("Market activity and trade guide",style=MaterialTheme.typography.headlineSmall) }
        if(showContracts) item { Text("1. Choose a market. 2. Tap a familiar name. 3. Use guided selection. The trade plan uses the existing strategy checks; order depth alone does not generate a call.",style=MaterialTheme.typography.bodySmall) }
        item { Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
            listOf("INDEX" to "Indices","STOCKS" to "Shares","STOCK_OPTIONS" to "Stock options","MCX" to "MCX").forEach { (key,label) ->
                FilterChip(selected=group==key,onClick={group=key;selected=null;snapshot=null;showContracts=true;
                    query="";underlying="";kind="";expiry="";page=0;rootsShown=40;catalogue=FlowCatalog()},label={Text(label)})
            }
        } }
        if(selected!=null) item { OutlinedButton(onClick={showContracts=!showContracts},modifier=Modifier.fillMaxWidth()) {
            Text(if(showContracts) "Back to ${friendlyName(selected!!.underlying)} activity" else "Choose another instrument")
        } }
        if(underlying.isNotBlank()) {
            item { Card(Modifier.fillMaxWidth()) { Column(Modifier.padding(14.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
                Text("Trade guide • ${friendlyName(underlying)}",style=MaterialTheme.typography.titleMedium)
                val a=vm.analysis
                val plan=vm.premiumTradePlan
                val matching=supported && a?.symbol==underlying && vm.selectedSymbol==underlying && a.timeframe==vm.selectedTimeframe
                val windowMessage=entryWindowMessage(group=="MCX",now)
                val recent=matching && analysisRecent(a?.timestamp,now)
                if(supported) Text("Analysis: ${timeframeLabel(vm.selectedTimeframe)} • ${if(recent) "Updated "+flowTime(a?.timestamp)+" IST" else "Waiting for current analysis"}",style=MaterialTheme.typography.bodySmall)
                val confirmed=matching && validFlowEntry(a,plan,underlying,vm.selectedTimeframe,supported,group=="MCX",now)
                if(confirmed) {
                    Text(if(plan.signal=="CE") "UPWARD • Buy Call (CE)" else "DOWNWARD • Buy Put (PE)",style=MaterialTheme.typography.titleLarge)
                    Text("Selected option: ${plan.contract?.tradingSymbol}")
                    Text("Option premium entry: ${flowNumber(plan.entry)}")
                    Text("Stop loss: ${flowNumber(plan.stopLoss)}")
                    Text("Target 1: ${flowNumber(plan.target1)}")
                    Text("Target 2: ${flowNumber(plan.target2)} • Target 3: ${flowNumber(plan.target3)}")
                    Text("These levels are for the option premium, not the futures price.",style=MaterialTheme.typography.bodySmall)
                    Text("Existing strategy selection for this instrument. Review the current price and entry conditions before acting.",style=MaterialTheme.typography.bodySmall)
                } else {
                    Text(if(windowMessage!=null && supported) "New entries paused" else "WAIT • No new confirmed entry",style=MaterialTheme.typography.titleMedium)
                    Text(if(group in listOf("STOCKS","STOCK_OPTIONS")) "Use the stock scanner to find a qualified stock and its trade levels." else if(!supported) "Activity monitoring is available. This instrument has no connected trade plan here." else if(windowMessage!=null) windowMessage else if(!matching) "Preparing analysis for this instrument and timeframe." else if(!recent || a?.dataFresh!=true) "Analysis is delayed or incomplete. Live depth alone cannot confirm an entry." else if(plan.status in listOf("ENTERED","T1_HIT","T2_HIT")) "An earlier call crossed its entry in sampled quotes. This is not a new entry or proof of a broker fill. Open the plan to manage or review it." else plan.decisionNote ?: a?.tradeDecision?.message?.ifBlank { "Waiting for fresh data and strategy confirmation." } ?: "Waiting for fresh data and strategy confirmation.")
                }
                if(supported) OutlinedButton(onClick=onOpenPlan,enabled=matching,modifier=Modifier.fillMaxWidth()) {Text(if(confirmed) "View entry, stop loss and targets" else "View strategy checks and existing plan")}
                if(group in listOf("STOCKS","STOCK_OPTIONS")) OutlinedButton(onClick=onOpenScanner,modifier=Modifier.fillMaxWidth()){Text("Find a stock with the scanner")}
                if(showContracts) Button(onClick={chooseRequest++},enabled=!choosing,modifier=Modifier.fillMaxWidth()) {Text(if(choosing) "Selecting..." else "Choose a contract for me")}
                selectionNote?.let { Text(it,style=MaterialTheme.typography.bodySmall) }
            } } }
        }
        if(showContracts) {
            if(underlying.isNotBlank()) item { Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                Text(friendlyName(underlying),style=MaterialTheme.typography.titleMedium)
                TextButton(onClick={underlying="";query="";kind="";expiry="";page=0}) { Text("Choose another") }
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
                    item { Text("Popular instruments",style=MaterialTheme.typography.titleSmall) }
                    items(quick.chunked(2)) { names -> Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                        names.forEach { name -> OutlinedButton(onClick={underlying=name;query="";kind="";expiry="";page=0;keyboard?.hide()},modifier=Modifier.weight(1f).heightIn(min=48.dp)) {Text(friendlyName(name))} }
                    } }
                }
                item { Text("${catalogue.roots.size} available names. Tap one to see its contracts.") }
                if(catalogue.roots.isEmpty()) item { Text("No names found. Try a shorter symbol or choose another market.") }
                items(catalogue.roots.take(rootsShown),key={"root:$it"}) { name ->
                    OutlinedButton(onClick={underlying=name;query="";kind="";expiry="";page=0;keyboard?.hide()},modifier=Modifier.fillMaxWidth().heightIn(min=48.dp)) {Text(friendlyName(name))}
                }
                if(rootsShown<catalogue.roots.size) item { OutlinedButton(onClick={rootsShown+=40},modifier=Modifier.fillMaxWidth()){Text("Show more names")} }
            }
            if(underlying.isNotBlank()) {
                item { Text("Manual selection • contract type",style=MaterialTheme.typography.titleSmall)
                    Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                        (listOf("")+catalogue.kinds).forEach { type -> FilterChip(selected=kind==type,onClick={kind=type;expiry="";page=0},label={Text(when(type){"FUT"->"Futures";"CE"->"Call CE";"PE"->"Put PE";"CASH"->"Shares";else->"All"})}) }
                    }
                }
                if(catalogue.expiries.isNotEmpty()) item { Text("Expiry",style=MaterialTheme.typography.titleSmall)
                    Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                        (listOf("")+catalogue.expiries).forEach { date -> FilterChip(selected=expiry==date,onClick={expiry=date;page=0},label={Text(if(date.isBlank()) "All expiries" else friendlyExpiry(date))}) }
                    }
                }
                if(!searching && catalogError==null) item { Text(if(choices.isEmpty()) "No matching contracts. Clear the search or change the filters." else "${catalogue.total} contracts. Showing ${page*40+1} to ${page*40+choices.size}. Tap to monitor.") }
            }
            items(choices,key={it.exchange+it.token}) { instrument ->
                OutlinedButton(onClick={selected=instrument;showContracts=false;keyboard?.hide();recent=(listOf(underlying)+recent).distinct().take(6)},modifier=Modifier.fillMaxWidth().heightIn(min=56.dp)) {
                    Column(Modifier.fillMaxWidth()) {
                        Text(friendlyContract(instrument),style=MaterialTheme.typography.titleSmall)
                        Text("${instrument.exchange} • ${instrument.kind}"+if(instrument.expiry.isNotBlank()) " • ${friendlyExpiry(instrument.expiry)}" else "",style=MaterialTheme.typography.bodySmall)
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
            item { Text("Monitoring: "+friendlyContract(selected!!),style=MaterialTheme.typography.titleMedium)
                Text(selected!!.symbol+if(selected!!.expiry.isNotBlank()) " • Expiry "+friendlyExpiry(selected!!.expiry) else "",style=MaterialTheme.typography.bodySmall)
                if(selected!!.kind.startsWith("FUT")) Text("Futures activity below; any option trade uses its own premium levels.",style=MaterialTheme.typography.bodySmall)
            }
            if(supported) item { Text("Trade analysis timeframe",style=MaterialTheme.typography.titleSmall)
                Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    listOf("ONE_MINUTE","THREE_MINUTE","FIVE_MINUTE","TEN_MINUTE","FIFTEEN_MINUTE").forEach { interval -> FilterChip(selected=vm.selectedTimeframe==interval,onClick={vm.selectTimeframe(interval)},label={Text(timeframeLabel(interval))}) }
                }
            }
            item { Text("Footprint grouping • independent of trade analysis",style=MaterialTheme.typography.titleSmall) }
            item { Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                listOf(1,3,5,10,15).forEach { m -> FilterChip(selected=minutes==m,onClick={minutes=m},label={Text("${m}m")}) }
            } }
            item { Text("Changing contract or footprint grouping restarts observation. Only volume received since connection is shown.") }
            item { OutlinedButton(onClick={restart++}){Text("Restart feed")} }
            error?.let { message -> item { Text(message,color=MaterialTheme.colorScheme.error) } }
            val data=snapshot
            val feedDelayed=error!=null || data?.error!=null || (data?.status=="LIVE" && !analysisRecent(data.lastTickAt,now))
            item { Text("${if(feedDelayed) "Updates delayed • showing last received snapshot" else when(data?.status){"LIVE"->"Live activity";"WAITING_FOR_FEED"->"Waiting for market updates";"STALE"->"Updates delayed";null->"Connecting";else->data.status.replace('_',' ')}} • Last update ${flowTime(data?.lastTickAt)} IST") }
            data?.error?.let { message -> item { Text(message,color=MaterialTheme.colorScheme.error) } }
            if(data!=null) {
                item { Card(Modifier.fillMaxWidth()) { Column(Modifier.padding(14.dp),verticalArrangement=Arrangement.spacedBy(6.dp)) {
                    Text("${if(feedDelayed) "Last received price" else "Price"} ${flowNumber(data.price)} • Spread ${flowNumber(data.spread)}")
                    Text("Open interest ${flowNumber(data.oi)}")
                    Text("Order book imbalance ${data.depthImbalance?.let { flowNumber(it*100)+" percent" } ?: "Unavailable"}")
                    val classified=data.bars.sumOf { it.buy.coerceAtLeast(0.0)+it.sell.coerceAtLeast(0.0) }
                    val total=classified+data.bars.sumOf { it.unknown.coerceAtLeast(0.0)+it.unallocated.coerceAtLeast(0.0) }
                    Text("Volume with estimated buy/sell side: ${if(total>0) flowNumber(classified/total*100)+"%" else "Not available"}")
                    Text("Estimated buy minus sell volume: ${flowNumber(data.estimatedCvd)}")
                    Text(if(total==0.0) "Collecting volume. No order flow conclusion yet." else "Coverage is the classified share of observed volume, not trade confidence. Unclassified volume can change the interpretation.",style=MaterialTheme.typography.bodySmall)
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
                        Text("${flowTime(bar.time)} IST • Observed portion only • Estimated delta ${flowNumber(bar.delta)}",style=MaterialTheme.typography.titleSmall)
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
