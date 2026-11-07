"""Shared, bounded, source-guarded private preset decoder; emits offline code."""
from pathlib import Path
import sys,struct,json,hashlib
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'pythonlibs'))
from keystone import Ks,KS_ARCH_X86,KS_MODE_64
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
CONTRACT_PATH=HERE/'preset-contract-v1.json'
SETTER=bytes.fromhex('488b15359c0d00488bca480fbae909480fbaf20984c0480f45d14889151b9c0d00')
FRAME=0x1c8;BUFFER=0x1a0;RESULT=0x190
GPRS=['rbx','rcx','rdx','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15']
SLOTS={n:0x120+8*i for i,n in enumerate(GPRS)}
NONVOL={'rbx':3,'rbp':5,'rsi':6,'rdi':7,'r12':12,'r13':13,'r14':14,'r15':15}

def _flush(prefix):
 return ['test edx,edx',f'je {prefix}_done',f'{prefix}_loop:','cmp r12d,32',f'jae {prefix}_full',
  'mov byte ptr [r10+r12],92','inc r12d','dec edx',f'jne {prefix}_loop',f'jmp {prefix}_done',
  f'{prefix}_full:','mov r12d,33',f'{prefix}_done:']
def _append(prefix):
 return ['cmp r12d,32',f'jae {prefix}_full','mov byte ptr [r10+r12],r11b','inc r12d',f'jmp {prefix}_done',f'{prefix}_full:','mov r12d,33',f'{prefix}_done:']

def emit(code_base,cache_address):
 assert cache_address%4==0
 raw=CONTRACT_PATH.read_bytes();contract=json.loads(raw);rows=contract['presets'];assert [x['id']for x in rows]==list(range(1,12))
 ks=Ks(KS_ARCH_X86,KS_MODE_64);md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True
 parse_base=code_base+0x40
 cache_asm='\n'.join(['mov eax,dword ptr [rip]','sub eax,1','cmp eax,11','jbe cached',f'jmp {parse_base}','cached:','ret'])
 cache=bytearray(ks.asm(cache_asm,addr=code_base)[0]);assert len(cache)<0x40
 # Required nonvolatile saves occur first, keeping unwind prologue <256bytes.
 pro=[f'sub rsp,{FRAME}']
 for n in GPRS:
  if n in NONVOL:pro.append(f'mov qword ptr [rsp+{SLOTS[n]}],{n}')
 for i in range(6,16):pro.append(f'movdqu [rsp+{0x20+16*i}],xmm{i}')
 pro_bytes=bytes(ks.asm('\n'.join(pro),addr=parse_base)[0]);assert len(pro_bytes)<256
 body=[]
 for n in GPRS:
  if n not in NONVOL:body.append(f'mov qword ptr [rsp+{SLOTS[n]}],{n}')
 for i in range(6):body.append(f'movdqu [rsp+{0x20+16*i}],xmm{i}')
 body += ['xor eax,eax','mov rcx,qword ptr gs:[rax+0x60]','test rcx,rcx','je invalid_host','mov rcx,[rcx+0x10]','test rcx,rcx','je invalid_host',
  'cmp word ptr [rcx],0x5a4d','jne invalid_host','mov edx,[rcx+0x3c]','cmp edx,0x40','jb invalid_host','cmp edx,0x800','ja invalid_host',
  'cmp dword ptr [rcx+rdx],0x4550','jne invalid_host','cmp word ptr [rcx+rdx+4],0x8664','jne invalid_host','cmp word ptr [rcx+rdx+0x18],0x20b','jne invalid_host',
  'cmp dword ptr [rcx+rdx+8],0x6a8fb94a','jne invalid_host','cmp dword ptr [rcx+rdx+0x50],0xd98000','jne invalid_host']
 for i in range(0,32,4):body += [f'cmp dword ptr [rcx+{0x4662c+i}],{int.from_bytes(SETTER[i:i+4],"little")}','jne invalid_host']
 body += [f'cmp byte ptr [rcx+{0x4662c+32}],{SETTER[32]}','jne invalid_host','mov rax,[rcx+0xa52f0]','test rax,rax','je invalid_host','call rax','test rax,rax','je invalid_host',
  'mov rsi,rax','xor ebx,ebx','xor ebp,ebp','xor edi,edi','xor r12d,r12d','xor r13d,r13d','xor r14d,r14d','xor r15d,r15d',f'lea r10,[rsp+{BUFFER}]',
  'read_next:','cmp edi,4096','jae partial','movzx r11d,byte ptr [rsi]','inc rsi','inc edi','test r11b,r11b','je end_string',
  'cmp r11b,92','je slash','cmp r11b,34','je quote','mov edx,r14d']
 body += _flush('ordinary_slashes')
 body += ['xor r14d,r14d','test r13d,r13d','jne ordinary','cmp r11b,32','je delimiter','cmp r11b,9','jb ordinary','cmp r11b,13','jbe delimiter',
  'ordinary:','mov r15d,1']+_append('ordinary_append')+['jmp read_next',
  'slash:','inc r14d','mov r15d,1','jmp read_next',
  'quote:','mov r15d,1','mov edx,r14d','shr edx,1']
 body += _flush('quote_slashes')
 body += ['test r14d,1','mov r14d,0','jne literal_quote','test r13d,r13d','je toggle_quote','cmp edi,4096','jae partial','cmp byte ptr [rsi],34','jne toggle_quote','inc rsi','inc edi','jmp literal_quote',
  'toggle_quote:','xor r13d,1','jmp read_next','literal_quote:','mov r11d,34']+_append('quote_append')+['jmp read_next',
  'delimiter:','test r15d,r15d','je read_next','xor r9d,r9d','jmp classify',
  'end_string:','test r13d,r13d','jne invalid_complete','mov edx,r14d']
 body += _flush('end_slashes')
 body += ['test r15d,r15d','je complete','mov r9d,1','classify:','cmp r12d,8','jne not_flag',
  f'mov rax,{int.from_bytes(b"-scaling","little")}','cmp qword ptr [r10],rax','jne not_flag','mov ebp,1','xor ebx,ebx','jmp classified',
  'not_flag:','test ebp,ebp','je classified','xor ebp,ebp','xor ebx,ebx']
 for p in rows:
  token=p['scalingToken'].encode('ascii');assert len(token)in[5,6]
  label=f'not_value_{p["id"]}'
  body += [f'cmp r12d,{len(token)}',f'jne {label}',f'cmp dword ptr [r10],{int.from_bytes(token[:4],"little")}',f'jne {label}']
  body += ([f'cmp byte ptr [r10+4],{token[4]}']if len(token)==5 else[f'cmp word ptr [r10+4],{int.from_bytes(token[4:],"little")}'])
  body += [f'jne {label}',f'mov ebx,{p["id"]}','jmp classified',f'{label}:']
 body += ['classified:','test r9d,r9d','jne complete','xor r12d,r12d','xor r13d,r13d','xor r14d,r14d','xor r15d,r15d','jmp read_next',
  'invalid_complete:','xor ebx,ebx','complete:','lea edx,[rbx+1]','mov dword ptr [rip],edx','jmp finish',
  'partial:','invalid_host:','xor ebx,ebx','finish:',f'mov dword ptr [rsp+{RESULT}],ebx']
 for i in range(16):body.append(f'movdqu xmm{i},[rsp+{0x20+16*i}]')
 for n in GPRS:body.append(f'mov {n},qword ptr [rsp+{SLOTS[n]}]')
 body += [f'mov eax,dword ptr [rsp+{RESULT}]',f'add rsp,{FRAME}','ret']
 body_asm='\n'.join(body);parser=bytearray(pro_bytes+bytes(ks.asm(body_asm,addr=parse_base+len(pro_bytes))[0]))
 blob=cache+b'\xcc'*(0x40-len(cache))+parser;links=[]
 for i in md.disasm(blob,code_base):
  if i.mnemonic in['mov']and i.op_str in['eax, dword ptr [rip]','dword ptr [rip], edx']:
   at=i.address-code_base;assert i.disp_size==4;disp=cache_address-(i.address+i.size);assert -(1<<31)<=disp<(1<<31);struct.pack_into('<i',blob,at+i.disp_offset,disp);links.append(dict(instructionVA=i.address,targetVA=cache_address))
 assert len(links)==2 and len(blob)<=0x1000
 # Standard x64 unwind operations for the fixed parser frame/nonvolatile saves.
 unwind=[]
 for i in md.disasm(pro_bytes,parse_base):
  offset=i.address+i.size-parse_base
  if i.mnemonic=='sub'and i.op_str.startswith('rsp,'):unwind.append((offset,bytes([offset,1])+struct.pack('<H',FRAME//8)))
  elif i.mnemonic=='mov':
   name=i.op_str.rsplit(', ',1)[1];assert name in NONVOL;unwind.append((offset,bytes([offset,NONVOL[name]*16+4])+struct.pack('<H',SLOTS[name]//8)))
  elif i.mnemonic=='movdqu':
   n=int(i.op_str.rsplit('xmm',1)[1]);unwind.append((offset,bytes([offset,n*16+8])+struct.pack('<H',(0x20+16*n)//16)))
  else:raise AssertionError(i.mnemonic)
 codes=b''.join(x[1]for x in sorted(unwind,reverse=True));assert len(codes)%2==0
 ui=bytes([1,len(pro_bytes),len(codes)//2,0])+codes;ui+=bytes((-len(ui))%4)
 meta=dict(schema='cs-native-visible-pixels-decoder-v1',entryVA=code_base,parseVA=parse_base,codeBytes=len(blob),codeSha256=hashlib.sha256(blob).hexdigest(),cacheVA=cache_address,cacheBytes=4,
  contractSha256=hashlib.sha256(raw).hexdigest(),unwindFunctions=[dict(beginVA=parse_base,endVA=parse_base+len(parser),unwindHex=ui.hex(),prologueBytes=len(pro_bytes),frameBytes=FRAME)],links=links,
  abi=dict(output='EAX0..11',preserve='allotherGPR/all16XMM/RSP',flags='clobbered',entryStackAlignment=8,onlyExternalCall='validatedEmuIAT+a52f0 GetCommandLineA'),
  bounds=dict(commandBytes=4096,tokenBytes=32),cacheRule='ID+1 only after terminatingNUL; partial/invalidhost never cached',
  assembly=cache_asm+'\n; PARSER\n'+'\n'.join(pro)+'\n'+body_asm)
 return bytes(blob),meta
