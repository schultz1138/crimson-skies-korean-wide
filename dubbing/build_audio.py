"""Repackage the pinned finalized Korean audio from owned before/after files.

This reproduces release deltas and installer from the finalized assets. It does
not call TTS or claim deterministic re-synthesis of the generated voices.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess
HERE=Path(__file__).resolve().parent;SRC=HERE/'audio';REPO=HERE.parent
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def run(args):
 env=dict(os.environ);env.pop('XDELTA',None);r=subprocess.run([str(x)for x in args],env=env,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=300)
 if r.returncode:raise RuntimeError((r.stdout+r.stderr).decode('utf-8','replace'))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-content',type=Path,required=True);p.add_argument('--dubbed-content',type=Path,required=True);p.add_argument('--xdelta',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 source=a.source_content.resolve();target=a.dubbed_content.resolve();out=a.out.resolve();assert not out.exists()and not out.is_relative_to(source)and not out.is_relative_to(target)
 manifest=json.loads((SRC/'manifest.json').read_text('utf-8'));assert sha(a.xdelta)==manifest['tool']['sha256']
 for f in manifest['files']:assert sha(source/f['path'])==f['sources'][0]['sourceSha256']and sha(target/f['path'])==f['targetSha256'],f['path']
 for g in manifest['guards']:assert sha(source/g['path'])==sha(target/g['path'])==g['sha256']
 out.mkdir(parents=True);(out/'patches').mkdir();(out/'tools').mkdir();shutil.copyfile(a.xdelta,out/'tools/xdelta3.exe');shutil.copyfile(SRC/'manifest.json',out/'manifest.json')
 for f in manifest['files']:
  s=f['sources'][0];delta=out/s['delta'];run([a.xdelta,'-e','-9','-D','-R','-s',source/f['path'],target/f['path'],delta]);assert delta.stat().st_size==s['deltaBytes']and sha(delta)==s['deltaSha256']
 csc=Path(os.environ.get('WINDIR',r'C:\Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
 run([csc,'/nologo','/codepage:65001','/target:winexe','/optimize+','/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Web.Extensions.dll','/r:System.Xml.dll','/r:System.Core.dll','/out:'+str(out/'KoreanDubInstaller.exe'),*[SRC/n for n in ['InstallerEngine.cs','NoSettings.cs','VoiceCache.cs','InstallerUi.cs','ReleasePins.cs']]])
 from package_common import notices
 notices(out);print('All21 VCDIFFs reproduce their published hashes. Installer rebuilt.')
if __name__=='__main__':main()
