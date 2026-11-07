"""Fifteen compatible native services with exact XY restore and profile selection."""
from pathlib import Path
import sys,struct
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT/'pythonlibs'),str(ROOT/'widescreen-analysis/ui')]
import scoped_ui_kernel_v2_movie as OLD
from keystone import Ks,KS_ARCH_X86,KS_MODE_64
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
SLOT=0x500;RECORD=56;STATE_USED=0x3000;CACHE_OFFSET=0x2f00

def pre(site,delta,direct,decoder):
 b=['cmp dword ptr [r10+20],0','jne overflow','mov eax,[r10+16]','cmp eax,16','jae overflow',
  'imul eax,eax,56','lea rbx,[r10+rax+0xc0]',f'mov dword ptr [rbx],{site}','mov dword ptr [rbx+4],0','mov [rbx+48],r12','inc dword ptr [r10+16]',
  'mov eax,[r10+4]','test eax,eax','je done','cmp eax,2','ja done','cmp r14,0x10000','jb done','cmp r14,0x7fffff00','ja done']
 if direct:b += [f'cmp dword ptr [r15+r14],{6 if site==4 else 7}','jne done','cmp dword ptr [r15+r14+4],4','jne done','cmp dword ptr [r15+r14+12],28','jne done','mov edx,[r15+r14+8]']
 else:b += ['cmp dword ptr [r15+r14+4],4','jne done','mov edx,[r15+r14]']
 b += [f'lea rcx,[r14+{delta}]','cmp rdx,rcx','jne done','cmp rdx,0x7fffff80','ja done','lea rsi,[r15+rdx]','mov [rbx+8],rsi',f'call {decoder}','mov r9d,eax',
  'lea rdx,[rip]','shl eax,5','add rdx,rax','movss xmm1,[rdx]','movss xmm4,[rdx+4]','movss xmm2,[rdx+8]','movss xmm5,[rdx+12]','xorps xmm3,xmm3','xorps xmm6,xmm6']
 for i in range(4):
  b += [f'mov eax,[rsi+{28*i}]',f'mov [rbx+{16+4*i}],eax','and eax,0x7fffffff','cmp eax,0x47800000','ja done',
   'test r9d,r9d',f'je skip_y_{i}',f'mov eax,[rsi+{28*i+4}]',f'mov [rbx+{32+4*i}],eax','and eax,0x7fffffff','cmp eax,0x47800000','ja done',f'skip_y_{i}:']
 b += ['cmp dword ptr [r10+4],2','jne transform_x','movss xmm2,[rbx+16]','addss xmm2,[rbx+20]','addss xmm2,[rbx+24]','addss xmm2,[rbx+28]',
  'mov eax,0x3e800000','movd xmm0,eax','mulss xmm2,xmm0','movaps xmm3,xmm2','test r9d,r9d','je transform_x',
  'movss xmm5,[rbx+32]','addss xmm5,[rbx+36]','addss xmm5,[rbx+40]','addss xmm5,[rbx+44]','mulss xmm5,xmm0','movaps xmm6,xmm5','transform_x:']
 for i in range(4):b += [f'movss xmm0,[rbx+{16+4*i}]','subss xmm0,xmm3','mulss xmm0,xmm1','addss xmm0,xmm2',f'movss [rsi+{28*i}],xmm0']
 b += ['mov dword ptr [rbx+4],1','test r9d,r9d','je done']
 for i in range(4):b += [f'movss xmm0,[rbx+{32+4*i}]','subss xmm0,xmm6','mulss xmm0,xmm4','addss xmm0,xmm5',f'movss [rsi+{28*i+4}],xmm0']
 b += ['mov dword ptr [rbx+4],3','jmp done','overflow:','inc dword ptr [r10+20]','jmp done'];return b

def post(site):
 b=['cmp dword ptr [r10+20],0','je normal_post','dec dword ptr [r10+20]','jmp done','normal_post:','mov eax,[r10+16]','test eax,eax','je done','dec eax','imul edx,eax,56','lea rbx,[r10+rdx+0xc0]',
  f'cmp dword ptr [rbx],{site}','jne mismatch','cmp [rbx+48],r12','jne mismatch','mov [r10+16],eax','mov edx,[rbx+4]','test edx,1','je done','mov rsi,[rbx+8]']
 for i in range(4):b += [f'mov eax,[rbx+{16+4*i}]',f'mov [rsi+{28*i}],eax']
 b += ['test edx,2','je restored']
 for i in range(4):b += [f'mov eax,[rbx+{32+4*i}]',f'mov [rsi+{28*i+4}],eax']
 return b+['restored:','mov dword ptr [rbx+4],0','jmp done','mismatch:','mov dword ptr [r10+4],0','jmp done']

def emit(code_base,state_base,iat,decoder,profile_table):
 specs={'hud_enter':OLD.V1.scope_enter(1),'hud_exit':OLD.V1.scope_exit(1),'widget_enter':OLD.V1.scope_enter(2),'widget_exit':OLD.V1.scope_exit(2)}
 for n,delta,direct in[(1,0xf0,True),(2,0x80,True),(3,0x7c,False)]:specs['quad_pre_'+str(n)]=pre(n,delta,direct,decoder);specs['quad_post_'+str(n)]=post(n)
 for name,vt in OLD.FLAT_TYPES.items():specs[name]=OLD.V2.flat_enter(vt)
 specs['flat_exit']=OLD.V1.scope_exit(3);specs['quad_pre_4']=pre(4,0x10,True,decoder);specs['quad_post_4']=post(4)
 pro=[s.replace('add r10,0x400','add r10,0x500')for s in OLD.V1.prologue()]
 ks=Ks(KS_ARCH_X86,KS_MODE_64);md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True;blob=bytearray();entries={};sources={};links=[]
 for name,body in specs.items():
  while len(blob)%16:blob.append(0xcc)
  address=code_base+len(blob);entries[name]=address;asm='\n'.join(pro+body+OLD.V1.epilogue());data=bytearray(ks.asm(asm,addr=address)[0]);sources[name]=asm
  for i in md.disasm(data,address):
   target=iat if i.mnemonic=='call'and i.op_str=='qword ptr [rip]'else state_base if i.mnemonic=='lea'and i.op_str=='r10, [rip]'else profile_table if i.mnemonic=='lea'and i.op_str=='rdx, [rip]'else None
   if target is not None:struct.pack_into('<i',data,i.address-address+i.disp_offset,target-i.address-i.size);links.append(dict(service=name,instructionVA=i.address,targetVA=target))
  blob.extend(data)
 assert len(entries)==15;return bytes(blob),entries,sources,links
