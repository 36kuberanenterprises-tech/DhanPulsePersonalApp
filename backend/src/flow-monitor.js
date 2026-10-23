import { WebSocket } from 'undici';
import { instrumentMaster } from './angel.js';

const exchanges = { NSE: 1, NFO: 2, BSE: 3, BFO: 4, MCX: 5 };
const sessions = new Map();
const note = 'Observed live snapshots only. Buy/sell classification is estimated from preceding quotes, not exchange aggressor flags. Missing volume is unallocated. No historical footprint recovery or trading signals.';

export function parseFlowPacket(data) {
  const b = Buffer.from(data);
  if (b.length < 379 || b[0] !== 3) return null;
  const integer = offset => Number(b.readBigInt64LE(offset));
  const tick = { token: b.subarray(2,27).toString().split('\0')[0], exchangeType: b[1],
    sequence: b.readBigInt64LE(27).toString(), time: integer(35), price: integer(43)/100,
    quantity: integer(51), volume: integer(67), oi: integer(131), bids: [], asks: [] };
  if (!/^\d+$/.test(tick.token) || ![tick.time,tick.quantity,tick.volume,tick.oi].every(Number.isSafeInteger) ||
      tick.time < Date.UTC(2020,0,1) || tick.price <= 0 || tick.quantity < 0 || tick.volume < 0) return null;
  for (let offset=147; offset<347; offset+=20) {
    const side=b.readUInt16LE(offset), quantity=integer(offset+2), price=integer(offset+10)/100;
    if ([0,1].includes(side) && quantity>0 && Number.isSafeInteger(quantity) && price>0)
      (side===1 ? tick.bids : tick.asks).push({ price, quantity, orders:b.readUInt16LE(offset+18) });
  }
  tick.bids.sort((a,b)=>b.price-a.price); tick.asks.sort((a,b)=>a.price-b.price);
  return tick;
}

export class FlowBook {
  constructor(minutes=5) { this.minutes=minutes; this.reset(); }
  reset() { this.previous=null; this.bars=new Map(); this.cvd=0; this.startedAt=new Date().toISOString(); }
  ingest(tick, receivedAt=Date.now()) {
    if (tick.time>receivedAt+1000 || receivedAt-tick.time>5000) return;
    const previous=this.previous;
    const day=t=>new Date(t.time+330*60_000).toISOString().slice(0,10);
    if (previous && (tick.time<previous.time || (day(tick)===day(previous) && BigInt(tick.sequence)<=BigInt(previous.sequence)))) return;
    if (previous && (day(tick)!==day(previous) || tick.volume<previous.volume)) this.reset();
    const old=this.previous;
    this.previous={...tick,receivedAt};
    if (!old) return; // Baseline cumulative volume is not observed trading.
    const delta=tick.volume-old.volume;
    if (delta<=0) return;
    const duration=this.minutes*60_000;
    const bucket=Math.floor((tick.time+330*60_000)/duration)*duration-330*60_000;
    if (!this.bars.has(bucket)) this.bars.set(bucket,{ time:new Date(bucket).toISOString(), buy:0,sell:0,unknown:0,unallocated:0,levels:new Map() });
    const bar=this.bars.get(bucket);
    // A snapshot may skip many executions. Never put that cumulative change
    // at the last price or invent a buy/sell split for the missing executions.
    if (delta!==tick.quantity || tick.time-old.time>3000 || receivedAt-old.receivedAt>3000) {
      bar.unallocated+=delta;
    } else {
      const bid=old.bids[0]?.price, ask=old.asks[0]?.price;
      const valid=bid>0 && ask>bid;
      const side=valid && tick.price>=ask ? 'buy' : valid && tick.price<=bid ? 'sell' : 'unknown';
      const price=tick.price.toFixed(2);
      if (!bar.levels.has(price)) bar.levels.set(price,{ price:tick.price,buy:0,sell:0,unknown:0 });
      bar.levels.get(price)[side]+=delta; bar[side]+=delta;
      this.cvd+=side==='buy' ? delta : side==='sell' ? -delta : 0;
    }
    while(this.bars.size>60) this.bars.delete(this.bars.keys().next().value);
  }
  snapshot(now=Date.now()) {
    const t=this.previous, bid=t?.bids[0]?.price, ask=t?.asks[0]?.price;
    const bidQty=t?.bids.reduce((s,x)=>s+x.quantity,0)||0, askQty=t?.asks.reduce((s,x)=>s+x.quantity,0)||0;
    return { status: !t ? 'WAITING_FOR_FEED' : now-t.receivedAt>5000 || now-t.time>5000 ? 'STALE' : 'LIVE',
      startedAt:this.startedAt,lastTickAt:t ? new Date(t.time).toISOString() : null,price:t?.price??null,
      spread:bid>0&&ask>=bid ? ask-bid : null,
      depthImbalance:bidQty+askQty>0 ? (bidQty-askQty)/(bidQty+askQty) : null,
      bids:t?.bids||[],asks:t?.asks||[],oi:t?.oi??null,estimatedCvd:this.cvd,note,
      bars:[...this.bars.values()].slice(-30).map(b=>({...b,delta:b.buy-b.sell,
        levels:[...b.levels.values()].sort((a,b)=>b.price-a.price).slice(0,150)})) };
  }
}

function tradable(row) {
  return exchanges[row.exch_seg] && /^\d{1,12}$/.test(String(row.token)) &&
    (String(row.symbol).endsWith('-EQ') || /^(FUT|OPT)/.test(row.instrumenttype||'')) &&
    (!row.expiry || Date.parse(row.expiry)+86_400_000>Date.now());
}
export function flowChoices(rows, query, group) {
  const words=query.toUpperCase().trim().split(/\s+/).filter(Boolean);
  return rows.filter(row=>tradable(row) &&
    (group==='MCX' ? row.exch_seg==='MCX' : group==='STOCKS' ? /-EQ$/.test(row.symbol) :
      group==='STOCK_OPTIONS' ? row.instrumenttype==='OPTSTK' : ['FUTIDX','OPTIDX'].includes(row.instrumenttype)) &&
    words.every(word=>`${row.symbol} ${row.name}`.includes(word)))
    .sort((a,b)=>(Date.parse(a.expiry)||0)-(Date.parse(b.expiry)||0)||a.symbol.localeCompare(b.symbol))
    .slice(0,40).map(row=>({token:String(row.token),exchange:row.exch_seg,symbol:row.symbol,kind:row.instrumenttype||'CASH'}));
}
// Guided catalogue: discover names first, then filter contracts by exact underlying.
export function flowCatalogue(rows, options={}) {
  const {group='INDEX',q='',underlying='',kind='',expiry=''}=options;
  const norm=value=>String(value||'').toUpperCase().trim();
  const root=row=>norm(row.name || String(row.symbol).replace(/-EQ$/,''));
  const universe=rows.filter(row=>tradable(row) &&
    (group==='MCX' ? row.exch_seg==='MCX' : group==='STOCKS' ? row.exch_seg==='NSE' && /-EQ$/.test(row.symbol) :
      group==='STOCK_OPTIONS' ? row.instrumenttype==='OPTSTK' : ['FUTIDX','OPTIDX'].includes(row.instrumenttype)));
  const words=norm(q).split(/\s+/).filter(Boolean);
  const names=[...new Set(universe.map(root))].sort();
  const roots=names.filter(name=>words.every(word=>name.includes(word)))
    .sort((a,b)=>(b===norm(q))-(a===norm(q))||a.localeCompare(b));
  const contracts=universe.filter(row=>!underlying || root(row)===norm(underlying));
  const kinds=[...new Set(contracts.map(row=>row.instrumenttype?.startsWith('FUT')?'FUT':/CE$/.test(row.symbol)?'CE':/PE$/.test(row.symbol)?'PE':'CASH'))];
  const byKind=contracts.filter(row=>!kind || (kind==='FUT' ? row.instrumenttype?.startsWith('FUT') : kind==='CASH' ? /-EQ$/.test(row.symbol) : row.symbol.endsWith(kind)));
  const expiries=[...new Set(byKind.map(row=>row.expiry).filter(Boolean))].sort((a,b)=>Date.parse(a)-Date.parse(b));
  const matches=byKind.filter(row=>(!expiry || row.expiry===expiry) && (!underlying || words.every(word=>norm(`${row.symbol} ${row.name} ${row.expiry}`).includes(word))))
    .sort((a,b)=>(Date.parse(a.expiry)||0)-(Date.parse(b.expiry)||0) || Number(a.strike||0)-Number(b.strike||0) || a.symbol.localeCompare(b.symbol) || String(a.token).localeCompare(String(b.token)));
  const offset=Math.max(0,Math.floor(Number(options.offset)||0));
  return {roots,totalRoots:roots.length,kinds,expiries,total:matches.length,offset,
    hasMore:offset+40<matches.length,
    items:underlying ? matches.slice(offset,offset+40).map(row=>({token:String(row.token),exchange:row.exch_seg,
      symbol:row.symbol,kind:row.instrumenttype||'CASH',underlying:root(row),expiry:row.expiry||'',
      strike:Number(row.strike)>0?Number(row.strike)/100:null})) : []};
}
function openMonitor(session,row,minutes) {
  if (![session.jwt,session.apiKey,session.clientCode,session.feedToken].every(Boolean)) throw new Error('Login again to obtain the broker streaming token');
  const state={key:`${row.exch_seg}:${row.token}:${minutes}`,book:new FlowBook(minutes),symbol:row.symbol,
    expiresAt:session.expiresAt,touched:Date.now(),error:null,closed:false};
  const ws=new WebSocket('wss://smartapisocket.angelone.in/smart-stream',{headers:{
    Authorization:session.jwt.replace(/^Bearer\s+/i,''),'x-api-key':session.apiKey,
    'x-client-code':session.clientCode,'x-feed-token':session.feedToken }});
  ws.binaryType='arraybuffer';
  state.close=()=>{if(state.closed)return;state.closed=true;clearInterval(timer);ws.close();};
  const timer=setInterval(()=>{
    if(Date.now()-state.touched>20_000 || Date.now()>=state.expiresAt) {state.close();if(sessions.get(session.clientCode)===state)sessions.delete(session.clientCode);}
    else if(ws.readyState===WebSocket.OPEN)ws.send('ping');
  },10_000);timer.unref?.();
  ws.addEventListener('open',()=>ws.send(JSON.stringify({correlationID:'flowmonitor',action:1,
    params:{mode:3,tokenList:[{exchangeType:exchanges[row.exch_seg],tokens:[String(row.token)]}]}})));
  ws.addEventListener('message',event=>{
    if(state.closed)return;
    if(typeof event.data==='string') {
      if(event.data!=='pong')state.error='Broker returned a streaming subscription message. Feed availability is not confirmed.';
      return;
    }
    try {const tick=parseFlowPacket(event.data);
      if(tick && tick.token===String(row.token) && tick.exchangeType===exchanges[row.exch_seg]) {state.book.ingest(tick);state.error=null;}
    }catch{state.error='Malformed broker snapshot ignored';}
  });
  ws.addEventListener('error',()=>{state.error='Broker stream failed. Tap Restart feed.';state.close();});
  ws.addEventListener('close',()=>{if(!state.closed){state.error='Broker stream disconnected. Tap Restart feed.';state.close();}});
  return state;
}

export function attachFlowRoutes(app,requireSession) {
  app.get('/api/flow/catalog',requireSession,async(req,res)=>{
    try {const rows=await instrumentMaster();res.json(req.query.guided==='true' ? flowCatalogue(rows,req.query) :
      {items:flowChoices(rows,String(req.query.q||'').slice(0,80),String(req.query.group||'INDEX'))});}
    catch {res.status(503).json({error:'Broker instrument catalogue unavailable'});}
  });
  app.get('/api/flow/monitor',requireSession,async(req,res)=>{
    try {
      const minutes=Number(req.query.minutes||5);
      if(![1,3,5,10,15].includes(minutes))return res.status(400).json({error:'Unsupported monitor timeframe'});
      const row=(await instrumentMaster()).find(x=>x.exch_seg===req.query.exchange && String(x.token)===req.query.token && tradable(x));
      if(!row)return res.status(400).json({error:'Select a listed cash share, futures or option contract. Spot indices have no traded footprint.'});
      let state=sessions.get(req.smartSession.clientCode);
      const key=`${row.exch_seg}:${row.token}:${minutes}`;
      if(!state || state.key!==key || req.query.restart==='true') {
        state?.close();
        if(sessions.size>=100 && !state)return res.status(503).json({error:'Monitor capacity reached; try later'});
        state=openMonitor(req.smartSession,row,minutes);sessions.set(req.smartSession.clientCode,state);
      }
      state.touched=Date.now();
      res.json({...state.book.snapshot(),symbol:state.symbol,error:state.error,
        ...(state.closed ? {status:'DISCONNECTED'} : {})});
    }catch(e){res.status(503).json({error:e.message||'Order flow monitor unavailable'});}
  });
}
