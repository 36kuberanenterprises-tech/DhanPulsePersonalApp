import test from 'node:test';
import assert from 'node:assert/strict';
import { flowReconnectDue } from '../src/flow-monitor.js';

test('Flow reconnect never restarts a currently connected stream', () => {
  assert.equal(flowReconnectDue({closed:false,closedAt:1000},200000),false);
  assert.equal(flowReconnectDue(null,20000),false);
  assert.equal(flowReconnectDue({closed:true,closedAt:null},20000),false);
});
test('Flow reconnect waits fifteen seconds after actual disconnection', () => {
  const state={closed:true,closedAt:10000};
  assert.equal(flowReconnectDue(state,24999),false);
  assert.equal(flowReconnectDue(state,25000),true);
});

test('Stale but open websocket recovers only during nominal exchange hours', () => {
  const now=Date.parse('2026-11-13T09:00:00Z'); // 14:30 IST
  const state={closed:false,exchange:'NFO',openedAt:now-120000,
    book:{previous:{receivedAt:now-45000}}};
  assert.equal(flowReconnectDue(state,now),true);
  assert.equal(flowReconnectDue({...state,openedAt:now-10000},now),false);
  assert.equal(flowReconnectDue({...state,book:{previous:{receivedAt:now-4000}}},now),false);
  assert.equal(flowReconnectDue(state,Date.parse('2026-11-13T12:00:00Z')),false);
});
