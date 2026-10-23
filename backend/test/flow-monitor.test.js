import test from 'node:test';
import assert from 'node:assert/strict';
import { FlowBook, parseFlowPacket, flowChoices, flowCatalogue } from '../src/flow-monitor.js';

test('snap quote parser decodes broker depth sides and rejects LTP only packets',()=>{
  const b=Buffer.alloc(379);b[0]=3;b[1]=2;b.write('12345',2);
  const put=(offset,value)=>b.writeBigInt64LE(BigInt(value),offset);
  put(27,99);put(35,Date.parse('2026-10-22T04:00:00Z'));put(43,10000);put(51,10);put(67,1000);put(131,500);
  b.writeUInt16LE(1,147);put(149,50);put(157,9900);
  b.writeUInt16LE(0,167);put(169,60);put(177,10100);
  const tick=parseFlowPacket(b);
  assert.equal(tick.price,100);assert.equal(tick.bids[0].price,99);assert.equal(tick.asks[0].price,101);
  assert.equal(tick.volume,1000);assert.equal(tick.oi,500);
  assert.equal(parseFlowPacket(b.subarray(0,51)),null);
  b[0]=1;assert.equal(parseFlowPacket(b),null);
});

const start=Date.parse('2026-10-22T04:00:00Z');
const tick=(sequence,volume,quantity,price=101,time=start+sequence*1000)=>({
  token:'123',exchangeType:2,sequence:String(sequence),volume,quantity,price,time,oi:500,
  bids:[{price:99,quantity:40}],asks:[{price:101,quantity:60}] });

test('footprint excludes baseline, duplicate and skipped executions; only preceding quotes classify observed volume',()=>{
  const book=new FlowBook();
  book.ingest(tick(1,1000,10),start+1000);
  assert.equal(book.snapshot(start+1000).bars.length,0);
  book.ingest(tick(2,1010,10),start+2000);
  book.ingest(tick(2,1010,10),start+2000);
  book.ingest(tick(3,1015,5,99),start+3000);
  book.ingest(tick(4,1045,10),start+4000);
  book.ingest(tick(5,1049,4,100),start+5000);
  const out=book.snapshot(start+5000),bar=out.bars[0];
  assert.equal(bar.buy,10);assert.equal(bar.sell,5);assert.equal(bar.unknown,4);
  assert.equal(bar.unallocated,30);assert.equal(out.estimatedCvd,5);
  assert.equal(bar.levels.reduce((s,x)=>s+x.buy+x.sell+x.unknown,0),19);
  assert.equal(out.depthImbalance,-0.2);
  assert.equal(book.snapshot(start+20000).status,'STALE');
});

test('feed interruptions leave quantity unallocated and new day resets cumulative estimates',()=>{
  const book=new FlowBook();book.ingest(tick(1,100,1),start+1000);
  book.ingest(tick(10,110,10),start+10000);
  assert.equal(book.snapshot(start+10000).bars[0].unallocated,10);
  const next=tick(1,5,5,101,start+86400000);
  book.ingest(next,next.time);
  assert.equal(book.snapshot(next.time).bars.length,0);assert.equal(book.cvd,0);
});

test('contract catalogue separates derivatives, cash and MCX and excludes spot index footprints',()=>{
  const rows=[
    {token:'1',symbol:'NIFTY',name:'NIFTY',exch_seg:'NSE',instrumenttype:'AMXIDX'},
    {token:'2',symbol:'NIFTYFUT',name:'NIFTY',exch_seg:'NFO',instrumenttype:'FUTIDX'},
    {token:'3',symbol:'INFY-EQ',name:'INFY',exch_seg:'NSE',instrumenttype:''},
    {token:'4',symbol:'INFYCE',name:'INFY',exch_seg:'NFO',instrumenttype:'OPTSTK'},
    {token:'5',symbol:'NATURALGASFUT',name:'NATURALGAS',exch_seg:'MCX',instrumenttype:'FUTCOM'}];
  assert.deepEqual(flowChoices(rows,'NIFTY','INDEX').map(x=>x.token),['2']);
  assert.deepEqual(flowChoices(rows,'','STOCKS').map(x=>x.token),['3']);
  assert.deepEqual(flowChoices(rows,'INFY','STOCK_OPTIONS').map(x=>x.token),['4']);
  assert.deepEqual(flowChoices(rows,'NATURALGAS','MCX').map(x=>x.token),['5']);
});

test('guided search separates exact NIFTY from BANKNIFTY and exposes all pages and expiry filters',()=>{
  const rows=Array.from({length:85},(_,i)=>({token:String(i+1),symbol:`NIFTY${20000+i}CE`,name:'NIFTY',exch_seg:'NFO',instrumenttype:'OPTIDX',expiry:'28OCT2099',strike:String((20000+i)*100)}));
  rows.push({token:'999',symbol:'BANKNIFTY47000CE',name:'BANKNIFTY',exch_seg:'NFO',instrumenttype:'OPTIDX',expiry:'28OCT2099',strike:'4700000'});
  const discovery=flowCatalogue(rows,{q:'NIFTY'});
  assert.deepEqual(discovery.roots,['NIFTY','BANKNIFTY']);assert.equal(discovery.items.length,0);
  const first=flowCatalogue(rows,{underlying:'NIFTY',kind:'CE'});
  const second=flowCatalogue(rows,{underlying:'NIFTY',kind:'CE',offset:40});
  const third=flowCatalogue(rows,{underlying:'NIFTY',offset:80});
  assert.equal(first.total,85);assert.equal(first.items.length,40);assert.equal(first.hasMore,true);
  assert.equal(second.items.length,40);assert.equal(third.items.length,5);assert.equal(third.hasMore,false);
  assert.equal(new Set([...first.items,...second.items,...third.items].map(x=>x.token)).size,85);
  assert.equal(first.items[0].strike,20000);assert.deepEqual(first.expiries,['28OCT2099']);
  assert.equal(flowCatalogue(rows,{underlying:'NIFTY',q:'20042'}).items[0].token,'43');
  assert.equal(flowCatalogue(rows,{underlying:'NIFTY',kind:'PE'}).total,0);
  assert.equal(flowCatalogue(rows,{underlying:'NIFTY',expiry:'01JAN2099'}).total,0);
});
