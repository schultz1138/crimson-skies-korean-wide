# SPDX-License-Identifier: MIT
"""Offline 4K AA pool10 helper generator. Emits code only; never patches a game.

The emitted helper matches the released target. Full PE integration, relocation,
exception-table registration, AA proxy change and validation are separate steps.
Dependencies: keystone-engine and capstone.
"""
import struct
from keystone import Ks, KS_ARCH_X86, KS_MODE_64
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86_const import X86_OP_MEM
IMAGE_BASE = 0x180000000
ENTRY_RVA = 0x763c00
UW_RVA = 0x741520
DIAG_RVA = 0x767300
FRAME = 0x38

def emit(entry=IMAGE_BASE+ENTRY_RVA,diag=IMAGE_BASE+DIAG_RVA):
 a=[];fix={}
 def add(*s):a.extend(s)
 def rip(reg,target,marker):fix[marker]=target;add(f'lea {reg},[rip+{marker}]')
 def pointer(reg,label,span=0):
  add(f'cmp {reg},0x10000',f'jb {label}',f'test {reg},7',f'jnz {label}',f'mov rax,{reg}','shr rax,47',f'jnz {label}')
  if span:add(f'mov rax,{0x7fffffffffff-span}',f'cmp {reg},rax',f'ja {label}')
 add('push rbp','sub rsp,0x30','lea rbp,[rsp+0x30]','mov [rsp],rcx','mov [rsp+8],rdx','mov [rsp+0x10],r10','mov [rsp+0x18],r11','mov [rsp+0x20],rax',
     'cmp esi,10','jne restore')
 rip('r10',diag,0x13610000)
 add('lock inc qword ptr [r10+8]','mov dword ptr [r10+0x10],2','mov dword ptr [r10+0x14],0','mov [r10+0x18],esi',
     'mov dword ptr [r10+0x1c],0','mov qword ptr [r10+0x20],0','mov [r10+0x28],rax','mov [r10+0x30],rax',
     'cmp rax,0x18000000','jne restore')
 rip('r11',IMAGE_BASE+0x767100,0x13620000)
 add('mov ecx,[r11]','mov [r10+0x14],ecx','cmp ecx,12','jne wrong_id')
 rip('r11',IMAGE_BASE+0x5aecf8,0x13630000)
 add('mov r11,[r11]');pointer('r11','bad_config',0x68)
 add('mov ecx,[r11+0x68]','mov [r10+0x1c],ecx','cmp ecx,6','jne restore','cmp dword ptr [r11+0x60],6','jne restore',
     'mov r11,[r11+0x38]');pointer('r11','bad_options',0x10)
 add('mov rcx,[r11+8]','mov rdx,[r11+0x10]');pointer('rcx','bad_vector');pointer('rdx','bad_vector')
 add('cmp rdx,rcx','jb bad_vector','sub rdx,rcx','cmp rdx,256','jb bad_vector','cmp rdx,0x10000','ja bad_vector',
     'mov rax,[rcx+0xf8]','mov [r10+0x20],rax','cmp rax,1','je apply','cmp rax,2','jne unsupported_aa',
     'apply:','mov qword ptr [rsp+0x20],0x60000000','mov qword ptr [r10+0x30],0x60000000','mov dword ptr [r10+0x10],1','jmp restore',
     'wrong_id:','mov dword ptr [r10+0x10],32','jmp restore',
     'bad_config:','mov dword ptr [r10+0x10],4','jmp restore',
     'bad_options:','mov dword ptr [r10+0x10],8','jmp restore',
     'bad_vector:','mov dword ptr [r10+0x10],16','jmp restore',
     'unsupported_aa:','mov dword ptr [r10+0x10],64','restore:',
     'mov rcx,[rsp]','mov rdx,[rsp+8]','mov r10,[rsp+0x10]','mov r11,[rsp+0x18]','mov rax,[rsp+0x20]',
     'add rax,0xffff','lea rsp,[rbp]','pop rbp','ret')
 asm='\n'.join(a);code=bytearray(Ks(KS_ARCH_X86,KS_MODE_64).asm(asm,addr=entry)[0]);md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True
 for i in md.disasm(bytes(code),entry):
  for op in i.operands:
   if op.type==X86_OP_MEM and i.reg_name(op.mem.base)=='rip'and op.mem.disp in fix:
    # Module-relative targets relocate with the code and image.
    target=fix[op.mem.disp]+(entry-(IMAGE_BASE+ENTRY_RVA))
    struct.pack_into('<i',code,i.address-entry+i.disp_offset,target-(i.address+i.size))
 assert code[:10].hex()=='554883ec30488d6c2430'and len(code)<=0x400
 return bytes(code),asm,dict(entryVA=entry,codeBytes=len(code),frameBytes=FRAME,frameAllocationBytes=0x30,frameRegister='RBP',frameRegisterOffsetBytes=0x30,prologueBytes=10,unwindHex='010a03350a03055201500000',unwindRva=UW_RVA,
   diagRva=hex(DIAG_RVA),diagBytes=64,diagOffsets=dict(calls=8,status=16,cachedIdPlusOne=20,pool=24,N=28,AA=32,oldCapacity=40,newCapacity=48),
   status=dict(applied=1,unchanged=2,invalidConfig=4,invalidOptions=8,invalidVector=16,wrongPreset=32,unsupportedAA=64),
   gate='ESI10; incomingRAX384MiB; GPUcacheID+1=12; configN(+68,+60)=6; validated vector slot31 exactly1or2',
   capacityBytesBefore=0x18000000,capacityBytesAfter=0x60000000,maximumPool10BudgetMiB=1536,
   originalInstruction='add rax,0xffff',originalRva='0x43d95',continuationRva='0x43d9b')


if __name__ == "__main__":
    code, assembly, metadata = emit()
    print(assembly)
    print("\n# emitted bytes:", len(code))
    print("# machine code:", code.hex())
