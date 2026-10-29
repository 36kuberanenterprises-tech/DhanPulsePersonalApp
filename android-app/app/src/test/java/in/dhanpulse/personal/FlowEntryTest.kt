package `in`.dhanpulse.personal

import `in`.dhanpulse.personal.model.*
import java.time.Instant
import org.junit.Assert.*
import org.junit.Test

class FlowEntryTest {
    private val now=Instant.parse("2026-10-29T05:00:00Z")
    private val contract=OptionContract(token="123",exchange="MCX",tradingSymbol="TESTCE")
    private val analysis=AnalysisResponse(symbol="NATURALGAS",timestamp=now.toString(),timeframe="FIVE_MINUTE",dataFresh=true,
        suggestedContract=contract,tradeDecision=TradeDecision(direction="CE",setupAllowed=true))
    private val plan=PremiumTradePlan(signal="CE",contract=contract,status="WAITING_ENTRY",entry=100.0,stopLoss=90.0,target1=110.0,target2=120.0,target3=130.0)
    private fun valid(a:AnalysisResponse=analysis,p:PremiumTradePlan=plan,time:Instant=now)=
        validFlowEntry(a,p,"NATURALGAS","FIVE_MINUTE",true,true,time)
    @Test fun currentQualifiedPlanIsEligible() { assertTrue(valid()) }
    @Test fun staleAndFutureAnalysisAreRejected() {
        assertFalse(valid(a=analysis.copy(timestamp=now.minusSeconds(46).toString())))
        assertFalse(valid(a=analysis.copy(timestamp=now.plusSeconds(5).toString())))
    }
    @Test fun wrongInstrumentTimeframeAndExchangeAreRejected() {
        assertFalse(valid(a=analysis.copy(symbol="NIFTY")))
        assertFalse(valid(a=analysis.copy(timeframe="ONE_MINUTE")))
        assertFalse(valid(p=plan.copy(contract=contract.copy(exchange="NFO"))))
    }
    @Test fun invalidLevelsAndConflictingDirectionAreRejected() {
        assertFalse(valid(p=plan.copy(stopLoss=101.0)))
        assertFalse(valid(p=plan.copy(target2=Double.NaN)))
        assertFalse(valid(p=plan.copy(target3=105.0)))
        assertFalse(valid(p=plan.copy(signal="PE")))
    }
    @Test fun existingEntryIsNotANewEntry() { assertFalse(valid(p=plan.copy(status="ENTERED"))) }
    @Test fun cutoffIsExclusiveAndOpeningInclusive() {
        val open=Instant.parse("2026-10-29T04:00:00Z")
        val cutoff=Instant.parse("2026-10-29T17:45:00Z")
        assertTrue(valid(a=analysis.copy(timestamp=open.toString()),time=open))
        assertFalse(valid(a=analysis.copy(timestamp=cutoff.toString()),time=cutoff))
        assertTrue(valid(a=analysis.copy(timestamp=cutoff.minusSeconds(1).toString()),time=cutoff.minusSeconds(1)))
    }
}
