// Keep the old snapshot visible while invalidating every entry path.
export function staleAnalysis(value) {
  const pause = decision => ({ ...decision, direction:'WAIT', setupAllowed:false,
    autoEntryAllowed:false, status:'DATA_STALE', message:'Broker refresh failed. Calls are paused until fresh quotes arrive.',
    ...(decision?.systems ? {agreement:'WAIT',sourceSystems:[],systems:decision.systems.map(system=>({
      ...system,decision:pause(system.decision),contract:null,plan:null,callId:null
    }))} : {}) });
  return {...value,dataFresh:false,signal:'WAIT',suggestedContract:null,levels:null,
    tradeDecision:pause(value.tradeDecision),notes:[...(value.notes||[]),
      'Latest broker refresh was unavailable. Showing the last snapshot; all entry plans are paused.']};
}
