"""Offline V2 extension with the separately pinned primitive6 Bink quad.

Preserves the V1 ten-service and V2 thirteen-service code prefixes and entry
offsets. The native integration owner must hook only guest71f48/71f4d for
the new fourth pair; this is not a general primitive6 render hook.
"""
from pathlib import Path
import struct,json,hashlib
import scoped_ui_kernel_v2 as V2
from scoped_ui_kernel_v2 import V1,REGS,SAVED,STATE_BYTES,PROJECTED,FLAT_TYPES
from keystone import Ks,KS_ARCH_X86,KS_MODE_64
from capstone import Cs,CS_ARCH_X86,CS_MODE_64

def movie_quad_pre():
 body=V1.quad_pre(4,0x10,True)
 old='cmp dword ptr [r15+r14],7'
 assert body.count(old)==1
 body[body.index(old)]='cmp dword ptr [r15+r14],6'
 return body

def emit(code_base,state_base,iat_address):
 prefix,old_entries,old_sources,old_links=V2.emit(code_base,state_base,iat_address)
 blob=bytearray(prefix);entries=dict(old_entries);sources=dict(old_sources);links=list(old_links)
 specs={'quad_pre_4':movie_quad_pre(),'quad_post_4':V1.quad_post(4)}
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
 assert bytes(blob[:len(prefix)])==prefix
 assert all(entries[k]==v for k,v in old_entries.items())
 return bytes(blob),entries,sources,links

if __name__=='__main__':
 out=Path(__file__).resolve().parent
 code_base,state_base,iat=0x10000000,0x10020000,0x10030000
 data,entries,sources,links=emit(code_base,state_base,iat)
 old=V2.emit(code_base,state_base,iat)[0]
 (out/'scoped-ui-services-v2-movie.bin').write_bytes(data)
 (out/'scoped-ui-services-v2-movie.asm').write_text('\n\n'.join('; '+n+'\n'+a for n,a in sources.items())+'\n','utf8')
 report=dict(schema='scoped-ui-flat-render-with-Bink-quad-v2',codeBase=code_base,stateBase=state_base,
  iat=iat,stateBytes=STATE_BYTES,entries=entries,links=links,codeBytes=len(data),
  codeSha256=hashlib.sha256(data).hexdigest(),v2PrefixBytes=len(old),
  v2PrefixSha256=hashlib.sha256(old).hexdigest(),v2PrefixAndEntriesExact=True,
  movieSite=dict(guestPre='0x71f48',guestPost='0x71f4d',nativePreRva='0x22178d',nativePostRva='0x22179f',
   primitive=6,count=4,stride=28,vertexPointer='guestESP+0x10',services=['quad_pre_4','quad_post_4']),
  behavior='Existing per-thread bounded quad LIFO: transform only4X values under active modes1/2, restoreexact originalfloatbits after synchronouscopy',
  coverage='Four pinned submission paths and typedflat scopes only; integration/nativeclear/actualMovieRender not tested',
  notIntegratedIntoDll=True,installedFilesModified=False)
 (out/'scoped-ui-services-v2-movie.json').write_text(json.dumps(report,indent=2)+'\n','utf8')
 print(json.dumps({k:v for k,v in report.items()if k not in ['entries','links']},indent=2))
