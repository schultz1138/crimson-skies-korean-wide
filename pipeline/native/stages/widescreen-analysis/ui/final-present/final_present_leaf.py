"""Offline, callsite-scoped proxy for the VGPU final viewport fit.

The builder must retarget only CALL RVA 0x4bd1. The original helper at
0x6aff0 and its other caller at 0x525cd must stay byte-for-byte intact.
No installed files or process state are modified by this module.
"""
from pathlib import Path
import sys, struct, hashlib, json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'pythonlibs'))
from keystone import Ks, KS_ARCH_X86, KS_MODE_64
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

IMAGE_BASE=0x180000000
CODE_RVA=0x73e000
FALLBACK_RVA=0x6aff0
BOUNDS={'maximumDimension':16384.0,'sourceAspect':[1.30,1.37],
        'destinationAspect':[1.75,1.80]}

def bits(x):
 return struct.unpack('<I',struct.pack('<f',x))[0]

def emit(code_base=IMAGE_BASE+CODE_RVA, fallback=IMAGE_BASE+FALLBACK_RVA):
 """Return bytes, assembly and finite policy, relocated to code_base.

 ABI: RCX=24-byte viewport output, XMM1=source width, XMM2=source
 height, XMM3=destination width, [entry RSP+0x28]=destination height.
 No stack frame, external calls, nonvolatile register or memory scratch.
 Fallback preserves every input argument and tail-jumps to the old leaf.
 """
 a=['movss xmm4,dword ptr [rsp+0x28]']
 for r in ['xmm1','xmm2','xmm3','xmm4']:
  a += [f'movd eax,{r}','test eax,eax','jz fallback',
        f'cmp eax,{bits(16384.0)}','ja fallback']
 # Unsigned float-bit comparison above rejects negative, +/-Inf and all
 # NaNs before arithmetic, and rejects both zero encodings.
 for numerator,denominator,lo,hi in [('xmm1','xmm2',1.30,1.37),
                                    ('xmm3','xmm4',1.75,1.80)]:
  a += [f'movaps xmm0,{numerator}',f'divss xmm0,{denominator}',
        f'mov eax,{bits(lo)}','movd xmm5,eax','ucomiss xmm0,xmm5',
        'jb fallback',f'mov eax,{bits(hi)}','movd xmm5,eax',
        'ucomiss xmm0,xmm5','ja fallback']
 a += ['xor eax,eax','mov [rcx],eax','mov [rcx+4],eax',
       'movss dword ptr [rcx+8],xmm3','movss dword ptr [rcx+12],xmm4',
       'mov [rcx+16],eax','mov dword ptr [rcx+20],0x3f800000',
       'mov rax,rcx','ret','fallback:',f'jmp {fallback}']
 source='\n'.join(a)
 raw,count=Ks(KS_ARCH_X86,KS_MODE_64).asm(source,addr=code_base)
 code=bytes(raw)
 assert len(code)<=0x200
 decoded=list(Cs(CS_ARCH_X86,CS_MODE_64).disasm(code,code_base))
 assert sum(i.size for i in decoded)==len(code)
 assert decoded[-1].mnemonic=='jmp' and int(decoded[-1].op_str,16)==fallback
 return code,source,dict(BOUNDS)

if __name__=='__main__':
 code,source,policy=emit()
 (HERE/'final-present-leaf.bin').write_bytes(code)
 (HERE/'final-present-leaf.asm').write_text('\n'.join(
  f'{i.address-IMAGE_BASE:08x} {i.bytes.hex():24} {i.mnemonic} {i.op_str}'
  for i in Cs(CS_ARCH_X86,CS_MODE_64).disasm(code,IMAGE_BASE+CODE_RVA))+'\n','utf8')
 receipt=dict(schema='vgpu-final-present-proxy-v1',codeRva=hex(CODE_RVA),
  fallbackRva=hex(FALLBACK_RVA),size=len(code),sha256=hashlib.sha256(code).hexdigest(),
  callsiteRva='0x4bd1',unchangedOtherCallerRva='0x525cd',policy=policy,
  scope='All 4:3-like sourceframes presented to 16:9-like destinations; movie/menu distinction unavailable here',
  abi='RCX/XMM1/XMM2/XMM3 and stack pristine on fallback; volatile RAX/XMM0/XMM4/XMM5 only',
  limitations=['No runtime proof','Does not preserve movie/menu aspect independently','No game or installed-file writes'])
 (HERE/'final-present-leaf.json').write_text(json.dumps(receipt,indent=2)+'\n','utf8')
 print(json.dumps(receipt,indent=2))
