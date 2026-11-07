"""Offline native overscan candidate based only on immutable workingV4."""
from pathlib import Path
import sys,json,struct,hashlib,re,subprocess
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];UI=ROOT/'widescreen-analysis/ui';SHARED=ROOT/'resolution-analysis/shared'
sys.path[:0]=[str(ROOT/'pythonlibs'),str(UI),str(UI/'testdeps'),str(SHARED),str(HERE)]
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from keystone import Ks,KS_ARCH_X86,KS_MODE_64
import scoped_ui_kernel_v2_movie as OLD
import preset_decoder as D
import uniform_kernel as K
NAME='xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll';SOURCE=ROOT/'widescreen-analysis/camera/startup-loader-fix/equivalent-native-v2'/NAME
SHA=lambda b:hashlib.sha256(b).hexdigest();AL=lambda n,a:(n+a-1)//a*a

def prepare():
 b=SOURCE.read_bytes();assert SHA(b)=='8c4679c79479b81b81e39d483ba3feebd694802e075af6139388e3e8f46564b1';p=pefile.PE(data=b);base=p.OPTIONAL_HEADER.ImageBase
 old=json.loads((SOURCE.parent/'manifest.json').read_text('utf8'));state=old['stateRva'];rx=p.sections[-2];rw=p.sections[-1]
 assert rx.Misc_VirtualSize==rx.SizeOfRawData==0x10000 and rw.SizeOfRawData==0x3000
 code_start=0x2853000;limit=rx.VirtualAddress+rx.SizeOfRawData;off=p.get_offset_from_rva(code_start);assert b[off:p.get_offset_from_rva(limit-1)+1]==b'\xcc'*(limit-code_start)
 decoder,dm=D.emit(base+code_start,base+state+K.CACHE_OFFSET);assert dm['contractSha256']==SHA((SHARED/'preset-contract-v1.json').read_bytes())
 payload=bytearray(decoder);sources={'preset_decoder':dm['assembly']};patches=[];md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True;ks=Ks(KS_ARCH_X86,KS_MODE_64)
 def pad(a):
  while len(payload)%a:payload.append(0xcc)
 def append(name,data,asm=''):
  pad(16);r=code_start+len(payload);payload.extend(data)
  if asm:sources[name]=asm
  return r
 pad(32);table_rva=code_start+len(payload);contract=json.loads((SHARED/'preset-contract-v1.json').read_text('utf8'));profiles=[dict(id=0,cameraX=.75,cameraY=1.,fixedUiScaleX=.75,fixedUiScaleY=1.,aspect='16:9')]+contract['presets'];table=[]
 for row in profiles:
  sx=row['fixedUiScaleX'];sy=row['fixedUiScaleY'];record=struct.pack('<6f2I',sx,sy,320*(1-sx),240*(1-sy),row['cameraX'],row['cameraY'],int(row['aspect']=='16:9'),0);payload.extend(record);table.append(dict(id=row['id'],hex=record.hex(),camera=[row['cameraX'],row['cameraY']],ui=[sx,sy],clear=row['aspect']=='16:9'))
 pad(16);kernel_rva=code_start+len(payload);kernel,entries,assemblies,links=K.emit(base+kernel_rva,base+state,base+0x1457060,base+code_start,base+table_rva);payload.extend(kernel);sources.update(assemblies)
 oldcode,oldentries,_,_=OLD.emit(base+old['codeRva'],base+state,base+0x1457060);assert b[p.get_offset_from_rva(old['codeRva']):p.get_offset_from_rva(old['codeRva'])+len(oldcode)]==oldcode
 def jmp(at,target,n):return b'\xe9'+struct.pack('<i',target-at-5)+b'\x90'*(n-5)
 def patch(name,rva,pin,new):
  o=p.get_offset_from_rva(rva);assert b[o:o+len(pin)]==pin and len(pin)==len(new)
  ins=list(md.disasm(pin,base+rva));assert sum(i.size for i in ins)==len(pin)
  patches.append(dict(name=name,rva=rva,fileOffset=o,before=pin.hex(),after=new.hex(),instructionStarts=[i.address-base for i in ins]))
 for name,address in oldentries.items():patch(name,address-base,bytes.fromhex('9c50535152'),jmp(address-base,entries[name]-base,5))
 camera=[]
 for axis,rva,hexbefore,field in[('Y',0x41004,'43c7043e0000803f',20),('X',0x41010,'43c7043e0000403f',16)]:
  pad(16);target=code_start+len(payload);lines=['pushfq','push rax','push rdx','push rbp','mov rbp,rsp','and rsp,-16','sub rsp,0x20',f'call {base+code_start}','lea rdx,[rip]','shl eax,5',f'mov eax,[rdx+rax+{field}]','mov [r15+r14],eax','mov rsp,rbp','pop rbp','pop rdx','pop rax','popfq',f'jmp {base+rva+8}'];asm='\n'.join(lines);raw=bytearray(ks.asm(asm,addr=base+target)[0])
  for i in md.disasm(raw,base+target):
   if i.mnemonic=='lea'and i.op_str=='rdx, [rip]':struct.pack_into('<i',raw,i.address-(base+target)+i.disp_offset,base+table_rva-i.address-i.size)
  payload.extend(raw);sources['camera_'+axis]=asm;patch('camera_'+axis,rva,bytes.fromhex(hexbefore),jmp(rva,target,8));camera.append(dict(axis=axis,rva=rva,continuationRva=rva+8,wrapperRva=target))
 cp=old['movieClear'];wo=p.get_offset_from_rva(cp['wrapperEntryRva']);pin=bytes.fromhex('81f900000100');prefix=b[wo:wo+0x200];assert prefix.count(pin)==1;gate=cp['wrapperEntryRva']+prefix.index(pin)
 pad(16);target=code_start+len(payload);lines=['mov rbp,rsp','and rsp,-16','sub rsp,0x20',f'call {base+code_start}','mov rsp,rbp','lea rdx,[rip]','shl eax,5','cmp dword ptr [rdx+rax+24],0',f'je {base+cp["returnNativeRva"]}','mov rax,qword ptr [r15+r14]','mov rcx,qword ptr [r15+r14+16]','mov rdx,qword ptr [r15+r14+24]','mov rbp,qword ptr [r15+r14+32]','cmp ecx,0x10000',f'jmp {base+gate+6}']
 # All original registers are already in the wrapper guest-stack spill. Its RCX
 # slot is index2*8=16; RBP/RDX/EAX scratch may change until original restore.
 asm='\n'.join(lines);raw=bytearray(ks.asm(asm,addr=base+target)[0])
 for i in md.disasm(raw,base+target):
  if i.mnemonic=='lea'and i.op_str=='rdx, [rip]':struct.pack_into('<i',raw,i.address-(base+target)+i.disp_offset,base+table_rva-i.address-i.size)
 payload.extend(raw);sources['preset_movie_clear_gate']=asm;patch('movie_clear_gate',gate,pin,jmp(gate,target,6))
 pad(4);unwind_rvas=[]
 for fn in dm['unwindFunctions']:
  at=code_start+len(payload);payload.extend(bytes.fromhex(fn['unwindHex']));pad(4);unwind_rvas.append(dict(beginRva=fn['beginVA']-base,endRva=fn['endVA']-base,unwindRva=at))
 pad(4);pdata_rva=code_start+len(payload);directory=p.OPTIONAL_HEADER.DATA_DIRECTORY[3];oldpd=b[p.get_offset_from_rva(directory.VirtualAddress):p.get_offset_from_rva(directory.VirtualAddress)+directory.Size];pd=list(struct.iter_unpack('<III',oldpd))+[(x['beginRva'],x['endRva'],x['unwindRva'])for x in unwind_rvas];pd.sort();assert all(pd[i][1]<=pd[i+1][0]for i in range(len(pd)-1));pdata=b''.join(struct.pack('<III',*row)for row in pd);payload.extend(pdata)
 assert code_start+len(payload)<=limit
 # No new map keys: all15 old service starts and both camera MOVs are detached
 # whole instructions; unknown branches/interior aliases are rejected.
 ranges=[(x['rva'],x['rva']+len(bytes.fromhex(x['before'])))for x in patches]
 interior=lambda r:any(l<r<e for l,e in ranges)
 tableStart=p.get_offset_from_rva(0x1457190);tableEnd=p.get_offset_from_rva(0x27c4fd8);mapdata=b[tableStart:tableEnd];aliases=[]
 for key,value in struct.iter_unpack('<II',mapdata):
  if interior(value):aliases.append(dict(guestVA=key+0x10000,rva=value))
 assert not aliases,'Unhandled dispatch entry inside new detour'
 branches=[]
 for s in p.sections:
  if not(s.Characteristics&0x20000000):continue
  d=b[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData];origin=s.VirtualAddress
  for match in re.finditer(rb'\xe8|\xe9|\x0f[\x80-\x8f]',d):
   pos=match.start();n=6 if d[pos]==15 else 5
   if pos+n<=len(d):
    dest=origin+pos+n+struct.unpack_from('<i',d,pos+n-4)[0]
    if interior(dest):branches.append(dict(sourceRva=origin+pos,targetRva=dest))
  for left,right in ranges:
   for pos in range(max(0,left-origin-130),min(len(d)-1,right-origin+130)):
    op=d[pos]
    if op==0xeb or 0x70<=op<=0x7f or 0xe0<=op<=0xe3:
     dest=origin+pos+2+struct.unpack_from('<b',d,pos+1)[0]
     if interior(dest):branches.append(dict(sourceRva=origin+pos,targetRva=dest))
 assert not branches,'Direct branch candidate into newdetour requires review'
 fixed=bytearray(b);allowed=[]
 def change(at,raw,purpose):fixed[at:at+len(raw)]=raw;allowed.append(dict(start=at,end=at+len(raw),purpose=purpose))
 for x in patches:change(x['fileOffset'],bytes.fromhex(x['after']),x['name'])
 change(off,payload,'newRXcode/data insideexistingreservation');change(rw.get_field_absolute_offset('Misc_VirtualSize'),struct.pack('<I',0x3000),'declareentireRWusedextent')
 change(directory.get_field_absolute_offset('VirtualAddress'),struct.pack('<II',pdata_rva,len(pdata)),'extendedparserunwinddirectory')
 q=pefile.PE(data=fixed);check=p.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum');change(check,struct.pack('<I',q.generate_checksum()),'checksum');q=pefile.PE(data=fixed);assert q.verify_checksum()and not q.get_warnings()
 mask=bytearray(len(b))
 for a in allowed:mask[a['start']:a['end']]=b'\1'*(a['end']-a['start'])
 assert all(a==z or mask[i]for i,(a,z)in enumerate(zip(b,fixed))) and len(fixed)==len(b)
 assert fixed[tableStart:tableEnd]==mapdata
 retained=[]
 for s in p.sections:
  if s.Name.rstrip(b'\0')in[b'.kradio',b'.autocap',b'.widesta']:
   raw=b[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData];assert raw==fixed[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData];retained.append(dict(name=s.Name.rstrip(b'\0').decode(),sha256=SHA(raw),bytes=len(raw)))
 r=dict(schema='native-overscan-preset-v1',source=str(SOURCE),sourceSha256=SHA(b),patchedSha256=SHA(fixed),bytes=len(fixed),imageBase=base,codeRva=code_start,codeBytes=len(payload),profileTableRva=table_rva,profiles=table,decoder=dm,kernelRva=kernel_rva,kernelBytes=len(kernel),kernelEntries={n:a-base for n,a in entries.items()},kernelLinks=links,
  cameraHooks=camera,movieGate=dict(sourceRva=gate,newRva=target),patches=patches,allowedExistingByteRanges=allowed,stateRva=state,stateReserve=0x3000,slotBytes=0x500,quadRecordBytes=56,cacheRva=state+K.CACHE_OFFSET,
  dispatchEntriesScanned=len(mapdata)//8,mapTableByteExact=True,newInteriorAliases=aliases,newDirectBranchCandidates=branches,koreanAndStateRawSections=retained,newSectionsAdded=False,fileSizeUnchanged=True,imageSizeUnchanged=True,
  parserUnwind=unwind_rvas,exceptionDirectoryRva=pdata_rva,exceptionEntries=len(pd),legacy=old,
  limits=['PhysicalrendercropandintegerNmustmatchsame sharedpresetdecoder inGPU; not a standalone resolutionchange.','Existing and regenerated scopedservices/camera trampolines have no newlyclaimed Windowsunwind metadata; normalreturn tested, exceptions notvalidated.','Logical640x480/singleplayerscope; unsupported2Dprimitivepaths remain.'],installedWrite=False,runtimeAccess=False)
 return b,bytes(fixed),r,sources

