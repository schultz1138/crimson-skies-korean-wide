"""Exercise the real unified engine with small synthetic file/ZIP identities.

Requires a built package's manifest/tool to retain its exact component graph.
No game content, installed settings, registry or save data is modified. The
fixture executable is compiled with UNIFIED_TEST and is never distributed.
"""
from pathlib import Path
import argparse, copy, hashlib, json, os, shutil, subprocess, time

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')

HARNESS=r'''
using System;using System.IO;using CrimsonSkiesUnified;
class Harness {static int Main(string[] a){try{
 PatchEngine.BackupOverride=Path.Combine(a[0],"backups");PatchEngine.SettingsOverride=Path.Combine(a[0],"settings.ini");
 if(a[4]!="none")PatchEngine.Fault=delegate(string p){if(p==a[4]){if(a[5]=="crash")Environment.Exit(73);throw new IOException("Injected failure: "+p);}};
 new PatchEngine(AppDomain.CurrentDomain.BaseDirectory,Console.WriteLine).Run(a[1],Path.Combine(a[0],"Content"),a[3]);return 0;
 }catch(Exception e){Console.Error.WriteLine(e.Message);return 1;}}}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    out=a.out.resolve();assert not out.exists() and not out.is_relative_to(REPO) and not REPO.is_relative_to(out) and not out.is_relative_to(a.package.resolve());out.mkdir(parents=True)
    m=json.loads((a.package/'manifest.json').read_text('utf-8-sig'));m=copy.deepcopy(m);bundle=out/'package';bundle.mkdir();(bundle/'tools').mkdir();(bundle/'patches').mkdir();blobs=out/'blobs';blobs.mkdir();compile_dir=out/'compile';compile_dir.mkdir()
    tool=bundle/'tools/xdelta3.exe';shutil.copyfile(a.package/'tools/xdelta3.exe',tool);assert sha(tool)==m['tool']['sha256']
    maps=[];data={}
    for i,f in enumerate(m['files']):
        mapping={}
        for j,n in enumerate(f['nodes']):
            b=(('owned synthetic fixture / file%d / '%i+n['sha256']+'\n').encode()*16)
            h=hashlib.sha256(b).hexdigest();mapping[n['sha256']]=h;n.update(sha256=h,bytes=len(b));data[i,h]=b;(blobs/f'{i}-{h}').write_bytes(b)
        maps.append(mapping)
        for e in f['edges']:
            e['source']=mapping[e['source']];e['target']=mapping[e['target']];dest=bundle/e['path']
            r=subprocess.run([str(tool),'-e','-9','-D','-R','-s',str(blobs/f"{i}-{e['source']}"),str(blobs/f"{i}-{e['target']}"),str(dest)],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
            assert r.returncode==0;r=None;e.update(bytes=dest.stat().st_size,sha256=sha(dest))
    for group in ['profiles','inputs','knownExternal']:
        for v in m[group]:v['hashes']=[maps[i][h] for i,h in enumerate(v['hashes'])]
    guards={}
    for g in m['guards']:
        if g['path']=='appxmanifest.xml':
            x=m['supportedPackage'];b=('<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"><Identity Name="'+x['name']+'" Version="'+x['version']+'" ProcessorArchitecture="'+x['architecture']+'" Publisher="'+x['publisher']+'"/></Package>').encode()
        else:b=('synthetic guard: '+g['path']).encode()
        guards[g['path']]=b;g.update(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
    save(bundle/'manifest.json',m)
    for name in ['Engine.cs','HostManifest.cs','Settings.cs','GameCache.cs']:shutil.copyfile(REPO/'unified/source'/name,compile_dir/name)
    for name,src in [('VoiceCache.cs','dubbing/audio/VoiceCache.cs'),('Resolution.cs','source/SelectionMigration.cs')]:
        (compile_dir/name).write_text((REPO/src).read_text('utf-8').replace('namespace CrimsonSkiesKoreanPatch','namespace CrimsonSkiesUnified'),encoding='utf-8')
    (compile_dir/'Pins.cs').write_text('namespace CrimsonSkiesUnified {public static class Pins {public const string Manifest="'+sha(bundle/'manifest.json')+'";public const string ReleaseId="'+m['releaseId']+'";}}')
    (compile_dir/'Harness.cs').write_text(HARNESS)
    csc=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe';exe=bundle/'Fixture.exe'
    r=subprocess.run([str(csc),'/nologo','/codepage:65001','/define:UNIFIED_TEST','/target:exe','/out:'+str(exe),*['/r:'+x for x in ['System.Core.dll','System.Web.Extensions.dll','System.Xml.dll']],*[str(p) for p in compile_dir.glob('*.cs')]],capture_output=True)
    assert r.returncode==0,(r.stdout+r.stderr).decode('utf-8','replace')
    checks=0;operations=[]
    def need(ok,why):
        nonlocal checks
        checks+=1
        if not ok:raise AssertionError(why)
    def vector(ident):return next(v['hashes'] for group in ['inputs','profiles','knownExternal'] for v in m[group] if v['id']==ident)
    initial=b'game-language = English\r\nscaling = 2x - 1280x960\r\nantialiasing = 4x MSAA\r\ncustom-key = keep me\r\n'
    def case(name,ident='stock'):
        root=out/name;root.mkdir();content=root/'Content';content.mkdir()
        for i,f in enumerate(m['files']):
            q=content/f['path'];q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data[i,vector(ident)[i]])
        for rel,b in guards.items():q=content/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
        (root/'settings.ini').write_bytes(initial);(root/'unrelated-save.txt').write_bytes(b'leave checkpoint alone')
        (content/'unowned-sentinel.txt').write_bytes(b'leave content alone')
        return root
    def state(root,ident):
        v=vector(ident)
        need(all(sha(root/'Content'/f['path'])==v[i] for i,f in enumerate(m['files'])),str(root)+' whole-file state '+ident)
        raw=(root/'settings.ini').read_bytes();need(b'antialiasing = 4x MSAA\r\n' in raw and b'custom-key = keep me\r\n' in raw,'Other settings retained')
        need((root/'unrelated-save.txt').read_bytes()==b'leave checkpoint alone' and (root/'Content/unowned-sentinel.txt').read_bytes()==b'leave content alone','Unowned sentinel retained')
    def call(root,mode,ident='k1-w1-d1-dub',fault='none',kind='throw',expected=0):
        start=time.monotonic();r=subprocess.run([str(exe),str(root),mode,'unused',ident,fault,kind],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=60)
        operations.append(dict(case=root.name,mode=mode,profile=ident,fault=fault,kind=kind,exit=r.returncode,seconds=round(time.monotonic()-start,3)))
        (root/'last.log').write_bytes(r.stdout+r.stderr)
        need(r.returncode==expected,(root.name,mode,ident,r.returncode,(r.stdout+r.stderr).decode('utf-8','replace')[-2500:]))
        return (r.stdout+r.stderr).decode('utf-8','replace')
    root=case('matrix');call(root,'--check');state(root,'stock');need(not (root/'backups').exists(),'Check is read only')
    for v in m['profiles']:
        call(root,'--apply',v['id']);state(root,v['id']);call(root,'--check')
    call(root,'--apply');state(root,'k1-w1-d1-dub');call(root,'--apply');state(root,'k1-w1-d1-dub')
    call(root,'--restore');state(root,'stock');need((root/'settings.ini').read_bytes()==initial,'Exact initial owned keys restored')
    root=case('foundation','foundation');call(root,'--apply');call(root,'--apply','k0-w1-d0-off');state(root,'k0-w1-d0-off');call(root,'--restore');state(root,'foundation')
    for fault in ['prepared','file-0','cache','settings']:
        root=case('rollback-'+fault);call(root,'--apply',fault=fault,expected=1);state(root,'stock');need((root/'settings.ini').read_bytes()==initial,'Failure settings rollback');call(root,'--check')
    default=vector('k1-w1-d1-dub');stock=vector('stock');last=max(i for i in range(29) if default[i]!=stock[i])
    for fault in ['prepared','file-0','file-'+str(last),'settings']:
        root=case('crash-'+fault);call(root,'--apply',fault=fault,kind='crash',expected=73);call(root,'--check',expected=1);call(root,'--apply',expected=1);call(root,'--recover');state(root,'stock');need((root/'settings.ini').read_bytes()==initial,'Crash settings recovered');call(root,'--apply');state(root,'k1-w1-d1-dub')
    root=case('crash-concurrent-aa');call(root,'--apply',fault='settings',kind='crash',expected=73)
    raw=(root/'settings.ini').read_bytes().replace(b'custom-key = keep me',b'custom-key = keep me\r\nnew-graphics-key = 42');(root/'settings.ini').write_bytes(raw);call(root,'--recover');state(root,'stock');need(b'new-graphics-key = 42' in (root/'settings.ini').read_bytes(),'Concurrent unrelated setting survives recovery')
    root=case('unknown-file');rel=m['files'][3]['path'];q=root/'Content'/rel;q.write_bytes(q.read_bytes()+b'unknown');before=q.read_bytes();call(root,'--apply',expected=1);need(q.read_bytes()==before and not (root/'backups').exists(),'Unknown file refused without backup/game mutation')
    root=case('corrupt-delta');edge=next(e for e in m['files'][0]['edges'] if e['source']==stock[0] and e['target']==default[0]);q=bundle/edge['path'];before=q.read_bytes();q.write_bytes(before+b'bad');call(root,'--apply',expected=1);state(root,'stock');need(not (root/'backups').exists(),'Bad selected payload refused before creating backups');q.write_bytes(before)
    root=case('backup-corrupt');call(root,'--apply');q=next((root/'backups').rglob('original-00.bin'));before=q.read_bytes();q.write_bytes(before+b'bad');call(root,'--restore',expected=1);state(root,'k1-w1-d1-dub');q.write_bytes(before);call(root,'--restore');state(root,'stock')
    root=case('duplicate-settings');(root/'settings.ini').write_bytes(initial+b'GAME-LANGUAGE = English\r\n');call(root,'--apply',expected=1);state(root,'stock')
    root=case('unknown-guard');q=root/'Content/appxmanifest.xml';q.write_bytes(q.read_bytes()+b' ');call(root,'--apply',expected=1);state(root,'stock')
    for ident in ['full-dub','dub-captions','k0-w1-d0-off']:
        root=case('unowned-'+ident,ident);call(root,'--apply',expected=1);state(root,ident);need(not (root/'backups').exists(),'Unowned patched state cannot acquire restore ownership')
    root=case('receipt-binding');call(root,'--apply');q=next((root/'backups').rglob('receipt.json'));before=q.read_bytes();v=json.loads(before);v['root']+='other';save(q,v);call(root,'--restore',expected=1);state(root,'k1-w1-d1-dub');q.write_bytes(before);call(root,'--restore');state(root,'stock')
    report=dict(schema=1,status='PASS_SYNTHETIC_TRANSACTION_GRAPH',assertions=checks,profiles=len(m['profiles']),operations=operations,gameDataIncluded=False,installedGameWrites=0,sourceFiles={x:sha(REPO/x) for x in ['unified/source/Engine.cs','unified/source/Settings.cs','unified/source/GameCache.cs','dubbing/audio/VoiceCache.cs']})
    save(out/'report.json',report);print(json.dumps(dict(status=report['status'],assertions=checks,operations=len(operations),profiles=report['profiles'])))
if __name__=='__main__':main()
