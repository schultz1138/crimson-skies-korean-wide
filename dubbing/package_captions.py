"""Package public Alpha2 captions as VCDIFF; no raw game/payload files shipped."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess
HERE=Path(__file__).resolve().parent;SRC=HERE/'captions';CSC=Path(os.environ.get('WINDIR',r'C:\Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
CS=['MultilingualCore.cs','MenuAndSettings.cs','MultilingualUi.cs','CaptionSpanEngine.cs','ProfileManagerUi.cs','ProfileManagerBackend.cs','ProfileStore.cs','ProfileBackup.cs','ProfileOperations.cs','ProfileTombstone.cs','ProfileRestoreImage.cs','ProfileRestoreOperations.cs']
REFS=['System.Windows.Forms.dll','System.Drawing.dll','System.Web.Extensions.dll','System.Xml.dll','System.Core.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll','System.Security.dll']
TOOL_SHA='732980d52f9220dc81817ccdd0c295eadce8a0048a24c2a771a73f791ac824e9'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_text('utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def run(args,cwd=None):
 env=dict(os.environ);env.pop('XDELTA',None);r=subprocess.run([str(x)for x in args],cwd=cwd,env=env,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=300)
 if r.returncode:raise RuntimeError((r.stdout+r.stderr).decode('utf-8','replace'))
def build(base,target,tool,out):
 base=base.resolve();target=target.resolve();out=out.resolve();assert not out.exists()and not out.is_relative_to(base)and not out.is_relative_to(target)
 assert sha(tool)==TOOL_SHA;catalog=load(SRC/'dub-caption-catalog.json');assert len(catalog['files'])==3
 for i,f in enumerate(catalog['files']):assert sha(base/f['path'])==catalog['styles'][0]['hashes'][i]and sha(target/f['path'])==catalog['styles'][1]['hashes'][i]
 out.mkdir(parents=True);(out/'tools').mkdir();(out/'patches').mkdir();shutil.copyfile(tool,out/'tools/xdelta3.exe')
 shutil.copyfile(SRC/'dub-caption-catalog.json',out/'dub-caption-catalog.json');shutil.copyfile(SRC/'catalog.json',out/'catalog.json');deltas=[]
 compile_dir=out/'.compile';compile_dir.mkdir()
 for i,f in enumerate(catalog['files']):
  pair=dict(fileIndex=i)
  for direction,a,b in [('forward',base,target),('reverse',target,base)]:
   rel='patches/caption-'+str(i)+'-'+direction+'.vcdiff';p=out/rel
   run([tool,'-e','-9','-D','-R','-s',a/f['path'],b/f['path'],p]);decoded=compile_dir/'decoded.bin'
   run([tool,'-d','-D','-R','-s',a/f['path'],p,decoded]);assert sha(decoded)==sha(b/f['path']);decoded.unlink()
   pair[direction]=dict(path=rel,bytes=p.stat().st_size,sha256=sha(p))
  deltas.append(pair)
 legacy=load(SRC/'catalog.json');pins=compile_dir/'Pins.cs'
 pins.write_text('namespace CrimsonSkiesMultilingual {public static class CatalogPin {public const string Digest="'+sha(SRC/'catalog.json')+'";public const string ReleaseId="'+legacy['releaseId']+'";}public static class CaptionCatalogPin {public const string Digest="'+sha(SRC/'dub-caption-catalog.json')+'";}}',encoding='utf-8')
 # Short compile basenames keep the legacy .NET compiler's working set portable.
 sources=[]
 for i,name in enumerate(CS):p=compile_dir/('s'+str(i)+'.cs');shutil.copyfile(SRC/'launcher'/name,p);sources.append(p.name)
 run([CSC,'/nologo','/codepage:65001','/target:winexe','/optimize+','/out:MultilingualLauncher.exe',*['/r:'+r for r in REFS],*sources,'Pins.cs'],compile_dir)
 shutil.copyfile(compile_dir/'MultilingualLauncher.exe',out/'MultilingualLauncher.exe')
 boot=dict(schema=1,catalogSha256=sha(out/'dub-caption-catalog.json'),legacyCatalogSha256=sha(out/'catalog.json'),launcherSha256=sha(out/'MultilingualLauncher.exe'),toolSha256=TOOL_SHA,deltas=deltas)
 save(out/'bootstrap.json',boot);(compile_dir/'BootstrapPin.cs').write_text('namespace CrimsonSkiesCaptionSetup {public static class BootstrapPin {public const string Digest="'+sha(out/'bootstrap.json')+'";}}',encoding='utf-8');shutil.copyfile(SRC/'CaptionSetup.cs',compile_dir/'CaptionSetup.cs')
 run([CSC,'/nologo','/codepage:65001','/target:winexe','/optimize+','/out:PrepareSubtitleLauncher.exe',*['/r:'+r for r in REFS],'CaptionSetup.cs','BootstrapPin.cs'],compile_dir)
 shutil.copyfile(compile_dir/'PrepareSubtitleLauncher.exe',out/'PrepareSubtitleLauncher.exe')
 # Delete only this builder's exact named compile products, never recurse.
 for p in list(compile_dir.iterdir()):assert p.is_file()and not p.is_symlink();p.unlink()
 compile_dir.rmdir()
 save(out/'build-metadata.json',dict(schema=1,captionSourceGameFilesExact=True,captionCatalogSha256=boot['catalogSha256'],bootstrapSha256=sha(out/'bootstrap.json'),deltaBytes=sum(x[d]['bytes']for x in deltas for d in ['forward','reverse']),payloadsGeneratedOnlyOnUsersMachine=True,originalGameFilesIncluded=False))
 from package_common import notices
 notices(out)
 print(json.dumps(dict(status='PUBLIC_CAPTION_DIFF_PACKAGE_BUILT',out=str(out),deltaBytes=sum(x[d]['bytes']for x in deltas for d in ['forward','reverse']))))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--full-dub-content',required=True,type=Path);p.add_argument('--caption-content',required=True,type=Path);p.add_argument('--xdelta',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();build(a.full_dub_content,a.caption_content,a.xdelta,a.out)
if __name__=='__main__':main()
