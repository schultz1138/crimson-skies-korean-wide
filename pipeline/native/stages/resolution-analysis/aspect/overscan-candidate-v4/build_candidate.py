"""Offline V4: admit zero-extended full guest32 stacks; retain V3 telemetry."""
from pathlib import Path
import sys,struct,hashlib,json,re,subprocess,importlib.util
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];V1=HERE.parent/'overscan-candidate-v1';V2=HERE.parent/'overscan-candidate-v2'
sys.path[:0]=[str(ROOT/'pythonlibs'),str(ROOT/'widescreen-analysis/ui'),str(ROOT/'widescreen-analysis/ui/testdeps'),str(V1),str(HERE)]
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from keystone import Ks,KS_ARCH_X86,KS_MODE_64
import uniform_kernel as K
import diagnostic_pre as DIAG
NAME='xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll';SOURCE=V2/NAME
SHA=lambda b:hashlib.sha256(b).hexdigest()
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

def prepare():
 b=SOURCE.read_bytes();assert SHA(b)=='84002944db6c9bdde3fe53db49adebf8d6bc9da8922e3e550e9acf190425cbc5'
 old=json.loads((V2/'manifest.json').read_text('utf8'));e4=old['inherited'];p=pefile.PE(data=b);base=p.OPTIONAL_HEADER.ImageBase
 ext=module('a5_builder_source',V2/'build_candidate.py');sites=[dict(site=1,delta=0xf0,direct=True,stride=28,primitive=7,count=4),dict(site=2,delta=0x80,direct=True,stride=28,primitive=7,count=4),dict(site=3,delta=0x7c,direct=False,stride=28,primitive=7,count=4),dict(site=4,delta=0x10,direct=True,stride=28,primitive=6,count=4)]+old['sites']
 md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True;ks=Ks(KS_ARCH_X86,KS_MODE_64)
 code_start=0x2858000;rx=next(s for s in p.sections if s.VirtualAddress<=code_start<s.VirtualAddress+s.Misc_VirtualSize);limit=rx.VirtualAddress+rx.SizeOfRawData;off=p.get_offset_from_rva(code_start)
 assert rx.Misc_VirtualSize==rx.SizeOfRawData==0x10000 and b[off:p.get_offset_from_rva(limit-1)+1]==b'\xcc'*(limit-code_start)
 payload=bytearray();entries={};sources={};links=[];patches=[]
 for site in sites:
  n=site['site'];name='quad_pre_'+str(n)
  while len(payload)%16:payload.append(0xcc)
  at=base+code_start+len(payload);entries[name]=at-base
  body=ext.geometry_stride(K.pre(n,site['delta'],site['direct'],base+e4['codeRva']),site['stride'])
  body=DIAG.decorate(DIAG.full_guest32(body),n,site['direct']);pro=[s.replace('add r10,0x400','add r10,0x500')for s in K.OLD.V1.prologue()]
  asm='\n'.join(pro+body+K.OLD.V1.epilogue());data=bytearray(ks.asm(asm,addr=at)[0]);sources[name]=asm
  ins=list(md.disasm(data,at));assert sum(i.size for i in ins)==len(data)
  for i in ins:
   target=base+0x1457060 if i.mnemonic=='call'and i.op_str=='qword ptr [rip]'else base+e4['stateRva'] if i.mnemonic=='lea'and i.op_str=='r10, [rip]'else base+e4['profileTableRva'] if i.mnemonic=='lea'and i.op_str=='rdx, [rip]'else None
   if target is not None:
    struct.pack_into('<i',data,i.address-at+i.disp_offset,target-i.address-i.size);links.append(dict(service=name,instructionVA=i.address,targetVA=target))
  payload.extend(data)
  origin=e4['kernelEntries'][name]if n<=4 else old['serviceEntries'][name]
  po=p.get_offset_from_rva(origin);pin=bytes.fromhex('9c50535152');assert b[po:po+5]==pin
  replacement=b'\xe9'+struct.pack('<i',at-(base+origin)-5)
  patches.append(dict(name=name,rva=origin,fileOffset=po,before=pin.hex(),after=replacement.hex(),diagnosticServiceRva=at-base))
 assert code_start+len(payload)<=limit
 ranges=[(h['rva'],h['rva']+5)for h in patches];interior=lambda r:any(lo<r<hi for lo,hi in ranges)
 ts=p.get_offset_from_rva(0x1457190);te=p.get_offset_from_rva(0x27c4fd8);mapdata=b[ts:te]
 aliases=[dict(guestVA=k+0x10000,rva=v)for k,v in struct.iter_unpack('<II',mapdata)if interior(v)];assert not aliases,aliases
 branches=[]
 for s in p.sections:
  if not(s.Characteristics&0x20000000):continue
  d=b[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData];origin=s.VirtualAddress
  for match in re.finditer(rb'\xe8|\xe9|\x0f[\x80-\x8f]',d):
   pos=match.start();n=6 if d[pos]==15 else 5
   if pos+n<=len(d):
    dest=origin+pos+n+struct.unpack_from('<i',d,pos+n-4)[0]
    if interior(dest):branches.append(dict(sourceRva=origin+pos,targetRva=dest))
  for lo,hi in ranges:
   for pos in range(max(0,lo-origin-130),min(len(d)-1,hi-origin+130)):
    op=d[pos]
    if op==0xeb or 0x70<=op<=0x7f or 0xe0<=op<=0xe3:
     dest=origin+pos+2+struct.unpack_from('<b',d,pos+1)[0]
     if interior(dest):branches.append(dict(sourceRva=origin+pos,targetRva=dest))
 assert not branches,branches
 fixed=bytearray(b);allowed=[]
 def change(at,raw,purpose):fixed[at:at+len(raw)]=raw;allowed.append(dict(start=at,end=at+len(raw),purpose=purpose))
 for h in patches:change(h['fileOffset'],bytes.fromhex(h['after']),h['name']+' diagnostic forwarding')
 change(off,payload,'seven diagnostic-only pre services inside existing RX reservation')
 checksum=p.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum');q=pefile.PE(data=fixed);change(checksum,struct.pack('<I',q.generate_checksum()),'PE checksum')
 q=pefile.PE(data=fixed);assert q.verify_checksum()and not q.get_warnings()
 mask=bytearray(len(b))
 for a in allowed:mask[a['start']:a['end']]=b'\1'*(a['end']-a['start'])
 assert len(fixed)==len(b)and all(x==y or mask[n]for n,(x,y)in enumerate(zip(b,fixed)))
 assert fixed[ts:te]==mapdata
 rw=next(s for s in p.sections if s.VirtualAddress==e4['stateRva']);assert b[rw.PointerToRawData:rw.PointerToRawData+rw.SizeOfRawData]==fixed[rw.PointerToRawData:rw.PointerToRawData+rw.SizeOfRawData]
 m=dict(schema='full-zero-extended-guest32-quad-pre-v4',source=str(SOURCE),sourceSha256=SHA(b),patchedSha256=SHA(fixed),bytes=len(b),imageBase=base,codeRva=code_start,codeBytes=len(payload),patches=patches,sites=sites,serviceEntries=entries,kernelLinks=links,
  inheritedManifest=old,allowedExistingByteRanges=allowed,dispatchEntriesScanned=len(mapdata)//8,dispatchTableByteExact=True,allKoreanDispatchEntriesByteExact=True,newInteriorAliases=aliases,newDirectBranchCandidates=branches,
  stateRva=e4['stateRva'],stateReserve=e4['stateReserve'],slotBytes=0x500,diagnosticOffset=0x440,diagnosticSiteBytes=24,diagnosticFields=DIAG.FIELDS,diagnosticReasons=DIAG.REASONS,diagnosticRegionEnd=0x500,
  modeZeroAggregateOffset=0x4e8,modeZeroAggregateFields=['site','scopeDepth','topScopeKind','topScopePreviousMode','guestEspLow32','scopeOverflow'],
  postServicesByteExact=True,allGuestNativeDetoursByteExact=True,geometryFormulaScopeAndThisPoliciesUnchanged=True,modeZeroPreservesLastEligibleHistory=True,extraGuestReadsAdded=False,newSectionsAdded=False,fileSizeUnchanged=True,imageSizeUnchanged=True,exceptionDirectoryUnchanged=True,
  fullGuest32StackGate=['mov eax,r14d','cmp r14,rax','jne done','cmp r14d,0x10000','jb done','cmp r14d,0xffffff00','ja done'],vertexCaps={'stride28':'0xffffff80','stride36':'0xffffff60'},zeroExtensionRejectReason=14,
  installedWrite=False,runtimeAccess=False,limits=['Diagnostics are non-atomic modulo32-bit counters and last eligible observations.','Mode0 calls preserve last eligible reason/value; no claim that stale success describes current frame.','R14.low32 is logged; source native pushes zeroextend legitimate guestESP.','Only7quadpre stack/pointer domains broaden; THIS/heap guards remain unchanged.','Private machine tests do not execute real D3D or host exception unwinding.'])
 return b,bytes(fixed),m,sources

