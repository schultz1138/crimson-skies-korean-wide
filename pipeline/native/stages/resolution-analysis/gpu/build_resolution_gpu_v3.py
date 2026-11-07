"""Offline, hash-pinned correction of the proxy's Present clip/canvas assumption."""
from final_call_proxy_v3 import *
import pefile,copy
sha=lambda b:hashlib.sha256(b).hexdigest()
SOURCE_SHA='398eb61b61b1aad36c6d4f5766af434bacd3b5f9ccef9808249c9af718b1f871'

def main():
 sourcepath=HERE/'candidate-v2/VGPUDX12.dll';source=sourcepath.read_bytes();assert sha(source)==SOURCE_SHA
 oldmanifest=json.loads((sourcepath.parent/'manifest.json').read_text('utf8'))
 pe=pefile.PE(data=source);assert pe.OPTIONAL_HEADER.SizeOfImage==0x768000
 code,asm,meta=emit();assert len(code)<0x1000
 # Independent machine-code QA is not a cached input.
 oldbytes=pe.get_data(RX_RVA,0x1000);assert oldbytes[1741:]==bytes(0x1000-1741)
 target=bytearray(source);at=pe.get_offset_from_rva(RX_RVA)
 target[at:at+0x1000]=code+bytes(0x1000-len(code))
 ed=pe.OPTIONAL_HEADER.DATA_DIRECTORY[3];pdata=pe.get_data(ed.VirtualAddress,ed.Size)
 matches=[k for k in range(0,len(pdata),12)if struct.unpack_from('<I',pdata,k)[0]==RX_RVA]
 assert len(matches)==1;k=matches[0];begin,end,unwind=struct.unpack_from('<III',pdata,k)
 assert end==RX_RVA+1741 and unwind==0x741300
 assert pe.get_data(unwind,8)==bytes.fromhex(meta['unwind'])
 endat=pe.get_offset_from_rva(ed.VirtualAddress+k+4)
 struct.pack_into('<I',target,endat,RX_RVA+len(code))
 checksumat=pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum')
 p=pefile.PE(data=bytes(target));struct.pack_into('<I',target,checksumat,p.generate_checksum())
 after=pefile.PE(data=bytes(target));assert not after.get_warnings()
 assert after.generate_checksum()==after.OPTIONAL_HEADER.CheckSum
 allowed=[(at,at+0x1000),(endat,endat+4),(checksumat,checksumat+4)]
 assert len(target)==len(source)
 changed=[i for i,(a,b)in enumerate(zip(source,target))if a!=b]
 assert all(any(lo<=i<hi for lo,hi in allowed)for i in changed)
 assert [s.__pack__()for s in pe.sections]==[s.__pack__()for s in after.sections]
 assert [d.__pack__()for d in pe.OPTIONAL_HEADER.DATA_DIRECTORY]==[d.__pack__()for d in after.OPTIONAL_HEADER.DATA_DIRECTORY]
 for rva,size in [(0x740000,1688),(0x741000,352),(0x764000,243),(0x765000,0x300),(0x767000,0x1000)]:
  assert pe.get_data(rva,size)==after.get_data(rva,size)
 out=HERE/'candidate-v3';out.mkdir(exist_ok=False);(out/'VGPUDX12.dll').write_bytes(target)
 manifest=copy.deepcopy(oldmanifest)
 manifest.update(schema='resolution-gpu-candidate-v3',status='offline candidate; not installed; runtime unverified',
  sourceCandidate='candidate-v2; exact398e frozen',sourceSha256=SOURCE_SHA,targetSha256=sha(target),targetBytes=len(target),
  sourceManifestSha256=sha((sourcepath.parent/'manifest.json').read_bytes()),
  correction={'rootCause':'The full logical canvas is640x480 while centered Present clipping can be638x480 at1,0. V2 incorrectly required the minimum clipped width to equal640.',
   'canvasGuard':'Runner+1c=640,+20=480',
   'clipGuard':'min(canvas,clip) must be638or640 by478or480, with2*origin+clip=canvas in both axes. Wider offsets/narrower/asymmetric rectangles preserve old UV.',
   'effectiveSize':'min canvas/clip bounds minus original Runner edge crops; used to reconstruct inverse texture scale from original UV.',
   'uvCenterFormula':'oldOffset+((minBound-selectedVisible/N)/2-edgeCropLeading)*inverseTextureSize',
   'observed1080pCase':'640x480 canvas;638x480 clip at1,0; edge crops1 each ->636x478 effective. Expected new UV=(1,.75,0,.125), density3, physical source1920x1440.',
   'proxyBytes':len(code),'proxySha256':sha(code),'proxyRva':hex(RX_RVA),'diagnosticLayoutUnchanged':True,'diagnosticVersion':2},
  changedFileRanges=[{'start':hex(lo),'endExclusive':hex(hi)}for lo,hi in allowed],changedByteCount=len(changed),
  sourceSnapshot='resolution-analysis/gpu/alpha1080-framebounds-32964.json',
  sectionsUnchanged=True,dataDirectoriesUnchanged=True,allOtherBytesExact=True,
  dpiProxyDecoderPresetTablesImportsAndRWDatesByteExact=True,installedOrGameRuntimeWrites=False)
 f=next(f for f in manifest['runtimeFunctions']if f['name']=='finalBlitCallProxy')
 assert f['beginVA']==IMAGE_BASE+RX_RVA
 f['endVA']=IMAGE_BASE+RX_RVA+len(code)
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n','utf8')
 (out/'proxy.bin').write_bytes(code);(out/'proxy.asm').write_text(asm+'\n','utf8')
 print(json.dumps({'candidate':str(out/'VGPUDX12.dll'),'targetSha256':sha(target),'targetBytes':len(target),'proxyBytes':len(code),'changedBytes':len(changed),'allOtherBytesExact':True},indent=2))
if __name__=='__main__':main()
