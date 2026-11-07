"""Append-only native HUD prototype for immutable CFB caption code.

Never reads/writes a running process or installed game. A final DLL is emitted
only after source pins, alias/branch scans and integrated machine checks pass.
"""
from pathlib import Path
import sys,json,struct,hashlib,re,bisect,importlib.util,argparse
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];UI=ROOT/'widescreen-analysis/ui'
sys.path[:0]=[str(ROOT/'pythonlibs'),str(UI),str(UI/'testdeps'),str(HERE)]
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_64,CS_GRP_JUMP,CS_GRP_CALL
from capstone.x86 import X86_OP_MEM,X86_REG_RIP
import scoped_ui_kernel_v2_movie as K
import movie_clear
SHA=lambda b:hashlib.sha256(b).hexdigest()
ALIGN=lambda n,a:(n+a-1)//a*a
NAME='xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll'
SOURCE=ROOT/'native-host-v5'/NAME
EXPECTED='cfb9d6558ff0035494af8866d72cccb0e369d2c6a1549825a699f7249154c650'
MODEL_SHA='9788be4b2e092f56014e84bedf25a70bc2f5b424ad2b659b8d31d67696feeeb8'
SPECS=[('hud_enter',0x111a00,0x7f7ab4,'458d76fc43891c3e'),('hud_exit',0x111a5e,0x7f7c12,'438b3c3e458d7604'),
 ('widget_enter',0x12f99c,0x8592d4,'468b543824'),('widget_exit',0x12f99f,0x8592f4,'83ee04ffcf'),
 ('quad_pre_1',0x2cf16,0x403c4,'43c7443efc1bcf0200'),('quad_post_1',0x2cf1b,0x403d6,'418b87c8193200'),
 ('quad_pre_2',0x2d3af,0x40b46,'43c7443efcb4d30200'),('quad_post_2',0x2d3b4,0x40b58,'418b87c8193200'),
 ('quad_pre_3',0x2cd39,0x400d3,'43c7443efc3ecd0200'),('quad_post_3',0x2cd3e,0x400e5,'438b2c3e458d7604'),
 ('flat_enter_movie',0x72420,0x222270,'458d76fc43892c3e'),('flat_exit_movie',0x72756,0x2228aa,'438b3c3e458d7604'),
 ('flat_enter_menu',0xf8460,0x64cc58,'458d76fc43892c3e'),('flat_exit_menu',0xf8525,0x64ce36,'438b3c3e458d7604'),
 ('quad_pre_4',0x71f48,0x22178d,'43c7443efc4d1f0700'),('quad_post_4',0x71f4d,0x22179f,'4183c670478b043e')]

def prepare():
 b=SOURCE.read_bytes();assert SHA(b)==EXPECTED
 p=pefile.PE(data=b);base=p.OPTIONAL_HEADER.ImageBase
 assert p.FILE_HEADER.Machine==0x8664 and p.OPTIONAL_HEADER.Magic==0x20b
 assert p.FILE_HEADER.NumberOfSections==8 and p.OPTIONAL_HEADER.SectionAlignment==0x1000 and p.OPTIONAL_HEADER.FileAlignment==0x200
 assert p.sections[-1].Name.rstrip(b'\0')==b'.autocap'
 table=p.sections[0].get_file_offset();newHeader=table+40*p.FILE_HEADER.NumberOfSections
 firstRaw=min(s.PointerToRawData for s in p.sections if s.SizeOfRawData)
 assert newHeader+80<=min(firstRaw,p.OPTIONAL_HEADER.SizeOfHeaders) and b[newHeader:newHeader+80]==bytes(80)
 assert p.sections[-1].PointerToRawData+p.sections[-1].SizeOfRawData==len(b),'Unexpected source overlay'
 code_rva=ALIGN(max(s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData) for s in p.sections),0x1000)
 code_reserve=0x10000;state_rva=code_rva+code_reserve;state_reserve=ALIGN(K.STATE_BYTES,0x1000)
 assert code_rva==0x2851000 and state_rva==0x2861000 and state_reserve==0x3000
 iat=[]
 for lib in p.DIRECTORY_ENTRY_IMPORT:
  for imp in lib.imports:
   if imp.name==b'GetCurrentThreadId':iat.append((lib.dll,imp.address-base))
 assert iat==[(b'KERNEL32.dll',0x1457060)]
 model,_,_,_=K.emit(0x10000000,0x10020000,0x10030000)
 assert SHA(model)==MODEL_SHA
 kernel,entries,asm,links=K.emit(base+code_rva,base+state_rva,base+0x1457060)
 md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True
 clearProof=movie_clear.prepare(b,p)
 hooks=[];payload=bytearray(kernel)
 def rel(op,at,target):
  d=target-(at+5);assert -(1<<31)<=d<(1<<31);return bytes([op])+struct.pack('<i',d)
 for name,guest,rva,hexpin in SPECS:
  raw=bytes.fromhex(hexpin);off=p.get_offset_from_rva(rva);assert b[off:off+len(raw)]==raw
  ins=list(md.disasm(raw,base+rva));assert sum(i.size for i in ins)==len(raw) and len(raw)>=5
  assert all(not i.group(CS_GRP_CALL) and not i.group(CS_GRP_JUMP) and not any(o.type==X86_OP_MEM and o.mem.base==X86_REG_RIP for o in i.operands) for i in ins),'Stolen instruction needs explicit relocation; not admitted'
  while len(payload)%16:payload.append(0xcc)
  stub_rva=code_rva+len(payload);stub=rel(0xe8,stub_rva,entries['flat_exit' if name.startswith('flat_exit_') else name]-base)+raw
  stub+=rel(0xe9,stub_rva+len(stub),rva+len(raw))
  if name=='flat_enter_movie':
   stub,clearAsm,clearProof=movie_clear.emit(base,stub_rva,entries[name],rva+len(raw),raw,clearProof);asm['fullscreen_movie_clear_wrapper']=clearAsm
  payload.extend(stub)
  hooks.append(dict(name=name,guestVA=guest,rva=rva,fileOffset=off,before=raw.hex(),after=(rel(0xe9,rva,stub_rva)+b'\x90'*(len(raw)-5)).hex(),
    stolenBytes=len(raw),continuationRva=rva+len(raw),stubRva=stub_rva,stubBytes=stub.hex(),serviceRva=entries['flat_exit' if name.startswith('flat_exit_') else name]-base,
    instructionStarts=[i.address-base for i in ins],relocatedInstructionStarts={i.address-base:(clearProof['replayedNativeRva'] if name=='flat_enter_movie' else stub_rva+5)+i.address-(base+rva) for i in ins}))
 assert len(payload)<code_reserve
 ranges=sorted((h['rva'],h['rva']+h['stolenBytes'],h) for h in hooks)
 def interior(r):return next((h for l,e,h in ranges if l<r<e),None)
 # Raw relative-transfer scan over every existing RX section. Candidate origins
 # are subsequently proven against nearest native dispatch instruction starts;
 # embedded opcode bytes are retained as rejected candidates, never patched.
 rawCandidates=[]
 for s in p.sections:
  if not(s.Characteristics&0x20000000):continue
  data=b[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData];origin=s.VirtualAddress
  for m in re.finditer(rb'\xe8|\xe9|\x0f[\x80-\x8f]',data):
   at=m.start();n=6 if data[at]==15 else 5
   if at+n>len(data):continue
   target=origin+at+n+struct.unpack_from('<i',data,at+n-4)[0]
   if interior(target):rawCandidates.append(dict(sourceRva=origin+at,targetRva=target,length=n,dispSize=4))
  seen=set()
  for left,right,_ in ranges:
   lo=max(0,left-origin-130);hi=min(len(data)-1,right-origin+130)
   for at in range(lo,hi):
    if at in seen:continue
    seen.add(at);op=data[at]
    if not(op==0xeb or 0x70<=op<=0x7f or 0xe0<=op<=0xe3):continue
    target=origin+at+2+struct.unpack_from('<b',data,at+1)[0]
    if interior(target):rawCandidates.append(dict(sourceRva=origin+at,targetRva=target,length=2,dispSize=1))
 assert len(rawCandidates)<=128,'Unexpected relative-reference density'
 for c in rawCandidates:c['nearestMapStart']=None
 mapstart=p.get_offset_from_rva(0x1457190);mapend=p.get_offset_from_rva(0x27c4fd8);aliases=[];mapcount=0
 for index,(key,rva) in enumerate(struct.iter_unpack('<II',b[mapstart:mapend])):
  mapcount+=1;h=interior(rva)
  if h:
   assert rva in h['relocatedInstructionStarts'],'Dispatch alias into stolen native instruction body'
   aliases.append(dict(guestVA=key+0x10000,sourceRva=rva,newRva=h['relocatedInstructionStarts'][rva],fileOffset=mapstart+8*index+4,hook=h['name']))
  for c in rawCandidates:
   if rva<=c['sourceRva'] and (c['nearestMapStart'] is None or rva>c['nearestMapStart']):c['nearestMapStart']=rva
 assert sorted((x['guestVA'],x['sourceRva']) for x in aliases)==[(0x71f50,0x2217a3),(0x12f9a2,0x8592f7)]
 branches=[];rejected=[]
 for c in rawCandidates:
  start=c['nearestMapStart'];assert start is not None and 0<=c['sourceRva']-start<=4096,'Unresolved candidate origin'
  off=p.get_offset_from_rva(start);decoded=list(md.disasm(b[off:off+c['sourceRva']-start+15],base+start))
  ins=next((i for i in decoded if i.address==base+c['sourceRva']),None)
  if ins is None:
   assert any(i.address<base+c['sourceRva']<i.address+i.size for i in decoded),'Unresolved raw candidate'
   rejected.append(dict(**c,reason='Opcode byte embedded in decoded instruction'));continue
  assert ins.size==c['length'] and ins.group(CS_GRP_JUMP) or (ins.size==c['length'] and ins.group(CS_GRP_CALL))
  h=interior(c['targetRva']);assert c['targetRva'] in h['relocatedInstructionStarts']
  assert c['dispSize']==4,'Short relative branch into detour interior requires separate nearby bridge'
  target=h['relocatedInstructionStarts'][c['targetRva']];newdisp=target-(c['sourceRva']+ins.size)
  assert -(1<<31)<=newdisp<(1<<31)
  branches.append(dict(**c,newTargetRva=target,fileOffset=p.get_offset_from_rva(c['sourceRva'])+ins.imm_offset,before=bytes(ins.bytes[ins.imm_offset:ins.imm_offset+4]).hex(),after=struct.pack('<i',newdisp).hex()))
 manifest=json.loads((ROOT/'native-host-v5/manifest.json').read_text('utf8'));assert len(manifest['mapChanges'])==611
 aliasOffsets={a['fileOffset'] for a in aliases}
 for m in manifest['mapChanges']:
  assert m['fileOffset'] not in aliasOffsets
  assert struct.unpack_from('<I',b,m['fileOffset'])[0]==m['afterRVA']
 report=dict(schema='crimson-full-cfb-scoped-hud-menu-movie-integration-v2',source=str(SOURCE.relative_to(ROOT)),sourceSha256=EXPECTED,
  sourceBytes=len(b),kernelModelSha256=MODEL_SHA,cachedProofInput=False,kernelSourceSha256=SHA((UI/'scoped_ui_kernel_v2_movie.py').read_bytes()),
  codeRva=code_rva,codeReserve=code_reserve,stateRva=state_rva,stateReserve=state_reserve,stateUsed=K.STATE_BYTES,
  imageBase=base,movieClear=clearProof,headerRoom=dict(newSectionTableOffset=newHeader,firstRaw=firstRaw,newHeadersEnd=newHeader+80),
  kernelActualSha256=SHA(kernel),kernelBytes=len(kernel),codePayloadBytes=len(payload),kernelLinks=links,
  hooks=hooks,dispatchTableEntriesScanned=mapcount,dispatchInteriorAliases=aliases,directNativeInteriorBranches=branches,rejectedEmbeddedOpcodeCandidates=rejected,
  cameraPatch=dict(fileOffset=0x40416,rva=0x41016,before='80',after='40'),
  originalKoreanMapChangesRetained=611,installedFilesModified=False,runtimeMemoryAccessed=False,
  scope='SP HUD/radio plus typed MoviePlayer/MenuMgr scopes and fourth Bink submit geometry prototype; camera X.75 needs separate correct16:9presentation. Fullscreen Bink inserts original color-only Clear through a synthetic guest return; visible output still unvalidated.',
  limits=['Inserted fullscreen-only Clear uses original current viewport; actual visible black outer bands require Bink runtime QA.',
   'MenuMgr scope encloses child virtual draws; the three generic text/sprite submission routes are covered, but no exhaustive dynamic child-class call census has run.',
   'New nonleaf native helpers have no addedWindowsUNWIND_INFO. Host exceptions/unwindthroughhelper is not validated; never claim productionunwindsafety.',
   'Threadscope/quadstate normalreturn machinechecked; exceptions/longjmp/source cancellation may bypass pairedposthooks.',
   'Fixed cameraX.75 is singleplayer scope; multiplayer/splitscreen and compositeaimwidgets require separate validation.',
   'GetCurrentThreadId is mocked in isolatedmachinechecks; realD3D/runtimescope behavior still needs actual HUD/radio QA.'])
 return b,p,payload,report,asm

def build():
 b,p,payload,r,asm=prepare();patched=bytearray(b);allowed=[]
 def change(offset,old,new,purpose):
  assert len(old)==len(new) and b[offset:offset+len(old)]==old
  patched[offset:offset+len(old)]=new;allowed.append((offset,offset+len(old),purpose))
 c=r['movieClear'];change(c['mapFileOffset'],struct.pack('<I',c['oldMapRva']),struct.pack('<I',c['returnNativeRva']),'reviewedunusedInt3syntheticClearReturn')
 for h in r['hooks']:change(h['fileOffset'],bytes.fromhex(h['before']),bytes.fromhex(h['after']),'detour:'+h['name'])
 for a in r['dispatchInteriorAliases']:change(a['fileOffset'],struct.pack('<I',a['sourceRva']),struct.pack('<I',a['newRva']),'dispatchinterioralias')
 for c in r['directNativeInteriorBranches']:change(c['fileOffset'],bytes.fromhex(c['before']),bytes.fromhex(c['after']),'directrelativebranchfixup')
 change(0x40416,b'\x80',b'\x40','reviewedcameraX.75')
 raw=ALIGN(len(b),p.OPTIONAL_HEADER.FileAlignment);assert raw==len(b)
 codeRaw=r['codeReserve'];stateRaw=raw+codeRaw
 patched+=bytes(payload)+b'\xcc'*(codeRaw-len(payload))+bytes(r['stateReserve'])
 def header(name,vsize,va,rawsize,at,flags):return struct.pack('<8s6I2HI',name,vsize,va,rawsize,at,0,0,0,0,flags)
 n=r['headerRoom']['newSectionTableOffset']
 change(n,b[n:n+80],header(b'.wideui',len(payload),r['codeRva'],codeRaw,raw,0x60000020)+header(b'.widesta',r['stateUsed'],r['stateRva'],r['stateReserve'],stateRaw,0xc0000040),'appendRXandRWsectionheaders')
 for owner,field,value,fmt in [(p.FILE_HEADER,'NumberOfSections',10,'<H'),(p.OPTIONAL_HEADER,'SizeOfImage',r['stateRva']+r['stateReserve'],'<I'),
   (p.OPTIONAL_HEADER,'SizeOfCode',p.OPTIONAL_HEADER.SizeOfCode+codeRaw,'<I'),
   (p.OPTIONAL_HEADER,'SizeOfInitializedData',p.OPTIONAL_HEADER.SizeOfInitializedData+r['stateReserve'],'<I')]:
  at=owner.get_field_absolute_offset(field);old=b[at:at+struct.calcsize(fmt)];change(at,old,struct.pack(fmt,value),'header:'+field)
 # Checksum itself is another explicitly admitted header field.
 q=pefile.PE(data=patched);at=p.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum')
 change(at,b[at:at+4],struct.pack('<I',q.generate_checksum()),'header:CheckSum')
 q=pefile.PE(data=patched);assert q.FILE_HEADER.NumberOfSections==10
 assert q.sections[-2].Characteristics==0x60000020 and q.sections[-1].Characteristics==0xc0000040
 assert patched[stateRaw:stateRaw+r['stateReserve']]==bytes(r['stateReserve'])
 # Every pre-existing byte change is explicitly enumerated. Existing section
 # content does not move; original KO code/data sections are byte-exact.
 mask=bytearray(len(b))
 for lo,hi,purpose in allowed:mask[lo:hi]=b'\1'*(hi-lo)
 assert all(x==y or mask[i] for i,(x,y) in enumerate(zip(b,patched)))
 korean=[]
 for s in p.sections:
  if s.Name.rstrip(b'\0') in [b'.kradio',b'.autocap']:
   old=b[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData];new=patched[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
   assert old==new;korean.append(dict(section=s.Name.rstrip(b'\0').decode(),bytes=len(old),sha256=SHA(old),byteIdentical=True))
 r['koreanSections']=korean;r['allowedExistingByteRanges']=[dict(start=a,end=z,purpose=s) for a,z,s in allowed]
 checks={'status':'SOURCE-BUILD', 'note':'Independent release QA is separate from code generation'}
 r['integratedMachineChecks']=checks;r['status']='SOURCE BUILD; independent machine/runtime QA is separate';r['patchedSha256']=SHA(patched);r['patchedBytes']=len(patched)
 out=HERE/'camera-wide-addon-v2';out.mkdir(exist_ok=False)
 (out/NAME).write_bytes(patched);(out/'manifest.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n','utf8')
 (out/'native-services.asm').write_text('\n\n'.join('; '+n+'\n'+x for n,x in asm.items())+'\n','utf8')
 print(json.dumps(dict(folder=str(out.relative_to(ROOT)),sha256=r['patchedSha256'],bytes=len(patched),hooks=len(r['hooks']),interiorAliases=len(r['dispatchInteriorAliases']),relativeFixups=len(r['directNativeInteriorBranches']),machineChecks=checks),indent=2))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--build',action='store_true');args=parser.parse_args()
 if args.build:build()
 else:
  _,_,_,r,_=prepare();(HERE/'integration-preflight-v2.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n','utf8')
  print(json.dumps({k:r[k] for k in ['sourceSha256','codeRva','stateRva','dispatchTableEntriesScanned','dispatchInteriorAliases','directNativeInteriorBranches','rejectedEmbeddedOpcodeCandidates']},indent=2))
