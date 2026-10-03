from pathlib import Path
import re

root = Path('crypto-forex-app/buildsrc')
idx = root / 'app/src/main/assets/index.html'
s = idx.read_text()

s = s.replace('Version 2.6.1 History Preserved', 'Version 2.6.2 Stable Migration')
s = s.replace('DhanPulse Crypto and Forex Version 2.6.1 History Preserved.', 'DhanPulse Crypto and Forex Version 2.6.2 Stable Migration.')

legacy_note = r'''
<div class="panel" id="migrationNote">
  <h2>Stable History Migration</h2>
  <div class="muted small">This stable app line keeps one permanent history store for future updates. The known V2.6 BTCUSDT 5m liquidity SELL loss is imported once as legacy research data so the strategy backtest does not start from zero.</div>
</div>
'''
if 'id="migrationNote"' not in s:
    anchor = '<div class="panel" id="historyLab">'
    if anchor not in s:
        raise SystemExit('historyLab anchor missing')
    s = s.replace(anchor, legacy_note + '\n' + anchor, 1)

js = r'''
/* V2.6.2 stable migration.
   Android cannot read another package's private WebView localStorage, so the known V2.6
   result captured in the user's screenshots is imported once as legacy backtest data.
   Future updates stay on this stable package and permanent master history store. */
var V262={version:'2.6.2',legacyMarker:'dhanpulse_v262_legacy_seed_done'};
function v262seedLegacy(){
  try{
    if(localStorage.getItem(V262.legacyMarker)==='1')return;
    var list=v261all();
    var exists=list.some(function(t){return t&&t.id==='legacy_v260_20261003_230232_btcusdt_5m_sell_liquidity'});
    if(!exists){
      list.push({
        id:'legacy_v260_20261003_230232_btcusdt_5m_sell_liquidity',
        market:'crypto',symbol:'BTCUSDT',tf:'5m',side:'SELL',
        strategy:'ICT LIQUIDITY REVERSAL',stage:'Imported V2.6 legacy result',
        quality:null,regime:'UNKNOWN',support:0,reasons:['Imported from V2.6 recorded result screenshot'],
        entry:null,sl:null,t1:null,t2:null,t3:null,
        status:'CLOSED',result:'SL',resultDisplay:'SL HIT',pnlR:-1,
        h1:false,h2:false,h3:false,createdAt:1791048752000,closedAt:1791049600000,
        sourceVersion:'2.6.0',legacyImported:true
      });
      save(list);
    }
    localStorage.setItem(V262.legacyMarker,'1');
    if(typeof renderTrades==='function')renderTrades();
    if(typeof v261renderHistory==='function')v261renderHistory();
  }catch(e){}
}
setTimeout(v262seedLegacy,250);
'''
if 'V2.6.2 stable migration.' not in s:
    s = s.replace('</script>', js + '\n</script>', 1)
idx.write_text(s)

b = root / 'app/build.gradle.kts'
bs = b.read_text()
# New permanent package line. This is intentionally different from V2.6 because the old
# V2.6 debug signing key was ephemeral and Android cannot update it with a different signer.
bs = re.sub(r'applicationId\s*=\s*"[^"]+"', 'applicationId = "com.dhanpulse.cryptofxstable"', bs, count=1)
bs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 33', bs, count=1)
bs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.6.2"', bs, count=1)
b.write_text(bs)
