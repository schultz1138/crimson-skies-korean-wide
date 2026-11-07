"""Rebuild authored Native/GPU/Menu targets from an owned, exact stock Content.

No code from the input DLLs is executed. The fresh work tree contains all
generated intermediate images, maps, assembly and logs; it is never an input.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
DLL='xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll'
INPUTS={DLL:'d49d36bd5e6beb6bcc2198dd92d1d3c9116fa0b6584b0291e0a581e28faed86d',
 'VGPUDX12.dll':'8306b4c06b100cae18f91dccd0468c2210cca11a02d928025de59bd827610247',
 'EmuMenu/Assets/TitleMenuData.json':'82cf420a22fd50455e04b92879e7c3137ef085ab9a2c373640b11897dfd12096'}
TARGETS={DLL:'45c2c716da6c01f0937ce922dbfe2de89a3a9dfb163578757cfc5c5cc7e65f44',
 'VGPUDX12.dll':'f4d7784a007919a1e397405340855ac539c76f4abccfc6ecf8edebb2ed9835aa',
 'EmuMenu/Assets/TitleMenuData.json':'200b609e7b279c25814fb42ed1dd1cdcd6f3203b670dc3b05749a6ee26686265'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--input-content',required=True,type=Path);ap.add_argument('--output-content',required=True,type=Path)
 ap.add_argument('--work-dir',required=True,type=Path)
 ap.add_argument('--assets-source',type=Path,default=HERE.parent/'assets',help='Public assets source directory containing package_io.py and localization/')
 ap.add_argument('--original-xbe',type=Path,help='Optional exact stock XBE already extracted by the public assets stage')
 ap.add_argument('--captions',type=Path,help='Shared authored native_captions.json (defaults to assets/localization/)')
 a=ap.parse_args();src=a.input_content.resolve();out=a.output_content.resolve();work=a.work_dir.resolve();assets=a.assets_source.resolve()
 for x in [out,work]:
  if x==src or x.is_relative_to(src)or src.is_relative_to(x)or x==HERE or HERE.is_relative_to(x)or x.is_relative_to(HERE):raise ValueError('Input, public source and output/work trees must be disjoint')
 if out==work or out.is_relative_to(work)or work.is_relative_to(out):raise ValueError('Output and work trees must be disjoint')
 if work.exists()and any(work.iterdir()):raise ValueError('Work directory must be new or empty (never reuse cached intermediates)')
 if any((out/f).exists()for f in TARGETS):raise ValueError('Native/GPU/Menu outputs must not already exist; existing Data0000/5 outputs are preserved')
 for f,pin in INPUTS.items():
  if digest(src/f)!=pin:raise ValueError('Unexpected stock source: '+f)
 if a.original_xbe:xbe=a.original_xbe.resolve().read_bytes()
 else:
  sys.path.insert(0,str(assets));from package_io import extract_owned_file
  xbe=extract_owned_file(src,'default.xbe')
 assert hashlib.sha256(xbe).hexdigest()=='43048e59b75065e82c032859ac700c75cc2bd124f6ae817a7a2d2ca3e252aad2'
 # Explicit extended paths keep the historical descriptive stage directories
 # portable on Windows systems that do not enable global long-path policy.
 if os.name=='nt':
  work=Path('\\\\?\\'+str(work)) if not str(work).startswith('\\\\?\\')else work
  out=Path('\\\\?\\'+str(out)) if not str(out).startswith('\\\\?\\')else out
 tree=work/'tree';shutil.copytree(HERE/'stages',tree);(work/'logs').mkdir()
 (tree/'native-host-v1').mkdir();shutil.copyfile(src/DLL,tree/'native-host-v1/original.xefu.dll')
 (tree/'work/default.original.xbe').write_bytes(xbe)
 p=tree/'widescreen-analysis/presentation/copies';p.mkdir(parents=True);shutil.copyfile(src/'VGPUDX12.dll',p/'VGPUDX12.dll')
 env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONIOENCODING']='utf-8';env['CS_NATIVE_CAPTIONS']=str(a.captions.resolve()if a.captions else assets/'localization/native_captions.json')
 stages=[]
 def run(name,args,output,pin):
  r=subprocess.run([sys.executable,*map(str,args)],cwd=tree,env=env,capture_output=True,text=True,encoding='utf8')
  (work/'logs'/f'{name}.log').write_text(r.stdout+r.stderr,'utf8')
  if r.returncode:raise RuntimeError(f'{name} failed; see {work / "logs" / (name+".log")}')
  got=digest(output)
  if got!=pin:raise ValueError(f'{name} output mismatch: {got} != {pin}')
  stages.append({'stage':name,'sha256':got,'bytes':output.stat().st_size});print(name,got,flush=True)
 # First generate authored guest routines; its JSON is an intermediate map,
 # not a shipped/cached byte patch or the final game image.
 r=subprocess.run([sys.executable,str(tree/'build_radio_scattered.py'),'--runtime'],cwd=tree,env=env,capture_output=True,text=True,encoding='utf8')
 (work/'logs/radio-source.log').write_text(r.stdout+r.stderr,'utf8')
 if r.returncode:raise RuntimeError('radio source failed; see work/logs/radio-source.log')
 run('radio-lift',[tree/'build_host_radio_wrap.py'],tree/'native-host-v2'/DLL,'f4432e0adb3a97a027cdc00fef98a20df2f0b784b467578a7b4550119e7f0cd3')
 run('captions',[tree/'build_caption_stage.py'],tree/'native-host-v5'/DLL,'cfb9d6558ff0035494af8866d72cccb0e369d2c6a1549825a699f7249154c650')
 run('typed-ui',[tree/'widescreen-analysis/camera/build_ui_addon_v2.py','--build'],tree/'widescreen-analysis/camera/camera-wide-addon-v2'/DLL,'e2d877690d098daa70a79d8bea89f546f927d8f3f5643a5f82789305836d692a')
 driver=HERE/'stage_driver.py'
 run('section-layout',[driver,tree,'header'],tree/'widescreen-analysis/camera/startup-loader-fix/equivalent-native-v2'/DLL,'8c4679c79479b81b81e39d483ba3feebd694802e075af6139388e3e8f46564b1')
 for v,pin in [(1,'e4d39a2d29f39ff0ccc15a5744590f0902d371dfc05ea268f0e883c5b6bf7ab9'),(2,'84002944db6c9bdde3fe53db49adebf8d6bc9da8922e3e550e9acf190425cbc5'),(4,'57be47f3e8b1c1f757880c68df67a7fa586445993e2f065aaefd42e7e15e30c1'),(5,'cd85b37e6df2c3a0c8a8efa3da916892171f540a1110fbeb85066daf3c59ed07'),(7,TARGETS[DLL])]:
  run('native-'+str(v),[driver,tree,'native-'+str(v)],tree/f'resolution-analysis/aspect/overscan-candidate-v{v}'/DLL,pin)
 run('gpu-wide',[driver,tree,'gpu-wide'],tree/'widescreen-analysis/presentation/vgpu-present-candidate-v1/VGPUDX12.dll','dc36c8071002346dbf2b412a7705cad32a462f7b71077d557fa6aa97566ffb0e')
 for v,pin in [(1,'95fb34b35326ec29d92b2dad202c7cdc4dea2787143afa464b48aa485f9fd09b'),(2,'398eb61b61b1aad36c6d4f5766af434bacd3b5f9ccef9808249c9af718b1f871'),(3,'bf07ec49033de438536c52a1529668c06407d4b00239175d77e2d576cca78931'),(4,'f264321eb528ca4e5edd1d9e2fa3ed38e3dd9ecbec35c703719c83408bcffd9c'),(5,TARGETS['VGPUDX12.dll'])]:
  run('gpu-'+str(v),[driver,tree,'gpu-'+str(v)],tree/f'resolution-analysis/gpu/candidate-v{v if v<5 else "5-final"}/VGPUDX12.dll',pin)
 out.mkdir(parents=True,exist_ok=True)
 for f,source in [(DLL,tree/'resolution-analysis/aspect/overscan-candidate-v7'/DLL),('VGPUDX12.dll',tree/'resolution-analysis/gpu/candidate-v5-final/VGPUDX12.dll')]:shutil.copyfile(source,out/f)
 from menu import generate_menu
 menu=out/'EmuMenu/Assets/TitleMenuData.json';menu.parent.mkdir(parents=True);menu.write_bytes(generate_menu((src/'EmuMenu/Assets/TitleMenuData.json').read_bytes(),tree/'resolution-analysis/shared/preset-contract-v1.json'))
 for f,pin in TARGETS.items():assert digest(out/f)==pin,(f,digest(out/f))
 b1=work/'intermediate-beta1-native'/DLL;b1.parent.mkdir();shutil.copyfile(tree/'native-host-v5'/DLL,b1)
 receipt={'schema':1,'status':'PASS','sourceOnlyBuild':True,'inputHashes':INPUTS,'targetHashes':TARGETS,'intermediateBeta1Native':{'path':str(b1),'sha256':digest(b1),'bytes':b1.stat().st_size},'stages':stages}
 (work/'build-report.json').write_text(json.dumps(receipt,indent=2)+'\n','utf8');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
