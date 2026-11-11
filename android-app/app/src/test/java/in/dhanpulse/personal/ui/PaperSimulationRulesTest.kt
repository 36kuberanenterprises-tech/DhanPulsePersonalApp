package `in`.dhanpulse.personal.ui

import `in`.dhanpulse.personal.model.PaperStockTrade
import `in`.dhanpulse.personal.model.StockCandidate
import `in`.dhanpulse.personal.model.StockPlan
import `in`.dhanpulse.personal.model.StockQuote
import `in`.dhanpulse.personal.model.StockScanResponse
import org.junit.Assert.*
import org.junit.Test
import java.time.Instant

class PaperSimulationRulesTest {
    private val now=Instant.parse("2026-11-11T05:00:30Z").toEpochMilli() // 10:30 IST
    private val ready=StockCandidate(
        symbol="TEST",token="12345",price=100.0,status="READY",side="BUY",setup="FIVE_MINUTE",
        plan=StockPlan(entry=100.0,stop=98.0,target1=102.0,target2=104.0,
            quantity=5,estimatedLoss=12.0,estimatedCosts=2.0))
    private fun scan(candidate:StockCandidate=ready,at:Long=now,market:String="SCANNING") =
        StockScanResponse(timestamp=Instant.ofEpochMilli(at).toString(),marketStatus=market,
            candidates=listOf(candidate))

    @Test fun validFreshQualifiedCrossingIsEligible() {
        assertEquals("TEST", PaperSimulationRules.selectAutoEntry(scan(),now,emptySet())?.symbol)
    }

    @Test fun staleClosedAndUnconfirmedQuotesMustNotEnter() {
        assertNull(PaperSimulationRules.selectAutoEntry(scan(at=now-46_000),now,emptySet()))
        assertNull(PaperSimulationRules.selectAutoEntry(scan(market="DATA_STALE"),now,emptySet()))
        assertNull(PaperSimulationRules.selectAutoEntry(scan(candidate=ready.copy(status="WAIT")),now,emptySet()))
        assertNull(PaperSimulationRules.selectAutoEntry(scan(candidate=ready.copy(plan=null)),now,emptySet()))
        assertNull(PaperSimulationRules.selectAutoEntry(scan(),now,setOf("TEST|BUY")))
        assertNull(PaperSimulationRules.selectAutoEntry(scan(),Instant.parse("2026-11-11T11:00:00Z").toEpochMilli(),emptySet()))
    }

    @Test fun entryPriceMustCrossAndBeCloseToPlannedPrice() {
        assertNull(PaperSimulationRules.selectAutoEntry(scan(ready.copy(price=99.99)),now,emptySet()))
        assertNull(PaperSimulationRules.selectAutoEntry(scan(ready.copy(price=102.0)),now,emptySet()))
        assertNull(PaperSimulationRules.selectAutoEntry(scan(ready.copy(token="")),now,emptySet()))
        assertEquals("TEST",PaperSimulationRules.selectAutoEntry(scan(ready.copy(
            side="SELL",price=100.0,
            plan=ready.plan?.copy(stop=102.0))),now,emptySet())?.symbol)
    }

    @Test fun sampledQuoteMayTriggerSimulatedExitButNeverMissingOrOldQuote() {
        val trade=PaperStockTrade(now,"TEST","12345","BUY","SCAN",now,100.0,98.0,
            102.0,104.0,5,2.0,12.0)
        assertEquals("Stop crossed on sampled quote",PaperSimulationRules.autoExitAtObservedQuote(
            trade,StockQuote("12345",97.5,fresh=true),scan(),now)?.second)
        assertEquals("Target 2 crossed on sampled quote",PaperSimulationRules.autoExitAtObservedQuote(
            trade,StockQuote("12345",104.25,fresh=true),scan(),now)?.second)
        assertNull(PaperSimulationRules.autoExitAtObservedQuote(
            trade,StockQuote("12345",103.0,fresh=true),scan(),now))
        assertNull(PaperSimulationRules.autoExitAtObservedQuote(
            trade,StockQuote("12345",104.25,fresh=false),scan(),now))
        assertNull(PaperSimulationRules.autoExitAtObservedQuote(
            trade,StockQuote("12345",104.25,fresh=true),scan(at=now-60_000),now))
        assertNull(PaperSimulationRules.autoExitAtObservedQuote(
            trade,StockQuote("WRONG",104.25,fresh=true),scan(),now))
    }
}
