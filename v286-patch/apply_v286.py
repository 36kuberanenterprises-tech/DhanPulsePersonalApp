from pathlib import Path
import re

root=Path('crypto-forex-app/buildsrc')
idx=root/'app/src/main/assets/index.html'
s=idx.read_text()

css=r'''
/* V2.8.6 Nifty 50 pre-market analyst */
.pm-panel{margin-top:16px}
.pm-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}
.pm-title{font-size:18px;font-weight:800}
.pm-sub{font-size:10px;color:#8995a3;line-height:1.45;margin-top:4px}
.pm-badge{font-size:9px;font-weight:800;border:1px solid #34404c;border-radius:999px;padding:7px 10px;white-space:nowrap}
.pm-badge.ok{border-color:rgba(34,197,94,.5);color:#36d399}
.pm-badge.warn{border-color:rgba(245,158,11,.5);color:#f5b942}
.pm-badge.bad{border-color:rgba(239,68,68,.5);color:#ff646f}
.pm-bias{margin:12px 0;padding:14px;border:1px solid #303844;border-radius:14px;background:#11161b}
.pm-bias span{display:block;color:#7f8b98;font-size:9px;text-transform:uppercase}
.pm-bias b{display:block;font-size:24px;margin-top:4px}
.pm-bias p{font-size:10px;color:#9aa4ae;line-height:1.45;margin:6px 0 0}
.pm-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.pm-grid>div{padding:10px;border:1px solid #2a323c;border-radius:10px;background:#151a20}
.pm-grid span{display:block;color:#7f8b98;font-size:8px;text-transform:uppercase}
.pm-grid b{display:block;font-size:13px;margin-top:4px}
.pm-news{margin-top:12px}
.pm-news h3{font-size:12px;margin:0 0 7px}
.pm-news-item{padding:8px 0;border-top:1px solid #252d35}
.pm-news-item b{display:block;font-size:10px;line-height:1.35}
.pm-news-item span{display:block;font-size:8px;color:#7f8b98;margin-top:3px}
.pm-actions{display:flex;gap:8px;margin-top:12px}
.pm-actions button{flex:1}
.pm-note{font-size:8px;color:#74808c;line-height:1.45;margin-top:9px}
@media(max-width:680px){.pm-grid{grid-template-columns:1fr 1fr}.pm-title{font-size:16px}}
'''
if 'V2.8.6 Nifty 50 pre-market analyst' not in s:
    s=s.replace('</style>',css+'\n</style>',1)

js=r'''
/* V2.8.6 Nifty 50 pre-market analyst.
   Uses latest available public market closes from Yahoo Finance and fresh web news from GDELT.
   It is independent of broker APIs and does not place orders. */
var PM286={version:'2.8.6',pending:{},data:{},news:[],startedAt:0,lastRefresh:0};

function pm286e(id){return document.getElementById(id)}
function pm286num(v){var n=Number(v);return Number.isFinite(n)?n:null}
function pm286fmt(n,d){return n==null?'NA':Number(n).toLocaleString('en-IN',{minimumFractionDigits:d||0,maximumFractionDigits:d||0})}
function pm286pct(n){return n==null?'NA':((n>=0?'+':'')+Number(n).toFixed(2)+'%')}
function pm286istWeekday(){
  try{return new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Kolkata',weekday:'short'}).format(new Date())}catch(e){return ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][new Date().getDay()]}
}
function pm286closed(){var d=pm286istWeekday();return d==='Sat'||d==='Sun'}
function pm286request(key,url){
  PM286.pending[key]=true;
  try{
    if(window.DhanPulseNative&&typeof DhanPulseNative.fetchPremarket==='function'){
      DhanPulseNative.fetchPremarket(key,url);return;
    }
  }catch(e){}
  PM286.pending[key]=false;
}
function pm286market(obj){
  try{
    var r=obj&&obj.chart&&obj.chart.result&&obj.chart.result[0];if(!r)return null;
    var m=r.meta||{},q=(r.indicators&&r.indicators.quote&&r.indicators.quote[0])||{},cl=(q.close||[]).filter(function(x){return x!=null&&Number.isFinite(Number(x))});
    var last=pm286num(m.regularMarketPrice);if(last==null&&cl.length)last=pm286num(cl[cl.length-1]);
    var prev=pm286num(m.chartPreviousClose);if(prev==null&&cl.length>1)prev=pm286num(cl[cl.length-2]);
    var change=(last!=null&&prev!=null&&prev!==0)?(last-prev)/prev*100:null;
    var ts=pm286num(m.regularMarketTime);
    return {last:last,prev:prev,change:change,ts:ts?ts*1000:null};
  }catch(e){return null}
}
function pm286parseNews(obj){
  var a=(obj&&obj.articles)||[];
  var cutoff=Date.now()-36*3600000;
  var seen={};
  return a.filter(function(x){
    var t=Date.parse(x.seendate||x.datetime||'')||0,title=String(x.title||'').trim();
    if(!title||seen[title])return false;seen[title]=1;
    return !t||t>=cutoff;
  }).slice(0,6).map(function(x){return{title:x.title||'',domain:x.domain||x.sourcecountry||'',seen:x.seendate||''}});
}
window.__dhanpulsePremarketNative=function(key,body){
  PM286.pending[key]=false;
  try{
    var obj=JSON.parse(body||'{}');
    if(key==='news')PM286.news=pm286parseNews(obj);
    else PM286.data[key]=pm286market(obj);
  }catch(e){
    if(key==='news')PM286.news=[];
    else PM286.data[key]=null;
  }
  pm286render();
}
function pm286score(){
  var d=PM286.data,s=0,reasons=[],available=0;
  function use(k,w,pos,neg,label){
    var x=d[k];if(!x||x.change==null)return;
    available++;
    if(x.change>=pos){s+=w;reasons.push(label+' positive '+pm286pct(x.change))}
    else if(x.change<=neg){s-=w;reasons.push(label+' weak '+pm286pct(x.change))}
  }
  use('nifty',1,.50,-.50,'Nifty prior session');
  use('spx',2,.50,-.50,'S&P 500');
  use('nasdaq',2,.60,-.60,'Nasdaq');
  var inr=d.inr;if(inr&&inr.change!=null){available++;if(inr.change>=.20){s-=1;reasons.push('Rupee weaker '+pm286pct(inr.change))}else if(inr.change<=-.20){s+=1;reasons.push('Rupee stronger '+pm286pct(inr.change))}}
  var brent=d.brent;if(brent&&brent.change!=null){available++;if(brent.change>=1){s-=1;reasons.push('Brent higher '+pm286pct(brent.change))}else if(brent.change<=-1){s+=1;reasons.push('Brent lower '+pm286pct(brent.change))}}
  var bias=s>=3?'BULLISH':s<=-3?'BEARISH':'MIXED';
  return{score:s,bias:bias,reasons:reasons,available:available}
}
function pm286render(){
  var st=pm286score(),closed=pm286closed(),badge=pm286e('pm286Status'),bias=pm286e('pm286Bias'),why=pm286e('pm286Why');
  if(badge){
    var waiting=Object.keys(PM286.pending).some(function(k){return PM286.pending[k]});
    badge.textContent=waiting?'REFRESHING':(closed?'MARKET CLOSED':'WEB UPDATED');
    badge.className='pm-badge '+(waiting?'warn':closed?'warn':'ok');
  }
  if(bias){
    bias.textContent=closed?('NEXT SESSION · '+st.bias):st.bias;
    bias.className=st.bias==='BULLISH'?'bull':st.bias==='BEARISH'?'bear':'neutral';
  }
  if(why){
    var prefix=closed?'NSE is closed today. This is a next-session risk briefing using the latest available market closes. ':'';
    why.textContent=prefix+(st.reasons.length?st.reasons.slice(0,4).join(' · '):'Waiting for verified public market inputs.');
  }
  var map={nifty:'pm286Nifty',spx:'pm286Spx',nasdaq:'pm286Nasdaq',inr:'pm286Inr',brent:'pm286Brent'};
  Object.keys(map).forEach(function(k){var e=pm286e(map[k]),x=PM286.data[k];if(e)e.textContent=x&&x.last!=null?(pm286fmt(x.last,k==='inr'?2:2)+' · '+pm286pct(x.change)):'NA'});
  var q=pm286e('pm286Quality');if(q)q.textContent=st.available+'/5 market inputs · '+PM286.news.length+' fresh headlines';
  var n=pm286e('pm286News');
  if(n)n.innerHTML=PM286.news.length?PM286.news.map(function(x){return'<div class="pm-news-item"><b>'+String(x.title||'').replace(/</g,'&lt;')+'</b><span>'+String(x.domain||'')+'</span></div>'}).join(''):'<div class="pm-note">Fresh headlines are not available yet.</div>';
  var t=pm286e('pm286Time');if(t&&PM286.lastRefresh)t.textContent='Last refresh '+new Date(PM286.lastRefresh).toLocaleString('en-IN');
}
function pm286refresh(){
  PM286.startedAt=Date.now();PM286.lastRefresh=Date.now();PM286.data={};PM286.news=[];PM286.pending={};
  var base='https://query1.finance.yahoo.com/v8/finance/chart/';
  pm286request('nifty',base+'%5ENSEI?range=5d&interval=1d&includePrePost=true');
  pm286request('spx',base+'%5EGSPC?range=5d&interval=1d&includePrePost=true');
  pm286request('nasdaq',base+'%5EIXIC?range=5d&interval=1d&includePrePost=true');
  pm286request('inr',base+'INR%3DX?range=5d&interval=1d&includePrePost=true');
  pm286request('brent',base+'BZ%3DF?range=5d&interval=1d&includePrePost=true');
  var gd='https://api.gdeltproject.org/api/v2/doc/doc?query=%28%22Nifty%2050%22%20OR%20%22Indian%20stock%20market%22%20OR%20%22GIFT%20Nifty%22%20OR%20RBI%20OR%20%22FII%22%29%20sourcelang%3Aenglish&mode=ArtList&maxrecords=30&format=json&sort=HybridRel&timespan=1d';
  pm286request('news',gd);
  pm286render();
}
function pm286layout(){
  if(pm286e('pm286Panel'))return;
  var app=document.querySelector('.app'),first=app&&app.querySelector('.panel');if(!app||!first)return;
  var p=document.createElement('section');p.id='pm286Panel';p.className='panel pm-panel';
  p.innerHTML='<div class="pm-head"><div><div class="pm-title">Nifty 50 Pre Market Analyst</div><div class="pm-sub">Fresh public web data and news · intraday context only · no broker API required</div></div><span id="pm286Status" class="pm-badge warn">STARTING</span></div>'+
    '<div class="pm-bias"><span>Pre Market Bias</span><b id="pm286Bias">WAIT</b><p id="pm286Why">Refreshing latest available information.</p></div>'+
    '<div class="pm-grid"><div><span>Nifty 50</span><b id="pm286Nifty">NA</b></div><div><span>S&P 500</span><b id="pm286Spx">NA</b></div><div><span>Nasdaq</span><b id="pm286Nasdaq">NA</b></div><div><span>USD INR</span><b id="pm286Inr">NA</b></div><div><span>Brent</span><b id="pm286Brent">NA</b></div><div><span>Data Quality</span><b id="pm286Quality">0/5</b></div></div>'+
    '<div class="pm-news"><h3>Latest Market Headlines</h3><div id="pm286News"></div></div>'+
    '<div class="pm-actions"><button id="pm286Refresh">Refresh Latest Briefing</button></div>'+
    '<div class="pm-note" id="pm286Time"></div><div class="pm-note">Priority is given to fresh information. Older market closes are used only when they are still the latest available, such as weekends. Missing inputs remain NA. This module does not invent GIFT Nifty, FII/DII or live broker values when a verified public feed is unavailable.</div>';
  first.insertAdjacentElement('beforebegin',p);
  pm286e('pm286Refresh').onclick=pm286refresh;
  pm286refresh();
}
setTimeout(pm286layout,900);
'''
if 'V2.8.6 Nifty 50 pre-market analyst.' not in s:
    s=s.replace('\n})();\n</script>',js+'\n})();\n</script>',1)
idx.write_text(s)

ma=root/'app/src/main/java/com/dhanpulse/cryptofxv11/MainActivity.java'
a=ma.read_text()

helper=r'''
    private boolean allowedPremarketUrl(String url) {
        return url != null && (
                url.startsWith("https://query1.finance.yahoo.com/") ||
                url.startsWith("https://api.gdeltproject.org/")
        );
    }

    private void deliverPremarketToVisibleWeb(String key, String body) {
        if (webView == null || key == null || body == null) return;
        webView.post(() -> {
            try {
                String js = "window.__dhanpulsePremarketNative&&window.__dhanpulsePremarketNative(" +
                        JSONObject.quote(key) + "," + JSONObject.quote(body) + ");";
                webView.evaluateJavascript(js, null);
            } catch (Exception ignored) {
            }
        });
    }

    private void fetchPremarketForVisibleWeb(String key, String url) {
        if (!allowedPremarketUrl(url)) {
            deliverPremarketToVisibleWeb(key, "{}");
            return;
        }
        Request request = new Request.Builder()
                .url(url)
                .header("User-Agent", "Mozilla/5.0 DhanPulse/2.8.6")
                .header("Accept", "application/json,text/plain,*/*")
                .get()
                .build();
        newsClient.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                deliverPremarketToVisibleWeb(key, "{}");
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                try (Response r = response) {
                    String body = r.body() == null ? "{}" : r.body().string();
                    deliverPremarketToVisibleWeb(key, r.isSuccessful() ? body : "{}");
                }
            }
        });
    }

'''
if 'fetchPremarketForVisibleWeb' not in a:
    a=a.replace('    private final class NativeBridge {\n',helper+'    private final class NativeBridge {\n',1)

target='''        @JavascriptInterface
        public void fetchNews(String url) {
            fetchNewsForVisibleWeb(url);
        }
'''
if 'public void fetchPremarket(String key, String url)' not in a:
    if target not in a: raise SystemExit('fetchNews bridge target missing')
    repl=target+'''
        @JavascriptInterface
        public void fetchPremarket(String key, String url) {
            fetchPremarketForVisibleWeb(key, url);
        }
'''
    a=a.replace(target,repl,1)
ma.write_text(a)

b=root/'app/build.gradle.kts'
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 28601',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.8.6"',bs,count=1)
b.write_text(bs)
