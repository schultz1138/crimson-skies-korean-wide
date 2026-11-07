"""Offline Alpha7 extension for source-owned radar8 and odometer9 submits."""
from pathlib import Path
import sys, struct, hashlib, json, re, subprocess, importlib.util
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]; V1=HERE.parent/'overscan-candidate-v1';V2=HERE.parent/'overscan-candidate-v2';V4=HERE.parent/'overscan-candidate-v4'
sys.path[:0]=[str(ROOT/'pythonlibs'),str(ROOT/'widescreen-analysis/ui'),str(ROOT/'widescreen-analysis/ui/testdeps'),str(HERE),str(V1)]
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from keystone import Ks,KS_ARCH_X86,KS_MODE_64
import uniform_kernel as K
import extra_diagnostic as DIAG
NAME='xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll'
SOURCE=V4/NAME
SHA=lambda b:hashlib.sha256(b).hexdigest()
PINS=[dict(name='quad_pre_8',guestVA=0x2e733,rva=0x42996,continuationRva=0x4299f,pin='43c7443efc38e70200'),
      dict(name='quad_post_8',guestVA=0x2e738,rva=0x429a8,continuationRva=0x429af,pin='418b87c8193200'),
      dict(name='quad_pre_9',guestVA=0x2f18e,rva=0x43b5d,continuationRva=0x43b66,pin='43c7443efc93f10200'),
      dict(name='quad_post_9',guestVA=0x2f193,rva=0x43b6f,continuationRva=0x43b76,pin='418b87c8193200')]
SITES=[dict(site=8,delta=0x78,direct=True,stride=36,primitive=7,count=4),
       dict(site=9,delta=0x24,direct=True,stride=28,primitive=7,count=4)]

def geometry_stride(body,stride):
 if stride==28:return body
 assert stride==36
 def replace(match):
  offset=int(match.group(1));q,r=divmod(offset,28);assert q<4 and r in (0,4)
  return '[rsi+'+str(q*stride+r)+']'
 return [re.sub(r'\[rsi\+(\d+)\]',replace,s).replace('cmp rdx,0x7fffff80','cmp rdx,0x7fffff60')for s in body]

def prepare():
 b=SOURCE.read_bytes();assert SHA(b)=='57be47f3e8b1c1f757880c68df67a7fa586445993e2f065aaefd42e7e15e30c1'
 p=pefile.PE(data=b); base=p.OPTIONAL_HEADER.ImageBase;alpha7=json.loads((V4/'manifest.json').read_text('utf8'));inherited=alpha7['inheritedManifest']['inherited']
 md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True; ks=Ks(KS_ARCH_X86,KS_MODE_64)
 code_start=0x285b000; rx=next(s for s in p.sections if s.VirtualAddress<=code_start<s.VirtualAddress+s.Misc_VirtualSize)
 assert rx.VirtualAddress==0x2851000 and rx.Misc_VirtualSize==rx.SizeOfRawData==0x10000
 off=p.get_offset_from_rva(code_start);limit=rx.VirtualAddress+rx.SizeOfRawData
 assert b[off:p.get_offset_from_rva(limit-1)+1]==b'\xcc'*(limit-code_start)
 payload=bytearray(); entries={}; asm_by_name={};links=[];patches=[]
 def pad():
  while len(payload)%16:payload.append(0xcc)
 specs=[]
 for site in SITES:
  n=site['site'];stride=site['stride']
  pre=geometry_stride(K.pre(n,site['delta'],site['direct'],base+inherited['codeRva']),stride)
  if stride==36:
   assert pre.count('cmp dword ptr [r15+r14+12],28')==1
   pre=[s.replace('cmp dword ptr [r15+r14+12],28','cmp dword ptr [r15+r14+12],36')for s in pre]
  pre=DIAG.decorate(DIAG.full_guest32(pre),n,True)
  specs.extend([('quad_pre_'+str(n),pre),('quad_post_'+str(n),geometry_stride(K.post(n),stride))])
 for name,body in specs:
  pad();address=base+code_start+len(payload);entries[name]=address
  pro=[s.replace('add r10,0x400','add r10,0x500')for s in K.OLD.V1.prologue()]
  asm='\n'.join(pro+body+K.OLD.V1.epilogue());data=bytearray(ks.asm(asm,addr=address)[0]);asm_by_name[name]=asm
  ins=list(md.disasm(data,address));assert sum(i.size for i in ins)==len(data)
  for i in ins:
   target=base+0x1457060 if i.mnemonic=='call'and i.op_str=='qword ptr [rip]'else base+inherited['stateRva'] if i.mnemonic=='lea'and i.op_str in ['r10, [rip]','rdi, [rip]']else base+inherited['profileTableRva'] if i.mnemonic=='lea'and i.op_str=='rdx, [rip]'else None
   if target is not None:
    assert i.disp_size==4;struct.pack_into('<i',data,i.address-address+i.disp_offset,target-i.address-i.size)
    links.append(dict(service=name,instructionVA=i.address,targetVA=target))
  payload.extend(data)
 for pin in PINS:
  raw=bytes.fromhex(pin['pin']);o=p.get_offset_from_rva(pin['rva']);assert b[o:o+len(raw)]==raw
  ins=list(md.disasm(raw,base+pin['rva']));assert sum(i.size for i in ins)==len(raw)
  assert all(not(op.type==3 and i.reg_name(op.mem.base)=='rip')for i in ins for op in i.operands)
  pad();target=code_start+len(payload);service=entries[pin['name']]
  thunk=b'\xe8'+struct.pack('<i',service-(base+target)-5)+raw
  thunk+=b'\xe9'+struct.pack('<i',pin['continuationRva']-(target+len(thunk))-5)
  payload.extend(thunk)
  new=b'\xe9'+struct.pack('<i',target-pin['rva']-5)+b'\x90'*(len(raw)-5)
  patches.append(dict(**pin,fileOffset=o,before=raw.hex(),after=new.hex(),wrapperRva=target,serviceRva=service-base))
 assert code_start+len(payload)<=limit
 ranges=[(h['rva'],h['continuationRva'])for h in patches]
 interior=lambda value:any(lo<value<hi for lo,hi in ranges)
 tableStart=p.get_offset_from_rva(0x1457190);tableEnd=p.get_offset_from_rva(0x27c4fd8)
 mapdata=b[tableStart:tableEnd];aliases=[];entry_aliases=[]
 for key,value in struct.iter_unpack('<II',mapdata):
  if interior(value):aliases.append(dict(guestVA=key+0x10000,rva=value))
  if any(value==lo for lo,hi in ranges):entry_aliases.append(dict(guestVA=key+0x10000,rva=value))
 assert not aliases,aliases
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
 # The conservative raw-byte short-branch scan sees E2 inside the original
 # CALL translation's JMP displacement. Pin the complete owning instruction,
 # its decoded destination and absence of any dispatch operand entry. This is
 # one explicit non-instruction byte case, not a general exception to the gate.
 ownerRva=0x43b6a;ownerOffset=p.get_offset_from_rva(ownerRva);ownerBytes=bytes.fromhex('e9e1e2f500')
 assert b[ownerOffset:ownerOffset+5]==ownerBytes
 ownerIns=list(md.disasm(ownerBytes,ownerRva));assert len(ownerIns)==1 and ownerIns[0].mnemonic=='jmp'and ownerIns[0].op_str=='0xfa1e50'
 ownerAliases=[dict(guestVA=k+0x10000,rva=v)for k,v in struct.iter_unpack('<II',mapdata)if ownerRva<v<ownerRva+5];assert not ownerAliases
 reviewed=[dict(**row,reason='E2 byte lies inside pinned original JMP displacement',ownerInstructionRva=ownerRva,ownerBytes=ownerBytes.hex(),ownerTargetRva=0xfa1e50)for row in branches if row==dict(sourceRva=0x43b6c,targetRva=0x43b63)]
 branches=[row for row in branches if row!=dict(sourceRva=0x43b6c,targetRva=0x43b63)]
 assert not branches,branches
 fixed=bytearray(b);allowed=[]
 def change(at,raw,purpose):
  fixed[at:at+len(raw)]=raw;allowed.append(dict(start=at,end=at+len(raw),purpose=purpose))
 for h in patches:change(h['fileOffset'],bytes.fromhex(h['after']),h['name'])
 change(off,payload,'four new radar/odometer services and whole-instruction wrappers in existing RX reservation')
 checksum=p.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum');q=pefile.PE(data=fixed)
 change(checksum,struct.pack('<I',q.generate_checksum()),'PE checksum')
 q=pefile.PE(data=fixed);assert q.verify_checksum()and not q.get_warnings()
 mask=bytearray(len(b))
 for r in allowed:mask[r['start']:r['end']]=b'\1'*(r['end']-r['start'])
 assert len(fixed)==len(b) and all(x==y or mask[n]for n,(x,y)in enumerate(zip(b,fixed)))
 assert fixed[tableStart:tableEnd]==mapdata
 for s in p.sections:
  if s.Name.rstrip(b'\0')!=b'.wideui':assert fixed[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]==b[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData] or any(s.PointerToRawData<=h['fileOffset']<s.PointerToRawData+s.SizeOfRawData for h in patches)
 directory=p.OPTIONAL_HEADER.DATA_DIRECTORY[3]
 eo=p.get_offset_from_rva(directory.VirtualAddress);exception=b[eo:eo+directory.Size]
 assert fixed[eo:eo+directory.Size]==exception
 metadata=dict(schema='native-overscan-preset-v5-radar-and-odometer',source=str(SOURCE),sourceSha256=SHA(b),patchedSha256=SHA(fixed),bytes=len(b),imageBase=base,codeRva=code_start,codeBytes=len(payload),hooks=patches,sites=SITES,serviceEntries={k:v-base for k,v in entries.items()},kernelLinks=links,
  inheritedManifestSha256=SHA((V4/'manifest.json').read_bytes()),alpha7Manifest=alpha7,inherited=inherited,allowedExistingByteRanges=allowed,dispatchEntriesScanned=len(mapdata)//8,dispatchTableByteExact=True,interiorAliases=aliases,entryAliases=entry_aliases,directBranchInteriorCandidates=branches,reviewedNonInstructionCandidates=reviewed,
  stateRva=inherited['stateRva'],stateReserve=inherited['stateReserve'],newSectionsAdded=False,fileSizeUnchanged=True,imageSizeUnchanged=True,exceptionDirectoryByteExact=True,exceptionDirectorySha256=SHA(exception),
  sourceChain=['radar8: RadarUI114900->1137a0->113910->30320->30384->2e320->2e733;direct7/4/36/ESP+78','odometer9: AmmoUIvt29d124+24=bd8c0->bcd20->bcea7->100f00->100c40->100d5c/100e60->2efc0->2f18e;direct7/4/28/ESP+24'],
  extraTelemetry=dict(stateOffset=0x2800,threadStride=0x40,siteStride=24,siteBase=8,threadCount=8,usedEnd=0x29f0,reservedEnd=0x2a00,cacheOffset=0x2f00,fields=DIAG.FIELDS,reasons=DIAG.REASONS,indexFormula='((R10-stateBase)/0x500)*0x40+(site-8)*24+0x2800;64-bit subtraction then32-bit DIV ECX with divisor0x500(1280)'),
  previousServicesDecoderProfilesAndRawStateByteExact=True,allKoreanDispatchEntriesByteExact=True,installedWrite=False,runtimeAccess=False,
  limits=['Private emulator tests do not execute the real D3D submit.','New helpers retain the existing dynamic-alignment service ABI; normal return is tested, host exception unwind is not claimed.','Only radar8/odometer9 are added; all old7 services and telemetry byteexact.','New mode0 calls update the existing per-slot4e8 aggregate with site8/9; the old7 layout and code are unchanged.'])
 return b,bytes(fixed),metadata,asm_by_name

