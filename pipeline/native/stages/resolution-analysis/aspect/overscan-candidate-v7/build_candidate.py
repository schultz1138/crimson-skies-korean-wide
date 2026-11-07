"""Offline Alpha8 extension; Solid12 preserves uniform full-canvas fills."""
from pathlib import Path
import sys, struct, hashlib, json, re, subprocess, importlib.util
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]; V1=HERE.parent/'overscan-candidate-v1';V2=HERE.parent/'overscan-candidate-v2';V4=HERE.parent/'overscan-candidate-v4';V5=HERE.parent/'overscan-candidate-v5'
sys.path[:0]=[str(ROOT/'pythonlibs'),str(ROOT/'widescreen-analysis/ui'),str(ROOT/'widescreen-analysis/ui/testdeps'),str(HERE),str(V1)]
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from keystone import Ks,KS_ARCH_X86,KS_MODE_64
import uniform_kernel as K
import extra_diagnostic as DIAG
from solid_policy import full_canvas_policy
NAME='xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll'
SOURCE=V5/NAME
SHA=lambda b:hashlib.sha256(b).hexdigest()
PINS=[dict(name='quad_pre_10',guestVA=0x124880,rva=0x83fae9,continuationRva=0x83faf2,pin='43c7443efc85481200'),
      dict(name='quad_post_10',guestVA=0x124885,rva=0x83fafb,continuationRva=0x83fb07,pin='458d76fc43c7043e01000000'),
      dict(name='quad_pre_11',guestVA=0x2ef5e,rva=0x43710,continuationRva=0x43719,pin='43c7443efc63ef0200'),
      dict(name='quad_post_11',guestVA=0x2ef63,rva=0x43722,continuationRva=0x43729,pin='418b87c8193200'),
      dict(name='quad_pre_12',guestVA=0x2f2c6,rva=0x43d94,continuationRva=0x43d9d,pin='43c7443efccbf20200'),
      dict(name='quad_post_12',guestVA=0x2f2cb,rva=0x43da6,continuationRva=0x43dad,pin='418b87c8193200')]
SITES=[dict(site=10,delta=0x5c,direct=False,stride=28,primitive=7,count=4),
       dict(site=11,delta=0x88,direct=True,stride=28,primitive=7,count=4),
       dict(site=12,delta=0x10,direct=True,stride=28,primitive=7,count=4)]

def geometry_stride(body,stride):
 if stride==28:return body
 assert stride==36
 def replace(match):
  offset=int(match.group(1));q,r=divmod(offset,28);assert q<4 and r in (0,4)
  return '[rsi+'+str(q*stride+r)+']'
 return [re.sub(r'\[rsi\+(\d+)\]',replace,s).replace('cmp rdx,0x7fffff80','cmp rdx,0x7fffff60')for s in body]

def prepare():
 b=SOURCE.read_bytes();assert SHA(b)=='cd85b37e6df2c3a0c8a8efa3da916892171f540a1110fbeb85066daf3c59ed07'
 p=pefile.PE(data=b); base=p.OPTIONAL_HEADER.ImageBase;alpha8=json.loads((V5/'manifest.json').read_text('utf8'));alpha7=alpha8['alpha7Manifest'];inherited=alpha8['inherited']
 md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True; ks=Ks(KS_ARCH_X86,KS_MODE_64)
 code_start=0x285c000; rx=next(s for s in p.sections if s.VirtualAddress<=code_start<s.VirtualAddress+s.Misc_VirtualSize)
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
  pre=DIAG.full_guest32(pre)
  if n==12:pre=full_canvas_policy(pre)
  pre=DIAG.decorate(pre,n,site['direct'])
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
 # Exact raw-byte falsepositive: E0F5 is inside the original CALL-lowering
 # JMP displacement, not a LOOPNE instruction. Require the whole owning JMP,
 # decoded destination and no dispatch operand entry; reject every other hit.
 ownerRva=0x43da1;ownerOffset=p.get_offset_from_rva(ownerRva);ownerBytes=bytes.fromhex('e9aae0f500')
 assert b[ownerOffset:ownerOffset+5]==ownerBytes
 ownerIns=list(md.disasm(ownerBytes,ownerRva));assert len(ownerIns)==1 and ownerIns[0].mnemonic=='jmp'and ownerIns[0].op_str=='0xfa1e50'
 ownerAliases=[dict(guestVA=k+0x10000,rva=v)for k,v in struct.iter_unpack('<II',mapdata)if ownerRva<v<ownerRva+5];assert not ownerAliases
 reviewed=[dict(**row,reason='E0F5 bytes lie inside pinned original JMP displacement',ownerInstructionRva=ownerRva,ownerBytes=ownerBytes.hex(),ownerTargetRva=0xfa1e50)for row in branches if row==dict(sourceRva=0x43da3,targetRva=0x43d9a)]
 branches=[row for row in branches if row!=dict(sourceRva=0x43da3,targetRva=0x43d9a)]
 assert not branches,branches
 fixed=bytearray(b);allowed=[]
 def change(at,raw,purpose):
  fixed[at:at+len(raw)]=raw;allowed.append(dict(start=at,end=at+len(raw),purpose=purpose))
 for h in patches:change(h['fileOffset'],bytes.fromhex(h['after']),h['name'])
 change(off,payload,'six new health/framecorner/solidrect services and whole-instruction wrappers in existing RX reservation')
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
 metadata=dict(schema='native-overscan-preset-v7-fullcanvas-preserving-solid',source=str(SOURCE),sourceSha256=SHA(b),patchedSha256=SHA(fixed),bytes=len(b),imageBase=base,codeRva=code_start,codeBytes=len(payload),hooks=patches,sites=SITES,serviceEntries={k:v-base for k,v in entries.items()},kernelLinks=links,
  inheritedManifestSha256=SHA((V5/'manifest.json').read_bytes()),alpha8Manifest=alpha8,alpha7Manifest=alpha7,inherited=inherited,allowedExistingByteRanges=allowed,dispatchEntriesScanned=len(mapdata)//8,dispatchTableByteExact=True,interiorAliases=aliases,entryAliases=entry_aliases,directBranchInteriorCandidates=branches,reviewedNonInstructionCandidates=reviewed,
  stateRva=inherited['stateRva'],stateReserve=inherited['stateReserve'],newSectionsAdded=False,fileSizeUnchanged=True,imageSizeUnchanged=True,exceptionDirectoryByteExact=True,exceptionDirectorySha256=SHA(exception),
  sourceChain=['health10: UnitHealthUI124a70->124adc->124490->124880->2b7f0;indirect4/28/ESP+5c;separateframe124893->2dec0','goal11: PauseWidgetFrame->FramePainterVT29fb4c+8de850->de891->2fda0;fourcorners300d3/30100/3012d/30167->2eb40->2ef5e;direct7/4/28/ESP+88','solid12: canonical2f1d0 integerRECT->screenXY;Z0/RHW1/texture0null/FVF144;2f2c6direct7/4/28/ESP+10'],
  extraTelemetry=dict(stateOffset=0x2a00,threadStride=0x80,siteStride=24,siteBase=10,threadCount=8,usedEnd=0x2dc8,reservedEnd=0x2e00,cacheOffset=0x2f00,fields=DIAG.FIELDS,reasons=DIAG.REASONS,indexFormula='((R10-stateBase)/0x500)*0x80+(site-10)*24+0x2a00;64-bit subtraction then32-bit DIV ECX with divisor0x500(1280)'),
  previousServicesDecoderProfilesAndRawStateByteExact=True,allKoreanDispatchEntriesByteExact=True,installedWrite=False,runtimeAccess=False,
  solid12FullCanvasBypass=dict(onlySite=12,predicate='minX<=0,maxX>=640,minY<=0,maxY>=480',coordinates='Already saved, finite-validated journalXY only',flags=0,diagnosticReason=15,acceptedCounterIncrements=False,sourceAxisAlignedRect=True,sourceUniformSingleDwordColor=True,extraValidationYReadsLegacySolid12Bytes=16,extraValidationReadsTaggedPresetsBytes=0,legacyPartialXOnlyFlags1Preserved=True,noAdditionalApiCall=True,noAdditionalColorOrUvRead=True),
  limits=['Private emulator tests do not execute the real D3D submit.','New helpers retain the existing dynamic-alignment service ABI; normal return is tested, host exception unwind is not claimed.','Only health10/framecorners11/canonicalsolid12 are added; all old9 services/telemetry byteexact.','New mode0 calls update the existing per-slot4e8 aggregate with site10/11/12; its format and old code are unchanged.'])
 return b,bytes(fixed),metadata,asm_by_name

