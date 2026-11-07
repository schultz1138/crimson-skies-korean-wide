"""Offline E4 extension for three source-owned clipped/textured quad submits."""
from pathlib import Path
import sys, struct, hashlib, json, re, subprocess, importlib.util
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]; V1=HERE.parent/'overscan-candidate-v1'
sys.path[:0]=[str(ROOT/'pythonlibs'),str(ROOT/'widescreen-analysis/ui'),str(ROOT/'widescreen-analysis/ui/testdeps'),str(V1)]
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from keystone import Ks,KS_ARCH_X86,KS_MODE_64
import uniform_kernel as K
NAME='xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll'
SOURCE=V1/NAME
SHA=lambda b:hashlib.sha256(b).hexdigest()
PINS=[dict(name='quad_pre_5',guestVA=0x2eaea,rva=0x42fc6,continuationRva=0x42fcf,pin='43c7443efcefea0200'),
      dict(name='quad_post_5',guestVA=0x2eaef,rva=0x42fd8,continuationRva=0x42fdf,pin='418b87c8193200'),
      dict(name='quad_pre_6',guestVA=0x2e2cb,rva=0x42293,continuationRva=0x4229c,pin='43c7443efcd0e20200'),
      dict(name='quad_post_6',guestVA=0x2e2d0,rva=0x422a5,continuationRva=0x422ac,pin='418b87c8193200'),
      dict(name='quad_pre_7',guestVA=0x7b873,rva=0x233e4e,continuationRva=0x233e57,pin='43c7443efc78b80700'),
      dict(name='quad_post_7',guestVA=0x7b878,rva=0x233e60,continuationRva=0x233e68,pin='438b3c3e458d7604')]
SITES=[dict(site=5,delta=0x6c,direct=True,stride=28,primitive=7,count=4),
       dict(site=6,delta=0x84,direct=True,stride=28,primitive=7,count=4),
       dict(site=7,delta=0x7c,direct=False,stride=36,primitive=7,count=4)]

def geometry_stride(body,stride):
 if stride==28:return body
 assert stride==36
 def replace(match):
  offset=int(match.group(1));q,r=divmod(offset,28);assert q<4 and r in (0,4)
  return '[rsi+'+str(q*stride+r)+']'
 return [re.sub(r'\[rsi\+(\d+)\]',replace,s).replace('cmp rdx,0x7fffff80','cmp rdx,0x7fffff60')for s in body]

def prepare():
 b=SOURCE.read_bytes();assert SHA(b)=='e4d39a2d29f39ff0ccc15a5744590f0902d371dfc05ea268f0e883c5b6bf7ab9'
 p=pefile.PE(data=b); base=p.OPTIONAL_HEADER.ImageBase; inherited=json.loads((V1/'manifest.json').read_text('utf8'))
 md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True; ks=Ks(KS_ARCH_X86,KS_MODE_64)
 code_start=0x2856000; rx=next(s for s in p.sections if s.VirtualAddress<=code_start<s.VirtualAddress+s.Misc_VirtualSize)
 assert rx.VirtualAddress==0x2851000 and rx.Misc_VirtualSize==rx.SizeOfRawData==0x10000
 off=p.get_offset_from_rva(code_start);limit=rx.VirtualAddress+rx.SizeOfRawData
 assert b[off:p.get_offset_from_rva(limit-1)+1]==b'\xcc'*(limit-code_start)
 payload=bytearray(); entries={}; asm_by_name={};links=[];patches=[]
 def pad():
  while len(payload)%16:payload.append(0xcc)
 specs=[]
 for site in SITES:
  n=site['site'];stride=site['stride']
  specs.extend([('quad_pre_'+str(n),geometry_stride(K.pre(n,site['delta'],site['direct'],base+inherited['codeRva']),stride)),('quad_post_'+str(n),geometry_stride(K.post(n),stride))])
 for name,body in specs:
  pad();address=base+code_start+len(payload);entries[name]=address
  pro=[s.replace('add r10,0x400','add r10,0x500')for s in K.OLD.V1.prologue()]
  asm='\n'.join(pro+body+K.OLD.V1.epilogue());data=bytearray(ks.asm(asm,addr=address)[0]);asm_by_name[name]=asm
  ins=list(md.disasm(data,address));assert sum(i.size for i in ins)==len(data)
  for i in ins:
   target=base+0x1457060 if i.mnemonic=='call'and i.op_str=='qword ptr [rip]'else base+inherited['stateRva'] if i.mnemonic=='lea'and i.op_str=='r10, [rip]'else base+inherited['profileTableRva'] if i.mnemonic=='lea'and i.op_str=='rdx, [rip]'else None
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
 assert not branches,branches
 fixed=bytearray(b);allowed=[]
 def change(at,raw,purpose):
  fixed[at:at+len(raw)]=raw;allowed.append(dict(start=at,end=at+len(raw),purpose=purpose))
 for h in patches:change(h['fileOffset'],bytes.fromhex(h['after']),h['name'])
 change(off,payload,'six new services and whole-instruction wrappers in existing RX reservation')
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
 metadata=dict(schema='native-overscan-preset-v2-clipped-and-textured-quads',source=str(SOURCE),sourceSha256=SHA(b),patchedSha256=SHA(fixed),bytes=len(b),imageBase=base,codeRva=code_start,codeBytes=len(payload),hooks=patches,sites=SITES,serviceEntries={k:v-base for k,v in entries.items()},kernelLinks=links,
  inheritedManifestSha256=SHA((V1/'manifest.json').read_bytes()),inherited= inherited,allowedExistingByteRanges=allowed,dispatchEntriesScanned=len(mapdata)//8,dispatchTableByteExact=True,interiorAliases=aliases,entryAliases=entry_aliases,directBranchInteriorCandidates=branches,
  stateRva=inherited['stateRva'],stateReserve=inherited['stateReserve'],newSectionsAdded=False,fileSizeUnchanged=True,imageSizeUnchanged=True,exceptionDirectoryByteExact=True,exceptionDirectorySha256=SHA(exception),
  sourceChain=['site5: clipped branch 0x2f930 -> 0x2fc46 calls 0x2e780;tail0x2eadf push0x1c;0x2eae1 leaecx[esp+0x60];threepushes;0x2eaea call0x1ffa10','site6: 0x302b0 ->0x2df30;0x2e2cb call0x1ffa10;push0x1c,lea[esp+0x78],threepushes givepreESP+0x84','site7: 0x7bf10 ->0x7b440;0x7b873 call0x2b830;push4,lea[esp+0x78],pushptr givepreESP+0x7c;wrapper0x2b84d submitsprimitive7,stride36'],
  previousServicesDecoderProfilesAndRawStateByteExact=True,allKoreanDispatchEntriesByteExact=True,installedWrite=False,runtimeAccess=False,
  limits=['Private emulator tests do not execute the real D3D submit.','New helpers retain the existing E4 dynamic-alignment service ABI; normal return is tested, host exception unwind through these helpers is not claimed.','Only three source-pinned paths are added; further unhooked 2D paths remain a separate review.','Site7 wrapper has no stride argument at the outer call;stride36 is source-proved in unchanged inner wrapper0x2b830.'])
 return b,bytes(fixed),metadata,asm_by_name

