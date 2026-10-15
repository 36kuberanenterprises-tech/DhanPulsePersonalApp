import test from 'node:test';
import assert from 'node:assert/strict';
import { createSensexCoordinator } from '../src/sensex-systems.js';
const now=Date.parse('2026-10-15T05:00:30Z');
const decision=(direction='WAIT')=>({direction,setupAllowed:direction!=='WAIT',status:'CONFIRMED',autoEntryAllowed:true,message:direction});
const base=()=>({key:'secret-account-key',interval:'FIVE_MINUTE',now,candleTime:'2026-10-15T04:55:00Z',
  referenceClose:73000,spot:73005,atr:100,fresh:true,
  contracts:{CE:{token:'ce',ask:100,bid:99,ltp:100},PE:{token:'pe',ask:100,bid:99,ltp:100}},
  systems:[{id:'SYSTEM_1',name:'Families',decision:decision('CE')},{id:'SYSTEM_2',name:'Indicators',decision:decision()}]});
test('either system can qualify independently without waiting for the other',()=>{
  for(const index of [0,1]){
    const input=base();input.systems[0].decision=decision();input.systems[index].decision=decision('CE');
    const output=createSensexCoordinator()(input);
    assert.equal(output.decision.setupAllowed,true);
    assert.equal(output.decision.agreement,'SINGLE');
    assert.deepEqual(output.decision.sourceSystems,[`SYSTEM_${index+1}`]);
    assert.equal(output.decision.autoEntryAllowed,false);
    assert.ok(!output.callId.includes('secret-account-key'));
  }
});
test('later agreement preserves identity and entry levels rather than creating another entry',()=>{
  const combine=createSensexCoordinator(),input=base(),first=combine(input);
  input.systems[1].decision=decision('CE');input.now+=1000;
  const next=combine(input);
  assert.equal(next.decision.agreement,'ALIGNED');
  assert.equal(next.callId,first.callId);
  assert.equal(next.decision.systems[0].callId,next.decision.systems[1].callId);
  assert.deepEqual(next.decision.systems[0].plan,first.decision.systems[0].plan);
});
test('opposite qualified calls stay visible independently and aggregate automatic execution stays paused',()=>{
  const input=base();input.systems[1].decision=decision('PE');
  const output=createSensexCoordinator()(input);
  assert.equal(output.decision.agreement,'OPPOSITE');
  assert.equal(output.decision.direction,'WAIT');
  assert.equal(output.contract,null);
  assert.equal(output.decision.systems.filter(s=>s.decision.setupAllowed).length,2);
  assert.equal(output.decision.autoEntryAllowed,false);
});
test('extended price, stale setup or missing data cannot create an entry',()=>{
  for(const change of [{spot:73050},{now:now+600_000},{fresh:false}]){
    const output=createSensexCoordinator()({...base(),...change});
    assert.equal(output.decision.setupAllowed,false);
  }
});
test('premium chase and insufficient remaining reward invalidate an entry until a fresh candle',()=>{
  const combine=createSensexCoordinator(),input=base();combine(input);
  input.contracts.CE={token:'ce',ask:105,bid:104,ltp:105};
  const missed=combine(input);
  assert.equal(missed.decision.status,'ENTRY_MISSED');
  assert.equal(missed.decision.setupAllowed,false);
  input.contracts.CE={token:'ce',ask:100,bid:99,ltp:100};
  assert.equal(combine(input).decision.setupAllowed,false);
});
