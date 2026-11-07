"""Separate DPI-corrected offline candidate from frozen v1; original stays exact."""
from dpi_rect_proxy_v2 import *
import pefile
sha=lambda x:hashlib.sha256(x).hexdigest()
align=lambda n,a:(n+a-1)//a*a
SOURCE_SHA='95fb34b35326ec29d92b2dad202c7cdc4dea2787143afa464b48aa485f9fd09b'
IMPORT_RVA=RX_RVA+0x26000;INT_RVA=IMPORT_RVA+0x200;HINT_RVA=IMPORT_RVA+0x220;DLL_RVA=IMPORT_RVA+0x260
UW_RVA=RX_RVA+0x2400
def main():
 sourcepath=HERE/'candidate-v1/VGPUDX12.dll';source=sourcepath.read_bytes();assert sha(source)==SOURCE_SHA
 oldmanifest=json.loads((sourcepath.parent/'manifest.json').read_text('utf8'))
 code,asm,meta=emit_dpi()
 pe=pefile.PE(data=source);assert pe.FILE_HEADER.NumberOfSections==9 and pe.OPTIONAL_HEADER.SizeOfImage==0x768000
 assert not pe.OPTIONAL_HEADER.DATA_DIRECTORY[11].VirtualAddress and not pe.OPTIONAL_HEADER.DATA_DIRECTORY[11].Size
 rxold,rwold=pe.sections[-2:];assert rxold.VirtualAddress==RX_RVA and rwold.VirtualAddress==RW_RVA
 assert rxold.Misc_VirtualSize==RX_RESERVATION and rwold.Misc_VirtualSize==RW_RESERVATION
 rx=bytearray(pe.get_data(RX_RVA,RX_RESERVATION));rx+=bytes(RX_RESERVATION-len(rx))
 rw=bytearray(rwold.get_data());assert len(rw)==RW_RESERVATION
 assert rx[DPI_RVA-RX_RVA:DPI_RVA-RX_RVA+len(code)]==bytes(len(code))
 rx[DPI_RVA-RX_RVA:DPI_RVA-RX_RVA+len(code)]=code
 uw=bytes.fromhex(meta['unwindHex']);assert rx[UW_RVA-RX_RVA:UW_RVA-RX_RVA+len(uw)]==bytes(len(uw))
 rx[UW_RVA-RX_RVA:UW_RVA-RX_RVA+len(uw)]=uw
 ed=pe.OPTIONAL_HEADER.DATA_DIRECTORY[3];oldpdata=pe.get_data(ed.VirtualAddress,ed.Size);rows=[struct.unpack_from('<III',oldpdata,k)for k in range(0,len(oldpdata),12)]
 row=(DPI_RVA,DPI_RVA+len(code),UW_RVA);assert rows[-1][1]<DPI_RVA
 newpdata=oldpdata+struct.pack('<III',*row);pdataoff=ed.VirtualAddress-RX_RVA
 assert ed.VirtualAddress+len(newpdata)<DPI_RVA
 rx[pdataoff:pdataoff+len(newpdata)]=newpdata
 # Copy descriptors, preserving every old Name/INT/IAT RVA and old IAT directory.
 descriptors=[d.struct.__pack__()for d in pe.DIRECTORY_ENTRY_IMPORT]
 assert all(len(d)==20 for d in descriptors)
 original_directory=b''.join(descriptors)+bytes(20)
 assert pe.get_data(pe.OPTIONAL_HEADER.DATA_DIRECTORY[1].VirtualAddress,len(original_directory))==original_directory
 newdesc=struct.pack('<5I',INT_RVA,0,0,DLL_RVA,DPI_IAT_RVA)
 directory=b''.join(descriptors)+newdesc+bytes(20);assert len(directory)<0x200
 rx[IMPORT_RVA-RX_RVA:IMPORT_RVA-RX_RVA+len(directory)]=directory
 rx[INT_RVA-RX_RVA:INT_RVA-RX_RVA+16]=struct.pack('<QQ',HINT_RVA,0)
 hint=b'\0\0SetThreadDpiAwarenessContext\0';dll=b'USER32.dll\0'
 rx[HINT_RVA-RX_RVA:HINT_RVA-RX_RVA+len(hint)]=hint;rx[DLL_RVA-RX_RVA:DLL_RVA-RX_RVA+len(dll)]=dll
 assert rw[DPI_IAT_RVA-RW_RVA:DPI_IAT_RVA-RW_RVA+16]==bytes(16)
 rw[DPI_IAT_RVA-RW_RVA:DPI_IAT_RVA-RW_RVA+16]=struct.pack('<QQ',HINT_RVA,0)
 rxbytes=align(DLL_RVA-RX_RVA+len(dll),0x200);assert rxbytes<=RX_RESERVATION
 rxat=rxold.PointerToRawData;rwat=rxat+rxbytes
 target=bytearray(source[:rxat]+rx[:rxbytes]+rw)
 struct.pack_into('<I',target,rxold.get_field_absolute_offset('SizeOfRawData'),rxbytes)
 struct.pack_into('<I',target,rwold.get_field_absolute_offset('PointerToRawData'),rwat)
 struct.pack_into('<I',target,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfCode'),pe.OPTIONAL_HEADER.SizeOfCode+rxbytes-rxold.SizeOfRawData)
 struct.pack_into('<II',target,pe.OPTIONAL_HEADER.DATA_DIRECTORY[1].get_file_offset(),IMPORT_RVA,len(directory))
 struct.pack_into('<I',target,ed.get_file_offset()+4,len(newpdata))
 calls=[]
 for rva,expected in [(0x3f766,'ff153c9f3900'),(0x54ec3,'ff15df473800')]:
  at=pe.get_offset_from_rva(rva);assert source[at:at+6].hex()==expected
  after=b'\xe8'+struct.pack('<i',DPI_RVA-rva-5)+b'\x90';target[at:at+6]=after
  calls.append({'rva':hex(rva),'fileOffset':hex(at),'before':expected,'after':after.hex()})
 p=pefile.PE(data=bytes(target));checksum=p.generate_checksum();struct.pack_into('<I',target,pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),checksum)
 after=pefile.PE(data=bytes(target));assert not after.get_warnings()and after.generate_checksum()==after.OPTIONAL_HEADER.CheckSum
 assert after.OPTIONAL_HEADER.SizeOfImage==pe.OPTIONAL_HEADER.SizeOfImage
 for n in range(16):
  if n not in [1,3]:assert pe.OPTIONAL_HEADER.DATA_DIRECTORY[n].__pack__()==after.OPTIONAL_HEADER.DATA_DIRECTORY[n].__pack__()
 # All old pre-v1 sections survive exactly except the two6-byte importcalls.
 for old,new in zip(pe.sections[:-2],after.sections[:-2]):
  assert old.__pack__()==new.__pack__();a=bytearray(old.get_data());b=bytearray(new.get_data())
  for c in calls:
   off=int(c['fileOffset'],16)-old.PointerToRawData
   if 0<=off<len(a):b[off:off+6]=a[off:off+6]
  assert a==b
 for begin,size in [(RX_RVA,1741),(0x740000,1688),(0x741000,352)]:assert pe.get_data(begin,size)==after.get_data(begin,size)
 # No old symbol or IAT address changes, and the extra symbol has its own RW thunk.
 oldimps=[(d.dll,[(i.name,i.ordinal,i.address)for i in d.imports])for d in pe.DIRECTORY_ENTRY_IMPORT]
 newimps=[(d.dll,[(i.name,i.ordinal,i.address)for i in d.imports])for d in after.DIRECTORY_ENTRY_IMPORT]
 assert newimps[:-1]==oldimps and newimps[-1][0]==b'USER32.dll'and newimps[-1][1]==[(b'SetThreadDpiAwarenessContext',None,IMAGE_BASE+DPI_IAT_RVA)]
 assert after.get_data(ed.VirtualAddress,len(oldpdata))==oldpdata
 out=HERE/'candidate-v2';out.mkdir(exist_ok=False);(out/'VGPUDX12.dll').write_bytes(target)
 manifest={'schema':'resolution-gpu-candidate-v2','status':'offline-candidate;not-installed;runtime-unverified','sourceSha256':sha(source),'targetSha256':sha(target),'targetBytes':len(target),
  'sourceCandidate':'candidate-v1; frozen bytes not overwritten','v1ProtocolManifestSha256':sha((sourcepath.parent/'manifest.json').read_bytes()),'dpiProxy':dict(meta,sha256=sha(code),unwindRva=hex(UW_RVA)),
  'callSites':calls,'newImport':{'dll':'USER32.dll','symbol':'SetThreadDpiAwarenessContext','descriptorRva':hex(IMPORT_RVA+20*len(descriptors)),'intRva':hex(INT_RVA),'iatRva':hex(DPI_IAT_RVA),'hintNameRva':hex(HINT_RVA)},
  'copiedImportDirectory':{'rva':hex(IMPORT_RVA),'bytes':len(directory),'originalDescriptors':len(descriptors),'oldDescriptorPrefixByteExact':True,'oldSymbolIatAddressesPreserved':True,'originalIatDirectoryPreserved':True,'boundImportAbsent':True},
  'runtimeFunctions':oldmanifest['runtimeFunctions']+[dict(meta,name='dpiAwareGetClientRectProxy',beginVA=IMAGE_BASE+DPI_RVA,endVA=IMAGE_BASE+DPI_RVA+len(code),unwindRva=UW_RVA)],
  'exceptionDirectory':{'rva':hex(ed.VirtualAddress),'bytes':len(newpdata),'v1EntriesPreserved':True,'addedEntries':1},
  'sections':[{'name':s.Name.decode().rstrip('\0'),'rva':hex(s.VirtualAddress),'virtualBytes':s.Misc_VirtualSize,'rawOffset':hex(s.PointerToRawData),'rawBytes':s.SizeOfRawData,'flags':hex(s.Characteristics)}for s in after.sections[-2:]],
  'v1CropProxyDecoderPresetTableByteExact':True,'oldWorkingV4FillAndNMsaaCodePreserved':True,'checksumValid':True,'sizeOfImageUnchanged':True,
  'threadScope':'DPI context temporarily changes only on the calling thread around the original GetClientRect API, for valid new-preset tags; no display-mode change or window mutation.',
  'diagnosticRva':hex(DIAG_RVA+0x80),'limits':['Actual backbuffer1920x1080 still needs controlled game verification.','New system import must be available on targetWindows; currenthost API availability is source/runtime-proved.','A failed context-restore API is recorded in diagnostics rather than represented as success.'],'installedOrGameRuntimeWrites':False}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n','utf8');(out/'dpi-proxy.bin').write_bytes(code);(out/'dpi-proxy.asm').write_text(asm+'\n','utf8')
 print(json.dumps({k:manifest[k]for k in ['status','targetSha256','targetBytes','callSites','newImport','sections']},indent=2))
if __name__=='__main__':main()
