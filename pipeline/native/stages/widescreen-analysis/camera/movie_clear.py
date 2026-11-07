"""Owned-source, guest-dispatch movie Clear wrapper; never accesses runtime."""
from pathlib import Path
import sys,struct,bisect,json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'pythonlibs')]
import xbe_tools as X
from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_MODE_64
from keystone import Ks,KS_ARCH_X86,KS_MODE_64
SHA=lambda b:hashlib.sha256(b).hexdigest()
REGS=['rax','rbx','rcx','rdx','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15']
SPILL=0x180

def prepare(b,p):
 assert SHA(X.data)=='43048e59b75065e82c032859ac700c75cc2bd124f6ae817a7a2d2ca3e252aad2'
 assert SHA(b)=='cfb9d6558ff0035494af8866d72cccb0e369d2c6a1549825a699f7249154c650'
 original=(ROOT/'native-host-v1/original.xefu.dll').read_bytes();assert SHA(original)=='d49d36bd5e6beb6bcc2198dd92d1d3c9116fa0b6584b0291e0a581e28faed86d'
 pins=[(0x2040e0,'83ec385355'),(0x20414b,'8b542454f6c2f0'),(0x2041c6,'f6c201'),(0x2042e5,'7522'),(0x2042e7,'8d4c2438895c2438897c243c8954244089742444894c2450c744244c01000000'),(0x204423,'8b4c24548950148b542430894818'),(0x20447c,'c21800'),(0x72997,'e8848bfbff')]
 for va,h in pins:assert X.data[X.va_to_file(va):X.va_to_file(va)+len(bytes.fromhex(h))]==bytes.fromhex(h),(hex(va),h)
 start=p.get_offset_from_rva(0x1457190);count=(0x27c4fd8-0x1457190)//8
 def record(g,raw=b):
  key=g-0x10000;lo=0;hi=count
  while lo<hi:
   m=(lo+hi)//2;v=struct.unpack_from('<I',raw,start+8*m)[0]
   if v<key:lo=m+1
   else:hi=m
  at=start+8*lo;assert lo<count and struct.unpack_from('<I',raw,at)[0]==key
  return at+4,struct.unpack_from('<I',raw,at+4)[0]
 # Conservative all-byte absolute and relative destination census, as in the
 # independently reviewed caption compiler. No new engine or installed input.
 text=next(s for s in X.sections if s['name']=='.text');low=text['va'];high=low+text['size'];targets=set()
 for off in range(len(X.data)-3):
  v=struct.unpack_from('<I',X.data,off)[0]
  if low<=v<high:targets.add(v)
 raw=X.data[text['raw']:text['raw']+text['size']]
 for off,op in enumerate(raw):
  at=low+off;t=None
  if op in [0xe8,0xe9] and off+5<=len(raw):t=at+5+struct.unpack_from('<i',raw,off+1)[0]
  elif op==15 and off+6<=len(raw) and 0x80<=raw[off+1]<=0x8f:t=at+6+struct.unpack_from('<i',raw,off+2)[0]
  elif (op==0xeb or 0x70<=op<=0x7f or 0xe0<=op<=0xe3) and off+2<=len(raw):t=at+2+struct.unpack_from('<b',raw,off+1)[0]
  if t is not None and low<=t<high:targets.add(t)
 targets=sorted(targets);m=json.loads((ROOT/'native-host-v5/manifest.json').read_text('utf8'));used={r['guestVA']for r in m['mapChanges']};assert len(used)==611
 review=(ROOT/'work/text-padding-island-review.json').read_bytes();e=json.loads(review);assert e['source_xbe_sha256']==SHA(X.data)
 selected=None;excluded_used=0;excluded_targets=0
 for c in e['eligible_islands']:
  g=c['va'];end=g+15;assert c['bytes']==15 and c['end_exclusive']==end and c['preimage_hex']=='cc'*15
  assert X.va_to_file(g)==c['file_offset'] and X.data[c['file_offset']:c['file_offset']+15]==b'\xcc'*15
  if any(g<=k<end for k in used):excluded_used+=1;continue
  i=bisect.bisect_left(targets,g)
  if i<len(targets) and targets[i]<end:excluded_targets+=1;continue
  for k in range(g,end):assert record(k)[1]==record(k,original)[1]
  selected=c;break
 assert selected is not None
 key=selected['va'];keyFile,keyOld=record(key);clearFile,clearRva=record(0x2040e0);retFile,retRva=record(0x20447c)
 return dict(schema='owned-fullscreen-bink-clear-guest-dispatch-v1',sourceXbeSha256=SHA(X.data),sourceNativeSha256=SHA(b),
  sourcePins=[dict(guestVA=v,hex=h)for v,h in pins],returnGuestVA=key,mapFileOffset=keyFile,oldMapRva=keyOld,
  selectedReviewed15ByteInt3Island=selected,islandReviewSha256=SHA(review),excludedUsedIslandsBeforeSelected=excluded_used,excludedTargetIslandsBeforeSelected=excluded_targets,
  allByteAbsoluteAndRelativeTargets=len(targets),existingKoreanDispatchKeysExcluded=611,clearGuestVA=0x2040e0,clearRva=clearRva,clearRetGuestVA=0x20447c,clearRetRva=retRva,
  clearAbi=dict(stackArgs=['Count=0','Rects=0','Flags=0xF0(coloronly)','Color=0xFF000000','Depth=1.0(unused)','Stencil=0(unused)'],retBytes=24,usesCurrentViewport=True),
  fullscreenGate='exact MoviePlayer vtable296c08 AND byte[this+128]==1 (blocking fullscreen loop producer728f6)',
  viewportProof='blocking728c0 calls2b520 at72997; 2b520 passesconfiguredfullrectto203280',
  sourceEntryFlagsProof='72420..72438 prologue has no conditional flags consumer; first branch7243f followsBinkWait/testEAX. Wrapper nevertheless preservesallnativeRFLAGS.',
  stackSpillBytes=SPILL,syntheticCallBytes=28,hostFrameAcrossGuestExecution=False,
  limits=['Actual D3D Clear writes/command processing are source-traced, not executed in standalone machine tests.','Guest stack scratch S-0x19c..S is intentionally used and not byte-restored, as normal x86callee stack scratch.','Clear is current viewport only; exact fullscreen viewport depends on original728c0 setup.','Clear clipping and multi-buffer presentation still need actual Bink QA; no static proof of visible black output.'])

def emit(base,stubRva,serviceVA,continuationRva,raw,proof):
 ks=Ks(KS_ARCH_X86,KS_MODE_64);restoreRva=stubRva+0x200;asm=[f'lea r14d,[r14-{SPILL}]']
 for i,n in enumerate(REGS):asm += [f'mov qword ptr [r15+r14+{8*i}],{n}']
 asm+=['pushfq','pop qword ptr [r15+r14+0x78]']
 for i in range(16):asm += [f'movdqu [r15+r14+{0x80+16*i}],xmm{i}']
 asm += ['cmp ecx,0x10000',f'jb {base+restoreRva}','cmp ecx,0x7ffffed4',f'ja {base+restoreRva}',
  'cmp dword ptr [r15+rcx],0x296c08',f'jne {base+restoreRva}','cmp byte ptr [r15+rcx+0x128],1',f'jne {base+restoreRva}',
  'lea r14d,[r14-0x1c]',f'mov dword ptr [r15+r14],{proof["returnGuestVA"]}',
  'mov dword ptr [r15+r14+4],0','mov dword ptr [r15+r14+8],0','mov dword ptr [r15+r14+12],0xf0',
  'mov dword ptr [r15+r14+16],0xff000000','mov dword ptr [r15+r14+20],0x3f800000','mov dword ptr [r15+r14+24],0',
  f'jmp {base+proof["clearRva"]}']
 first=bytes(ks.asm('\n'.join(asm),addr=base+stubRva)[0]);assert len(first)<0x200
 tail=[]
 for i in range(16):tail += [f'movdqu xmm{i},[r15+r14+{0x80+16*i}]']
 tail += ['push qword ptr [r15+r14+0x78]','popfq']
 for i,n in enumerate(REGS):
  if n not in ['r14','r15']:tail += [f'mov {n},qword ptr [r15+r14+{8*i}]']
 tail += ['mov r15,qword ptr [r15+r14+112]','mov r14,qword ptr [r15+r14+104]',f'lea r14d,[r14+{SPILL}]',f'call {serviceVA}']
 tailbytes=bytes(ks.asm('\n'.join(tail),addr=base+restoreRva)[0]);at=base+restoreRva+len(tailbytes)
 jmp=bytes(ks.asm(f'jmp {base+continuationRva}',addr=at+len(raw))[0]);payload=first+b'\xcc'*(0x200-len(first))+tailbytes+raw+jmp
 assert len(payload)<0x400
 payload+=b'\xcc'*(0x400-len(payload))
 proof.update(wrapperEntryRva=stubRva,returnNativeRva=restoreRva,wrapperBytes=len(payload),replayedNativeRva=restoreRva+len(tailbytes),clearPayloadSha256=SHA(payload))
 return payload,'\n'.join(asm)+'\n; SYNTHETIC GUEST RETURN / BYPASS RESTORE\n'+'\n'.join(tail),proof
