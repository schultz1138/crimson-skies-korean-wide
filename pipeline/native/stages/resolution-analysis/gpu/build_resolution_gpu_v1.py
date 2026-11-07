"""Build offline GPU candidate from pinned working V4; no installed access."""
from final_call_proxy_v1 import *
import importlib.util
import pefile
from capstone import CS_GRP_CALL,CS_GRP_JUMP
from capstone.x86 import X86_OP_IMM
sha=lambda b:hashlib.sha256(b).hexdigest()
align=lambda v,a:(v+a-1)//a*a
SOURCE_SHA='dc36c8071002346dbf2b412a7705cad32a462f7b71077d557fa6aa97566ffb0e'
DECODER_SOURCE_SHA='613075eaf969753f664308cd1651ab5bf14265b4e519455858735e8253d24dc4'
CONTRACT_SHA='d6bd4f1a2a339593d76db8cd25452cc85f4364e7993ff16eb66770e36de72821'
DECODER_RVA=RX_RVA+0x1000;UNWIND_RVA=RX_RVA+0x2300;PDATA_RVA=RX_RVA+0x3000
def main():
 original=ROOT/'widescreen-analysis/presentation/vgpu-present-candidate-v1/VGPUDX12.dll';source=original.read_bytes();assert sha(source)==SOURCE_SHA
 contract_raw=(ROOT/'resolution-analysis/shared/preset-contract-v1.json').read_bytes();assert sha(contract_raw)==CONTRACT_SHA
 contract=json.loads(contract_raw)
 decoder_path=ROOT/'resolution-analysis/shared/preset_decoder.py'
 spec=importlib.util.spec_from_file_location('gpu_preset_decoder_frozen',decoder_path);decoder_mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder_mod)
 decoder,dm=decoder_mod.emit(IMAGE_BASE+DECODER_RVA,IMAGE_BASE+DECODER_CACHE_RVA)
 assert dm['contractSha256']==CONTRACT_SHA and len(decoder)<=0x1000
 proxy,asm,pm=emit(IMAGE_BASE+RX_RVA,IMAGE_BASE+DECODER_RVA,IMAGE_BASE+TABLE_RVA,IMAGE_BASE+DIAG_RVA,IMAGE_BASE+0x3e58)
 assert len(proxy)<0x1000
 # Machine-code tests are independently executed by release QA.
 # Both emitters are entirely image-relative under ASLR.
 delta=0x15000000
 assert decoder_mod.emit(IMAGE_BASE+DECODER_RVA+delta,IMAGE_BASE+DECODER_CACHE_RVA+delta)[0]==decoder
 assert emit(IMAGE_BASE+RX_RVA+delta,IMAGE_BASE+DECODER_RVA+delta,IMAGE_BASE+TABLE_RVA+delta,IMAGE_BASE+DIAG_RVA+delta,IMAGE_BASE+0x3e58+delta)[0]==proxy
 pe=pefile.PE(data=source);assert pe.FILE_HEADER.Machine==0x8664 and pe.FILE_HEADER.NumberOfSections==7 and pe.OPTIONAL_HEADER.SizeOfImage==RX_RVA
 assert pe.OPTIONAL_HEADER.ImageBase==IMAGE_BASE and pe.OPTIONAL_HEADER.SizeOfHeaders==0x400
 assert not pe.OPTIONAL_HEADER.DATA_DIRECTORY[4].Size and pe.get_overlay_data_start_offset()is None
 descriptor_at=pe.sections[-1].get_file_offset()+40;assert descriptor_at==0x328 and descriptor_at+80<=0x400 and source[descriptor_at:descriptor_at+80]==bytes(80)
 call_rva=0x4d60;call_at=pe.get_offset_from_rva(call_rva);assert source[call_at:call_at+5]==bytes.fromhex('e8f3f0ffff')
 ed=pe.OPTIONAL_HEADER.DATA_DIRECTORY[3];old_pdata=pe.get_data(ed.VirtualAddress,ed.Size);assert len(old_pdata)%12==0
 old_rows=[struct.unpack_from('<III',old_pdata,i)for i in range(0,len(old_pdata),12)]
 assert old_rows==sorted(old_rows)
 functions=[{'beginVA':IMAGE_BASE+RX_RVA,'endVA':IMAGE_BASE+RX_RVA+len(proxy),'unwindHex':pm['unwind'],'name':'finalBlitCallProxy'}]
 functions.extend(dict(f,name='sharedPresetParser')for f in dm['unwindFunctions'])
 rx=bytearray(RX_RESERVATION);rx[:len(proxy)]=proxy;rx[0x1000:0x1000+len(decoder)]=decoder;tb=table_bytes(contract);rx[0x2000:0x2000+len(tb)]=tb
 new_rows=[];unwind_at=UNWIND_RVA
 for f in functions:
  begin,end=f['beginVA']-IMAGE_BASE,f['endVA']-IMAGE_BASE;uw=bytes.fromhex(f['unwindHex'])
  assert RX_RVA<=begin<end<TABLE_RVA and uw[0]&7==1 and not uw[0]&0xf8
  assert unwind_at+len(uw)<PDATA_RVA
  rx[unwind_at-RX_RVA:unwind_at-RX_RVA+len(uw)]=uw
  new_rows.append((begin,end,unwind_at));f['unwindRva']=unwind_at;unwind_at=align(unwind_at+len(uw),4)
 rows=sorted(old_rows+new_rows);assert len(set(a for a,b,c in rows))==len(rows)
 for left,right in zip(rows,rows[1:]):assert left[1]<=right[0],(left,right)
 pdata=b''.join(struct.pack('<III',*row)for row in rows);assert pdata.startswith(old_pdata)
 pdata_end=PDATA_RVA-RX_RVA+len(pdata);assert pdata_end<=RX_RESERVATION
 rx[PDATA_RVA-RX_RVA:pdata_end]=pdata
 rxraw=align(pdata_end,pe.OPTIONAL_HEADER.FileAlignment);rx_at=align(len(source),0x200);rw_at=rx_at+rxraw
 assert rxraw<=RX_RESERVATION and RW_RVA==RX_RVA+RX_RESERVATION
 target=bytearray(source+bytes(rw_at+RW_RESERVATION-len(source)));target[rx_at:rx_at+rxraw]=rx[:rxraw]
 diag=struct.pack('<4sI',b'CSRG',2)+bytes(RW_RESERVATION-8);target[rw_at:rw_at+RW_RESERVATION]=diag
 for pos,name,vs,va,rs,raw_at,flags in [(descriptor_at,b'.resgpu\0',RX_RESERVATION,RX_RVA,rxraw,rx_at,0x60000020),(descriptor_at+40,b'.resrw\0\0',RW_RESERVATION,RW_RVA,RW_RESERVATION,rw_at,0xc0000040)]:
  struct.pack_into('<8sIIIIIIHHI',target,pos,name,vs,va,rs,raw_at,0,0,0,0,flags)
 struct.pack_into('<H',target,pe.FILE_HEADER.get_field_absolute_offset('NumberOfSections'),9)
 struct.pack_into('<I',target,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'),RW_RVA+RW_RESERVATION)
 struct.pack_into('<I',target,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfCode'),pe.OPTIONAL_HEADER.SizeOfCode+rxraw)
 struct.pack_into('<I',target,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfInitializedData'),pe.OPTIONAL_HEADER.SizeOfInitializedData+RW_RESERVATION)
 struct.pack_into('<II',target,ed.get_file_offset(),PDATA_RVA,len(pdata))
 target[call_at:call_at+5]=b'\xe8'+struct.pack('<i',RX_RVA-call_rva-5)
 rebuilt=pefile.PE(data=bytes(target));struct.pack_into('<I',target,pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),rebuilt.generate_checksum())
 allowed=set(range(descriptor_at,descriptor_at+80))|set(range(call_at,call_at+5))|set(range(ed.get_file_offset(),ed.get_file_offset()+8))
 for obj,field,size in [(pe.FILE_HEADER,'NumberOfSections',2),(pe.OPTIONAL_HEADER,'SizeOfImage',4),(pe.OPTIONAL_HEADER,'SizeOfCode',4),(pe.OPTIONAL_HEADER,'SizeOfInitializedData',4),(pe.OPTIONAL_HEADER,'CheckSum',4)]:
  x=obj.get_field_absolute_offset(field);allowed.update(range(x,x+size))
 changed=[i for i in range(len(source))if target[i]!=source[i]];assert set(changed)<=allowed
 after=pefile.PE(data=bytes(target));assert after.generate_checksum()==after.OPTIONAL_HEADER.CheckSum and not after.get_warnings()
 for n in range(16):
  if n!=3:assert pe.OPTIONAL_HEADER.DATA_DIRECTORY[n].__pack__()==after.OPTIONAL_HEADER.DATA_DIRECTORY[n].__pack__()
 for old,new in zip(pe.sections,after.sections):
  assert old.__pack__()==new.__pack__()
  lo,hi=old.PointerToRawData,old.PointerToRawData+old.SizeOfRawData
  assert {i for i in changed if lo<=i<hi}<=set(range(call_at,call_at+5))
 assert after.get_data(0x4bd1,5)==pe.get_data(0x4bd1,5)and after.get_data(0x73e000,188)==pe.get_data(0x73e000,188)
 # Independent decode validates only permitted private stack/volatile writes.
 md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True;ins=list(md.disasm(proxy,IMAGE_BASE+RX_RVA));assert sum(x.size for x in ins)==len(proxy)
 for i in ins:
  _,writes=i.regs_access();names={i.reg_name(x)for x in writes}
  assert not names&{'rbx','ebx','rbp','ebp','rsi','esi','rdi','edi','r12','r12d','r13','r13d','r14','r14d','r15','r15d'}
  assert not names&{f'xmm{x}'for x in range(6,16)}
  if i.group(CS_GRP_CALL):assert i.operands[0].type==X86_OP_IMM and i.operands[0].imm in [IMAGE_BASE+DECODER_RVA,IMAGE_BASE+0x3e58]
 out=HERE/'candidate-v1';out.mkdir(exist_ok=False);(out/'VGPUDX12.dll').write_bytes(target)
 manifest={'schema':'resolution-gpu-candidate-v1','status':'offline-candidate;not-installed;runtime-unverified','sourceSha256':sha(source),'targetSha256':sha(target),'targetBytes':len(target),
  'contractSha256':CONTRACT_SHA,'decoderSourceSha256':DECODER_SOURCE_SHA,'callsiteRva':hex(call_rva),'callsiteFileOffset':hex(call_at),'before':source[call_at:call_at+5].hex(),'after':bytes(target[call_at:call_at+5]).hex(),
  'proxy':dict(pm,sha256=sha(proxy)),'decoder':{k:v for k,v in dm.items()if k!='assembly'},'runtimeFunctions':functions,
  'sections':[{'name':s.Name.decode().rstrip('\0'),'rva':hex(s.VirtualAddress),'virtualBytes':s.Misc_VirtualSize,'rawOffset':hex(s.PointerToRawData),'rawBytes':s.SizeOfRawData,'flags':hex(s.Characteristics)}for s in after.sections[-2:]],
  'exceptionDirectory':{'rva':hex(PDATA_RVA),'bytes':len(pdata),'originalEntries':len(old_rows),'addedEntries':len(new_rows),'originalEntryBytesPreserved':True},
  'diagRva':hex(DIAG_RVA),'decoderCacheRva':hex(DECODER_CACHE_RVA),'oldV4FillCallAndLeafPreserved':True,'allIntegerScalingMsaaAllocationCodePreserved':True,
  'changedOriginalFileByteCount':len(changed),'changedOriginalOffsets':[hex(i)for i in changed],'allOtherOriginalBytesPreserved':True,'checksumValid':True,
  'sourceDensityPolicy':'Reconstruct UV from original scale/offset and logical Runner frame/crop; require full640x480 and actual physical density at least integerN allowing4 F32 ULP roundoff. Accept valid MSAA sample counts; preserve padding/frame origins.',
  'unwindPolicy':'Original.pdata entries copied exactly into new sorted directory plus proxy and shared parser; explicit Win64 metadata for both nonleaf frames. Cache entry remains a no-frame leaf.',
  'diagnostics':'Best-effort last-call fields and atomic callcounter in privateRW; status must be checked before treating data as accepted crop.',
  'limitations':['Actual source-view lifetime/pointer validity follows the original game resource contract.','Real physical backbuffer/client DPI and user playback still require validation.','N6/4K memory and performance remain unverified.'],'installedOrRuntimeWrites':False}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n','utf8');(out/'proxy.asm').write_text(asm+'\n','utf8');(out/'proxy.bin').write_bytes(proxy)
 (out/'decoder.bin').write_bytes(decoder);(out/'extended-pdata.bin').write_bytes(pdata)
 print(json.dumps({k:manifest[k]for k in ['status','targetSha256','targetBytes','after','sections','exceptionDirectory','diagRva','decoderCacheRva']},indent=2))
if __name__=='__main__':main()
