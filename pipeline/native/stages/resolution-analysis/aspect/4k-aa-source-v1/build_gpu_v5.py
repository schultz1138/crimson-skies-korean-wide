"""Build a separate offline GPUv5; frozen v4 is read-only."""
from shadow_heap_budget_v5 import *
import copy,pefile
def main():
 path=ROOT/'resolution-analysis/gpu/candidate-v4/VGPUDX12.dll';source=path.read_bytes();sha=lambda x:hashlib.sha256(x).hexdigest()
 assert sha(source)=='f264321eb528ca4e5edd1d9e2fa3ed38e3dd9ecbec35c703719c83408bcffd9c'
 pe=pefile.PE(data=source);target=bytearray(source);manifest=copy.deepcopy(json.loads((path.parent/'manifest.json').read_text('utf8')));changes=[]
 def put(rva,b,label):
  at=pe.get_offset_from_rva(rva);target[at:at+len(b)]=b;changes.append(dict(rva=hex(rva),fileOffset=hex(at),bytes=len(b),purpose=label))
 oldaa,_,_=emit_aa();newaa,aameta=aa_preserved();assert pe.get_data(0x763800,len(oldaa))==oldaa
 rva=int(aameta['branchRva'],16);put(rva,bytes.fromhex(aameta['after'])[:1],'AA validated unchanged path for ID11 too; one-byte75->EB')
 code,asm,meta=emit();assert pe.get_data(ENTRY_RVA,0x400)==bytes(0x400)
 assert pe.get_data(UW_RVA,12)==bytes(12)and pe.get_data(DIAG_RVA,64)==bytes(64)
 put(ENTRY_RVA,code,'pool10-only ID11 AA capacity helper');put(UW_RVA,bytes.fromhex(meta['unwindHex']),'Win64 fixed56B frame unwind');put(DIAG_RVA,b'CSHB'+struct.pack('<I',1)+bytes(56),'private pool10 budget diagnostic')
 assert pe.get_data(0x43d95,6).hex()=='4805ffff0000'
 hook=b'\xe8'+struct.pack('<i',ENTRY_RVA-0x43d95-5)+b'\x90';put(0x43d95,hook,'whole6B ADD replaced by CALL+NOP; helper replaysADD')
 ed=pe.OPTIONAL_HEADER.DATA_DIRECTORY[3];rows=[struct.unpack_from('<III',pe.get_data(ed.VirtualAddress,ed.Size),k)for k in range(0,ed.Size,12)]
 row=(ENTRY_RVA,ENTRY_RVA+len(code),UW_RVA);newrows=sorted(rows+[row]);assert len(set(newrows))==len(newrows)
 pdata=b''.join(struct.pack('<III',*r)for r in newrows);assert pe.get_data(ed.VirtualAddress+ed.Size,12)==bytes(12)
 put(ed.VirtualAddress,pdata,'old runtime functions exact; one new budget helper entry')
 sizeat=ed.get_file_offset()+4;struct.pack_into('<I',target,sizeat,len(pdata))
 checksumat=pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum');p=pefile.PE(data=bytes(target));struct.pack_into('<I',target,checksumat,p.generate_checksum())
 after=pefile.PE(data=bytes(target));assert not after.get_warnings()and after.generate_checksum()==after.OPTIONAL_HEADER.CheckSum
 assert len(target)==len(source)and after.OPTIONAL_HEADER.SizeOfImage==pe.OPTIONAL_HEADER.SizeOfImage
 assert [s.__pack__()for s in pe.sections]==[s.__pack__()for s in after.sections]
 for i in range(16):
  if i!=3:assert pe.OPTIONAL_HEADER.DATA_DIRECTORY[i].__pack__()==after.OPTIONAL_HEADER.DATA_DIRECTORY[i].__pack__()
 allowed=[(int(c['fileOffset'],16),int(c['fileOffset'],16)+c['bytes'])for c in changes]+[(sizeat,sizeat+4),(checksumat,checksumat+4)]
 diff=[i for i,(a,b)in enumerate(zip(source,target))if a!=b];assert all(any(a<=i<b for a,b in allowed)for i in diff)
 out=ROOT/'resolution-analysis/gpu/candidate-v5-final';out.mkdir(exist_ok=False);(out/'VGPUDX12.dll').write_bytes(target)
 manifest.update(schema='resolution-gpu-candidate-v5',status='offline prototype; not installed; runtime unverified',sourceSha256=sha(source),sourceCandidate='frozen candidate-v4 f264',targetSha256=sha(target),targetBytes=len(target),sourceManifestSha256=sha((path.parent/'manifest.json').read_bytes()),
   aaPolicy='All presets retain user-selected per-run AA. Only ID11+N6+AA1/2 pool10 budget changes384→1536MiB.',aaPreservedBranch=aameta,shadowHeapBudget=dict(meta,sha256=sha(code),callBefore='4805ffff0000',callAfter=hook.hex()),
   changedRanges=changes,changedByteCount=len(diff),allOtherBytesExact=True,imageFileAndSectionsUnchanged=True,installedOrGameRuntimeWrites=False,
   experimentLimit='This is a measured pool10 exhaustion repair prototype. It does not guarantee enough budget for everymission and may raise device memory pressure; parent controls testing/recovery.',
   exceptionDirectory={'rva':hex(ed.VirtualAddress),'bytes':len(pdata),'oldEntriesByteExact':True,'addedEntries':1})
 manifest['runtimeFunctions'].append(dict(meta,name='id11AAShadowHeapBudget',beginVA=IMAGE_BASE+ENTRY_RVA,endVA=IMAGE_BASE+ENTRY_RVA+len(code)))
 manifest['aaOverride'].update(sha256=sha(newaa),policy=aameta['policy'],oldId11AAOffActionUnreachable=True,branchChange=aameta)
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n','utf8');(out/'shadow-budget.asm').write_text(asm+'\n','utf8');(out/'shadow-budget.bin').write_bytes(code)
 print(json.dumps(dict(candidate=str(out/'VGPUDX12.dll'),sha256=sha(target),helperBytes=len(code),changedByteCount=len(diff),manifestSha256=sha((out/'manifest.json').read_bytes())),indent=2))
if __name__=='__main__':main()
