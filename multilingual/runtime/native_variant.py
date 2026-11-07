"""Append a subtitle pack to the canonical source-built 0.11 Native image.

Only data is appended. Existing authored leaf services stay at their original
RVAs; their RIP-relative table references are regenerated from source. The
original camera/HUD/movie/AA code, dispatch map and unwind metadata stay exact.
"""
from pathlib import Path
import argparse,hashlib,importlib,json,math,os,struct,sys
sys.dont_write_bytecode=True
BASE_SHA='45c2c716da6c01f0937ce922dbfe2de89a3a9dfb163578757cfc5c5cc7e65f44'
DLL='xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll'
AUTO_RVA=42036992
LOOKUP_RVA=42020608
PART_RVA=42024704
FORMATTER_RVA=41939648
FORMAT_TABLE_RVA=41962688
MAX_APPEND=2*1024*1024
def sha(b):return hashlib.sha256(b).hexdigest()
def align(x,n):return (x+n-1)//n*n
def diskpath(path):
 p=Path(path).resolve()
 return Path('\\\\?\\'+str(p))if os.name=='nt'and not str(p).startswith('\\\\?\\')else p
def read_json(path):
 b=diskpath(path).read_bytes()
 if len(b)>8*1024*1024:raise ValueError('Caption source exceeds the finite source bound')
 return json.loads(b.decode('utf-8'))

def checked_entries(source,canonical):
 entries=source['entries'];base=canonical['entries']
 if len(entries)!=1805 or len(base)!=1805:raise ValueError('The complete 1805-record audio identity table is required')
 keys=set();parts=0
 for e,b in zip(entries,base):
  if any(e.get(k)!=b.get(k)for k in ['basename','audio','duration']):raise ValueError('Audio identity/order/duration changed')
  if not math.isfinite(e['duration'])or not 0<e['duration']<3600:raise ValueError('Invalid duration')
  if len(e['parts'])!=len(b['parts']):raise ValueError('Part count changed')
  for p,q in zip(e['parts'],b['parts']):
   parts+=1
   if any(p.get(k)!=q.get(k)for k in ['key','offset']):raise ValueError('Part identity/timing changed')
   if p['key']in keys:raise ValueError('Duplicate part key')
   keys.add(p['key']);text=p['text'];wide=text.encode('utf-16le')
   if not text or len(wide)>510 or text.count('\n')>1 or any(ord(c)<32 and c!='\n'for c in text):raise ValueError('Caption text exceeds the native UTF16/two-line contract')
 if parts!=1901:raise ValueError('The complete 1901-part corpus is required')
 return entries

def format_table(source,canonical):
 entries=source['entries'];base=canonical['entries']
 if [e['key']for e in entries]!=[e['key']for e in base]:raise ValueError('Tutorial identities/order changed')
 result=bytearray();seen={};records=[]
 for e in entries:
  text=e['source_text'];wide=text.encode('utf-16le');index=e['break_index_utf16']
  if not text or len(wide)>510 or any(ord(c)<32 for c in text):raise ValueError('Invalid tutorial source text')
  if sha(wide)!=e['source_utf16le_sha256']:raise ValueError('Tutorial UTF16 source hash mismatch')
  if index is None:continue
  if type(index)is not int or not 0<=index<len(wide)//2 or wide[index*2:index*2+2]!=b' \0':raise ValueError('Tutorial break must replace an existing UTF16 space')
  if wide in seen:
   if seen[wide]!=index:raise ValueError('Ambiguous tutorial break for identical text')
   continue
  seen[wide]=index;encoded=wide+b'\0\0'
  result+=struct.pack('<II',len(encoded),index*2)+encoded
  records.append({'key':e['key'],'text':text,'breakIndexUtf16':index})
 result+=bytes(8)
 return bytes(result),records

def source_tools(pipeline):
 p=Path(pipeline).resolve();sys.path.insert(0,str(p/'native/stages/native-auto-caption'))
 aot=importlib.import_module('aot_compile');data=importlib.import_module('scouting_data')
 from keystone import Ks,KS_ARCH_X86,KS_MODE_64
 from capstone import Cs,CS_ARCH_X86,CS_MODE_64
 c=object.__new__(aot.AotCompiler);c.image_base=0x180000000;c.dispatch_ptr_rva=0x27f16d0
 c._ks64=Ks(KS_ARCH_X86,KS_MODE_64);c._cs64=Cs(CS_ARCH_X86,CS_MODE_64);c._cs64.detail=True
 return c,data

def build(base_native,caption_source,tutorial_source,pipeline):
 import pefile
 from capstone import Cs,CS_ARCH_X86,CS_MODE_64,CS_GRP_CALL
 from capstone.x86 import X86_OP_MEM,X86_REG_RIP
 b=diskpath(base_native).read_bytes()
 if sha(b)!=BASE_SHA:raise ValueError('A canonical source-built 0.11 Native image is required')
 p=pefile.PE(data=b);pipeline=Path(pipeline).resolve()
 canonical=read_json(pipeline/'assets/localization/native_captions.json')
 tutorial=read_json(pipeline/'native/stages/translations/tutorial.linebreak-proposals.json')
 entries=checked_entries(read_json(caption_source),canonical)
 table,records=format_table(read_json(tutorial_source),tutorial)
 oldtable,oldrecords=format_table(tutorial,tutorial)
 if len(oldtable)!=1028 or p.get_data(FORMAT_TABLE_RVA,len(oldtable))!=oldtable:raise ValueError('Canonical tutorial source/table mismatch')
 c,source=source_tools(pipeline);olddata,oldmeta=source.pack_dictionary(canonical['entries'],AUTO_RVA)
 if sha(olddata)!='82ff3eb28d2b97e19a963bf5201c602463ad032b78dff3940a13ad591f9d92ba'or p.get_data(AUTO_RVA,len(olddata))!=olddata:raise ValueError('Canonical caption source/table mismatch')
 newdata_at=align(max(s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData)for s in p.sections),p.OPTIONAL_HEADER.SectionAlignment)
 if newdata_at!=0x2864000:raise ValueError('Unexpected original image layout')
 # If only assets outside Native differ, retain the canonical Native exactly.
 same_text=all(x['text']==y['text']for e,q in zip(entries,canonical['entries'])for x,y in zip(e['parts'],q['parts']))
 if same_text and table==oldtable:
  return b,{'schema':1,'status':'PASS','identityOutput':True,'sourceSha256':BASE_SHA,'targetSha256':BASE_SHA,'bytes':len(b),'allWideAndKoreanEngineCodeByteExact':True,'newExecutableBytes':0,'unwindDirectoryByteExact':True,'dispatchMapByteExact':True}
 data,meta=source.pack_dictionary(entries,newdata_at)
 tutorial_at=align(len(data),16);payload=data+bytes(tutorial_at-len(data))+table
 if len(payload)>MAX_APPEND:raise ValueError('Language section exceeds the finite 2MiB bound')
 if p.FILE_HEADER.NumberOfSections!=10 or p.OPTIONAL_HEADER.SizeOfHeaders!=0x400:raise ValueError('Unexpected section layout')
 h=p.sections[-1].get_file_offset()+40
 if h!=0x3a0 or h+40>p.OPTIONAL_HEADER.SizeOfHeaders or b[h:h+40]!=bytes(40):raise ValueError('No unused section header slot')
 if p.get_overlay_data_start_offset()is not None or p.OPTIONAL_HEADER.DATA_DIRECTORY[4].Size:raise ValueError('Unexpected overlay/certificate')
 raw=align(len(b),p.OPTIONAL_HEADER.FileAlignment);rawsize=align(len(payload),p.OPTIONAL_HEADER.FileAlignment)
 target=bytearray(b+bytes(raw+rawsize-len(b)));target[raw:raw+len(payload)]=payload
 md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True;patches=[];allowed=[];services={}
 def put(at,old,new,purpose):
  if len(old)!=len(new)or b[at:at+len(old)]!=old:raise ValueError('Unexpected source bytes at '+purpose)
  target[at:at+len(new)]=new;allowed.append((at,at+len(new)));patches.append({'fileOffset':at,'bytes':len(new),'before':old.hex(),'after':new.hex(),'purpose':purpose})
 for name,rva,make in [('lookup',LOOKUP_RVA,source.build_lookup),('part',PART_RVA,lambda ctx,at,m:source.build_part(ctx,at,m,allow_delayed_start=True))]:
  before=make(c,rva,oldmeta);after=make(c,rva,meta)
  if len(before)!=len(after)or p.get_data(rva,len(before))!=before:raise ValueError('Owned service source pin mismatch: '+name)
  oldins=list(md.disasm(before,c.image_base+rva));newins=list(md.disasm(after,c.image_base+rva));dispbytes=set();rip_changes=[]
  if len(oldins)!=len(newins):raise ValueError('Instruction structure changed')
  for x,y in zip(oldins,newins):
   if x.size!=y.size or x.mnemonic!=y.mnemonic or x.group(CS_GRP_CALL):raise ValueError('Owned leaf service ABI changed')
   if x.bytes!=y.bytes:
    if x.disp_size!=4 or y.disp_size!=4 or not any(o.type==X86_OP_MEM and o.mem.base==X86_REG_RIP for o in x.operands):raise ValueError('Only RIP data references may change')
    start=x.address-c.image_base-rva+x.disp_offset;dispbytes.update(range(start,start+4))
    olddest=x.address+x.size+x.disp;newdest=y.address+y.size+y.disp
    if olddest not in [c.image_base+oldmeta['entryTableRVA'],c.image_base+oldmeta['fadeRVA']]or newdest not in [c.image_base+meta['entryTableRVA'],c.image_base+meta['fadeRVA']]:raise ValueError('Unexpected table reference')
    rip_changes.append({'instructionRva':x.address-c.image_base,'oldTargetRva':olddest-c.image_base,'newTargetRva':newdest-c.image_base})
  if any(a!=z and i not in dispbytes for i,(a,z)in enumerate(zip(before,after))):raise ValueError('Non-table code byte changed')
  put(p.get_offset_from_rva(rva),before,after,'owned '+name+' RIP table references')
  services[name]={'rva':rva,'bytes':len(after),'codeSha256':sha(after),'ripChanges':rip_changes}
 # The existing formatter uses one LEA R9 to find its length/index/text table.
 formatter=p.get_data(FORMATTER_RVA,192);ins=list(md.disasm(formatter,c.image_base+FORMATTER_RVA))
 refs=[i for i in ins if i.mnemonic=='lea'and i.op_str.startswith('r9, [rip')and i.address+i.size+i.disp==c.image_base+FORMAT_TABLE_RVA]
 if len(refs)!=1 or refs[0].disp_size!=4:raise ValueError('Tutorial table LEA source pin mismatch')
 i=refs[0];newtutorial=newdata_at+tutorial_at;at=p.get_offset_from_rva(i.address-c.image_base)+i.disp_offset
 put(at,b[at:at+4],struct.pack('<i',newtutorial-(i.address-c.image_base+i.size)),'owned tutorial formatter RIP table reference')
 put(h,bytes(40),struct.pack('<8s6I2HI',b'.cslang\0',len(payload),newdata_at,rawsize,raw,0,0,0,0,0x40000040),'new read-only initialized-data section')
 for obj,field,value,fmt in [(p.FILE_HEADER,'NumberOfSections',11,'<H'),(p.OPTIONAL_HEADER,'SizeOfImage',align(newdata_at+len(payload),p.OPTIONAL_HEADER.SectionAlignment),'<I'),(p.OPTIONAL_HEADER,'SizeOfInitializedData',p.OPTIONAL_HEADER.SizeOfInitializedData+rawsize,'<I')]:
  at=obj.get_field_absolute_offset(field);put(at,b[at:at+struct.calcsize(fmt)],struct.pack(fmt,value),'PE '+field)
 q=pefile.PE(data=target);at=p.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum');put(at,b[at:at+4],struct.pack('<I',q.generate_checksum()),'PE checksum')
 after=pefile.PE(data=target)
 if not after.verify_checksum()or after.get_warnings():raise ValueError('Invalid resulting PE')
 if p.OPTIONAL_HEADER.SizeOfCode!=after.OPTIONAL_HEADER.SizeOfCode:raise ValueError('Executable extent changed')
 if any(x.__pack__()!=y.__pack__()for x,y in zip(p.sections,after.sections)):raise ValueError('Existing section header changed')
 if any(x.__pack__()!=y.__pack__()for x,y in zip(p.OPTIONAL_HEADER.DATA_DIRECTORY,after.OPTIONAL_HEADER.DATA_DIRECTORY)):raise ValueError('Existing import/unwind/relocation directory changed')
 mask=bytearray(len(b))
 for lo,hi in allowed:mask[lo:hi]=b'\1'*(hi-lo)
 changed=[i for i,(x,y)in enumerate(zip(b,target))if x!=y]
 if any(not mask[i]for i in changed):raise ValueError('A non-allowlisted original byte changed')
 ed=p.OPTIONAL_HEADER.DATA_DIRECTORY[3];unwind=p.get_data(ed.VirtualAddress,ed.Size)
 if after.get_data(ed.VirtualAddress,ed.Size)!=unwind:raise ValueError('Unwind metadata changed')
 maprva,mapsize=0x1457190,0x27c4fd8-0x1457190
 if p.get_data(maprva,mapsize)!=after.get_data(maprva,mapsize):raise ValueError('Native dispatch map changed')
 report={'schema':1,'status':'PASS','identityOutput':False,'sourceSha256':BASE_SHA,'targetSha256':sha(target),'bytes':len(target),'inputBytes':len(b),
  'append':{'name':'.cslang','rva':newdata_at,'fileOffset':raw,'virtualBytes':len(payload),'rawBytes':rawsize,'characteristics':'0x40000040','maximumBytes':MAX_APPEND,'sha256':sha(payload)},
  'dictionary':{'rva':meta['entryTableRVA'],'bytes':len(data),'fadeRva':meta['fadeRVA'],'entries':1805,'parts':1901,'sha256':sha(data)},
  'tutorial':{'rva':newtutorial,'bytes':len(table),'records':len(records)},'services':services,'patches':patches,'changedOriginalBytes':len(changed),
  'allOtherOriginalBytesExact':True,'newExecutableBytes':0,'allExistingSectionHeadersByteExact':True,'dataDirectoriesByteExact':True,
  'unwindDirectoryByteExact':True,'dispatchMapByteExact':True,'originalAudioIdentityAndTimingExact':True,'noNewImportsOrHostFunctions':True,
  'sourceGeneration':'Original owned AOT service assembly; only RIP table displacements differ. New section contains no executable code.',
  'installedFilesModified':False,'targetCodeExecuted':False}
 return bytes(target),report

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base-native',type=Path,required=True);ap.add_argument('--captions',type=Path,required=True);ap.add_argument('--tutorial-format',type=Path,required=True);ap.add_argument('--pipeline',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--report',type=Path)
 a=ap.parse_args();out=diskpath(a.output);rp=diskpath(a.report or out.with_suffix(out.suffix+'.json'))
 protected={diskpath(x)for x in [a.base_native,a.captions,a.tutorial_format]}
 if out in protected or out.exists():raise ValueError('Output must be a new, separate file')
 if rp in protected or rp==out or rp.exists():raise ValueError('Report must be a new, separate file')
 data,report=build(a.base_native,a.captions,a.tutorial_format,a.pipeline);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
 rp.parent.mkdir(parents=True,exist_ok=True);rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
 print(json.dumps({k:report[k]for k in ['status','identityOutput','targetSha256','bytes']}))
if __name__=='__main__':main()
