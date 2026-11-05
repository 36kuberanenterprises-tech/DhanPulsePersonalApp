import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluateMoverQuote, parseNifty500Csv, moverMarketBreadth, moversMarketOpen, selectRotatingBrokerUniverse } from '../src/live-movers.js';

const now=Date.parse('2026-11-05T05:13:10Z'); // 10:43:10 IST
function fullQuote(override={}){
 return {
  exchFeedTime:'05-Nov-2026 10:43:04',ltp:170.93,close:155.0,
  open:163.8,high:171.24,low:163.2,tradeVolume:1_200_000,
  upperCircuit:190,
  depth:{buy:[{price:170.90}],sell:[{price:170.95}]},
  ...override
 };
}
const example={symbol:'ASHOKLEY',sector:'Automobiles',instrument:{token:'999'}};
test('an Ashok Leyland style opening gap and strong follow-through is identified from FULL quote without candles',()=>{
 const row=evaluateMoverQuote(example,fullQuote(),now);
 assert.ok(row);
 assert.equal(row.symbol,'ASHOKLEY');
 assert.equal(row.pattern,'GAP_CONTINUATION');
 assert.ok(row.changePct>10);
 assert.ok(row.fromOpenPct>4);
 assert.equal(row.status,'WATCH_CAUTION'); // extended opening move must not be presented as safe entry
 assert.match(row.note,/WATCH ONLY/);
 assert.equal(row.quoteTime,'2026-11-05T05:13:04.000Z');
});
test('a gap that fades back to the opening price does not become an intraday momentum alert',()=>{
 assert.equal(evaluateMoverQuote(example,fullQuote({ltp:163.5,open:164,high:170}),now),null);
});
test('a stale feed is excluded even if quote percent change is high',()=>{
 assert.equal(evaluateMoverQuote(example,fullQuote({exchFeedTime:'05-Nov-2026 10:41:00'}),now),null);
});
test('a quote without executable depth is shown with review warning instead of a confirmed setup',()=>{
 const row=evaluateMoverQuote(example,fullQuote({depth:null}),now);
 assert.ok(row);
 assert.equal(row.status,'WATCH_CAUTION');
 assert.match(row.warnings.join(' '),/spread not available/);
});
test('strong intraday momentum is detected without an opening gap',()=>{
 const row=evaluateMoverQuote(example,fullQuote({ltp:105,open:102,close:102,high:105.4,upperCircuit:115,
   depth:{buy:[{price:104.95}],sell:[{price:105.02}]}}),now);
 assert.ok(row);
 assert.equal(row.pattern,'INTRADAY_MOMENTUM');
});
test('only validated NSE 500 constituent files are allowed',()=>{
 const lines=['Company Name,Industry,Symbol','"First, Limited",Automobile,ASHOKLEY'];
 for(let i=0;i<499;i++)lines.push('Example '+i+',Services,XYZ'+i);
 const result=parseNifty500Csv(lines.join('\n'));
 assert.equal(result.length,500);
 assert.ok(result.some(r=>r.symbol==='ASHOKLEY'));
 assert.throws(()=>parseNifty500Csv('Symbol,Industry\nA,Auto'),/failed constituent count/);
});
test('market breadth distinguishes advances and declines in the scanned quotes',()=>{
 const breadth=moverMarketBreadth([
  {sector:'Auto',pct:5},{sector:'Auto',pct:3},{sector:'Auto',pct:-1},
  {sector:'Banks',pct:2},{sector:'Banks',pct:-2},{sector:'Banks',pct:0}
 ]);
 assert.equal(breadth.scanned,6);
 assert.equal(breadth.advancers,3);
 assert.equal(breadth.decliners,2);
 assert.equal(breadth.sectorBreadth.length,2);
});
test('scan is only allowed during NSE cash hours in IST',()=>{
 assert.equal(moversMarketOpen(new Date('2026-11-05T03:44:00Z')),false);
 assert.equal(moversMarketOpen(new Date('2026-11-05T03:46:00Z')),true);
 assert.equal(moversMarketOpen(new Date('2026-11-05T10:00:00Z')),false);
});

test('broker EQ fallback is broad, rotates and always includes ASHOKLEY when available',()=>{
  const master=[{exch_seg:'NSE',symbol:'ASHOKLEY-EQ'}];
  for(let i=0;i<1100;i++)master.push({exch_seg:'NSE',symbol:'EQ'+String(i).padStart(4,'0')+'-EQ'});
  const priority=[{symbol:'ASHOKLEY',sector:'Automobiles'},{symbol:'EQ0000',sector:'Services'}];
  const a=selectRotatingBrokerUniverse(master,priority,new Date('2026-11-05T03:47:00Z'),500);
  const b=selectRotatingBrokerUniverse(master,priority,new Date('2026-11-05T03:49:00Z'),500);
  assert.equal(a.length,500);
  assert.ok(a.some(row=>row.symbol==='ASHOKLEY'));
  assert.ok(b.some(row=>row.symbol==='ASHOKLEY'));
  assert.ok(a.some(row=>row.symbol==='EQ0000'));
  assert.notDeepEqual(a,b);
  assert.ok(a.every(row=>row.symbol==='ASHOKLEY'||row.symbol.startsWith('EQ')));
});
