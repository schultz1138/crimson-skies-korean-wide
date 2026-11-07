"""Build native caption v2 with reviewed radio-only two-line formatting.

The original guest XBE and game data stay unchanged. Lift the previously audited
small x86 caption routines into the port's native x64 register convention and
extend its existing precompiled guest-address map. Never writes installation.
"""
from pathlib import Path
import sys,struct,json,hashlib,bisect,re
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pythonlibs'))
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_MODE_64,CS_GRP_JUMP,CS_GRP_CALL
from capstone.x86 import X86_OP_IMM,X86_OP_REG,X86_OP_MEM
from keystone import Ks,KS_ARCH_X86,KS_MODE_32,KS_MODE_64

SOURCE=ROOT/'native-host-v1/xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll'
EXPECTED='d49d36bd5e6beb6bcc2198dd92d1d3c9116fa0b6584b0291e0a581e28faed86d'
original=(ROOT/'native-host-v1/original.xefu.dll').read_bytes()
if hashlib.sha256(original).hexdigest()!=EXPECTED:raise ValueError('Unexpected host DLL preimage')
pe=pefile.PE(data=original)
base=pe.OPTIONAL_HEADER.ImageBase
u32=lambda b,o:struct.unpack_from('<I',b,o)[0]
MAP_BEGIN=0x1457190;MAP_END=0x27c4fd8;MAP_COUNT=(MAP_END-MAP_BEGIN)//8
MAP_FILE=pe.get_offset_from_rva(MAP_BEGIN)
def map_record(va):
 key=va-0x10000;lo=0;hi=MAP_COUNT
 while lo<hi:
  mid=(lo+hi)//2;value=u32(original,MAP_FILE+mid*8)
  if value<key:lo=mid+1
  else:hi=mid
 off=MAP_FILE+lo*8
 if lo==MAP_COUNT or u32(original,off)!=key:raise ValueError('Unmapped guest VA '+hex(va))
 return off,u32(original,off+4)

native=json.loads((ROOT/'runtime-radio/native-renderer.json').read_text('utf8'))
patches=json.loads((ROOT/'runtime-radio/runtime-patches.json').read_text('utf8'))
if patches['originalXbeSha256']!='43048e59b75065e82c032859ac700c75cc2bd124f6ae817a7a2d2ca3e252aad2':raise ValueError('Wrong guest source')
C=Cs(CS_ARCH_X86,CS_MODE_32);C.detail=True
D=Cs(CS_ARCH_X86,CS_MODE_64)
K=Ks(KS_ARCH_X86,KS_MODE_64)
insns={}
for p in patches['patches']:
 if 'code padding' not in p['purpose']:continue
 b=bytes.fromhex(p['after']);decoded=list(C.disasm(b,p['guestVA']))
 if sum(i.size for i in decoded)!=len(b):raise ValueError('Incomplete guest patch decoding')
 for i in decoded:
  if i.address in insns:raise ValueError('Overlapping guest patch instructions')
  insns[i.address]=i

# Add the new cdecl radio paragraph wrapper in independently reviewed unused
# guest instruction slots. These addresses are dispatch keys only: the original
# guest code/data on disk and in memory are not overwritten.
wrapper_source=(ROOT/'work/radio-wrap-wrapper.asm').read_text('utf8')
logical=0x500000
K32=Ks(KS_ARCH_X86,KS_MODE_32)
wrapper_code=bytes(K32.asm(wrapper_source,addr=logical)[0])
wrapper_decoded=list(C.disasm(wrapper_code,logical))
if sum(i.size for i in wrapper_decoded)!=len(wrapper_code):raise ValueError('Incomplete wrapper decode')
used_caves={int(r['va'],16) for r in native['relocations']}
eligible=json.loads((ROOT/'work/text-padding-island-review.json').read_text('utf8'))
if eligible['source_xbe_sha256']!=patches['originalXbeSha256']:raise ValueError('Cave evidence mismatch')
spare=[c['va'] for c in eligible['eligible_islands'] if c['va'] not in used_caves]
if len(spare)<len(wrapper_decoded):raise ValueError('Insufficient reviewed guest dispatch slots')
wrapper_relocations={i.address:spare[n] for n,i in enumerate(wrapper_decoded)}
for index,i in enumerate(wrapper_decoded):
 va=wrapper_relocations[i.address];args=i.op_str
 if i.group(CS_GRP_JUMP) or i.group(CS_GRP_CALL):
  if i.operands[0].type!=X86_OP_IMM:raise ValueError('Indirect wrapper branch')
  dest=i.operands[0].imm
  if logical<=dest<logical+len(wrapper_code):dest=wrapper_relocations[dest]
  args=hex(dest)
 code=bytes(K32.asm(i.mnemonic+' '+args,addr=va)[0])
 if i.mnemonic not in ('jmp','ret'):
  if index+1==len(wrapper_decoded):raise ValueError('Unterminated wrapper')
  dest=wrapper_relocations[wrapper_decoded[index+1].address]
  code+=b'\xe9'+struct.pack('<i',dest-(va+len(code))-5)
 if len(code)>15:raise ValueError('Wrapper guest slot overflow')
 for j in C.disasm(code,va):
  if j.address in insns:raise ValueError('Duplicate wrapper guest key')
  insns[j.address]=j
wrapper_guest=wrapper_relocations[logical]

proposals=json.loads((ROOT/'translations/tutorial.linebreak-proposals.json').read_text('utf8'))
# Every emitted source string is checked below. The development dictionary's
# unrelated audio transcripts/review metadata are not a build input.
format_records=[];format_table=b'';seen=set()
for e in proposals['entries']:
 index=e['break_index_utf16']
 if index is None:continue
 text=e['source_text'];wide=text.encode('utf-16le')
 if hashlib.sha256(wide).hexdigest()!=e['source_utf16le_sha256']:raise ValueError('Caption identity mismatch')
 if wide[2*index:2*index+2]!=b' \0' or len(wide)>510:raise ValueError('Unsafe break or caption length')
 if wide in seen:continue
 seen.add(wide);wide+=b'\0\0'
 format_records.append({'key':e['key'],'source':text,'utf16Units':len(wide)//2-1,'breakIndex':index,'lines':e['lines']})
 format_table+=struct.pack('<II',len(wide),index*2)+wide
format_table+=b'\0'*8
if len(format_records)!=12:raise ValueError('Unexpected forced-break count')

align=lambda x,a:(x+a-1)//a*a
section_alignment=pe.OPTIONAL_HEADER.SectionAlignment
file_alignment=pe.OPTIONAL_HEADER.FileAlignment
last=pe.sections[-1]
new_rva=align(last.VirtualAddress+max(last.Misc_VirtualSize,last.SizeOfRawData),section_alignment)
new_raw=align(len(original),file_alignment)
SLOT=192
labels={va:new_rva+n*SLOT for n,va in enumerate(sorted(insns))}
draw_guest=int(native['entries']['draw'],16)
host_specs=[dict(h) for h in native['hooks'] if int(h['va'],16)!=0x29f998]
# The original guest vtable resides on a read-only host mapping. Redirect just
# the HUD's Dialogue render call instead; preserve every other no-op renderer.
host_specs.append({'va':'0x111a3d','before':'ff5224','directTarget':draw_guest,'purpose':'Dialogue-only HUD render call; no guest vtable mutation'})
host_specs.append({'va':'0xffe17','before':None,'directTarget':wrapper_guest,'purpose':'Radio-only explicit paragraph breaks with balanced font references'})
hookslots={int(h['va'],16):new_rva+(len(labels)+n)*SLOT for n,h in enumerate(host_specs)}
dispatch_ptr_rva=0x27f16d0

def target(va):
 return base+(labels[va] if va in labels else map_record(va)[1])
def mem(op):
 m=op.mem
 if m.segment:raise ValueError('Unsupported segmented memory')
 if m.index:raise ValueError('Unexpected indexed guest operand; requires address scratch')
 b=C.reg_name(m.base)
 regs={'eax':'rax','ecx':'rcx','edx':'rdx','ebx':'rbx','esp':'r14','ebp':'rbp','esi':'rsi','edi':'rdi'}
 address='r15'+(' + '+regs[b] if b else '')
 if m.disp:address+=(' + '+hex(m.disp)) if m.disp>=0 else (' - '+hex(-m.disp))
 return {1:'byte',2:'word',4:'dword'}[op.size]+' ptr ['+address+']'
def operand(op):
 if op.type==X86_OP_REG:
  name=C.reg_name(op.reg);return 'r14d' if name=='esp' else name
 if op.type==X86_OP_IMM:return hex(op.imm & 0xffffffff)
 if op.type==X86_OP_MEM:return mem(op)
 raise ValueError('Unsupported operand')
def gpush(value):return ['lea r14d, [r14 - 4]','mov dword ptr [r14 + r15], '+value]
def gret(imm=0):return ['mov r8d, dword ptr [r14 + r15]',f'lea r14d, [r14 + {4+imm}]',f'mov r9, qword ptr [rip + DISPATCH]','jmp qword ptr [r9 + r8*8]']

def lift(i):
 nextva=i.address+i.size;m=i.mnemonic
 # These helper routines contain no variable-index memory operands. Guest
 # registers are zero-extended 32-bit host registers; R14 is guest ESP, R15 base.
 if m=='push':
  op=i.operands[0]
  if op.type==X86_OP_REG and C.reg_name(op.reg)=='esp':return ['mov r8d, r14d']+gpush('r8d')
  if op.type==X86_OP_MEM:return ['mov r8d, '+mem(op)]+gpush('r8d')
  return gpush(operand(op))
 if m=='pop':return ['mov '+operand(i.operands[0])+', dword ptr [r14 + r15]','lea r14d, [r14 + 4]']
 if m=='pushal':
  return ['lea r14d, [r14 - 32]']+[f'mov dword ptr [r14 + r15 + {off}], {reg}' for off,reg in [(28,'eax'),(24,'ecx'),(20,'edx'),(16,'ebx'),(8,'ebp'),(4,'esi'),(0,'edi')]]+['lea r8d, [r14 + 32]','mov dword ptr [r14 + r15 + 12], r8d']
 if m=='popal':return [f'mov {reg}, dword ptr [r14 + r15 + {off}]' for off,reg in [(0,'edi'),(4,'esi'),(8,'ebp'),(16,'ebx'),(20,'edx'),(24,'ecx'),(28,'eax')]]+['lea r14d, [r14 + 32]']
 if m=='ret':return gret(i.operands[0].imm if i.operands else 0)
 if i.group(CS_GRP_CALL):
  if i.operands[0].type!=X86_OP_IMM:raise ValueError('Unexpected indirect payload call')
  return gpush(hex(nextva))+[f'jmp {target(i.operands[0].imm):#x}']
 if i.group(CS_GRP_JUMP):
  if i.operands[0].type!=X86_OP_IMM:raise ValueError('Unexpected indirect payload jump')
  return [f'{m} {target(i.operands[0].imm):#x}']
 if m=='lea':
  op=i.operands[1];b=C.reg_name(op.mem.base);reg={'eax':'rax','ecx':'rcx','edx':'rdx','ebx':'rbx','esp':'r14','ebp':'rbp','esi':'rsi','edi':'rdi'}[b]
  if op.mem.index:raise ValueError('Indexed LEA not handled')
  disp=op.mem.disp;addr=reg+(' + '+hex(disp) if disp>=0 else ' - '+hex(-disp))
  return ['lea '+operand(i.operands[0])+', ['+addr+']']
 if m not in ('mov','cmp','test','neg','sbb','inc','add','sub','xor','or','nop'):raise ValueError('Unsupported guest opcode '+m)
 return [m+' '+', '.join(operand(o) for o in i.operands)]

def assemble(lines,rva):
 # Keystone has no external symbol resolver here. Resolve RIP displacement
 # through the next-instruction address (the mov r9,[rip+disp32] is 7 bytes).
 out=b''
 for line in lines:
  addr=base+rva+len(out)
  if 'DISPATCH' in line:line=line.replace('DISPATCH',str(base+dispatch_ptr_rva-(addr+7)))
  code=bytes(K.asm(line,addr=addr)[0]);out+=code
 return out

slot_bytes=(len(labels)+len(host_specs))*SLOT
format_table_rva=new_rva+slot_bytes
def formatter(rva):
 # Four translator scratch registers only; no guest registers or stack change.
 # The UserMsg localization caller provides a 256-WCHAR writable stack buffer.
 prefix=['mov r8d, dword ptr [r14 + r15]','lea r8, [r8 + r15]']
 first=assemble(prefix,rva)
 delta=format_table_rva-(rva+len(first)+7)
 asm=f'''
 lea r9, [rip + {delta}]
next_record:
 mov r10d, dword ptr [r9]
 test r10d, r10d
 jz done
compare_word:
 mov r11w, word ptr [r8 + r10 - 2]
 cmp r11w, word ptr [r9 + r10 + 6]
 jne mismatch
 sub r10d, 2
 jnz compare_word
 mov r10d, dword ptr [r9 + 4]
 mov word ptr [r8 + r10], 10
 jmp done
mismatch:
 mov r10d, dword ptr [r9]
 lea r9, [r9 + r10 + 8]
 jmp next_record
done:
 '''
 return first+bytes(K.asm(asm,addr=base+rva+len(first))[0])

payload=bytearray(b'\xcc'*slot_bytes+format_table)
generated=[]
formatter_rva=None
for va,i in sorted(insns.items()):
 lines=lift(i)
 if i.mnemonic not in ('jmp','ret'):
  nextva=va+i.size
  if nextva not in insns:raise ValueError('Missing payload fallthrough '+hex(nextva))
  lines.append(f'jmp {target(nextva):#x}')
 intro=b''
 if i.group(CS_GRP_CALL) and i.operands[0].type==X86_OP_IMM and i.operands[0].imm==0xffc50:
  if formatter_rva is not None:raise ValueError('Multiple radio setters')
  formatter_rva=labels[va];intro=formatter(labels[va])
 code=intro+assemble(lines,labels[va]+len(intro))
 if len(code)>SLOT:raise ValueError('Lift exceeds its slot')
 at=labels[va]-new_rva;payload[at:at+len(code)]=code
 decoded=list(D.disasm(code,base+labels[va]))
 if sum(x.size for x in decoded)!=len(code):raise ValueError('Incomplete host code')
 generated.append({'guestVA':va,'source':i.mnemonic+' '+i.op_str,'hostRVA':labels[va],'assembly':lines,'hex':code.hex()})

patched=bytearray(original)
mapchanges=[]
for va,rva in labels.items():
 off,before=map_record(va);struct.pack_into('<I',patched,off+4,rva)
 mapchanges.append({'guestVA':va,'fileOffset':off+4,'beforeRVA':before,'afterRVA':rva})
hosthooks=[]
for h in host_specs:
 va=int(h['va'],16)
 before=bytes.fromhex(h['before']) if h['before'] is not None else b'\xe8'+struct.pack('<i',0x12f280-(va+5))
 if 'directTarget' in h:
  lines=gpush(hex(va+len(before)))+[f'jmp {target(h["directTarget"]):#x}']
 else:
  after=bytes.fromhex(h['after']);first=list(C.disasm(after,va))[0];lines=lift(first)
 start_rva=map_record(va)[1];end_rva=map_record(va+len(before))[1]
 span=end_rva-start_rva
 if span<5 or span>128:raise ValueError('Noncontiguous/short host hook '+hex(va))
 code=assemble(lines,hookslots[va]);at=hookslots[va]-new_rva;payload[at:at+len(code)]=code
 off=pe.get_offset_from_rva(start_rva)
 old=original[off:off+span]
 decoded=list(D.disasm(old,base+start_rva))
 if sum(x.size for x in decoded)!=span:raise ValueError('Hook boundary splits host instruction')
 new=b'\xe9'+struct.pack('<i',hookslots[va]-(start_rva+5))+b'\x90'*(span-5)
 patched[off:off+span]=new
 hosthooks.append({'guestVA':va,'hostRVA':start_rva,'fileOffset':off,'before':old.hex(),'after':new.hex(),'payloadRVA':hookslots[va],'payloadAssembly':lines,'payloadHex':code.hex(),'purpose':h['purpose']})

# Append a normal executable PE section. No new imports or absolute host
# pointers: all host control transfers and pointer-table reads are relative.
section_header=pe.sections[-1].get_file_offset()+40
if section_header+40>pe.OPTIONAL_HEADER.SizeOfHeaders:raise ValueError('No PE header room')
if any(patched[section_header:section_header+40]):raise ValueError('Section header slot not empty')
rawsize=align(len(payload),file_alignment)
patched.extend(b'\0'*(new_raw-len(patched)));patched.extend(payload);patched.extend(b'\0'*(rawsize-len(payload)))
patched[section_header:section_header+40]=struct.pack('<8s6I2HI',b'.kradio\0',len(payload),new_rva,rawsize,new_raw,0,0,0,0,0x60000020)
struct.pack_into('<H',patched,pe.FILE_HEADER.get_field_absolute_offset('NumberOfSections'),len(pe.sections)+1)
struct.pack_into('<I',patched,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'),align(new_rva+len(payload),section_alignment))
struct.pack_into('<I',patched,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfCode'),pe.OPTIONAL_HEADER.SizeOfCode+rawsize)
struct.pack_into('<I',patched,pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),0)
q=pefile.PE(data=bytes(patched));struct.pack_into('<I',patched,pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),q.generate_checksum())
out=ROOT/'native-host-v2';out.mkdir(exist_ok=True)
output=out/SOURCE.name
output.write_bytes(patched)
report={'format':1,'status':'Offline candidate; not applied or runtime verified','source':str(SOURCE),'sourceSha256':EXPECTED,'patchedSha256':hashlib.sha256(patched).hexdigest(),'originalBytes':len(original),'patchedBytes':len(patched),'originalGuestXbeUnchanged':True,'assetsUnchanged':True,'prefix':'KR_SH_TUT_','section':{'rva':new_rva,'raw':new_raw,'virtualBytes':len(payload),'rawBytes':rawsize},'mapChanges':mapchanges,'hooks':hosthooks,'generated':generated,'dispatchPointerRVA':dispatch_ptr_rva,'guestVtableWrite':False,'limitations':['Candidate host DLL load acceptance and actual lower-caption rendering are not established.','This targets exactly one precompiled host build.','A separate radio object is created/released through existing native functions; original tutorial instructions and objective paths stay original.','Five-second caption duration is inherited from the validated tutorial expansion.']}
(out/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf8')
report['layout']={'policy':'Twelve long source captions split at reviewed existing spaces;30shortaudioentries retainone line','records':format_records,'formatterRVA':formatter_rva,'formatterTableRVA':format_table_rva,'formatterTableBytes':len(format_table),'wrapperGuestVA':wrapper_guest,'wrapperHostRVA':labels[wrapper_guest],'originalWrapGuestVA':0x12f280,'originalWrapHostRVA':map_record(0x12f280)[1],'newGlobalLineFeedHandling':False,'fontReferenceContract':'One extra reference before two original wrap calls; each consumes one, preserving original ownership.'}
(out/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:report[k] for k in ('status','sourceSha256','patchedSha256','originalBytes','patchedBytes','section','limitations')},indent=2))
print('liftedInstructions',len(generated),'mapRecordsChanged',len(mapchanges),'hostHooks',len(hosthooks))
