"""Offline x64 final-blit proxy. No process/installed-file access.

ABI matches original3e58: RCX/RDX/R8/R9 and stack arguments5..9 pass
through. New viewport/UV objects live in this proxy's stack frame.
"""
from pathlib import Path
import sys,struct,json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'pythonlibs'))
from keystone import Ks,KS_ARCH_X86,KS_MODE_64
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86 import X86_OP_MEM
IMAGE_BASE=0x180000000
RX_RVA=0x73f000;RX_RESERVATION=0x28000
RW_RVA=RX_RVA+RX_RESERVATION;RW_RESERVATION=0x1000
TABLE_RVA=RX_RVA+0x2000;DIAG_RVA=RW_RVA;DECODER_CACHE_RVA=RW_RVA+0x100
FRAME=0x128
STATUS={'nativeDensityCrop':1,'sourceMismatch':2,'sourceInvalid':4,'destinationInvalid':8,'destinationSizeMismatch':16,'unexpectedId':32,'densityTooLow':64,'uvInvalid':128,'logicalFrameMismatch':256}
def emit(entry=IMAGE_BASE+RX_RVA,decoder=IMAGE_BASE+RX_RVA+0x1000,table=IMAGE_BASE+TABLE_RVA,diag=IMAGE_BASE+DIAG_RVA,original=IMAGE_BASE+0x3e58):
 a=[];fixups={}
 def add(*s):a.extend(s)
 def lea(reg,target):
  marker=0x13570000+len(fixups);fixups[marker]=target
  add(f'lea {reg},[rip+{marker}]')
 def guard_ptr(reg,fail):
  add(f'cmp {reg},0x10000',f'jb {fail}',f'test {reg},7',f'jnz {fail}',f'mov rcx,{reg}','shr rcx,47',f'jnz {fail}')
 add(f'sub rsp,{FRAME}','mov [rsp+0x48],rcx','mov [rsp+0x50],rdx','mov [rsp+0x58],r8','mov [rsp+0x60],r9')
 for k in range(5):add(f'mov rax,[rsp+{FRAME+0x28+k*8}]',f'mov [rsp+{0x20+k*8}],rax')
 add('mov dword ptr [rsp+0xe0],0',f'call {decoder}')
 lea('r10',diag)
 add('lock inc qword ptr [r10+8]','mov [r10+0x10],eax','mov qword ptr [r10+0x18],0','mov qword ptr [r10+0x20],0','mov qword ptr [r10+0x28],0',
     'test eax,eax','jz forward','cmp eax,11','ja unexpected_id','dec eax','shl eax,5')
 lea('r11',table)
 add('add r11,rax','mov [rsp+0x78],r11','mov eax,[r11]','mov [r10+0x28],eax','mov eax,[r11+4]','mov [r10+0x2c],eax',
     'mov rax,[rsp+0x58]')
 guard_ptr('rax','destination_invalid')
 add('mov rdx,[rax+8]');guard_ptr('rdx','destination_invalid')
 add('cmp dword ptr [rdx+0x20],3','jne destination_invalid','cmp dword ptr [rdx+0x44],1','jne destination_invalid',
     'mov rax,[rdx+0x30]','test rax,rax','jz destination_invalid','cmp rax,16384','ja destination_invalid',
     'mov [rsp+0xd8],eax','mov [r10+0x20],eax','cmp eax,[r11]','je destination_width_matches',
     'or dword ptr [rsp+0xe0],16','destination_width_matches:',
     'mov eax,[rdx+0x38]','test eax,eax','jz destination_invalid','cmp eax,16384','ja destination_invalid',
     'mov [rsp+0xdc],eax','mov [r10+0x24],eax','cmp eax,[r11+4]','je destination_height_matches',
     'or dword ptr [rsp+0xe0],16','destination_height_matches:')
 # Fit selected visible aspect to actual cached destination resource size.
 add('xorps xmm0,xmm0','cvtsi2ss xmm0,dword ptr [rsp+0xd8]',
     'xorps xmm1,xmm1','cvtsi2ss xmm1,dword ptr [r11]','divss xmm0,xmm1',
     'xorps xmm2,xmm2','cvtsi2ss xmm2,dword ptr [rsp+0xdc]',
     'xorps xmm3,xmm3','cvtsi2ss xmm3,dword ptr [r11+4]','divss xmm2,xmm3',
     'minss xmm0,xmm2','mulss xmm1,xmm0','mulss xmm3,xmm0',
     'cvtsi2ss xmm2,dword ptr [rsp+0xd8]','minss xmm1,xmm2',
     'cvtsi2ss xmm2,dword ptr [rsp+0xdc]','minss xmm3,xmm2',
     'movss [rsp+0xa8],xmm1','movss [rsp+0xac],xmm3',
     'xorps xmm0,xmm0','cvtsi2ss xmm0,dword ptr [rsp+0xd8]','subss xmm0,xmm1',
     'xorps xmm2,xmm2','cvtsi2ss xmm2,dword ptr [rsp+0xdc]','subss xmm2,xmm3',
     'mov eax,0x3f000000','movd xmm5,eax','mulss xmm0,xmm5','mulss xmm2,xmm5',
     'movss [rsp+0xa0],xmm0','movss [rsp+0xa4],xmm2',
     'mov dword ptr [rsp+0xb0],0','mov dword ptr [rsp+0xb4],0x3f800000',
     'lea rax,[rsp+0xa0]','mov [rsp+0x20],rax',
     'mov rax,[rsp+0x50]')
 guard_ptr('rax','source_invalid')
 add('mov rdx,[rax+8]');guard_ptr('rdx','source_invalid')
 add('cmp dword ptr [rdx+0x20],3','jne source_invalid',
     'mov eax,[rdx+0x44]','test eax,eax','jz source_invalid','cmp eax,16','ja source_invalid','mov ecx,eax','dec ecx','test ecx,eax','jnz source_invalid',
     'cmp word ptr [rdx+0x3c],1','jne source_invalid',
     'mov rax,[rdx+0x30]','test rax,rax','jz source_invalid','cmp rax,16384','ja source_invalid',
     'mov [r10+0x18],eax',
     'mov eax,[rdx+0x38]','test eax,eax','jz source_invalid','cmp eax,16384','ja source_invalid',
     'mov [r10+0x1c],eax','mov [rsp+0xf8],rdx','mov rax,rsi')
 guard_ptr('rax','frame_mismatch')
 add('mov eax,[rsi+0x1c]','cmp eax,[rsi+0x5c]','cmova eax,[rsi+0x5c]','cmp eax,640','jne frame_mismatch',
     'mov eax,[rsi+0x20]','cmp eax,[rsi+0x60]','cmova eax,[rsi+0x60]','cmp eax,480','jne frame_mismatch',
     'mov eax,[rsi+0xe50]','mov [rsp+0xe4],eax','mov ecx,[rsi+0xe58]','add ecx,eax','jc frame_mismatch','cmp ecx,640','jae frame_mismatch',
     'mov eax,640','sub eax,ecx','mov [rsp+0xd0],eax','mov [r10+0x48],eax',
     'mov eax,[rsi+0xe54]','mov [rsp+0xe8],eax','mov ecx,[rsi+0xe5c]','add ecx,eax','jc frame_mismatch','cmp ecx,480','jae frame_mismatch',
     'mov eax,480','sub eax,ecx','mov [rsp+0xd4],eax','mov [r10+0x4c],eax',
     'mov rax,[rsp+0x28]')
 guard_ptr('rax','uv_invalid')
 add('mov [rsp+0xf0],rax','mov rdx,rax')
 # Original UV must be a positive finite scale and nonnegative finite offset.
 for off in [0,4,8,12]:
  add(f'mov eax,[rdx+{off}]')
  if off<8:add('test eax,eax','jz uv_invalid')
  add('cmp eax,0x3f800000','ja uv_invalid')
 add('movups xmm0,[rdx]','movups [r10+0x50],xmm0',
     'movss xmm0,[rdx]','addss xmm0,[rdx+8]','mov eax,0x3f800000','movd xmm4,eax','ucomiss xmm0,xmm4','ja uv_invalid',
     'movss xmm0,[rdx+4]','addss xmm0,[rdx+12]','ucomiss xmm0,xmm4','ja uv_invalid',
     'xorps xmm1,xmm1','cvtsi2ss xmm1,dword ptr [rsp+0xd0]','movss xmm0,[rdx]','divss xmm0,xmm1','movss [rsp+0xc8],xmm0',
     'xorps xmm1,xmm1','cvtsi2ss xmm1,dword ptr [rsp+0xd4]','movss xmm2,[rdx+4]','divss xmm2,xmm1','movss [rsp+0xcc],xmm2',
     'xorps xmm1,xmm1','cvtsi2ss xmm1,dword ptr [r10+0x18]','mulss xmm1,xmm0','movss [r10+0x40],xmm1','ucomiss xmm1,[r11+28]','jb density_low',
     'xorps xmm1,xmm1','cvtsi2ss xmm1,dword ptr [r10+0x1c]','mulss xmm1,xmm2','movss [r10+0x44],xmm1','ucomiss xmm1,[r11+28]','jb density_low',
     'movss xmm0,[r11+16]','mulss xmm0,[rsp+0xc8]','movss [rsp+0xb8],xmm0',
     'movss xmm0,[r11+20]','mulss xmm0,[rsp+0xcc]','movss [rsp+0xbc],xmm0',
     'mov eax,0x3f000000','movd xmm5,eax',
     'mov eax,640','xorps xmm0,xmm0','cvtsi2ss xmm0,eax','subss xmm0,[r11+16]','mulss xmm0,xmm5',
     'xorps xmm1,xmm1','cvtsi2ss xmm1,dword ptr [rsp+0xe4]','subss xmm0,xmm1','mulss xmm0,[rsp+0xc8]','addss xmm0,[rdx+8]','movss [rsp+0xc0],xmm0',
     'mov eax,480','xorps xmm0,xmm0','cvtsi2ss xmm0,eax','subss xmm0,[r11+20]','mulss xmm0,xmm5',
     'xorps xmm1,xmm1','cvtsi2ss xmm1,dword ptr [rsp+0xe8]','subss xmm0,xmm1','mulss xmm0,[rsp+0xcc]','addss xmm0,[rdx+12]','movss [rsp+0xc4],xmm0')
 for off in [0xb8,0xbc,0xc0,0xc4]:
  add(f'mov eax,[rsp+{off}]','cmp eax,0x3f800000','ja uv_invalid')
 add('movss xmm0,[rsp+0xb8]','addss xmm0,[rsp+0xc0]','ucomiss xmm0,xmm4','ja uv_invalid',
     'movss xmm0,[rsp+0xbc]','addss xmm0,[rsp+0xc4]','ucomiss xmm0,xmm4','ja uv_invalid',
     'lea rax,[rsp+0xb8]','mov [rsp+0x28],rax','movups xmm0,[rsp+0xb8]','movups [r10+0x30],xmm0',
     'or dword ptr [rsp+0xe0],1','jmp forward',
     'density_low:','or dword ptr [rsp+0xe0],64','jmp forward',
     'uv_invalid:','or dword ptr [rsp+0xe0],128','jmp forward',
     'frame_mismatch:','or dword ptr [rsp+0xe0],256','jmp forward',
     'source_mismatch:','or dword ptr [rsp+0xe0],2','jmp forward',
     'source_invalid:','or dword ptr [rsp+0xe0],4','jmp forward',
     'destination_invalid:','or dword ptr [rsp+0xe0],8','jmp forward',
     'unexpected_id:','or dword ptr [rsp+0xe0],32',
     'forward:','mov eax,[rsp+0xe0]','mov [r10+0x14],eax',
     'mov rcx,[rsp+0x48]','mov rdx,[rsp+0x50]','mov r8,[rsp+0x58]','mov r9,[rsp+0x60]',
     f'call {original}',f'add rsp,{FRAME}','ret')
 source='\n'.join(a);code=bytearray(Ks(KS_ARCH_X86,KS_MODE_64).asm(source,addr=entry)[0])
 md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True;patched=[]
 for ins in md.disasm(bytes(code),entry):
  for op in ins.operands:
   if op.type==X86_OP_MEM and ins.reg_name(op.mem.base)=='rip' and op.mem.disp in fixups:
    target=fixups[op.mem.disp];disp=target-(ins.address+ins.size)
    assert -(1<<31)<=disp<(1<<31)
    at=ins.address-entry+ins.disp_offset;struct.pack_into('<i',code,at,disp);patched.append(target)
 assert len(patched)==len(fixups)
 # Version1, prolog7B, ALLOC_LARGE128h, no nonvolatile register modifications.
 unwind=bytes([1,7,2,0,7,1,FRAME//8,0])
 return bytes(code),source,{'frameBytes':FRAME,'unwind':unwind.hex(),'entry':hex(entry),'codeBytes':len(code),'diagnosticLayout':{'calls':8,'lastId':16,'status':20,'sourceW':24,'sourceH':28,'destinationW':32,'destinationH':36,'selectedW':40,'selectedH':44,'cropUv':48,'densityX':64,'densityY':68,'effectiveLogicalW':72,'effectiveLogicalH':76,'originalUv':80},'statusBits':dict(STATUS)}
def table_bytes(contract):
 result=b''
 for p in contract['presets']:
  n=p['integerScale'];threshold=struct.unpack('<f',struct.pack('<I',struct.unpack('<I',struct.pack('<f',n))[0]-4))[0]
  vals=[p['width']/n,p['height']/n,float(n),threshold]
  assert 0<vals[0]<=640 and 0<vals[1]<=480
  result+=struct.pack('<4I4f',p['width'],p['height'],n,0,*vals)
 assert len(result)==11*32
 return result
if __name__=='__main__':
 code,asm,meta=emit();(HERE/'final-call-proxy-v1.bin').write_bytes(code);(HERE/'final-call-proxy-v1.asm').write_text(asm+'\n','utf8')
 print(json.dumps(meta,indent=2))
