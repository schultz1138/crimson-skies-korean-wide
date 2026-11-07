"""Offline ID11-only AA override at scaling initialization; no runtime access."""
from final_call_proxy_v3 import *
AA_RVA=0x763800;AA_UW_RVA=0x741500;AA_DIAG_RVA=0x767120
AA_FRAME=0x90
def emit_aa(entry=IMAGE_BASE+AA_RVA,decoder=IMAGE_BASE+0x740000,diag=IMAGE_BASE+AA_DIAG_RVA):
 a=[];fixups={}
 def add(*s):a.extend(s)
 def pointer(reg,label):
  add(f'cmp {reg},0x10000',f'jb {label}',f'test {reg},7',f'jnz {label}',f'mov rax,{reg}','shr rax,47',f'jnz {label}')
 # LEA stack allocation leaves entry RFLAGS intact until they are saved. RBP
 # provides stable unwind state even during the balanced PUSHFQ/POPFQ pairs.
 add('push rbp',f'lea rsp,[rsp-{AA_FRAME}]',f'lea rbp,[rsp+{AA_FRAME}]')
 for off,reg in [(0x20,'rax'),(0x28,'rcx'),(0x30,'rdx'),(0x38,'r8'),(0x40,'r9'),(0x48,'r10'),(0x50,'r11')]:add(f'mov [rsp+{off}],{reg}')
 add('mov [rbx+0x68],eax','mov [rbx+0x60],eax','pushfq','pop rax','mov [rsp+0x58],rax',f'call {decoder}')
 marker=0x13590000;fixups[marker]=diag;add(f'lea r10,[rip+{marker}]')
 add('lock inc qword ptr [r10+8]','mov [r10+0x10],eax','mov dword ptr [r10+0x14],0',
     'mov qword ptr [r10+0x18],0','mov qword ptr [r10+0x20],0','mov qword ptr [r10+0x28],0','mov [r10+0x30],rbx',
     'mov rcx,[rsp+0x20]','mov [r10+0x38],ecx','cmp eax,11','ja invalid_id')
 pointer('rbx','invalid_config')
 add('mov r11,[rbx+0x38]');pointer('r11','invalid_options')
 add('mov rdx,[r11+8]','mov rcx,[r11+0x10]');pointer('rdx','invalid_bounds');pointer('rcx','invalid_bounds')
 add('cmp rcx,rdx','jb invalid_bounds','sub rcx,rdx','cmp rcx,256','jb invalid_bounds','cmp rcx,0x10000','ja invalid_bounds',
     'mov [r10+0x28],rdx','mov rax,[rdx+0xf8]','mov [r10+0x18],rax','mov [r10+0x20],rax','cmp dword ptr [r10+0x10],11','jne unchanged',
     'mov qword ptr [rdx+0xf8],0','mov qword ptr [r10+0x20],0','mov dword ptr [r10+0x14],1','jmp restore',
     'unchanged:','mov dword ptr [r10+0x14],2','jmp restore',
     'invalid_config:','mov dword ptr [r10+0x14],4','jmp restore',
     'invalid_options:','mov dword ptr [r10+0x14],8','jmp restore',
     'invalid_bounds:','mov dword ptr [r10+0x14],16','jmp restore',
     'invalid_id:','mov dword ptr [r10+0x14],32','restore:')
 for off,reg in [(0x28,'rcx'),(0x30,'rdx'),(0x38,'r8'),(0x40,'r9'),(0x48,'r10'),(0x50,'r11'),(0x20,'rax')]:add(f'mov {reg},[rsp+{off}]')
 add('push qword ptr [rsp+0x58]','popfq','lea rsp,[rbp]','pop rbp','ret')
 asm='\n'.join(a);code=bytearray(Ks(KS_ARCH_X86,KS_MODE_64).asm(asm,addr=entry)[0]);md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True
 for i in md.disasm(bytes(code),entry):
  for op in i.operands:
   if op.type==X86_OP_MEM and i.reg_name(op.mem.base)=='rip'and op.mem.disp in fixups:
    struct.pack_into('<i',code,i.address-entry+i.disp_offset,fixups[op.mem.disp]-(i.address+i.size))
 assert code[:17].hex()=='55488da42470ffffff488dac2490000000'
 # SET_FPREG at17; ALLOC_LARGE(144B) at9; PUSH_NONVOL RBP at1.
 unwind=bytes.fromhex('011104951103090112000150')
 return bytes(code),asm,{'entryVA':entry,'codeBytes':len(code),'frameAllocationBytes':AA_FRAME,'frameBytesIncludingSavedRbp':AA_FRAME+8,'prologueBytes':17,'frameRegister':'RBP','frameRegisterOffsetBytes':AA_FRAME,'unwindHex':unwind.hex(),
  'diagRva':hex(AA_DIAG_RVA),'diagBytes':64,'diagVersion':1,'diagOffsets':{'calls':8,'lastId':16,'status':20,'originalAA':24,'finalAA':32,'optionVectorBegin':40,'configPointer':48,'originalN':56},
  'statusBits':{'id11OverrideApplied':1,'otherPresetUnchanged':2,'invalidConfig':4,'invalidOptionsObject':8,'invalidVectorBounds':16,'invalidId':32},
  'boundary':'Standard owned profile, with optional shader string setting121 absent. No persistent launcher setting is changed.'}
