import test from 'node:test';
import assert from 'node:assert/strict';
import { buildBacktestCatalog, findBacktestChoice } from '../src/backtest-catalog.js';
import { stockTechnicalModel } from '../src/backtest.js';

test('broker catalogue admits only actual historical underlyings and watchlist shares', () => {
  const rows = [
    { token:'99926000',symbol:'NIFTY 50',name:'NIFTY 50',exch_seg:'NSE',instrumenttype:'AMXIDX' },
    { token:'99926009',symbol:'NIFTY BANK',name:'NIFTY BANK',exch_seg:'NSE',instrumenttype:'AMXIDX' },
    { token:'99919000',symbol:'SENSEX',name:'SENSEX',exch_seg:'BSE',instrumenttype:'AMXIDX' },
    { token:'99926074',symbol:'NIFTY MID SELECT',name:'NIFTY MID SELECT',exch_seg:'NSE',instrumenttype:'IDX' },
    { token:'99926075',symbol:'NIFTY IT',name:'NIFTY IT',exch_seg:'NSE',instrumenttype:'AMXIDX' },
    { token:'99920005',symbol:'MCXBULLDEX',name:'MCXBULLDEX',exch_seg:'MCX',instrumenttype:'AMXIDX' },
    { token:'1001',symbol:'RELIANCE-EQ',name:'RELIANCE',exch_seg:'NSE',instrumenttype:'' },
    { token:'22',symbol:'MIDCPNIFTY30OCT2620000CE',name:'MIDCPNIFTY',exch_seg:'NFO',instrumenttype:'OPTIDX' }
  ];
  const catalog=buildBacktestCatalog(rows,{items:[{symbol:'RELIANCE',sector:'Energy'},{symbol:'NOTLISTED',sector:'Other'}],source:'test'});
  assert.deepEqual(catalog.indices.slice(0,3).map(x=>x.symbol),['NIFTY','BANKNIFTY','SENSEX']);
  assert.ok(catalog.indices.some(x=>x.symbol==='NIFTY MID SELECT'));
  assert.ok(catalog.indices.some(x=>x.symbol==='NIFTY IT'));
  assert.equal(catalog.mcx[0].symbol,'MCXBULLDEX');
  assert.deepEqual(catalog.stocks.map(x=>x.symbol),['RELIANCE']);
  assert.equal(findBacktestChoice(catalog,{symbol:'RELIANCE',exchange:'NSE',kind:'STOCK'}).token,'1001');
  assert.throws(()=>findBacktestChoice(catalog,{symbol:'NOTLISTED',exchange:'NSE',kind:'STOCK'}));
});

const candle=(day,h,m,open,high,low,close,volume)=>({
  timestamp:new Date(Date.UTC(2026,8,day,h-5,m-30)).toISOString(),open,high,low,close,volume
});

function fixture(){
  const previous=[17,18,21,22,23,24].flatMap((day,d)=>Array.from({length:75},(_,i)=>{
    const time=15+5*i,price=91.5+d*0.5+i*0.07;
    return candle(day,9+Math.floor(time/60),time%60,price,price+1,price-1,price+0.05,10000);
  }));
  const today=[
    candle(25,9,15,100,100.5,99.9,100.3,25000),
    candle(25,9,20,100.3,100.7,100.0,100.5,25000),
    candle(25,9,25,100.5,100.85,100.2,100.6,25000),
    candle(25,9,30,100.6,100.75,100.1,100.6,25000),
    candle(25,9,35,100.6,100.75,98.8,100.6,25000),
    candle(25,9,40,100.6,101.2,100.7,101.0,25000),
    candle(25,9,45,101,101.4,100.8,101.2,25000),
    candle(25,9,50,101.2,108,101.1,107,25000)
  ];
  const rows=[...previous,...today];
  const higher=[];
  for(let i=0;i<rows.length;i+=3){
    const group=rows.slice(i,i+3);
    if(group.length!==3)continue;
    higher.push({...group[0],high:Math.max(...group.map(x=>x.high)),low:Math.min(...group.map(x=>x.low)),
      close:group[2].close,volume:group.reduce((sum,x)=>sum+x.volume,0)});
  }
  return {rows,higher};
}

test('cash technical model uses real candle volume and risk sized next bar entries', () => {
  const {rows,higher}=fixture();
  const result=stockTechnicalModel(rows,higher,20000);
  assert.ok(result.trades.length>0,'The completed opening break should produce at least one research trade');
  const first=result.trades[0];
  assert.equal(first.side,'BUY');
  assert.equal(first.entry,101);
  assert.equal(first.reason,'T2');
  assert.ok(first.quantity>0 && first.quantity*first.entry<=18000);
  assert.ok(result.modelPnl>0);
  const noVolume=rows.map(x=>x.timestamp.startsWith('2026-09-25')?{...x,volume:0}:x);
  assert.equal(stockTechnicalModel(noVolume,higher,20000).trades.length,0);
});
