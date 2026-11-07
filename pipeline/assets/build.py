"""Build the Korean data assets from user-owned stock Content and pinned Noto."""
from pathlib import Path
import argparse,copy,hashlib,io,json,re,shutil,struct,zipfile
import db
from db_edits import apply_plan
from fonts import build_fonts
from package_io import Package,locate,digest
HERE=Path(__file__).resolve().parent
TARGETS={'Data0000':'91f96697337e6717dcdfaa99eb321196c3521da33295e77e54fb6777c92ed487','Data0005':'68317f440ba24f74a832346f9ddf400f6a3076a743cd8e80b67be62aa5484e31'}
def sha(b):return hashlib.sha256(b).hexdigest()
def load(path):return json.loads((HERE/path).read_text('utf8'))
def checked_plan(data,names,plan):
 if sha(data)!=plan['sourceSha256']:raise ValueError('Unexpected source DB '+plan['member'])
 out=apply_plan(data,names,plan)
 if sha(out)!=plan['targetSha256']:raise ValueError('Semantic DB rebuild mismatch '+plan['member'])
 return out

def unicode_edits(source,plan):
 if sha(source)!=plan['sourceSha256']:raise ValueError('Unexpected original Korean string table')
 lines=source.decode('utf-16le').splitlines(keepends=True)
 for item in plan['edits']:
  old=lines[item['line']];key=old.split(' = ',1)[0]
  if key!=item['key']:raise ValueError('Korean string identity mismatch')
  lines[item['line']]=item['key']+' = "'+item['text']+'"\r\n'
 for item in plan['append']:lines.append('\r\n'if item.get('blank')else item['key']+' = "'+item['text']+'"\r\n')
 out=''.join(lines).encode('utf-16le')
 if sha(out)!=plan['targetSha256']:raise ValueError('Korean string rebuild mismatch')
 return out

def build_zip(original,replacements):
 """Preserve original ZIP member metadata and deterministic authored additions."""
 source=zipfile.ZipFile(io.BytesIO(original));infos={x.filename:x for x in source.infolist()}
 template=source.infolist()[0]
 for name in replacements.keys()-infos.keys():
  if name in['ca/res/art/fonts/kradio19.bmf','ca/res/art/fonts/kradio19_KO.bmf']:
   item=copy.copy(template);item.filename=name;item.orig_filename=name
  else:
   item=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));item.create_system=0;item.external_attr=0x1800000
  infos[name]=item
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED,allowZip64=False)as output:
  output.comment=source.comment
  for name in sorted(infos,key=str.lower):output.writestr(copy.copy(infos[name]),replacements[name]if name in replacements else source.read(name))
 compact=stream.getvalue();eocd=bytearray(compact[-22:])
 if eocd[:4]!=b'PK\x05\x06'or struct.unpack_from('<H',eocd,20)[0]:raise ValueError('Unexpected ZIP comment')
 central=struct.unpack_from('<I',eocd,16)[0];desired=len(original)-18;pad=desired-len(compact)
 if pad<0:raise ValueError('Assets exceed fixed original data.zip allocation')
 struct.pack_into('<I',eocd,16,central+pad)
 out=compact[:central]+bytes(pad)+compact[central:-22]+eocd
 if len(out)!=desired or sha(out)!='bf74d3abea934bc4d480ba6da9ad62481597f12b9fad8508f11366d21f6fad64':raise ValueError('Archive build mismatch '+sha(out))
 return out

def build(input_content,output_content,font_path,report_path=None):
 source=Path(input_content).resolve();output=Path(output_content).resolve()
 if output==source or output.is_relative_to(source)or source.is_relative_to(output):raise ValueError('Input and output Content must be separate trees')
 paths=[output/'Game/DefaultPackage.data'/n for n in TARGETS]
 if any(x.exists()for x in paths):raise ValueError('Refusing to overwrite existing output Data files')
 with Package(source)as package:
  original=package.file('data.zip');fonts_raw=package.file('fonts.zip');names=db.globals_from_bytes(package.file('ConfigNames.bin'))
  archive=zipfile.ZipFile(io.BytesIO(original));replacements={}
  cleanup=load('config/script_editor_cleanup.json')['scripts']
  for item in cleanup:
   raw=archive.read(item['member'])
   if sha(raw)!=item['sourceSha256']:raise ValueError('Unexpected script '+item['member'])
   rebuilt=db.write(db.strip_descriptions(db.parse(raw,names)))
   if sha(rebuilt)!=item['targetSha256']:raise ValueError('Editor cleanup mismatch '+item['member'])
   replacements[item['member']]=rebuilt
  for filename in['tutorial.json','bink_subtitles.json','fonts_ko.json','pandoraplaneupgrade_screen.json']:
   plan=load('localization/'+filename);member=plan['member'];replacements[member]=checked_plan(archive.read(member),names,plan)
  plan=load('localization/unicode_ko.json');replacements[plan['member']]=unicode_edits(archive.read(plan['member']),plan)
  fz=zipfile.ZipFile(io.BytesIO(fonts_raw));new_fonts,font_report=build_fonts({x.filename:fz.read(x)for x in fz.infolist()},font_path);replacements.update(new_fonts)
  final_zip=build_zip(original,replacements)
  for p in paths:p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(package.folder/p.name,p)
  handles={p.name:p.open('r+b')for p in paths}
  def write(at,data):
   pos=0
   while pos<len(data):
    name,physical,within=locate(at+pos);take=min(4096-within,len(data)-pos)
    if name not in handles:raise ValueError('Unexpected output volume')
    handles[name].seek(physical);handles[name].write(data[pos:pos+take]);pos+=take
  try:
   entry=package.entry('data.zip');start=(entry['sector']-32)*2048;central_size=struct.unpack_from('<I',original,len(original)-10)[0]
   # Historical cache generations left only ZIP EOCD metadata past the final EOF.
   # Regenerate those standard metadata records, rather than embed unused tail bytes.
   stages=[(6,0),(7,2),(8,2),(9,2),(13,3),(15,4),(16,4),(17,4)]
   additions=['ca/res/art/fonts/kradio19_KO.bmf','ca/res/art/fonts/kradio19.bmf','ca/res/art/fonts/kcredits19_KO.bmf','ca/res/art/fonts/kstory19_KO.bmf']
   for shrink,count in stages:
    size=len(original)-shrink;n=len(archive.infolist())+count;cs=central_size+sum(46+len(x)for x in additions[:count])
    write(start+size-22,struct.pack('<IHHHHIIH',0x06054b50,0,0,n,n,cs,size-22-cs,0))
   write(start,final_zip);write(entry['sizeField'],struct.pack('<I',len(final_zip)))
  finally:
   for f in handles.values():f.close()
 results=[]
 for p in paths:
  got=digest(p)
  if got!=TARGETS[p.name]:raise ValueError('Final volume mismatch '+p.name+': '+got)
  results.append(dict(path='Game/DefaultPackage.data/'+p.name,bytes=p.stat().st_size,sha256=got))
 report=dict(schema=1,operation='Original-owned extraction plus authored semantic localization and Noto rasterization',dataZip=dict(bytes=len(final_zip),sha256=sha(final_zip)),fontBuild=font_report,scriptEditorCleanupCount=len(cleanup),changedMembers=len(replacements),outputs=results)
 report_path=Path(report_path)if report_path else output/'assets-build.json';report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input-content',required=True);p.add_argument('--output-content',required=True);p.add_argument('--font',required=True);p.add_argument('--report');a=p.parse_args();print(json.dumps(build(a.input_content,a.output_content,a.font,a.report),ensure_ascii=False,indent=2))