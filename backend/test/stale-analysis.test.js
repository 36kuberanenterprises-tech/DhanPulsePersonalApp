import test from 'node:test';
import assert from 'node:assert/strict';
import { staleAnalysis } from '../src/stale-analysis.js';
import { createSensexCoordinator } from '../src/sensex-systems.js';
test('failed refresh clears both system plans and preserves the cached snapshot',()=>{
 const original={signal:'CE',dataFresh:true,spot:72000,suggestedContract:{token:'1'},levels:{entry:100},tradeDecision:{
 direction:'CE',setupAllowed:true,agreement:'ALIGNED',sourceSystems:['1','2'],systems:['1','2'].map(id=>({id,
 decision:{direction:'CE',setupAllowed:true},contract:{token:'1'},plan:{entry:100},callId:'old'}))}};
 const result=staleAnalysis(original);
 assert.equal(result.signal,'WAIT');assert.equal(result.spot,72000);
 assert.equal(result.levels,null);assert.equal(result.suggestedContract,null);
 assert.equal(result.tradeDecision.agreement,'WAIT');assert.deepEqual(result.tradeDecision.sourceSystems,[]);
 for(const s of result.tradeDecision.systems){assert.equal(s.decision.setupAllowed,false);assert.equal(s.decision.direction,'WAIT');assert.equal(s.plan,null);assert.equal(s.contract,null);assert.equal(s.callId,null);}
 assert.equal(original.tradeDecision.systems[0].decision.setupAllowed,true);
});
test('a strategy without an eligible option contract cannot qualify',()=>{
 const r=createSensexCoordinator()({key:'test',interval:'FIVE_MINUTE',contracts:{},systems:[{id:'1',name:'Families',decision:{direction:'CE',setupAllowed:true}}]});
 assert.equal(r.decision.setupAllowed,false);assert.equal(r.decision.direction,'WAIT');assert.equal(r.decision.status,'NO_CONTRACT');assert.equal(r.contract,null);
});
