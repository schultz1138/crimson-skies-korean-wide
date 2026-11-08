"""Notices and conservative release archive allowlist; excludes local game data."""
from pathlib import Path
import hashlib,shutil,zipfile
HERE=Path(__file__).resolve().parent;REPO=HERE.parent
def notices(out):
 out=Path(out);shutil.copytree(REPO/'licenses',out/'licenses',dirs_exist_ok=True);shutil.copyfile(REPO/'LICENSE',out/'LICENSE');shutil.copyfile(HERE/'AI-DUB-NOTICE.txt',out/'AI-DUB-NOTICE.txt')
 for language in ['ko','en']:
  text=(REPO/'docs'/('DUBBING.'+language+'.md')).read_text('utf-8-sig').replace('../dubbing/README.en.md','https://github.com/schultz1138/crimson-skies-korean-wide/blob/v0.13.0-alpha.2/dubbing/README.en.md')
  (out/('README.'+language+'.md')).write_text(text,encoding='utf-8')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def archive(bundle,destination,root_name):
 bundle=Path(bundle).resolve();destination=Path(destination).resolve();assert not destination.exists()and not destination.is_relative_to(bundle)
 allowed={'KoreanDubInstaller.exe','MultilingualLauncher.exe','PrepareSubtitleLauncher.exe','manifest.json','dub-caption-catalog.json','catalog.json','bootstrap.json','build-metadata.json','README.ko.md','README.en.md','LICENSE','AI-DUB-NOTICE.txt','CHECKSUMS.sha256','VERIFICATION.json'};rows=[]
 for p in sorted(bundle.rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(bundle).as_posix()
  if rel in ['captions/original.bin','captions/dub.bin']:continue
  assert not p.is_symlink()and(rel in allowed or rel=='tools/xdelta3.exe'or rel.startswith('patches/')and rel.endswith('.vcdiff')or rel.startswith('licenses/')and p.suffix=='.txt'),('Unexpected release file',rel)
  if rel!='CHECKSUMS.sha256':rows.append((rel,p))
 (bundle/'CHECKSUMS.sha256').write_text(''.join(sha(p)+'  '+rel+'\n'for rel,p in rows),encoding='utf-8');rows.append(('CHECKSUMS.sha256',bundle/'CHECKSUMS.sha256'))
 with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9,allowZip64=False)as z:
  for rel,p in sorted(rows):
   info=zipfile.ZipInfo(root_name+'/'+rel,(2026,11,9,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0x81a40000;z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
 with zipfile.ZipFile(destination)as z:assert z.testzip()is None and len(z.namelist())==len(rows)
 return dict(name=destination.name,bytes=destination.stat().st_size,sha256=sha(destination),files=len(rows),noRawGameFiles=True)
