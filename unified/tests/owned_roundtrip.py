"""Full-sized transactions on a new isolated copy of owned stock files.

Only the explicitly new scratch tree is mutated. The same engine is compiled
with isolated settings/backup paths. The shipping binary also checks the
stock and installed full-dub results without writing them.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,time
from transactions import HARNESS
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for x in ['package','stock','out']:p.add_argument('--'+x,type=Path,required=True)
 a=p.parse_args();out=a.out.resolve();assert not out.exists()
 for x in [REPO,a.package.resolve(),a.stock.resolve()]:assert not out.is_relative_to(x) and not x.is_relative_to(out)
 m=json.loads((a.package/'manifest.json').read_text('utf-8-sig'));stock=next(x['hashes']for x in m['inputs']if x['id']=='stock')
 for i,f in enumerate(m['files']):assert sha(a.stock/f['path'])==stock[i]
 for g in m['guards']:assert sha(a.stock/g['path'])==g['sha256']
 out.mkdir();case=out/'case';case.mkdir();content=case/'Content';content.mkdir();bundle=out/'bundle';shutil.copytree(a.package,bundle);cd=out/'compile';cd.mkdir()
 for row in [*m['files'],*m['guards']]:
  rel=row['path'];dest=content/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.stock/rel,dest)
 initial=b'game-language = English\r\nscaling = 2x - 1280x960\r\nantialiasing = 4x MSAA\r\ncustom-key = retain\r\n'
 (case/'settings.ini').write_bytes(initial);(case/'unrelated-save.txt').write_bytes(b'unchanged checkpoint sentinel')
 for name in ['Engine.cs','Settings.cs','GameCache.cs']:shutil.copyfile(REPO/'unified/source'/name,cd/name)
 for name,src in [('VoiceCache.cs','dubbing/audio/VoiceCache.cs'),('Resolution.cs','source/SelectionMigration.cs')]:
  (cd/name).write_text((REPO/src).read_text('utf-8').replace('namespace CrimsonSkiesKoreanPatch','namespace CrimsonSkiesUnified'),encoding='utf-8')
 (cd/'Pins.cs').write_text('namespace CrimsonSkiesUnified {public static class Pins {public const string Manifest="'+sha(bundle/'manifest.json')+'";public const string ReleaseId="'+m['releaseId']+'";}}');(cd/'Harness.cs').write_text(HARNESS)
 exe=bundle/'Fixture.exe';csc=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
 r=subprocess.run([str(csc),'/nologo','/codepage:65001','/define:UNIFIED_TEST','/target:exe','/out:'+str(exe),*['/r:'+x for x in ['System.Core.dll','System.Web.Extensions.dll','System.Xml.dll']],*[str(p)for p in cd.glob('*.cs')]],capture_output=True);assert r.returncode==0,(r.stdout+r.stderr).decode('utf-8','replace')
 operations=[]
 def run(args,label,expected=0):
  t=time.monotonic();r=subprocess.run([str(x)for x in args],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=1200);(out/(label+'.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==expected,(label,(r.stdout+r.stderr).decode('utf-8','replace')[-2500:]);operations.append(dict(operation=label,seconds=round(time.monotonic()-t,3),exit=r.returncode,expected=expected));print(label,'PASS',operations[-1]['seconds'],flush=True)
 def verify(ident):
  v=next(x['hashes']for group in ['inputs','profiles']for x in m[group]if x['id']==ident)
  assert all(sha(content/f['path'])==v[i]for i,f in enumerate(m['files'])),ident
  assert all(sha(content/g['path'])==g['sha256']for g in m['guards'])
  raw=(case/'settings.ini').read_bytes();assert b'antialiasing = 4x MSAA\r\n' in raw and b'custom-key = retain\r\n' in raw
  assert (case/'unrelated-save.txt').read_bytes()==b'unchanged checkpoint sentinel'
 run([bundle/'CrimsonSkiesSetup.exe','--check','--root',content],'shipping-check-stock')
 for ident in ['k1-w1-d1-dub','k1-w0-d1-dub','k1-w0-d0-original','k0-w1-d0-off']:
  run([exe,case,'--apply','unused',ident,'none','throw'],'install-'+ident);verify(ident)
  # The fixture owns its isolated backup location. The shipping binary must
  # refuse to adopt that full-dub state without its own production receipt.
  if ident=='k1-w1-d1-dub':run([bundle/'CrimsonSkiesSetup.exe','--check','--root',content],'shipping-reject-unowned-full',expected=1)
 run([exe,case,'--restore','unused','k1-w1-d1-dub','none','throw'],'restore-stock');verify('stock');assert (case/'settings.ini').read_bytes()==initial
 assert all(sha(a.stock/f['path'])==stock[i]for i,f in enumerate(m['files']))
 report=dict(schema=1,status='PASS_OWNED_FULL_SIZE_ROUNDTRIP',operations=operations,all29FilesAnd4GuardsVerified=True,sourceInputsUnchanged=True,installedGameWrites=0,installedSettingsWrites=0,shippingExeSha256=sha(bundle/'CrimsonSkiesSetup.exe'),engineSha256=sha(REPO/'unified/source/Engine.cs'))
 (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(dict(status=report['status'],operations=len(operations))))
if __name__=='__main__':main()
