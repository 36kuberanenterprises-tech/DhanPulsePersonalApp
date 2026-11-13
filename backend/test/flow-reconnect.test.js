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
