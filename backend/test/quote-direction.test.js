import test from 'node:test';
import assert from 'node:assert/strict';
import { quoteDirection } from '../src/quote-direction.js';

test('fresh price above both references is observational upward movement, not a call', () => {
  const x=quoteDirection({open:100,close:99},101,1000);
  assert.equal(x.status,'UP'); assert.equal(x.tradeCall,false);
  assert.equal(x.vsOpenPct,1);
});
test('fresh price below both references is observational downward movement', () => {
  const x=quoteDirection({open:100,close:101},98,1000);
  assert.equal(x.status,'DOWN'); assert.equal(x.tradeCall,false);
});
test('conflicting comparisons or tiny changes cannot declare strong direction', () => {
  assert.equal(quoteDirection({open:100,close:98},99,1000).status,'MIXED');
  assert.equal(quoteDirection({open:100,close:100},100.02,1000).status,'MIXED');
});
test('stale quote or missing references never declares a direction', () => {
  assert.equal(quoteDirection({open:100,close:99},101,46_000).status,'UNVERIFIED');
  assert.equal(quoteDirection({open:0,close:99},101,1000).status,'UNVERIFIED');
  assert.equal(quoteDirection({open:100,close:99},101,null).status,'UNVERIFIED');
});
