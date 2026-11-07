"""New-preset-only scoped PMv2 GetClientRect; no runtime/tool-side calls."""
from final_call_proxy_v1 import *
DPI_RVA=RX_RVA+0x25000
DPI_IAT_RVA=RW_RVA+0x200
GETRECT_IAT_RVA=0x3d96a8
DPI_FRAME=0x68
def emit_dpi(entry=IMAGE_BASE+DPI_RVA,decoder=IMAGE_BASE+0x740000,setdpi_iat=IMAGE_BASE+DPI_IAT_RVA,getrect_iat=IMAGE_BASE+GETRECT_IAT_RVA,diag=IMAGE_BASE+DIAG_RVA+0x80):
 a=[];fixups={}
 def add(*s):a.extend(s)
 def indirect(target):
  marker=0x13580000+len(fixups);fixups[marker]=target;add(f'call qword ptr [rip+{marker}]')
 def diagptr():
  marker=0x13580000+len(fixups);fixups[marker]=diag;add(f'lea r10,[rip+{marker}]')
 def geterror():add('xor eax,eax','mov eax,dword ptr gs:[rax+0x68]')
 def seterror(slot):add('xor ecx,ecx',f'mov edx,[rsp+{slot}]','mov dword ptr gs:[rcx+0x68],edx')
 add(f'sub rsp,{DPI_FRAME}','mov [rsp+0x20],rcx','mov [rsp+0x28],rdx')
 geterror();add('mov [rsp+0x30],eax','mov qword ptr [rsp+0x38],0','mov dword ptr [rsp+0x4c],0',f'call {decoder}',
  'mov [rsp+0x48],eax','test eax,eax','jz old_api','cmp eax,11','ja old_api','mov rcx,-4')
 indirect(setdpi_iat)
 add('mov [rsp+0x38],rax','test rax,rax','jz dpi_set_failed','or dword ptr [rsp+0x4c],1','jmp old_api',
  'dpi_set_failed:','or dword ptr [rsp+0x4c],2','old_api:')
 # Restore entry LastError before calling the real API, including ID0/cache miss.
 seterror(0x30);add('mov rcx,[rsp+0x20]','mov rdx,[rsp+0x28]')
 indirect(getrect_iat)
 add('mov [rsp+0x40],eax');geterror();add('mov [rsp+0x44],eax','cmp dword ptr [rsp+0x40],0','jne check_restore','or dword ptr [rsp+0x4c],4',
  'check_restore:','mov rcx,[rsp+0x38]','test rcx,rcx','jz finish')
 indirect(setdpi_iat)
 add('test rax,rax','jnz finish','or dword ptr [rsp+0x4c],8','finish:')
 diagptr()
 add('lock inc qword ptr [r10]','mov eax,[rsp+0x48]','mov [r10+8],eax','mov eax,[rsp+0x4c]','mov [r10+12],eax',
  'mov rax,[rsp+0x38]','mov [r10+16],rax','mov eax,[rsp+0x40]','mov [r10+24],eax','mov eax,[rsp+0x44]','mov [r10+28],eax')
 seterror(0x44);add('mov eax,[rsp+0x40]',f'add rsp,{DPI_FRAME}','ret')
 asm='\n'.join(a);code=bytearray(Ks(KS_ARCH_X86,KS_MODE_64).asm(asm,addr=entry)[0]);md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True
 found=0
 for i in md.disasm(bytes(code),entry):
  for op in i.operands:
   if op.type==X86_OP_MEM and i.reg_name(op.mem.base)=='rip'and op.mem.disp in fixups:
    at=i.address-entry+i.disp_offset;struct.pack_into('<i',code,at,fixups[op.mem.disp]-i.address-i.size);found+=1
 assert found==len(fixups)and len(code)<0x1000 and code[:4]==bytes.fromhex('4883ec68')
 meta={'entryVA':entry,'codeBytes':len(code),'frameBytes':DPI_FRAME,'unwindHex':'0104010004c20000','prologueBytes':4,
  'diagRva':hex(DIAG_RVA+0x80),'diagnosticFlags':{'enteredPmV2':1,'enterFailed':2,'getClientRectFalse':4,'restoreFailed':8},
  'threadPolicy':'ID0 calls only originalGetClientRect; valid preset attempts SetThreadDpiAwarenessContext(-4), calls originalAPI, then restores saved oldContext whenever enter succeeded, including BOOLfalse.',
  'lastErrorPolicy':'Save entry LastError before decoder; restore before GetClientRect; preserve GetClientRect LastError across context restoration/diagnostics using Win64TEB GS+68.'}
 return bytes(code),asm,meta
if __name__=='__main__':
 code,asm,meta=emit_dpi();(HERE/'dpi-rect-proxy-v2.bin').write_bytes(code);(HERE/'dpi-rect-proxy-v2.asm').write_text(asm+'\n','utf8');print(json.dumps(meta,indent=2))
