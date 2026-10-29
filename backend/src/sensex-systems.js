// Independent system decisions share an entry identity, not an approval vote.
export function createSensexCoordinator() {
  const entries = new Map();
  return function combine({ key, systems, contracts, spot, atr, referenceClose, candleTime, interval,
    now = Date.now(), fresh = true }) {
    for (const [id,value] of entries) if (now-value.at > 86_400_000) entries.delete(id);
    const round = x => Math.round(x*20)/20;
    const results = systems.map(system => {
      const decision = { ...system.decision, autoEntryAllowed:false };
      const contract = contracts[decision.direction];
      let plan = null, callId = null;
      if (!fresh) Object.assign(decision,{direction:'WAIT',setupAllowed:false,status:'DATA_STALE',message:'Fresh broker candles and quotes are required.'});
      if (decision.setupAllowed && !contract) Object.assign(decision,{direction:'WAIT',setupAllowed:false,
        status:'NO_CONTRACT',message:'No eligible option contract is available for this direction.'});
      if (decision.setupAllowed && contract) {
        const direction = decision.direction, sign = direction === 'CE' ? 1 : -1;
        const id = [interval,candleTime,direction,contract.token].join('|');
        const storageId = JSON.stringify([key,id]);
        let entry = entries.get(storageId);
        const ask = Number(contract.ask), bid = Number(contract.bid);
        const extension = sign*(spot-referenceClose);
        const age = now-Date.parse(candleTime);
        const durations = {ONE_MINUTE:60_000,THREE_MINUTE:180_000,FIVE_MINUTE:300_000,TEN_MINUTE:600_000,FIFTEEN_MINUTE:900_000};
        const tooLate = !Number.isFinite(extension) || !(atr>0) || Math.abs(extension) > atr*0.35 ||
          !Number.isFinite(age) || age > (durations[interval] || 300_000)*2+20_000;
        if (!entry && !tooLate && ask>0 && bid>0) {
          // Fixed research premium levels. They are not exchange fills or
          // a forecast; execution costs still vary by broker and quantity.
          const stop = round(ask*0.92), target1=round(ask*1.12), target2=round(ask*1.20), target3=round(ask*1.30);
          entry={at:now,entry:round(ask),stop,target1,target2,target3,missed:false};
          entries.set(storageId,entry);
        }
        const spread = ask-bid;
        const netRisk = entry ? ask-entry.stop+spread : NaN;
        const netReward = entry ? entry.target2-ask-spread : NaN;
        const rr = netRisk>0 ? netReward/netRisk : 0;
        const missed = tooLate || !entry || entry.missed || ask>entry.entry*1.02 ||
          ask<=entry.stop || !Number.isFinite(rr) || rr<1.5;
        if (entry && missed) entry.missed=true;
        callId=id;
        if (entry) plan={ entry:entry.entry, entryMax:round(entry.entry*1.02), stopLoss:entry.stop,
          target1:entry.target1,target2:entry.target2,target3:entry.target3,remainingRr:Math.round(rr*100)/100 };
        if (missed) Object.assign(decision,{setupAllowed:false,status:'ENTRY_MISSED',message:'Entry missed: price extension, premium or remaining reward relative to risk is outside the entry limits. Wait for a fresh candle setup.'});
      }
      if (decision.setupAllowed) decision.message = `${system.name} qualified independently. Use the fixed entry zone; missed entries are not chased.`;
      return { id:system.id, name:system.name, decision, contract:fresh ? contract || null : null, plan, callId };
    });
    const ready=results.filter(s=>s.decision.setupAllowed);
    const opposite=new Set(ready.map(s=>s.decision.direction)).size>1;
    const aligned=ready.length===2 && !opposite;
    const chosen=ready[0] || results.find(s=>s.decision.status==='ENTRY_MISSED') || results[0];
    const decision={...chosen.decision,autoEntryAllowed:false,sourceSystems:ready.map(s=>s.id),
      agreement:opposite?'OPPOSITE':aligned?'ALIGNED':ready.length?'SINGLE':'WAIT',
      systems:results,
      message:opposite?'Opposite independent calls. Review each system; automatic execution is paused.':
        aligned?'Both systems aligned. Additional confirmation, not a measured win probability.':chosen.decision.message };
    if (opposite) Object.assign(decision,{direction:'WAIT',setupAllowed:false,status:'SYSTEM_CONFLICT'});
    return {decision,contract:opposite?null:chosen.contract,callId:opposite?null:chosen.callId};
  };
}
export const combineSensexSystems=createSensexCoordinator();
