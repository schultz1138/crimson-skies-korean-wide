# SPDX-License-Identifier: MIT
"""Source-build the 0.12 multilingual add-on as deltas against installed 0.11 KO.

The private work tree holds original-dependent complete game files. Only the
explicit bundle allowlist is distributable. Nothing is installed or launched.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,shutil,stat,struct,subprocess,sys,zipfile
sys.dont_write_bytecode=True
RELEASE='CrimsonSkies-Multilingual-0.12.0-alpha.1'
TOOL_SHA='732980d52f9220dc81817ccdd0c295eadce8a0048a24c2a771a73f791ac824e9'
FONT_SHA='26d0c6748500a0444844280b308f5b62c7ae92ac6c6ac88148e502dd211eb52a'
MANIFEST_SHA='f80c775038edd5673fee39362d5e82e607353ceb0ee59bfeea2776172ba4251e'
NATIVE='xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll'
FILES=[NATIVE,'Game/DefaultPackage.data/Data0000','Game/DefaultPackage.data/Data0005']
FOUNDATION={NATIVE:'45c2c716da6c01f0937ce922dbfe2de89a3a9dfb163578757cfc5c5cc7e65f44',
 FILES[1]:'91f96697337e6717dcdfaa99eb321196c3521da33295e77e54fb6777c92ed487',
 FILES[2]:'68317f440ba24f74a832346f9ddf400f6a3076a743cd8e80b67be62aa5484e31',
 'VGPUDX12.dll':'f4d7784a007919a1e397405340855ac539c76f4abccfc6ecf8edebb2ed9835aa',
 'EmuMenu/Assets/TitleMenuData.json':'200b609e7b279c25814fb42ed1dd1cdcd6f3203b670dc3b05749a6ee26686265'}
LICENSES=['BLAKE3-LICENSE-Apache.txt','FONT-NOTICE.txt','Installer-MIT.txt','OFL-NotoSansCJK.txt','THIRD-PARTY-NOTICES.txt','xdelta-LICENSE.txt','XZ-COPYING.txt','XZ-LICENSE-0BSD.txt']
CS=['MultilingualCore.cs','MenuAndSettings.cs','MultilingualUi.cs']
ENGLISH={'ko-KR':'Korean (baseline)','en-US':'English (partial starter)','es-ES':'Spanish (5-part sample)'}
DELTA_NAMES=['native.vcdiff','data0000.vcdiff','data0005.vcdiff']
MAX_DELTA=16*1024*1024

def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def require(ok,message):
 if not ok:raise ValueError(message)
def load(path):return json.loads(Path(path).read_text('utf8'))
def write(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf8')
def separated(a,b):return a!=b and not a.is_relative_to(b)and not b.is_relative_to(a)
def module(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def execute(label,args,log,timeout=1200,cwd=None):
 environment=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHONIOENCODING='utf-8');environment.pop('PYTHONPATH',None);environment.pop('XDELTA',None)
 print(json.dumps(dict(stage=label,state='starting')),flush=True)
 r=subprocess.run([str(x)for x in args],cwd=cwd,env=environment,capture_output=True,timeout=timeout)
 log.parent.mkdir(parents=True,exist_ok=True);log.write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(label+' failed: '+(r.stdout+r.stderr).decode('utf8',errors='replace')[-6000:])
 print(json.dumps(dict(stage=label,state='passed')),flush=True)

def coverage_line(report):
 if report['canonicalBaseline']:prefix='Canonical Korean baseline; no translation overrides.'
 else:prefix='Partial translation; missing text uses Korean (ko-KR).'if report['locale']['status']=='partial'else'Complete key coverage; linguistic/gameplay QA still required.'
 counts=[]
 for name in['native','tutorial','movie','credits','ui']:
  c=report['coverage'][name];n=c['total']if report['canonicalBaseline']else c['explicitTranslations'];counts.append(name+' '+str(n)+'/'+str(c['total']))
 value=prefix+' '+', '.join(counts)+'.'
 require(len(value)<=512 and not any(ord(c)<32 for c in value),'Coverage summary must be bounded plain text')
 return value

def private_type_guid_fields(data):
 """Locate only the C# compiler-owned private TypeDef's #Strings GUID."""
 import pefile,re
 p=pefile.PE(data=bytes(data));cli=p.get_offset_from_rva(p.OPTIONAL_HEADER.DATA_DIRECTORY[14].VirtualAddress)
 metadata=p.get_offset_from_rva(struct.unpack_from('<I',data,cli+8)[0]);require(data[metadata:metadata+4]==b'BSJB','Missing CLI metadata')
 at=(metadata+16+struct.unpack_from('<I',data,metadata+12)[0]+3)&~3;count=struct.unpack_from('<H',data,at+2)[0];at+=4;streams={}
 require(1<=count<=16,'Unexpected CLI stream count')
 for _ in range(count):
  offset,size=struct.unpack_from('<II',data,at);end=data.index(0,at+8,min(at+40,len(data)));name=bytes(data[at+8:end]).decode('ascii');require(metadata+offset+size<=len(data),'CLI stream exceeds image');streams[name]=(metadata+offset,size);at=(end+4)&~3
 tables=streams.get('#~',streams.get('#-'));require(tables is not None and '#Strings'in streams,'Missing CLI tables/strings')
 start=tables[0];heaps=data[start+6];valid=struct.unpack_from('<Q',data,start+8)[0];cursor=start+24;rows={}
 for table in range(64):
  if valid&(1<<table):rows[table]=struct.unpack_from('<I',data,cursor)[0];cursor+=4
 string_size=4 if heaps&1 else 2;guid_size=4 if heaps&2 else 2
 scope_size=4 if max(rows.get(t,0)for t in[0,26,35,1])>=16384 else 2
 type_ref_size=4 if max(rows.get(t,0)for t in[2,1,27])>=16384 else 2
 cursor+=rows.get(0,0)*(2+string_size+guid_size*3)+rows.get(1,0)*(scope_size+string_size*2)
 row_size=4+string_size*2+type_ref_size+(4 if rows.get(4,0)>=65536 else 2)+(4 if rows.get(6,0)>=65536 else 2)
 require(rows.get(2,0)<=4096,'TypeDef table exceeds finite compiler boundary');heap,heap_size=streams['#Strings'];owners=[];prefix='<PrivateImplementationDetails>{'
 for index in range(rows.get(2,0)):
  row=cursor+index*row_size;flags=struct.unpack_from('<I',data,row)[0];name_index=int.from_bytes(data[row+4:row+4+string_size],'little');namespace_index=int.from_bytes(data[row+4+string_size:row+4+string_size*2],'little')
  require(name_index<heap_size,'Invalid TypeDef string index');position=heap+name_index;end=data.index(0,position,heap+heap_size);name=bytes(data[position:end]).decode('utf8')
  if not name.startswith('<PrivateImplementationDetails>'):continue
  require(flags==0 and namespace_index==0 and re.fullmatch(r'<PrivateImplementationDetails>\{[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}\}',name)is not None,'Unexpected compiler-generated private TypeDef identity')
  owners.append(dict(typeDefRow=index+1,typeDefRowFileOffset=row,typeFlags=flags,namespaceIndex=namespace_index,stringIndex=name_index,stringFileOffset=position,guidFileOffset=position+len(prefix),guidBytes=36,stringsHeapFileOffset=heap,stringsHeapBytes=heap_size))
 require(len(owners)<=1,'Unexpected multiple private implementation identity types');return owners

def normalize_launcher(path,repo,source_digest):
 """Canonicalize three compiler build identities; never rewrite IL/code."""
 helper=module(repo/'pipeline/installer_repro.py','cs_identity_locations');data=bytearray(path.read_bytes());before=bytes(data);stamp,mvid=helper.metadata_locations(data)
 identity=hashlib.sha256(('CS-Multilingual-Launcher-identity-v1:'+source_digest).encode('ascii')).digest()[:16]
 struct.pack_into('<I',data,stamp,0);data[mvid:mvid+16]=identity;allowed=set(range(stamp,stamp+4))|set(range(mvid,mvid+16));owners=private_type_guid_fields(data)
 private_hex=hashlib.sha256(('CS-Multilingual-PrivateImpl-identity-v1:'+source_digest).encode('ascii')).hexdigest()[:32].upper();private_guid='-'.join([private_hex[:8],private_hex[8:12],private_hex[12:16],private_hex[16:20],private_hex[20:]])
 for owner in owners:
  at=owner['guidFileOffset'];data[at:at+36]=private_guid.encode('ascii');allowed.update(range(at,at+36));owner['canonicalGuid']=private_guid
 require(len(data)==len(before)and all(a==b or i in allowed for i,(a,b)in enumerate(zip(before,data))),'Launcher normalization changed code/other metadata')
 path.write_bytes(data)
 return dict(sha256=digest(path),timestamp=0,mvidHex=identity.hex(),timestampOffset=stamp,mvidOffset=mvid,compilerGeneratedPrivateTypeGuids=owners,onlyIdentityFieldsCanonicalized=True,ilAndOtherMetadataByteExact=True)

def compile_launcher(repo,stage,private,catalog_sha,skip,csc=None):
 csc=Path(csc or Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe').resolve()
 compiler=private/'csc';compiler.mkdir();pin=compiler/'AutoGenerateCatalogPin.cs'
 pin.write_text('namespace CrimsonSkiesMultilingual { public static class CatalogPin { public const string Digest = "'+catalog_sha+'"; public const string ReleaseId = "'+RELEASE+'"; } }\n','utf8')
 if skip:
  (stage/'STAGING-NOT-DISTRIBUTABLE.txt').write_text('Launcher compilation was deliberately skipped. This staging folder is NOT a distributable release.\n','utf8')
  return dict(compiled=False,distributable=False,reason='--skip-launcher')
 require(csc.is_file(),'Windows .NET Framework x64 C# compiler is required')
 source_hashes={};short=[]
 for i,name in enumerate(CS):
  source=repo/'multilingual/launcher'/name;require(source.is_file(),'Launcher source not ready: '+name);source_hashes[name]=digest(source);destination=compiler/('s'+str(i)+'.cs');shutil.copyfile(source,destination);require(digest(destination)==source_hashes[name],'Launcher source changed while copying');short.append(destination.name)
 output=compiler/'MultilingualLauncher.exe';require(len(str(output))<250,'Use a shorter --out path for the legacy Windows C# compiler')
 command=[csc,'/nologo','/codepage:65001','/target:winexe','/optimize+','/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Web.Extensions.dll','/r:System.Xml.dll','/r:System.Core.dll','/out:MultilingualLauncher.exe',*short,pin.name]
 execute('compile-owned-launcher',command,private/'logs/launcher.log',300,compiler)
 seed=hashlib.sha256((catalog_sha+''.join(k+v for k,v in sorted(source_hashes.items()))).encode('ascii')).hexdigest();identity=normalize_launcher(output,repo,seed)
 shutil.copyfile(output,stage/output.name)
 return dict(compiled=True,distributable=True,compilerSha256=digest(csc),sourceHashes=source_hashes,catalogSha256=catalog_sha,identity=identity)

def bundle_readme():
 return RELEASE+'\n\nRequires the installed CrimsonSkies-KO-Wide-0.11.0-beta.1 foundation (all five exact target files). This add-on does not upgrade stock games.\n\nSave your progress and close both the game and the original Play window. Open MultilingualLauncher.exe, select the game folder and a language pack, click Check, then Apply & open. The tool applies the matching Native/Data0000/Data0005 set and opens the original Play window. It never closes the game for you.\n\nRestore returns to the canonical 0.11 Korean foundation, NOT to the stock game. Existing backups made by the old 0.11 installer are kept; use that installer for its original stock recovery workflow. Before using a rebuilt catalog or adding a new language bundle, use the old exact launcher to Restore 0.11 first. Keep the old bundle and its backups.\n\nEnglish and Spanish are explicitly partial examples. Missing entries fall back to Korean (ko-KR). Original audio and timing are unchanged.\n\nEnglish guide: https://github.com/schultz1138/crimson-skies-korean-wide/blob/main/docs/MULTILINGUAL.en.md\nKorean guide: https://github.com/schultz1138/crimson-skies-korean-wide/blob/main/docs/MULTILINGUAL.ko.md New languages are built from declarative source packs.\n\nThis bundle contains forward deltas, a pinned xdelta tool and the owned patch launcher. It contains no original/complete game DLLs, Data volumes, fonts or movies.\n'

def finish_distribution(stage,output,allowed,summary,skip_launcher):
 actual={p.relative_to(stage).as_posix()for p in stage.rglob('*')if p.is_file()};require(actual==allowed-{'CHECKSUMS.sha256'},'Unexpected or missing public bundle members: '+str(actual^(allowed-{'CHECKSUMS.sha256'})))
 require(not any(p.lower().endswith(('.dll','.otf','.bmf'))or Path(p).name in['Data0000','Data0005']for p in actual),'An original-dependent full game/font file leaked into the bundle')
 (stage/'CHECKSUMS.sha256').write_text(''.join(digest(stage/n)+'  '+n+'\n'for n in sorted(actual)),'ascii',newline='\n')
 inventory=[dict(path=n,bytes=(stage/n).stat().st_size,sha256=digest(stage/n))for n in sorted(allowed)]
 archive=None
 if not skip_launcher:
  archive=output/(RELEASE+'.zip')
  with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9)as zipped:
   for n in sorted(allowed):
    info=zipfile.ZipInfo(RELEASE+'/'+n,(2026,11,7,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.create_system=3;info.external_attr=(stat.S_IFREG|0o644)<<16;zipped.writestr(info,(stage/n).read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
  archive.with_suffix(archive.suffix+'.sha256').write_text(digest(archive)+'  '+archive.name+'\n','ascii')
 return archive,inventory

def bundle_build(original,dependencies,output,repo,pack_root=None,skip_launcher=False,csc=None):
 require(os.name=='nt'and sys.maxsize>2**32,'Reference bundle build requires Windows x64')
 original,dependencies,output,repo=map(lambda p:Path(p).resolve(),[original,dependencies,output,repo]);pack_root=Path(pack_root).resolve()if pack_root else repo/'multilingual/packs/locales'
 require(not output.exists(),'Use a new --out directory')
 for source in[original,dependencies,repo,pack_root]:require(separated(output,source),'Build output must be disjoint from input/dependencies/repository/packs')
 pipeline=repo/'pipeline';pack_tools=repo/'multilingual/packs';runtime=repo/'multilingual/runtime/native_variant.py'
 require(digest(repo/'manifest.json')==MANIFEST_SHA,'The canonical0.11 foundation manifest differs')
 foundation=load(repo/'manifest.json');require({x['path']:x['targetSha256']for x in foundation['files']}==FOUNDATION,'Foundation five target hashes differ')
 tool=dependencies/'xdelta3.exe';font=dependencies/'NotoSansCJKkr-Bold.otf';require(tool.stat().st_size==340992 and digest(tool)==TOOL_SHA,'Wrong pinned xdelta3 tool');require(digest(font)==FONT_SHA,'Wrong pinned Noto input')
 require(runtime.is_file()and(pack_tools/'compile.py').is_file(),'Multilingual source files are not assembled under the repository')
 sys.path.insert(0,str(pack_tools));validation=module(pack_tools/'validation.py','cs_source_pack_validation');entries=validation.registry(pack_root)
 require(1<=len(entries)<=32 and any(x['id']=='ko-KR'for x in entries),'Expected1..32 packs including canonical ko-KR')
 for entry in entries:require((pack_root/entry['manifest']).resolve().is_relative_to(pack_root),'Pack manifest escapes the selected pack root')
 entries.sort(key=lambda x:(x['id']!='ko-KR',x['id']))
 if not skip_launcher:
  for name in CS:require((repo/'multilingual/launcher'/name).is_file(),'Launcher source not ready: '+name+'; --skip-launcher is staging only')
 before={x['path']:digest(original/x['path'])for x in foundation['files']}
 for i,x in enumerate(foundation['files']):require(before[x['path']]==foundation['profiles'][0]['sha256'][i],'Input must be the exact original stock Content')
 output.mkdir(parents=True);private=output/'work';private.mkdir();logs=private/'logs';canonical=private/'canonical'
 execute('source-build-canonical0.11',[sys.executable,'-B',pipeline/'build.py','--input-content',original,'--dependencies',dependencies,'--out',canonical,'--game-only'],logs/'canonical.log')
 base=canonical/'generated-content'
 for name,pin in FOUNDATION.items():require(digest(base/name)==pin,'Source-built0.11 foundation differs: '+name)
 stage=output/('staging-only'if skip_launcher else'bundle')/RELEASE;stage.mkdir(parents=True);(stage/'tools').mkdir();shutil.copyfile(tool,stage/'tools/xdelta3.exe')
 catalog=dict(schema=1,releaseId=RELEASE,tool=dict(path='tools/xdelta3.exe',sha256=TOOL_SHA),packs=[]);private_reports=[];allowed={'tools/xdelta3.exe','catalog.json','CHECKSUMS.sha256','README.txt','build-summary.json','LICENSE'}
 allowed.add('STAGING-NOT-DISTRIBUTABLE.txt'if skip_launcher else'MultilingualLauncher.exe')
 decode=private/'decode';decode.mkdir()
 for entry in entries:
  id=entry['id'];work=private/'packs'/id
  execute('compile-pack-'+id,[sys.executable,'-B',pack_tools/'compile.py','--pipeline',pipeline,'--input-content',original,'--pack',pack_root/entry['manifest'],'--font',font,'--out',work],logs/('pack-'+id+'.log'))
  report=load(work/'locale-build.json');require(report['locale']['id']==id,'Compiler locale identity changed');content=work/'Content';inputs=report['nativeInputs']
  execute('native-variant-'+id,[sys.executable,'-B',runtime,'--base-native',base/NATIVE,'--captions',work/inputs['captions'],'--tutorial-format',work/inputs['tutorialFormat'],'--pipeline',pipeline,'--output',content/NATIVE,'--report',work/'native-build.json'],logs/('native-'+id+'.log'),300)
  native=load(work/'native-build.json');files=[]
  for i,name in enumerate(FILES):
   target=content/name;expected=digest(target);size=target.stat().st_size
   require(expected==(native['targetSha256']if i==0 else next(x['sha256']for x in report['files']if x['path']==name)),'Variant output differs from its source report')
   record=dict(path=name,sha256=expected,bytes=size,delta=None,deltaSha256=None,deltaBytes=0)
   if expected!=FOUNDATION[name]or size!=(base/name).stat().st_size:
    relative='patches/'+id+'-'+DELTA_NAMES[i];delta=stage/relative;delta.parent.mkdir(parents=True,exist_ok=True)
    execute('encode-'+id+'-'+str(i),[tool,'-e','-9','-A','-D','-s',base/name,target,delta],logs/('encode-'+id+'-'+str(i)+'.log'),300)
    require(0<delta.stat().st_size<=MAX_DELTA,'Delta exceeds the bounded payload size')
    rebuilt=decode/(id+'-'+str(i)+'.bin');execute('verify-'+id+'-'+str(i),[tool,'-d','-D','-R','-s',base/name,delta,rebuilt],logs/('decode-'+id+'-'+str(i)+'.log'),300)
    require(rebuilt.stat().st_size==size and digest(rebuilt)==expected,'Fresh forward delta does not reconstruct the exact variant')
    record.update(delta=relative,deltaSha256=digest(delta),deltaBytes=delta.stat().st_size);allowed.add(relative)
   files.append(record)
  fallback=None if id=='ko-KR'else'ko-KR'
  catalog['packs'].append(dict(id=id,displayName=report['locale']['displayName'],englishName=ENGLISH.get(id,id),status=report['locale']['status'],fallback=fallback,coverage=coverage_line(report),files=files))
  sanitized=dict(schema=1,id=id,status=report['locale']['status'],fallback=fallback,coverage={k:{a:b for a,b in v.items()if a!='fallbackKeys'}for k,v in report['coverage'].items()},fontCoverage=report['fontCoverage'],layout=report['layout'],files=files,native={k:native[k]for k in['identityOutput','targetSha256','bytes','dispatchMapByteExact','unwindDirectoryByteExact','newExecutableBytes']},originalAudioAndTimingPreserved=True)
  public_report='reports/'+id+'.json';write(stage/public_report,sanitized);allowed.add(public_report);private_reports.append(dict(id=id,privateOutput=str(work),files=files))
 catalog_path=stage/'catalog.json';write(catalog_path,catalog);require(catalog_path.stat().st_size<=1024*1024,'Catalog exceeds finite size limit');catalog_sha=digest(catalog_path)
 launcher=compile_launcher(repo,stage,private,catalog_sha,skip_launcher,csc)
 for name in LICENSES:
  source=repo/'licenses'/name;require(source.is_file(),'Required upstream notice missing: '+name);dest=stage/'licenses'/name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(source,dest);allowed.add('licenses/'+name)
 shutil.copyfile(repo/'LICENSE',stage/'LICENSE')
 (stage/'README.txt').write_text(bundle_readme(),'utf8')
 for name,pin in before.items():require(digest(original/name)==pin,'An original source file changed during the build')
 require(digest(tool)==TOOL_SHA,'Tool changed during the build')
 summary=dict(schema=1,releaseId=RELEASE,distributable=not skip_launcher,catalogSha256=catalog_sha,foundationRequired=FOUNDATION,sourceBuiltFoundation=True,publishedDeltasUsedAsInputs=False,gameOrSettingsModified=False,originalFiveInputsUnchanged=True,packCount=len(entries),deltaCount=sum(bool(f['delta'])for p in catalog['packs']for f in p['files']),launcher=launcher)
 write(stage/'build-summary.json',summary)
 archive,inventory=finish_distribution(stage,output,allowed,summary,skip_launcher)
 result=dict(schema=1,status='PASS'if not skip_launcher else'STAGING_ONLY',releaseId=RELEASE,distributable=not skip_launcher,bundle=str(stage),archive=None if archive is None else dict(path=str(archive),bytes=archive.stat().st_size,sha256=digest(archive)),catalogSha256=catalog_sha,summary=summary,inventory=inventory,privatePackOutputs=private_reports)
 write(output/'build-report.json',result);return result

def repackage_verified(previous,repo,output,csc=None):
 """Recompile only the launcher after revalidating PRIVATE source-built targets.

 This is not a source-authoring shortcut: a published ZIP/delta-only directory
 is rejected. The prior full source build's canonical images and every locale
 target must still be present and exact. The original catalog is immutable.
 Public output is identical to a full build with the same launcher sources;
 reuse provenance is recorded only in the private build-report.json.
 """
 import re
 previous,repo,output=map(lambda x:Path(x).resolve(),[previous,repo,output]);require(not output.exists(),'Use a new packaging output directory')
 require(separated(output,previous)and separated(output,repo),'Packaging output must be disjoint from prior build/source repository')
 prior=load(previous/'build-report.json');require(prior.get('status')=='PASS'and prior.get('distributable')is True and prior['summary'].get('sourceBuiltFoundation')is True and prior['summary'].get('publishedDeltasUsedAsInputs')is False,'A private verified full source build is required, not a published bundle')
 source=Path(prior['bundle']).resolve();require(source.is_relative_to(previous),'Prior bundle escapes its private source build')
 require(digest(source/'catalog.json')==prior['catalogSha256'],'Prior catalog changed');catalog=load(source/'catalog.json')
 require(catalog['schema']==1 and catalog['releaseId']==RELEASE and catalog['tool']==dict(path='tools/xdelta3.exe',sha256=TOOL_SHA),'Prior catalog contract differs')
 require(1<=len(catalog['packs'])<=32,'Prior catalog pack count invalid');ids=set();expected={'tools/xdelta3.exe','catalog.json','CHECKSUMS.sha256','README.txt','build-summary.json','LICENSE','MultilingualLauncher.exe'}|{'licenses/'+x for x in LICENSES}
 for pack in catalog['packs']:
  id=pack['id'];require(isinstance(id,str)and re.fullmatch(r'[a-z]{2,3}(?:-[A-Z][a-z]{3})?(?:-[A-Z]{2}|-[0-9]{3})?',id)is not None and id not in ids,'Invalid/duplicate prior pack ID');ids.add(id);require(len(pack['files'])==3,'Prior file count invalid');expected.add('reports/'+id+'.json')
  for i,f in enumerate(pack['files']):
   require(f['path']==FILES[i],'Prior game file order/path differs')
   if f['delta']is not None:require(f['delta']=='patches/'+id+'-'+DELTA_NAMES[i],'Prior delta path is not the compiled flat allowlist');expected.add(f['delta'])
 require('ko-KR'in ids,'Canonical Korean pack missing')
 inventory={x['path']:x for x in prior['inventory']};require(set(inventory)==expected,'Prior public inventory is not the complete fixed allowlist')
 actual={x.relative_to(source).as_posix()for x in source.rglob('*')if x.is_file()};require(actual==expected,'Unexpected prior bundle files')
 for name,record in inventory.items():
  path=(source/name).resolve();require(path.is_relative_to(source)and path.stat().st_size==record['bytes']and digest(path)==record['sha256'],'Prior bundle hash/size changed: '+name)
 base=previous/'work/canonical/generated-content'
 for name,pin in FOUNDATION.items():require(digest(base/name)==pin,'Private source-built canonical foundation is missing/changed: '+name)
 for pack in catalog['packs']:
  content=previous/'work/packs'/pack['id']/'Content'
  for f in pack['files']:require((content/f['path']).stat().st_size==f['bytes']and digest(content/f['path'])==f['sha256'],'Private source-built variant target is missing/changed')
 output.mkdir(parents=True);private=output/'work';private.mkdir();stage=output/'bundle'/RELEASE;stage.mkdir(parents=True)
 for name in sorted(expected-{'MultilingualLauncher.exe','CHECKSUMS.sha256','build-summary.json','README.txt'}):
  target=stage/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,target)
 # Re-read current notices like the full source path, never copy arbitrary files.
 for name in LICENSES:shutil.copyfile(repo/'licenses'/name,stage/'licenses'/name)
 shutil.copyfile(repo/'LICENSE',stage/'LICENSE');(stage/'README.txt').write_text(bundle_readme(),'utf8')
 decode=private/'decode';decode.mkdir();tool=stage/'tools/xdelta3.exe';require(digest(tool)==TOOL_SHA,'Wrong pinned delta tool')
 for pack in catalog['packs']:
  for i,f in enumerate(pack['files']):
   if f['delta']is None:require(f['sha256']==FOUNDATION[f['path']]and f['bytes']==(base/f['path']).stat().st_size,'Invalid prior identity output');continue
   require(0<f['deltaBytes']<=MAX_DELTA and digest(stage/f['delta'])==f['deltaSha256']and(stage/f['delta']).stat().st_size==f['deltaBytes'],'Prior forward delta changed')
   reconstructed=decode/(pack['id']+'-'+str(i)+'.bin');execute('reverify-'+pack['id']+'-'+str(i),[tool,'-d','-D','-R','-s',base/f['path'],stage/f['delta'],reconstructed],private/'logs'/('decode-'+pack['id']+'-'+str(i)+'.log'),300)
   require(reconstructed.stat().st_size==f['bytes']and digest(reconstructed)==f['sha256'],'Prior delta no longer reconstructs its exact source-built target')
 require(digest(stage/'catalog.json')==prior['catalogSha256'],'Packaging-only mode cannot change the catalog')
 launcher=compile_launcher(repo,stage,private,prior['catalogSha256'],False,csc);summary=dict(prior['summary']);summary['launcher']=launcher;write(stage/'build-summary.json',summary)
 archive,members=finish_distribution(stage,output,expected,summary,False)
 result=dict(schema=1,status='PASS',releaseId=RELEASE,distributable=True,bundle=str(stage),archive=dict(path=str(archive),bytes=archive.stat().st_size,sha256=digest(archive)),catalogSha256=prior['catalogSha256'],summary=summary,inventory=members,privatePackOutputs=prior['privatePackOutputs'],packagingOnlyRebuild=True,sourceBuildReportSha256=digest(previous/'build-report.json'),sourceCatalogByteExact=True,gameTargetsRebuilt=False,verifiedPrivateSourceBuild=str(previous))
 write(output/'build-report.json',result);return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input-content',type=Path);p.add_argument('--dependencies',type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--pack-root',type=Path);p.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parent.parent);p.add_argument('--skip-launcher',action='store_true',help='Private early staging only; no distributable ZIP is produced');p.add_argument('--csc',type=Path)
 p.add_argument('--package-from',type=Path,help='Recompile/repackage a prior PRIVATE verified full source build after launcher-only edits; published bundles are rejected. Catalog/game targets remain locked.')
 a=p.parse_args()
 if a.package_from:
  require(a.input_content is None and a.dependencies is None and a.pack_root is None and not a.skip_launcher,'Packaging-only mode cannot alter source targets/packs or skip the launcher');r=repackage_verified(a.package_from,a.repo_root,a.out,a.csc)
 else:
  require(a.input_content is not None and a.dependencies is not None,'Full source builds require --input-content and --dependencies');r=bundle_build(a.input_content,a.dependencies,a.out,a.repo_root,a.pack_root,a.skip_launcher,a.csc)
 print(json.dumps({k:r[k]for k in['status','distributable','bundle','archive','catalogSha256']},indent=2))
