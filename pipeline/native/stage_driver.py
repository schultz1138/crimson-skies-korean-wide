"""Run one authored source stage in a fresh interpreter (no target execution)."""
from pathlib import Path
import sys,json,struct,hashlib,importlib.util
sys.dont_write_bytecode=True
def load(path):
 sys.path.insert(0,str(path.parent))
 spec=importlib.util.spec_from_file_location('current_build_stage',path)
 m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);return m
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf8')
def sha(b):return hashlib.sha256(b).hexdigest()
R=Path(sys.argv[1]).resolve();phase=sys.argv[2]
sys.path.insert(0,str(R))
NAME='xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll'
if phase=='header':
 import pefile
 src=R/'widescreen-analysis/camera/camera-wide-addon-v2';b=(src/NAME).read_bytes()
 assert sha(b)=='e2d877690d098daa70a79d8bea89f546f927d8f3f5643a5f82789305836d692a'
 p=pefile.PE(data=b);fixed=bytearray(b)
 assert p.sections[-2].Misc_VirtualSize==0x1f62
 struct.pack_into('<I',fixed,p.sections[-2].get_field_absolute_offset('Misc_VirtualSize'),0x10000)
 q=pefile.PE(data=fixed);struct.pack_into('<I',fixed,p.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),q.generate_checksum())
 assert sha(fixed)=='8c4679c79479b81b81e39d483ba3feebd694802e075af6139388e3e8f46564b1'
 out=R/'widescreen-analysis/camera/startup-loader-fix/equivalent-native-v2';out.mkdir(parents=True)
 (out/NAME).write_bytes(fixed);m=json.loads((src/'manifest.json').read_text('utf8'));m['patchedSha256']=sha(fixed);dump(out/'manifest.json',m)
elif phase.startswith('native-'):
 path=R/'resolution-analysis/aspect'/('overscan-candidate-v'+phase.split('-')[1])/'build_candidate.py'
 m=load(path);original,candidate,meta,asm=m.prepare();(path.parent/NAME).write_bytes(candidate);dump(path.parent/'manifest.json',meta)
 (path.parent/'native-services.asm').write_text('\n\n'.join('; '+n+'\n'+v for n,v in asm.items())+'\n','utf8')
 print(json.dumps({'phase':phase,'sha256':sha(candidate)}))
elif phase=='gpu-wide':
 import pefile
 mod=load(R/'widescreen-analysis/ui/final-present/final_present_leaf.py');leaf,asm,policy=mod.emit()
 b=(R/'widescreen-analysis/presentation/copies/VGPUDX12.dll').read_bytes();p=pefile.PE(data=b)
 assert sha(b)=='8306b4c06b100cae18f91dccd0468c2210cca11a02d928025de59bd827610247'
 assert len(leaf)==188 and p.FILE_HEADER.NumberOfSections==6
 raw=len(b);rva=0x73e000;size=(len(leaf)+511)&~511;n=p.sections[-1].get_file_offset()+40
 assert raw==0x5f1a00 and n==0x300 and b[n:n+40]==bytes(40)
 target=bytearray(b+bytes(size));target[raw:raw+len(leaf)]=leaf
 struct.pack_into('<8sIIIIIIHHI',target,n,b'.wide16\0',len(leaf),rva,size,raw,0,0,0,0,0x60000020)
 struct.pack_into('<H',target,p.FILE_HEADER.get_field_absolute_offset('NumberOfSections'),7)
 struct.pack_into('<I',target,p.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'),0x73f000)
 struct.pack_into('<I',target,p.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfCode'),p.OPTIONAL_HEADER.SizeOfCode+size)
 at=p.get_offset_from_rva(0x4bd1);assert b[at:at+5].hex()=='e81a640600'
 target[at:at+5]=b'\xe8'+struct.pack('<i',rva-0x4bd1-5)
 q=pefile.PE(data=target);struct.pack_into('<I',target,p.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),q.generate_checksum())
 assert sha(target)=='dc36c8071002346dbf2b412a7705cad32a462f7b71077d557fa6aa97566ffb0e'
 out=R/'widescreen-analysis/presentation/vgpu-present-candidate-v1';out.mkdir();(out/'VGPUDX12.dll').write_bytes(target)
 dump(out/'manifest.json',{'targetSha256':sha(target),'policy':policy})
elif phase.startswith('gpu-'):
 version=phase.split('-')[1]
 path=R/('resolution-analysis/aspect/4k-aa-source-v1/build_gpu_v5.py'if version=='5'else f'resolution-analysis/gpu/build_resolution_gpu_v{version}.py')
 load(path).main()
else:raise ValueError(phase)
