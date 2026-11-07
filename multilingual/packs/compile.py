# SPDX-License-Identifier: MIT
"""Build one locale's data and resolved native inputs; never execute pack code."""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,io,json,math,re,shutil,struct,sys,zipfile
sys.dont_write_bytecode=True
from validation import load_pack,preserve_format,read_json
HERE=Path(__file__).resolve().parent
FONTS={'radio':'ca/res/art/fonts/kradio19_KO.bmf','story':'ca/res/art/fonts/kstory19_KO.bmf','credits':'ca/res/art/fonts/kcredits19_KO.bmf'}
BASE_FILES={'assets/localization/native_captions.json':'1174a5e34e1240a46453da9cdd3a38b0967ba01f107dabe5ba1515e94a2d59b7','assets/localization/unicode_ko.json':'22086e9564da8d44626eb236353f00489ee8e5ced7418a84622554b8171f21be','assets/config/font_metrics.json':'506629dfb20e49071901e80d7df3918178c64d764b7e0d737c81f5128b58ff84','native/stages/translations/tutorial.linebreak-proposals.json':'c0eb3b333d1d4b1ca2901652128be4ffe8d856c7410f49190943eff6cb940924'}
def sha(b):return hashlib.sha256(b).hexdigest()
def write_json(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf8')
def load_module(path,name):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def strings(raw):
 result={};positions={}
 for i,line in enumerate(raw.decode('utf-16le').splitlines(keepends=True)):
  m=re.fullmatch(r'(.*?) = "(.*)"\r\n',line)
  if not m:continue
  if m[1]in result:raise ValueError('Ambiguous original Unicode key '+m[1])
  result[m[1]]=m[2];positions[m[1]]=i
 return result,positions

def visible(text):return re.sub(r'~\[[^\]]+\]','',text)
def codepoints(text):return{ord(c)for c in visible(text)if c!='\n'}
def width(text,adv):return sum(adv.get(ord(c),0)for c in visible(text))
def wrap(text,adv):
 if '\n'in text:
  lines=text.split('\n')
  if max(width(x,adv)for x in lines)>560:raise ValueError('Explicit caption line exceeds560 nativepixels')
  return text,None
 if width(text,adv)<=360:return text,None
 choices=[]
 for i,c in enumerate(text):
  if c!=' 'or not text[:i].strip()or not text[i+1:].strip():continue
  a,b=width(text[:i],adv),width(text[i+1:],adv)
  if max(a,b)<=560:choices.append((max(a,b)>448,abs(a-b),max(a,b),i))
 if not choices:raise ValueError('Caption needs more than two lines; translate more concisely without changing audio/timing')
 at=min(choices)[3];return text[:at]+'\n'+text[at+1:],len(text[:at].encode('utf-16le'))//2

def raster_fonts(module,stock,config,font_path,required,extra):
 """The same pinned Noto BASIC raster algorithm as the canonical0.11 builder."""
 if sha(font_path.read_bytes())!=module.NOTO_SHA:raise ValueError('Wrong pinned Noto font')
 if(module.PIL.__version__,module.features.version_module('freetype2'),module.fontTools.__version__)!=('13.0.0','2.14.3','4.68.0'):raise ValueError('Use pinned Pillow13/FreeType2.14.3/fontTools4.68')
 cmap=module.TTFont(font_path).getBestCmap();face=module.ImageFont.truetype(str(font_path),17,layout_engine=module.ImageFont.Layout.BASIC)
 base=module.BMF(stock['ca/res/art/fonts/impact19Normal_KO.bmf']);result={'ca/res/art/fonts/kradio19.bmf':stock['ca/res/art/fonts/impact19Normal.bmf']};metrics=copy.deepcopy(config);added={};receipts=[]
 for f in metrics['fonts']:
  glyphs={g['codepoint']:g['advance']for g in f['glyphs']};missing=(required[f['member']]|set(extra))-glyphs.keys()
  if missing-cmap.keys():raise ValueError('Pinned Noto lacks glyphs: '+str(sorted(missing-cmap.keys())))
  for cp in sorted(missing):glyphs[cp]=max(1,min(255,int(math.floor(face.getlength(chr(cp))+.5))))
  f['glyphs']=[dict(codepoint=cp,advance=advance)for cp,advance in sorted(glyphs.items())];added[f['member']]=sorted(missing);records={}
  for cp,advance in sorted(glyphs.items()):
   if cp not in cmap:raise ValueError('Pinned Noto lacks U+%04X'%cp)
   if cp==0x2588:bmp=dict(width=17,height=19,advance=17,bearing_x=0,bearing_y=15,pixels=[4]*323)
   else:
    mask,offset=face.getmask2(chr(cp),mode='L',anchor='ls');image=module.Image.frombytes('L',mask.size,bytes(mask));crop=image.getbbox()
    if crop is None:bmp=dict(width=0,height=0,advance=advance,bearing_x=0,bearing_y=0,pixels=[])
    else:
     image=image.crop(crop);left=offset[0]+crop[0];top=offset[1]+crop[1];w,h=image.size;nw=min(w,max(1,advance));nh=min(h,19)
     if(nw,nh)!=(w,h):
      if 0xac00<=cp<=0xd7a3:raise ValueError('Hangul must not be squeezed')
      image=image.resize((nw,nh),module.Image.Resampling.LANCZOS)
     w,h=image.size;top=max(-15,min(top,4-h));left=max(0,(advance-w)//2)
     bmp=dict(width=w,height=h,advance=advance,bearing_x=left,bearing_y=-top,pixels=[min(4,(v*4+127)//255)for v in image.tobytes()])
   records[cp]=module.encode(bmp,4,2)
  data=base.rebuild(records);result[f['member']]=data;f['bytes']=len(data);f['sha256']=sha(data);receipts.append(dict(member=f['member'],bytes=len(data),sha256=sha(data),addedCodepoints=sorted(missing)))
 return result,metrics,receipts,added

def stored_zip(original,replacements):
 source=zipfile.ZipFile(io.BytesIO(original));infos={x.filename:x for x in source.infolist()};template=source.infolist()[0]
 for name in replacements.keys()-infos.keys():
  if name in['ca/res/art/fonts/kradio19.bmf','ca/res/art/fonts/kradio19_KO.bmf']:item=copy.copy(template);item.filename=name;item.orig_filename=name
  else:item=zipfile.ZipInfo(name,(1980,1,1,0,0,0));item.create_system=0;item.external_attr=0x1800000
  infos[name]=item
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED,allowZip64=False)as out:
  out.comment=source.comment
  for name in sorted(infos,key=str.lower):out.writestr(copy.copy(infos[name]),replacements[name]if name in replacements else source.read(name))
 compact=stream.getvalue();eocd=bytearray(compact[-22:]);central=struct.unpack_from('<I',eocd,16)[0];padding=len(original)-18-len(compact)
 if padding<0:raise ValueError('Locale exceeds fixed data.zip allocation by%d bytes'%(-padding))
 struct.pack_into('<I',eocd,16,central+padding)
 return compact[:central]+bytes(padding)+compact[central:-22]+eocd,padding

def compile_pack(pipeline,input_content,pack_path,font_path,out_dir):
 pipeline=Path(pipeline).resolve();source=Path(input_content).resolve();out=Path(out_dir).resolve();font_path=Path(font_path).resolve();pack_path=Path(pack_path).resolve()
 for other in[source,pipeline,pack_path.parent]:
  if out==other or out.is_relative_to(other)or other.is_relative_to(out):raise ValueError('Output must be disjoint from input, pipeline and pack sources')
 if out.exists()and any(out.iterdir()):raise ValueError('Output must be new or empty')
 for name,pin in BASE_FILES.items():
  if sha((pipeline/name).read_bytes())!=pin:raise ValueError('Unsupported canonical source version: '+name)
 manifest,overlays=load_pack(pack_path);assets=pipeline/'assets';sys.path.insert(0,str(assets));import db
 from package_io import Package,locate
 canonical=load_module(assets/'build.py','cs_canonical_assets');font_module=load_module(assets/'fonts.py','cs_canonical_fonts')
 with Package(source)as package:
  original=package.file('data.zip');names=db.globals_from_bytes(package.file('ConfigNames.bin'));archive=zipfile.ZipFile(io.BytesIO(original));fz=zipfile.ZipFile(io.BytesIO(package.file('fonts.zip')));stock_fonts={x.filename:fz.read(x)for x in fz.infolist()}
  unicode_plan=read_json(assets/'localization/unicode_ko.json');raw=canonical.unicode_edits(archive.read(unicode_plan['member']),unicode_plan);base,positions=strings(raw)
  native=read_json(assets/'localization/native_captions.json');parts={p['key']:p for e in native['entries']for p in e['parts']}
  if len(parts)!=sum(len(e['parts'])for e in native['entries']):raise ValueError('Ambiguous native caption keys')
  for kind,known in[('nativeCaptions',parts),('strings',base)]:
   unknown=overlays[kind].keys()-known.keys()
   if unknown:raise ValueError('Unknown '+kind+' keys: '+str(sorted(unknown)))
   for key,value in overlays[kind].items():
    if kind=='strings'and key.startswith('KR_CREDITS_BG_'):raise ValueError('Credits backplate is structural, not translatable: '+key)
    preserve_format(known[key]['text']if kind=='nativeCaptions'else known[key],value,key)
  if manifest['status']=='complete'and(set(overlays['nativeCaptions'])!=set(parts)or set(overlays['strings'])!={k for k in base if not k.startswith('KR_CREDITS_BG_')}):raise ValueError('A complete pack must explicitly supply every native and Unicode key')
  replacements={};cleanup=read_json(assets/'config/script_editor_cleanup.json')['scripts']
  for item in cleanup:
   old=archive.read(item['member'])
   if sha(old)!=item['sourceSha256']:raise ValueError('Unexpected script input')
   replacements[item['member']]=db.write(db.strip_descriptions(db.parse(old,names)))
  for filename in['tutorial.json','bink_subtitles.json','fonts_ko.json','pandoraplaneupgrade_screen.json']:
   plan=read_json(assets/'localization'/filename);replacements[plan['member']]=canonical.checked_plan(archive.read(plan['member']),names,plan)
  bink=db.parse(replacements['ca/res/bink_subtitles.db'],names);movie_keys=set();fold={k.casefold():k for k in base}
  for root in bink['roots']:
   if db.name(bink,root[0])!='_KO':continue
   for node in bink['nodes'][root[2]:root[2]+root[3]]:
    for k,t,v in bink['props'][node[1]:node[1]+node[2]]:
     if db.name(bink,k)=='Text'and t==4:
      key=db.cstring(bink['pool'],v).replace(' ','_').casefold()
      if key in fold:movie_keys.add(fold[key])
  def surface(key):return'structural'if key.startswith('KR_CREDITS_BG_')else'tutorial'if key.startswith('KR_SH_TUT_')else'credits'if key.startswith('KR_CREDITS_')else'movie'if key in movie_keys else'ui'
  groups={k:surface(k)for k in base};required={m:set()for m in FONTS.values()}
  for key,p in parts.items():p['text']=overlays['nativeCaptions'].get(key,p['text']);required[FONTS['radio']]|=codepoints(p['text'])
  for key,value in base.items():
   value=overlays['strings'].get(key,value);base[key]=value;group=groups[key]
   if group in['tutorial','movie','credits','structural']:required[FONTS['radio'if group=='tutorial'else'story'if group=='movie'else'credits']]|=codepoints(value)
   elif key in overlays['strings']:required[FONTS['radio']]|=codepoints(value)
  # UI keys may use any of the original KO Font1..9 registry fonts. A new
  # radio/story glyph does not repair those fonts: require the conservative
  # intersection of their actual source cmaps for every translated UI value.
  ui_fonts=['impact24Normal_KO.bmf','gillsans16normal_KO.bmf','anna38bold_KO.bmf','impact19Normal_KO.bmf'];ui_sets=[]
  for name in ui_fonts:
   matches=[b for n,b in stock_fonts.items()if n.casefold().endswith('/'+name.casefold())]
   if len(matches)!=1:raise ValueError('Expected source UI font '+name)
   ui_sets.append(set(font_module.BMF(matches[0]).index))
  ui_common=set.intersection(*ui_sets)
  for key,value in overlays['strings'].items():
   if groups[key]=='ui'and codepoints(value)-ui_common:raise ValueError('UI key needs unaudited original-font glyphs: '+key+' '+str(sorted(codepoints(value)-ui_common)))
  config=read_json(assets/'config/font_metrics.json');font_data,metrics,font_receipts,added=raster_fonts(font_module,stock_fonts,config,font_path,required,manifest['font']['extraCodepoints']);replacements.update(font_data)
  radio_adv={g['codepoint']:g['advance']for f in metrics['fonts']if f['member']==FONTS['radio']for g in f['glyphs']};layout=[]
  for key,value in overlays['strings'].items():
   group=groups[key]
   if group in['movie','credits']:
    adv={g['codepoint']:g['advance']for f in metrics['fonts']if f['member']==FONTS['story'if group=='movie'else'credits']for g in f['glyphs']}
    if len(value.encode('utf-16le'))//2>127 or width(value,adv)>560:raise ValueError('Movie/credits caption exceeds127 UTF16 units or560 nativepixels: '+key)
    layout.append(dict(key=key,lines=1,maximumLineWidth=width(value,adv)))
  for key in overlays['nativeCaptions']:
   p=parts[key];p['text'],at=wrap(p['text'],radio_adv);layout.append(dict(key=key,lines=p['text'].count('\n')+1,maximumLineWidth=max(width(x,radio_adv)for x in p['text'].split('\n'))))
  proposals=read_json(pipeline/'native/stages/translations/tutorial.linebreak-proposals.json')
  for item in proposals['entries']:
   if item['key']not in overlays['strings']:continue
   value=base[item['key']];wrapped,at=wrap(value,radio_adv);item.update(source_text=value,source_utf16le_sha256=sha(value.encode('utf-16le')),break_index_utf16=at,lines=wrapped.split('\n'))
   item.update(source_utf16_code_units=len(value.encode('utf-16le'))//2,source_utf8_sha256=sha(value.encode('utf8')),source_width_native_px=width(value,radio_adv),proposed_text=wrapped,line_widths_native_px=[width(x,radio_adv)for x in wrapped.split('\n')],reason='Locale compiler: source-owned radio advance metrics; replace one space with LF when needed')
   ws=item['line_widths_native_px'];item['line_width_ratio']=round(min(ws)/max(ws),4)if max(ws)else 1
   layout.append(dict(key=item['key'],lines=wrapped.count('\n')+1,maximumLineWidth=max(width(x,radio_adv)for x in wrapped.split('\n'))))
  if not manifest['id']=='ko-KR':
   proposals['status']='Generated locale-specific tutorial layout; original audio/timing unchanged'
   proposals['source_dictionary']=dict(kind='localeUnicodeOverlay',locale=manifest['id'],keys=[x['key']for x in proposals['entries']])
   proposals['font_measurement']=dict(kind='Generated radio BMF advance sum',font_member=FONTS['radio'],font_sha256=next(f['sha256']for f in metrics['fonts']if f['member']==FONTS['radio']))
  # Rewrite only explicitly changed values, retaining the exact baseline bytes.
  lines=raw.decode('utf-16le').splitlines(keepends=True)
  for key,value in overlays['strings'].items():lines[positions[key]]=key+' = "'+value+'"\r\n'
  translated_raw=''.join(lines).encode('utf-16le');replacements[unicode_plan['member']]=translated_raw
  original_values,original_positions=strings(archive.read(unicode_plan['member']));edit_by_key={x['key']:x for x in unicode_plan['edits']}
  for key,value in overlays['strings'].items():
   if key in original_values:edit_by_key[key]=dict(line=original_positions[key],key=key,text=value)
   else:
    item=next(x for x in unicode_plan['append']if x.get('key')==key);item['text']=value
  unicode_plan['edits']=list(edit_by_key.values());unicode_plan['targetSha256']=sha(translated_raw)
  final_zip,padding=stored_zip(original,replacements)
  if manifest['id']=='ko-KR'and sha(final_zip)!='bf74d3abea934bc4d480ba6da9ad62481597f12b9fad8508f11366d21f6fad64':raise ValueError('Canonical KO archive changed')
  out.mkdir(parents=True,exist_ok=True);resolved=out/'resolved/assets';shutil.copytree(assets,resolved,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
  write_json(resolved/'localization/native_captions.json',native);write_json(resolved/'localization/unicode_ko.json',unicode_plan);write_json(resolved/'config/font_metrics.json',metrics);write_json(out/'resolved/native/tutorial.linebreak-proposals.json',proposals)
  content=out/'Content';folder=content/'Game/DefaultPackage.data';folder.mkdir(parents=True);handles={}
  for name in['Data0000','Data0005']:shutil.copyfile(package.folder/name,folder/name);handles[name]=(folder/name).open('r+b')
  def patch(at,data):
   pos=0
   while pos<len(data):
    name,physical,within=locate(at+pos);n=min(4096-within,len(data)-pos)
    if name not in handles:raise ValueError('Unexpected target volume')
    handles[name].seek(physical);handles[name].write(data[pos:pos+n]);pos+=n
  try:
   entry=package.entry('data.zip');start=(entry['sector']-32)*2048;cs0=struct.unpack_from('<I',original,len(original)-10)[0];additions=['ca/res/art/fonts/kradio19_KO.bmf','ca/res/art/fonts/kradio19.bmf','ca/res/art/fonts/kcredits19_KO.bmf','ca/res/art/fonts/kstory19_KO.bmf']
   for shrink,nadd in[(6,0),(7,2),(8,2),(9,2),(13,3),(15,4),(16,4),(17,4)]:
    size=len(original)-shrink;n=len(archive.infolist())+nadd;cs=cs0+sum(46+len(x)for x in additions[:nadd]);patch(start+size-22,struct.pack('<IHHHHIIH',0x06054b50,0,0,n,n,cs,size-22-cs,0))
   patch(start,final_zip);patch(entry['sizeField'],struct.pack('<I',len(final_zip)))
  finally:
   for f in handles.values():f.close()
 files=[dict(path='Game/DefaultPackage.data/'+p.name,bytes=p.stat().st_size,sha256=sha(p.read_bytes()))for p in sorted(folder.iterdir())]
 if manifest['id']=='ko-KR'and any(f['sha256']!=canonical.TARGETS[Path(f['path']).name]for f in files):raise ValueError('Canonical KO output changed')
 coverage={};baseline=manifest['id']=='ko-KR'
 for group in['native','tutorial','movie','credits','ui']:
  keys=set(parts)if group=='native'else{k for k,g in groups.items()if g==group};given=overlays['nativeCaptions']if group=='native'else overlays['strings'];missing=[]if baseline else sorted(keys-given.keys())
  coverage[group]=dict(total=len(keys),explicitTranslations=len(keys&given.keys()),fallbackCount=len(missing),fallbackKeys=missing)
 report=dict(schema=1,baseRelease='0.11.0-beta.1',baseSourceHashes=BASE_FILES,featureVersion='0.12.0-alpha.1',locale=manifest,canonicalBaseline=baseline,coverage=coverage,fontCoverage=dict(source='Noto CJK KR Bold2.004/BASIC',fonts=font_receipts,uiPolicy='All translated UI glyphs must exist in every originalKO Font1..9 candidate; no UI raster replacement',uiCandidates=ui_fonts),layout=layout,files=files,dataZip=dict(bytes=len(final_zip),sha256=sha(final_zip),paddingBytes=padding),nativeInputs=dict(captions='resolved/assets/localization/native_captions.json',tutorialFormat='resolved/native/tutorial.linebreak-proposals.json',fontMetrics='resolved/assets/config/font_metrics.json'),limitations=['Original audio/part offsets/durations are unchanged.','Missing translations explicitly use the canonical Korean value.','Native DLL still must be built coherently from nativeInputs; these Datafiles alone are not a selectable installed locale.','BASIC BMP rendering only; RTL, combining shaping and non-BMP scripts rejected.','Source UI registry coverage is conservative; visual localization QA remains required.'])
 write_json(out/'locale-build.json',report)
 catalog=dict(schema=1,privateOriginalDependent=True,nativeCaptions={k:p['text']for k,p in parts.items()},strings={k:v for k,v in base.items()if groups[k]!='structural'},surfaces={k:v for k,v in groups.items()if v!='structural'},protectedKeys=sorted(k for k,v in groups.items()if v=='structural'))
 write_json(out/'catalog.private.json',catalog)
 return report

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pipeline',required=True,type=Path);p.add_argument('--input-content',required=True,type=Path);p.add_argument('--pack',required=True,type=Path);p.add_argument('--font',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();r=compile_pack(a.pipeline,a.input_content,a.pack,a.font,a.out);print(json.dumps(dict(locale=r['locale']['id'],files=r['files'],coverage={k:{x:y for x,y in v.items()if x!='fallbackKeys'}for k,v in r['coverage'].items()}),indent=2))