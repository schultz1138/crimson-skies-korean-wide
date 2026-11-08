"""Rebuild Alpha2 caption game files from the Full Dub Beta1 owned baseline.

No TTS, game execution or installed-file mutation. Requires the pinned public
pipeline Python dependencies and Noto Sans CJK KR Bold2.004.
"""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,io,json,math,shutil,struct,sys,zipfile
HERE=Path(__file__).resolve().parent;REPO=HERE.parent;DATA=HERE/'captions'
sys.path[:0]=[str(REPO/'pipeline/assets'),str(DATA)]
import db
from bmf import BMF,encode
from package_io import Package,locate
import native_inplace
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_text('utf-8-sig'))
def font_bytes(raw,required,font):
 from PIL import Image,ImageFont,features
 import PIL,fontTools
 from fontTools.ttLib import TTFont
 assert(PIL.__version__,features.version_module('freetype2'),fontTools.__version__)==('13.0.0','2.14.3','4.68.0')
 assert sha(font)=='26d0c6748500a0444844280b308f5b62c7ae92ac6c6ac88148e502dd211eb52a'
 base=BMF(raw);records=dict(base.records);face=ImageFont.truetype(str(font),17,layout_engine=ImageFont.Layout.BASIC);cmap=TTFont(str(font)).getBestCmap()
 for cp in sorted(required-records.keys()):
  assert cp>=32 and cp in cmap;advance=max(1,min(255,int(math.floor(face.getlength(chr(cp))+.5))))
  mask,offset=face.getmask2(chr(cp),mode='L',anchor='ls');im=Image.frombytes('L',mask.size,bytes(mask));crop=im.getbbox()
  if crop is None:bmp=dict(width=0,height=0,advance=advance,bearing_x=0,bearing_y=0,pixels=[])
  else:
   im=im.crop(crop);left=offset[0]+crop[0];top=offset[1]+crop[1];width,height=im.size;nw=min(width,max(1,advance));nh=min(height,19)
   if(nw,nh)!=(width,height):
    assert not 0xac00<=cp<=0xd7a3;im=im.resize((nw,nh),Image.Resampling.LANCZOS)
   width,height=im.size;top=max(-15,min(top,4-height));left=max(0,(advance-width)//2)
   bmp=dict(width=width,height=height,advance=advance,bearing_x=left,bearing_y=-top,pixels=[min(4,(v*4+127)//255)for v in im.tobytes()])
  records[cp]=encode(bmp,4,2)
 result=base.rebuild(records)if set(records)!=set(base.records)else raw;parsed=BMF(result)
 assert all(parsed.records[k]==v for k,v in base.records.items());return result
def movie_database(raw,names):
 import re
 d=db.parse(raw,names);old=copy.deepcopy(d);global_keys={n:(~i)&65535 for i,n in enumerate(d['names'])};local_keys={db.cstring(d['pool'],p):i for i,p in enumerate(d['local'])}
 def string(s):
  assert s and s.isascii()and'\0'not in s;at=len(d['pool']);d['pool']+=s.encode('ascii')+b'\0';return at
 def key(s):
  if s in global_keys:return global_keys[s]
  if s not in local_keys:local_keys[s]=len(d['local']);d['local'].append(string(s));assert len(d['local'])<32768
  return local_keys[s]
 rows=load(DATA/'movie-lines.json');silent={s.casefold()for s in load(DATA/'silent-titles.json')};movies={r['nativeNodeName'].rsplit('_Subtitle',1)[0].casefold()for r in rows};new=[]
 for r in rows:
  first=len(d['props'])
  for k,v in sorted(r['properties'].items()):d['props'].append([key(k),4,string(v)]if isinstance(v,str)else[key(k),0,v&0xffffffff])
  assert first<65536;new.append([key(r['nativeNodeName']),first,len(r['properties'])])
 nodes=[]
 for root in sorted(d['roots'],key=lambda r:r[2]):
  keep=[];ko=db.name(d,root[0])=='_KO'
  for n in old['nodes'][root[2]:root[2]+root[3]]:
   name=db.name(d,n[0]);m=re.fullmatch(r'(.+\.bik)_Subtitle(\d+)',name,re.I)
   if ko and m and m[1].casefold()in movies and name.casefold()not in silent:continue
   keep.append(n)
  if ko:keep+=new;keep.sort(key=lambda n:db.name(d,n[0]).casefold())
  root[2]=len(nodes);root[3]=len(keep);nodes+=keep
 d['nodes']=nodes;result=db.write(d)
 assert hashlib.sha256(result).hexdigest()=='9273af73e1782760c8a3d86a6528cfbd996fa463f0af5ceed1db0d19cf7eb098';return result
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--full-dub-content',type=Path,required=True);p.add_argument('--font',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 content=a.full_dub_content.resolve();out=a.out.resolve();assert not out.exists()and not out.is_relative_to(content)and not content.is_relative_to(out)
 catalog=load(DATA/'dub-caption-catalog.json')
 for f in catalog['files']:assert sha(content/f['path'])==f['baselineSha256'],f['path']
 out.mkdir(parents=True);target=out/'Content';target.mkdir()
 native=catalog['files'][0]['path'];b,proof=native_inplace.build(content/native,DATA/'native_captions.json',DATA/'tutorial-format.json');(target/native).write_bytes(b)
 with Package(content,verify=False)as package:
  raw=package.file('data.zip');arc=zipfile.ZipFile(io.BytesIO(raw));names=db.globals_from_bytes(package.file('ConfigNames.bin'));entry=package.entry('data.zip')
  logical=(entry['sector']-32)*2048;size_field=entry['sizeField']
 movie=load(DATA/'movie-unicode.json');tutorial=load(DATA/'tutorial-unicode.json');caps=load(DATA/'native_captions.json')
 required_radio={ord(c)for e in caps['entries']for part in e['parts']for c in part['text']if ord(c)>=32}|{ord(c)for text in tutorial.values()for c in text if ord(c)>=32}
 required_story={ord(c)for text in movie.values()for c in text if ord(c)>=32}
 # Retained title cards may contribute glyphs already present in the baseline.
 replacements={}
 for name,required in [('kradio19_KO.bmf',required_radio),('kstory19_KO.bmf',required_story)]:
  member='ca/res/art/fonts/'+name;replacements[member]=font_bytes(arc.read(member),required,a.font)
 replacements['ca/res/bink_subtitles.db']=movie_database(arc.read('ca/res/bink_subtitles.db'),names)
 import re
 member='ca/res/config/unicode_KO.dat';lines=arc.read(member).decode('utf-16le').splitlines(keepends=True);indices={}
 for i,line in enumerate(lines):
  match=re.fullmatch(r'(.*?) = "(.*)"\r\n',line)
  if match:indices[match[1]]=i
 for key,value in tutorial.items():assert key in indices;lines[indices[key]]=key+' = "'+value+'"\r\n'
 for key,value in movie.items():assert key not in indices;lines.append(key+' = "'+value+'"\r\n')
 replacements[member]=''.join(lines).encode('utf-16le')
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED,allowZip64=False)as z:
  z.comment=arc.comment
  for info in arc.infolist():assert info.compress_type==zipfile.ZIP_STORED;z.writestr(copy.copy(info),replacements.get(info.filename,arc.read(info.filename)))
 compact=stream.getvalue();assert compact[-22:-18]==b'PK\x05\x06'and compact[-2:]==b'\0\0';end=bytearray(compact[-22:]);central=struct.unpack_from('<I',end,16)[0]
 # Distinct logical sizes are required by the game's size-only HDD cache. Its
 # ZIP scanner insists on EOCD at EOF-22, so comments cannot be used here.
 pad=len(raw)+1-len(compact);assert pad>=0;struct.pack_into('<I',end,16,central+pad)
 final=compact[:central]+bytes(pad)+compact[central:-22]+bytes(end);assert len(final)==len(raw)+1
 assert hashlib.sha256(final).hexdigest()=='0a232e5e056d7aeebda48a492afcfc112774827cdab7d8f226fb9d504dc60848'
 folder=target/'Game/DefaultPackage.data';folder.mkdir(parents=True)
 for name in ['Data0000','Data0005']:shutil.copyfile(content/'Game/DefaultPackage.data'/name,folder/name)
 pos=0
 while pos<len(final):
  name,physical,within=locate(logical+pos);take=min(4096-within,len(final)-pos)
  with(folder/name).open('r+b')as f:f.seek(physical);f.write(final[pos:pos+take])
  pos+=take
 name,physical,within=locate(size_field);assert within<=4092
 with(folder/name).open('r+b')as f:f.seek(physical);f.write(struct.pack('<I',len(final)))
 hashes=[sha(target/f['path'])for f in catalog['files']];assert hashes==catalog['styles'][1]['hashes']
 report=dict(schema=1,status='PASS_ALPHA2_SOURCE_REPRODUCTION',targetHashes=hashes,changedMembers=sorted(replacements),logicalArchiveBytes=len(final),native=proof,gameWrites=0,ttsCalls=0)
 (out/'source-build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(status=report['status'],targetHashes=hashes)))
if __name__=='__main__':main()
