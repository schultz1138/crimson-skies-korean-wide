"""Fixed-size source-bound Native caption tables; no target execution/writes."""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,math,struct,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PIPELINE=ROOT/'pipeline'
import pefile
BASE_SHA='45c2c716da6c01f0937ce922dbfe2de89a3a9dfb163578757cfc5c5cc7e65f44'
AUTO_RVA,AUTO_BYTES,FADE_RVA=0x2816f00,233964,0x28500e8
FORMAT_RVA,FORMAT_BYTES=0x2804cc0,1028

def require(ok,why):
 if not ok:raise ValueError(why)
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text('utf-8-sig'))
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def save_new(p,obj):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')

def frozen_tools():
 variant=module('caption_native_variant',ROOT/'multilingual/runtime/native_variant.py')
 c,source=variant.source_tools(PIPELINE)
 return variant,c,source

def checked_entries(proposal,base):
 entries=proposal['entries'];canonical=base['entries']
 require(len(entries)==len(canonical)==1805,'Require all1805 WAV entries')
 reviewed=proposal.get('rootReviewedOffsetChanges',{})
 observed={};keys=set();parts=0
 for e,b in zip(entries,canonical):
  require(all(e.get(k)==b.get(k) for k in ['basename','audio','duration']),'WAV identity/order/duration changed')
  require(len(e['parts'])==len(b['parts']),'Part count changed')
  previous=-1.
  for p,q in zip(e['parts'],b['parts']):
   parts+=1;require(p['key']==q['key'] and p['key'] not in keys,'Part identity/order/duplicate changed');keys.add(p['key'])
   off=p['offset'];require(type(off)in [int,float] and math.isfinite(off) and previous<off<e['duration'] and off>=0,'Invalid ordered timing offset')
   previous=off
   if off!=q['offset']:
    r=reviewed.get(p['key'],{});require(r.get('from')==q['offset'] and r.get('to')==off and isinstance(r.get('reason'),str) and r['reason'].strip(),'Unreviewed timing change')
    observed[p['key']]=r
   text=p['text'];require(isinstance(text,str) and text and len(text.encode('utf-16le'))<=510 and text.count('\n')<=1 and all(ord(x)>=32 or x=='\n' for x in text),'UTF16/two-line caption contract exceeded')
 require(parts==1901 and set(reviewed)==set(observed),'Require1901 parts and exact offset-review membership')
 return entries,observed

def build(base_native,caption_source,tutorial_source):
 b=Path(base_native).read_bytes();require(sha(b)==BASE_SHA,'Frozen installed baseline changed')
 p=pefile.PE(data=b);variant,c,source=frozen_tools()
 canonical=load(PIPELINE/'assets/localization/native_captions.json')
 original_format=load(PIPELINE/'native/stages/translations/tutorial.linebreak-proposals.json')
 proposal=load(caption_source);entries,offsets=checked_entries(proposal,canonical)
 olddata,oldmeta=source.pack_dictionary(canonical['entries'],AUTO_RVA)
 require(len(olddata)==AUTO_BYTES and oldmeta['fadeRVA']==FADE_RVA and
  sha(olddata)=='82ff3eb28d2b97e19a963bf5201c602463ad032b78dff3940a13ad591f9d92ba' and p.get_data(AUTO_RVA,AUTO_BYTES)==olddata,'Installed source dictionary mismatch')
 oldformat,oldrecords=variant.format_table(original_format,original_format)
 require(len(oldformat)==FORMAT_BYTES and p.get_data(FORMAT_RVA,FORMAT_BYTES)==oldformat,'Installed tutorial table mismatch')
 fmt,records=variant.format_table(load(tutorial_source),original_format)
 packed,meta=source.pack_dictionary(entries,AUTO_RVA)
 require(packed[-4:]==olddata[-4:]==struct.pack('<f',.25),'Fade source changed')
 require(len(packed)<=AUTO_BYTES,'New dictionary exceeds233964-byte owned allocation: '+str(len(packed)))
 require(len(fmt)<=FORMAT_BYTES,'New tutorial table exceeds1028-byte owned allocation: '+str(len(fmt)))
 body=packed[:-4];payload=body+bytes(AUTO_BYTES-4-len(body))+olddata[-4:]
 fixedmeta=copy.deepcopy(meta);fixedmeta['fadeRVA']=FADE_RVA
 # Re-emitted leaf services must be exact because counts, entry and fade RVAs
 # remain exact. No host instructions or table-reference displacements change.
 services={}
 for name,rva,make in [('lookup',variant.LOOKUP_RVA,source.build_lookup),('part',variant.PART_RVA,lambda ctx,at,m:source.build_part(ctx,at,m,allow_delayed_start=True))]:
  old=make(c,rva,oldmeta);new=make(c,rva,fixedmeta)
  require(old==new==p.get_data(rva,len(old)),'Source-owned service ABI/code changed: '+name)
  services[name]=dict(rva=rva,bytes=len(old),sha256=sha(old),byteExactInstalled=True)
 target=bytearray(b);at=p.get_offset_from_rva(AUTO_RVA);target[at:at+AUTO_BYTES]=payload
 fat=p.get_offset_from_rva(FORMAT_RVA);target[fat:fat+FORMAT_BYTES]=fmt+bytes(FORMAT_BYTES-len(fmt))
 checksum=p.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum')
 if target!=b:
  q=pefile.PE(data=target);struct.pack_into('<I',target,checksum,q.generate_checksum())
 q=pefile.PE(data=target)
 require(len(target)==len(b),'Native file size changed')
 require(q.verify_checksum() and not q.get_warnings(),'Output PE validation failed')
 require(p.OPTIONAL_HEADER.__pack__()[:64]==q.OPTIONAL_HEADER.__pack__()[:64],'PE optional layout changed')
 require(all(x.__pack__()==y.__pack__() for x,y in zip(p.sections,q.sections)),'Existing section header changed')
 require(all(x.__pack__()==y.__pack__() for x,y in zip(p.OPTIONAL_HEADER.DATA_DIRECTORY,q.OPTIONAL_HEADER.DATA_DIRECTORY)),'Import/unwind/relocation data directories changed')
 spans=[dict(fileOffset=at,bytes=AUTO_BYTES,rva=AUTO_RVA,purpose='Owned caption dictionary; fixed original fade'),
        dict(fileOffset=fat,bytes=FORMAT_BYTES,rva=FORMAT_RVA,purpose='Owned tutorial formatter table'),
        dict(fileOffset=checksum,bytes=4,purpose='PE checksum')]
 mask=bytearray(len(b))
 for r in spans:
  lo,hi=r['fileOffset'],r['fileOffset']+r['bytes'];mask[lo:hi]=b'\1'*(hi-lo)
  r['beforeSha256']=sha(b[lo:hi]);r['afterSha256']=sha(target[lo:hi])
 changed=[i for i,(x,y)in enumerate(zip(b,target)) if x!=y]
 require(all(mask[i] for i in changed),'Non-owned installed byte changed')
 # Hash whole original bytes outside data/checksum, including every executable
 # service, wide/HUD/AA hook, imports, dispatch map and unwind information.
 oldoutside=hashlib.sha256();newoutside=hashlib.sha256()
 for lo in range(0,len(b),65536):
  hi=min(len(b),lo+65536);keep=[i for i in range(lo,hi) if not mask[i]]
  oldoutside.update(bytes(b[i] for i in keep));newoutside.update(bytes(target[i] for i in keep))
 require(oldoutside.digest()==newoutside.digest(),'Protected original bytes differ')
 report=dict(schema=1,status='PASS_FIXED_SIZE_SOURCE_OWNED_CAPTION_TABLES_OFFLINE',
  sourceSha256=BASE_SHA,targetSha256=sha(target),bytes=len(target),identityOutput=target==b,
  dictionary=dict(rva=AUTO_RVA,allocationBytes=AUTO_BYTES,packedBytes=len(packed),paddingBeforeFixedFadeBytes=AUTO_BYTES-len(packed),fadeRva=FADE_RVA,entries=1805,parts=1901),
  tutorial=dict(rva=FORMAT_RVA,allocationBytes=FORMAT_BYTES,packedBytes=len(fmt),wrappedUniqueRecords=len(records),paddingBytes=FORMAT_BYTES-len(fmt)),
  services=services,ownedFileSpans=spans,changedOriginalBytes=len(changed),
  allOtherOriginalBytesByteExact=True,protectedOriginalBytesSha256=oldoutside.hexdigest(),
  allOriginalCodeByteExact=True,wideHUDCameraMovieAAAudioHooksByteExact=True,
  sectionHeadersByteExact=True,dataDirectoriesByteExact=True,newImports=0,newExecutableBytes=0,
  WAVIdentityAndDurationExact=True,originalPartOffsetsExact=not offsets,reviewedOffsetChanges=offsets,
  offsetSemantics='Seconds after first observed playing frame. Next part offset selects following caption; last part ends at original WAV duration. Original0.25s fade retained.',
  captionSource=dict(path=str(Path(caption_source).resolve()),sha256=sha(Path(caption_source).read_bytes())),
  tutorialSource=dict(path=str(Path(tutorial_source).resolve()),sha256=sha(Path(tutorial_source).read_bytes())),
  builderSha256=sha(Path(__file__).read_bytes()),sourceVariantSha256=sha((ROOT/'multilingual/runtime/native_variant.py').read_bytes()),
  installedFilesModified=False,targetCodeExecuted=False,humanVisualPlaybackVerified=False)
 return bytes(target),report

def main():
 a=argparse.ArgumentParser();a.add_argument('--base-native',required=True,type=Path);a.add_argument('--captions',required=True,type=Path);a.add_argument('--tutorial-format',required=True,type=Path);a.add_argument('--out',required=True,type=Path);args=a.parse_args()
 out=args.out.resolve();require(not out.exists() and not out.is_relative_to(args.base_native.resolve().parent),'Output must be new and outside input Content')
 data,report=build(args.base_native,args.captions,args.tutorial_format);out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('xb') as f:f.write(data)
 save_new(out.with_suffix(out.suffix+'.json'),report)
 print(json.dumps({k:report[k]for k in ['status','identityOutput','targetSha256','bytes','dictionary','tutorial']}))

if __name__=='__main__':main()
