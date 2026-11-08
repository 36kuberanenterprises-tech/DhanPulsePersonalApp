import test from 'node:test';
import assert from 'node:assert/strict';
import { capacityGate } from '../src/request-capacity.js';

test('bounded heavy work frees its slot once and rejects excess workload', () => {
  const gate = capacityGate(2);
  const first = gate.acquire(), second = gate.acquire();
  assert.equal(gate.active, 2);
  assert.equal(gate.acquire(), null);
  first();
  assert.equal(gate.active, 1);
  first();
  assert.equal(gate.active, 1);
  const third = gate.acquire();
  assert.equal(typeof third, 'function');
  second(); third();
  assert.equal(gate.active, 0);
});
test('invalid capacity is rejected', () => {
  assert.throws(() => capacityGate(0));
});
