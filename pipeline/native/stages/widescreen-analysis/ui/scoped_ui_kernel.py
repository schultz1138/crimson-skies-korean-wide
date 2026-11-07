"""Offline native services, not an installer or complete title-DLL builder.

Parent trampolines may CALL a service, replay displaced whole instructions,
then resume exact original native flow. No host frame persists across guest
execution. Requires RX code, separate zero-initialized RW state of0x2100bytes,
and the already verified GetCurrentThreadId import IAT.
"""
from pathlib import Path
import sys,struct,json,hashlib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'pythonlibs'))
from keystone import Ks,KS_ARCH_X86,KS_MODE_64
from capstone import Cs,CS_ARCH_X86,CS_MODE_64

REGS=['rax','rbx','rcx','rdx','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15']
SAVED={reg:8*(14-i) for i,reg in enumerate(REGS)}
SLOT_SIZE=0x400;THREADS=8;DEPTH=16;SCOPES=0x40;QUADS=0xc0;RECORD=40
STATE_BYTES=0x2100
PROJECTED=[0x2c0b0c,0x2c5504,0x2c43a8]

def prologue():
 return ['pushfq']+['push '+r for r in REGS]+['mov rbp,rsp','and rsp,-16','sub rsp,0xb0','mov [rsp+0xa0],rbp']+[
  f'movdqu [rsp+{0x20+16*i}],xmm{i}'for i in range(8)]+[
  'call qword ptr [rip]','mov r11d,eax','lea r10,[rip]','mov ecx,8',
  'scan:','mov eax,[r10]','cmp eax,r11d','je found','test eax,eax','jne next_slot',
  'xor eax,eax','lock cmpxchg dword ptr [r10],r11d','je found',
  'next_slot:','add r10,0x400','dec ecx','jne scan','jmp done','found:']

def epilogue():
 return ['done:']+[f'movdqu xmm{i},[rsp+{0x20+16*i}]'for i in range(8)]+[
  'mov rsp,[rsp+0xa0]']+['pop '+r for r in reversed(REGS)]+['popfq','ret']

def scope_enter(kind):
 body=[
  'cmp dword ptr [r10+12],0','jne scope_overflow_nested',
  'mov eax,[r10+8]','cmp eax,16','jae scope_overflow_first',
  'lea rdx,[r10+rax*8+0x40]',f'mov dword ptr [rdx],{kind}',
  'mov ecx,[r10+4]','mov [rdx+4],ecx','inc dword ptr [r10+8]']
 if kind==1:
  body += [f'mov ecx,[rbp+{SAVED["rcx"]}]','cmp ecx,0x10000','jb disable',
   'cmp ecx,0x7ffff600','ja disable','lea rdx,[r15+rcx]',
   'cmp dword ptr [rdx+0x984],0','jne disable','cmp dword ptr [rdx+0x988],0','jne disable',
   'cmp dword ptr [rdx+0x98c],640','jne disable','cmp dword ptr [rdx+0x990],480','jne disable',
   'mov dword ptr [r10+4],1','jmp done','disable:','mov dword ptr [r10+4],0','jmp done']
 else:
  body += ['cmp dword ptr [r10+4],0','je done',f'mov eax,[rbp+{SAVED["rax"]}]']
  for vt in PROJECTED:body+= [f'cmp eax,{vt}','je projected']
  body+=['jmp done','projected:','mov dword ptr [r10+4],2','jmp done']
 return body+['scope_overflow_first:','mov eax,[r10+4]','mov [r10+32],eax',
  'scope_overflow_nested:','inc dword ptr [r10+12]','mov dword ptr [r10+4],0','jmp done']

def scope_exit(kind):
 return ['cmp dword ptr [r10+12],0','je scope_normal','dec dword ptr [r10+12]',
  'jne done','mov eax,[r10+32]','mov [r10+4],eax','jmp done','scope_normal:',
  'mov eax,[r10+8]','test eax,eax','je done','dec eax','lea rdx,[r10+rax*8+0x40]',
  f'cmp dword ptr [rdx],{kind}','jne mismatch','mov ecx,[rdx+4]','mov [r10+4],ecx',
  'mov [r10+8],eax','jmp done','mismatch:','mov dword ptr [r10+4],0','jmp done']

def quad_pre(site,pointer_delta,direct):
 b=['cmp dword ptr [r10+20],0','jne overflow','mov eax,[r10+16]','cmp eax,16','jae overflow',
  'imul eax,eax,40','lea rbx,[r10+rax+0xc0]',f'mov dword ptr [rbx],{site}',
  'mov dword ptr [rbx+4],0','mov [rbx+32],r12','inc dword ptr [r10+16]',
  'mov eax,[r10+4]','test eax,eax','je done','cmp eax,2','ja done',
  'cmp r14,0x10000','jb done','cmp r14,0x7fffff00','ja done']
 if direct:
  b+=['cmp dword ptr [r15+r14],7','jne done','cmp dword ptr [r15+r14+4],4','jne done',
   'cmp dword ptr [r15+r14+12],28','jne done','mov edx,[r15+r14+8]']
 else:b+=['cmp dword ptr [r15+r14+4],4','jne done','mov edx,[r15+r14]']
 b += [f'lea rcx,[r14+{pointer_delta}]','cmp rdx,rcx','jne done',
  'cmp rdx,0x7fffff80','ja done','lea rsi,[r15+rdx]','mov [rbx+8],rsi']
 for i in range(4):
  b += [f'mov eax,[rsi+{28*i}]',f'mov [rbx+{16+4*i}],eax','and eax,0x7fffffff',
   'cmp eax,0x47800000','ja done']
 b += ['mov eax,0x3f400000','movd xmm1,eax','cmp dword ptr [r10+4],2','je local_center',
  'mov eax,0x42a00000','movd xmm2,eax','xorps xmm3,xmm3','jmp transform','local_center:',
  'movss xmm2,[rbx+16]','addss xmm2,[rbx+20]','addss xmm2,[rbx+24]','addss xmm2,[rbx+28]',
  'mov eax,0x3e800000','movd xmm3,eax','mulss xmm2,xmm3','movaps xmm3,xmm2','transform:']
 for i in range(4):
  b += [f'movss xmm0,[rbx+{16+4*i}]','subss xmm0,xmm3','mulss xmm0,xmm1',
   'addss xmm0,xmm2',f'movss [rsi+{28*i}],xmm0']
 b += ['mov dword ptr [rbx+4],1','jmp done','overflow:','inc dword ptr [r10+20]','jmp done']
 return b

def quad_post(site):
 b=['cmp dword ptr [r10+20],0','je normal_post','dec dword ptr [r10+20]','jmp done',
  'normal_post:','mov eax,[r10+16]','test eax,eax','je done','dec eax','imul edx,eax,40',
  'lea rbx,[r10+rdx+0xc0]',f'cmp dword ptr [rbx],{site}','jne mismatch',
  'cmp [rbx+32],r12','jne mismatch','mov [r10+16],eax','cmp dword ptr [rbx+4],1','jne done',
  'mov rsi,[rbx+8]']
 for i in range(4):b += [f'mov eax,[rbx+{16+4*i}]',f'mov [rsi+{28*i}],eax']
 b += ['mov dword ptr [rbx+4],0','jmp done','mismatch:','mov dword ptr [r10+4],0','jmp done']
 return b

def emit(code_base,state_base,iat_address):
 """Return linked RX bytes + entry offsets; caller owns PE section admission."""
 specs={'hud_enter':scope_enter(1),'hud_exit':scope_exit(1),
  'widget_enter':scope_enter(2),'widget_exit':scope_exit(2)}
 for n,delta,direct in [(1,0xf0,True),(2,0x80,True),(3,0x7c,False)]:
  specs['quad_pre_'+str(n)]=quad_pre(n,delta,direct);specs['quad_post_'+str(n)]=quad_post(n)
 ks=Ks(KS_ARCH_X86,KS_MODE_64);md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True
 blob=bytearray();entries={};sources={};links=[]
 for name,body in specs.items():
  while len(blob)%16:blob.append(0xcc)
  at=code_base+len(blob);entries[name]=at;asm='\n'.join(prologue()+body+epilogue());sources[name]=asm
  data=bytearray(ks.asm(asm,addr=at)[0]);ins=list(md.disasm(data,at))
  assert sum(i.size for i in ins)==len(data)
  for i in ins:
   target=iat_address if i.mnemonic=='call' and i.op_str=='qword ptr [rip]' else state_base if i.mnemonic=='lea' and i.op_str=='r10, [rip]' else None
   if target is not None:
    assert i.disp_size==4;disp=target-(i.address+i.size);assert -(1<<31)<=disp<(1<<31)
    struct.pack_into('<i',data,i.address-at+i.disp_offset,disp)
    links.append(dict(service=name,instruction=hex(i.address),target=hex(target),displacement=disp))
  assert sum(x['service']==name for x in links)==2
  blob.extend(data)
 return bytes(blob),entries,sources,links

if __name__=='__main__':
 out=Path(__file__).resolve().parent
 data,entries,sources,links=emit(0x10000000,0x10020000,0x10030000)
 (out/'scoped-ui-services.bin').write_bytes(data)
 (out/'scoped-ui-services.asm').write_text('\n\n'.join('; '+n+'\n'+a for n,a in sources.items())+'\n','utf8')
 (out/'scoped-ui-services.json').write_text(json.dumps(dict(schema=1,codeBase=0x10000000,stateBase=0x10020000,iat=0x10030000,stateBytes=STATE_BYTES,
   entries=entries,links=links,codeBytes=len(data),codeSha256=hashlib.sha256(data).hexdigest(),notIntegratedIntoDll=True,installedFilesModified=False),indent=2)+'\n','utf8')
 print('Emitted',len(data),'bytes;10services,notinstalled')
