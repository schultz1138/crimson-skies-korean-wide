"""Separate offline extension: typed flat MenuMgr/MoviePlayer render scopes.

This leaves scoped_ui_kernel.py and its accepted service bytes unchanged.
The first V1 service bytes and all ten entry offsets are byte-identical for
the same placement. Three added services use the existing per-thread scope
stack with kind3. No game file or process is modified by this module.
"""
from pathlib import Path
import struct,json,hashlib
import scoped_ui_kernel as V1
from scoped_ui_kernel import REGS,SAVED,STATE_BYTES,PROJECTED
from keystone import Ks,KS_ARCH_X86,KS_MODE_64
from capstone import Cs,CS_ARCH_X86,CS_MODE_64

FLAT_TYPES={'flat_enter_movie':0x296c08,'flat_enter_menu':0x2c1d90}

def flat_enter(vtable):
 return [
  'cmp dword ptr [r10+12],0','jne scope_overflow_nested',
  'mov eax,[r10+8]','cmp eax,16','jae scope_overflow_first',
  'lea rdx,[r10+rax*8+0x40]','mov dword ptr [rdx],3',
  'mov ecx,[r10+4]','mov [rdx+4],ecx','inc dword ptr [r10+8]',
  f'mov ecx,[rbp+{SAVED["rcx"]}]','cmp ecx,0x10000','jb disable',
  'cmp ecx,0x7ffffffb','ja disable','lea rdx,[r15+rcx]',
  f'cmp dword ptr [rdx],{vtable}','jne disable',
  'mov dword ptr [r10+4],1','jmp done',
  'disable:','mov dword ptr [r10+4],0','jmp done',
  'scope_overflow_first:','mov eax,[r10+4]','mov [r10+32],eax',
  'scope_overflow_nested:','inc dword ptr [r10+12]',
  'mov dword ptr [r10+4],0','jmp done']

def emit(code_base,state_base,iat_address):
 old,old_entries,old_sources,old_links=V1.emit(code_base,state_base,iat_address)
 blob=bytearray(old);entries=dict(old_entries);sources=dict(old_sources);links=list(old_links)
 specs={name:flat_enter(vt)for name,vt in FLAT_TYPES.items()}
 specs['flat_exit']=V1.scope_exit(3)
 ks=Ks(KS_ARCH_X86,KS_MODE_64);md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True
 for name,body in specs.items():
  while len(blob)%16:blob.append(0xcc)
  at=code_base+len(blob);entries[name]=at
  assembly='\n'.join(V1.prologue()+body+V1.epilogue());sources[name]=assembly
  data=bytearray(ks.asm(assembly,addr=at)[0]);ins=list(md.disasm(data,at))
  assert sum(i.size for i in ins)==len(data)
  for i in ins:
   target=iat_address if i.mnemonic=='call'and i.op_str=='qword ptr [rip]'else state_base if i.mnemonic=='lea'and i.op_str=='r10, [rip]'else None
   if target is not None:
    assert i.disp_size==4;disp=target-(i.address+i.size);assert -(1<<31)<=disp<(1<<31)
    struct.pack_into('<i',data,i.address-at+i.disp_offset,disp)
    links.append(dict(service=name,instruction=hex(i.address),target=hex(target),displacement=disp))
  assert sum(x['service']==name for x in links)==2
  blob.extend(data)
 assert bytes(blob[:len(old)])==old
 assert all(entries[k]==v for k,v in old_entries.items())
 return bytes(blob),entries,sources,links

if __name__=='__main__':
 out=Path(__file__).resolve().parent
 code_base,state_base,iat=0x10000000,0x10020000,0x10030000
 data,entries,sources,links=emit(code_base,state_base,iat)
 old=V1.emit(code_base,state_base,iat)[0]
 (out/'scoped-ui-services-v2.bin').write_bytes(data)
 (out/'scoped-ui-services-v2.asm').write_text('\n\n'.join('; '+n+'\n'+a for n,a in sources.items())+'\n','utf8')
 report=dict(schema='scoped-ui-flat-render-scope-v2',codeBase=code_base,stateBase=state_base,
  iat=iat,stateBytes=STATE_BYTES,entries=entries,links=links,codeBytes=len(data),
  codeSha256=hashlib.sha256(data).hexdigest(),v1PrefixBytes=len(old),
  v1PrefixSha256=hashlib.sha256(old).hexdigest(),v1PrefixAndEntriesExact=True,
  flatTypes=FLAT_TYPES,scopeKind=3,mode=1,
  typeGuard='RCX.low32 guest offset10000..7ffffffb and exact firstDWORD vtable; R15 must be valid translated guest base',
  behavior='Save prior mode and pushkind3; validtypedobject enablesfixedmode1; invalidtype disablesinner scope; flat_exit restoresprior mode',
  overflow='Existing16-deep paired no-op overflow;8threadslots, ninth threadbypasses',
  coverage='Only existing3quadsubmission paths; MenuMgr/MoviePlayer source hooks not integrated or runtime tested',
  notIntegratedIntoDll=True,installedFilesModified=False)
 (out/'scoped-ui-services-v2.json').write_text(json.dumps(report,indent=2)+'\n','utf8')
 print(json.dumps({k:v for k,v in report.items()if k not in ['entries','links']},indent=2))
