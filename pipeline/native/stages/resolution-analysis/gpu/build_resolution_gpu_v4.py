from aa_override_proxy_v4 import *
import pefile,copy
sha=lambda b:hashlib.sha256(b).hexdigest()
SOURCE_SHA='bf07ec49033de438536c52a1529668c06407d4b00239175d77e2d576cca78931'
def main():
 path=HERE/'candidate-v3/VGPUDX12.dll';source=path.read_bytes();assert sha(source)==SOURCE_SHA
 pe=pefile.PE(data=source);manifest=copy.deepcopy(json.loads((path.parent/'manifest.json').read_text('utf8')))
 code,asm,meta=emit_aa()
 assert len(code)<0x800 and pe.get_data(AA_RVA,len(code))==bytes(len(code))
 unwind=bytes.fromhex(meta['unwindHex']);assert pe.get_data(AA_UW_RVA,len(unwind))==bytes(len(unwind))
 assert pe.get_data(AA_DIAG_RVA,64)==bytes(64)
 target=bytearray(source);changed=[]
 def put(rva,b,label):
  at=pe.get_offset_from_rva(rva);target[at:at+len(b)]=b;changed.append({'rva':hex(rva),'fileOffset':hex(at),'bytes':len(b),'purpose':label})
 put(AA_RVA,code,'ID11 AA-off initialization proxy');put(AA_UW_RVA,unwind,'frame-pointer Win64 unwind');put(AA_DIAG_RVA,b'CSAA'+struct.pack('<I',1)+bytes(56),'AA diagnostic initial record')
 before=pe.get_data(0x354b8,6);assert before.hex()=='894368894360'
 hook=b'\xe8'+struct.pack('<i',AA_RVA-0x354b8-5)+b'\x90';put(0x354b8,hook,'replace exactly two N stores with CALL+NOP')
 ed=pe.OPTIONAL_HEADER.DATA_DIRECTORY[3];oldpdata=pe.get_data(ed.VirtualAddress,ed.Size);rows=[struct.unpack_from('<III',oldpdata,k)for k in range(0,len(oldpdata),12)]
 newrow=(AA_RVA,AA_RVA+len(code),AA_UW_RVA);newrows=sorted(rows+[newrow]);assert len(set(newrows))==len(newrows)
 newpdata=b''.join(struct.pack('<III',*r)for r in newrows);assert ed.VirtualAddress+len(newpdata)<AA_RVA
 assert [r for r in newrows if r!=newrow]==rows
 put(ed.VirtualAddress,newpdata,'existing runtime entries exact; one sorted AA function entry added')
 sizeat=ed.get_file_offset()+4;struct.pack_into('<I',target,sizeat,len(newpdata))
 checksumat=pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum');p=pefile.PE(data=bytes(target));struct.pack_into('<I',target,checksumat,p.generate_checksum())
 after=pefile.PE(data=bytes(target));assert not after.get_warnings()and after.generate_checksum()==after.OPTIONAL_HEADER.CheckSum
 assert len(target)==len(source)and pe.OPTIONAL_HEADER.SizeOfImage==after.OPTIONAL_HEADER.SizeOfImage
 assert [s.__pack__()for s in pe.sections]==[s.__pack__()for s in after.sections]
 for i in range(16):
  if i!=3:assert pe.OPTIONAL_HEADER.DATA_DIRECTORY[i].__pack__()==after.OPTIONAL_HEADER.DATA_DIRECTORY[i].__pack__()
 for rva,size in [(0x73f000,1859),(0x740000,1688),(0x741000,352),(0x764000,243),(0x765000,0x300)]:assert pe.get_data(rva,size)==after.get_data(rva,size)
 for rva,n in [(0x4bd1,5),(0x4d60,5),(0x3f766,6),(0x54ec3,6)]:assert pe.get_data(rva,n)==after.get_data(rva,n)
 allowed=[(int(c['fileOffset'],16),int(c['fileOffset'],16)+c['bytes'])for c in changed]+[(sizeat,sizeat+4),(checksumat,checksumat+4)]
 diff=[i for i,(a,b)in enumerate(zip(source,target))if a!=b];assert all(any(a<=i<b for a,b in allowed)for i in diff)
 out=HERE/'candidate-v4';out.mkdir(exist_ok=False);(out/'VGPUDX12.dll').write_bytes(target)
 manifest.update(schema='resolution-gpu-candidate-v4',status='offline candidate; not installed; runtime unverified',sourceCandidate='candidate-v3 bf07 frozen',sourceSha256=SOURCE_SHA,targetSha256=sha(target),targetBytes=len(target),sourceManifestSha256=sha((path.parent/'manifest.json').read_bytes()),
  aaOverride=dict(meta,sha256=sha(code),callRva='0x354b8',callBefore=before.hex(),callAfter=hook.hex(),unwindRva=hex(AA_UW_RVA)),
  v3PixelCropDpiDecoderImportsAndPresetTableByteExact=True,existingRuntimeFunctionsByteExact=True,changedRanges=changed,changedByteCount=len(diff),allOtherBytesExact=True,installedOrGameRuntimeWrites=False,
  aaPolicy='Only tagged ID11 writes per-run shared options slot31=0. Other IDs and persistent launcher AA preference are unchanged. The4K menu label explicitly explains automatic AA-off.',
  profileBoundary='Standard owned launch profile with optional shader string setting121 absent; its separate AA re-enable path is not changed.',
  exceptionDirectory={'rva':hex(ed.VirtualAddress),'bytes':len(newpdata),'oldEntriesByteExact':True,'addedEntries':1})
 manifest['runtimeFunctions'].append(dict(meta,name='id11AAOffInitProxy',beginVA=IMAGE_BASE+AA_RVA,endVA=IMAGE_BASE+AA_RVA+len(code),unwindRva=AA_UW_RVA,frameBytes=AA_FRAME+8))
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n','utf8');(out/'aa-proxy.bin').write_bytes(code);(out/'aa-proxy.asm').write_text(asm+'\n','utf8')
 print(json.dumps({'candidate':str(out/'VGPUDX12.dll'),'sha256':sha(target),'bytes':len(target),'hook':hook.hex(),'proxyBytes':len(code),'changedByteCount':len(diff),'allOtherBytesExact':True},indent=2))
if __name__=='__main__':main()
