"""Build an offline selective installer from owned, source-built game targets.

The public build accepts exact stock, 0.11 foundation, full dub and Alpha2
caption outputs. Only VCDIFFs, managed tools, metadata and notices are shipped.
"""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, sys

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
REPO=HERE.parent
TOOL_SHA='732980d52f9220dc81817ccdd0c295eadce8a0048a24c2a771a73f791ac824e9'
RELEASE='CrimsonSkies-Unified-0.14.0-alpha.2'

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def load(p): return json.loads(Path(p).read_text('utf-8-sig'))
def save(p,v): Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def run(args,cwd=None):
    env=dict(os.environ);env.pop('XDELTA',None)
    r=subprocess.run([str(x) for x in args],cwd=cwd,env=env,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=300)
    if r.returncode: raise RuntimeError((r.stdout+r.stderr).decode('utf-8','replace'))

def compile_setup(bundle,compile_dir):
    """Compile the shipping UI/engine; fixture defines are never supplied."""
    assert not compile_dir.exists();compile_dir.mkdir(parents=True)
    files=[]
    for name in ['Engine.cs','Settings.cs','Selection.cs','Ui.cs']:
        p=compile_dir/name;shutil.copyfile(HERE/'source'/name,p);files.append(name)
    for name,source in [('VoiceCache.cs','dubbing/audio/VoiceCache.cs'),('Resolution.cs','source/SelectionMigration.cs')]:
        p=compile_dir/name;p.write_text((REPO/source).read_text('utf-8').replace('namespace CrimsonSkiesKoreanPatch','namespace CrimsonSkiesUnified'),encoding='utf-8');files.append(name)
    from release import assembly_metadata, pins_source
    release_id=load(bundle/'manifest.json')['releaseId']
    (compile_dir/'Pins.cs').write_text(pins_source(sha(bundle/'manifest.json'),release_id),encoding='utf-8');files.append('Pins.cs')
    (compile_dir/'AssemblyInfo.cs').write_text(assembly_metadata(release_id),encoding='utf-8');files.append('AssemblyInfo.cs')
    csc=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    run([csc,'/nologo','/codepage:65001','/target:winexe','/optimize+','/out:CrimsonSkiesSetup.exe',*['/r:'+x for x in ['System.Core.dll','System.Windows.Forms.dll','System.Drawing.dll','System.Web.Extensions.dll','System.Xml.dll']],*files],compile_dir)
    shutil.copyfile(compile_dir/'CrimsonSkiesSetup.exe',bundle/'CrimsonSkiesSetup.exe')

def build(a):
    from native_options import compose, NAME
    from release import check_signed_tool, record_preparation, finalize
    out=a.out.resolve()
    assert not out.exists(), 'Use a new output directory'
    for p in [a.stock,a.foundation,a.full_dub,a.dub_captions,a.native_work,REPO]:
        p=p.resolve();assert not out.is_relative_to(p) and not p.is_relative_to(out)
    assert sha(a.xdelta)==TOOL_SHA
    shipping_tool=a.xdelta
    if a.signed_xdelta:
        check_signed_tool(a.xdelta,a.signed_xdelta)
        shipping_tool=a.signed_xdelta
    f=load(REPO/'manifest.json');audio=load(REPO/'dubbing/audio/manifest.json');cap=load(REPO/'dubbing/captions/dub-caption-catalog.json')
    for i,row in enumerate(f['files']):
        assert sha(a.stock/row['path'])==f['profiles'][0]['sha256'][i]
        assert sha(a.foundation/row['path'])==row['targetSha256']
    for i,row in enumerate(audio['files']):
        assert sha(a.foundation/row['path'])==audio['profiles'][0]['sha256'][i]
        assert sha(a.full_dub/row['path'])==row['targetSha256']
    for i,row in enumerate(cap['files']):
        assert sha(a.full_dub/row['path'])==cap['styles'][0]['hashes'][i]
        assert sha(a.dub_captions/row['path'])==cap['styles'][1]['hashes'][i]
    # Store-protected apphost EXEs may expose metadata but deny data reads;
    # verify the existing launcher's pinned managed DLL and argument contract.
    guard_paths=['Game/DefaultPackage','appxmanifest.xml','EmuMenu/EmuMenu.dll','EmuMenu/EmuMenuLaunchArguments.txt']
    for rel in guard_paths:assert (a.stock/rel).is_file(), 'Missing owned guard input: '+rel
    assert sha(a.stock/'EmuMenu/EmuMenu.dll')=='40e78379367b74c6dc7ccffce9215abae7400a069cebb9f8d50360f7a46fdc11'
    assert sha(a.stock/'EmuMenu/EmuMenuLaunchArguments.txt')=='da7174421ed8ec03bbdbe9d9b8e094a937786c82b445d05906911335eb25a4f0'
    out.mkdir(parents=True);bundle=out/RELEASE;bundle.mkdir();(bundle/'patches').mkdir();(bundle/'tools').mkdir();work=out/'private-work';work.mkdir()
    shutil.copyfile(shipping_tool,bundle/'tools/xdelta3.exe')
    # Include every volume in the coherent fingerprint, including untouched
    # ones. Full backups and staging are limited to files actually changing.
    paths=[NAME,'VGPUDX12.dll','EmuMenu/Assets/TitleMenuData.json']+[f'Game/DefaultPackage.data/Data{i:04d}' for i in range(26)]
    rows=[];sources={};edge_id=0
    def node(i,p):
        h=sha(p);r=rows[i]
        if not any(n['sha256']==h for n in r['nodes']):r['nodes'].append(dict(sha256=h,bytes=p.stat().st_size));sources[i,h]=p
        return h
    def edge(i,fr,to):
        nonlocal edge_id
        if fr==to or any(e['source']==fr and e['target']==to for e in rows[i]['edges']):return
        rel=f'patches/{edge_id:03d}.vcdiff';edge_id+=1;p=bundle/rel
        cached=a.delta_cache/p.name if a.delta_cache else None
        if cached and cached.is_file():shutil.copyfile(cached,p)
        else:run([a.xdelta,'-e','-9','-D','-R','-s',sources[i,fr],sources[i,to],p])
        decoded=work/'decode.tmp';run([a.xdelta,'-d','-D','-R','-s',sources[i,fr],p,decoded]);assert sha(decoded)==to;decoded.unlink()
        rows[i]['edges'].append(dict(source=fr,target=to,path=rel,bytes=p.stat().st_size,sha256=sha(p)))
    vectors={}
    for path in paths:rows.append(dict(path=path,nodes=[],edges=[]))
    for key,folder in [('stock',a.stock),('foundation',a.foundation),('full-dub',a.full_dub)]:
        vectors[key]=[node(i,folder/p) for i,p in enumerate(paths)]
    # Alpha2 captions only change three files; other volume inputs are shared.
    vectors['dub-captions']=vectors['full-dub'][:]
    for row in cap['files']:
        i=paths.index(row['path']);vectors['dub-captions'][i]=node(i,a.dub_captions/row['path'])
    for i in range(len(paths)):
        edge(i,vectors['stock'][i],vectors['foundation'][i]);edge(i,vectors['foundation'][i],vectors['stock'][i])
        edge(i,vectors['foundation'][i],vectors['full-dub'][i])
        edge(i,vectors['full-dub'][i],vectors['dub-captions'][i]);edge(i,vectors['dub-captions'][i],vectors['full-dub'][i])
    # Menus preserve original languages when Korean is off and force the
    # Korean resource slot otherwise. No global locale/font installation.
    menus={}
    for ko in [False,True]:
        for wide in [False,True]:
            raw=(a.foundation if wide else a.stock)/paths[2]
            if ko:
                obj=load(raw);found=0
                for cat in obj['Categories']:
                    for it in cat['Items']:
                        if it.get('Id')=='game-language':
                            found+=1;it.update(Options=['ko-KR'],ArgValues=['-locale ko-KR'],Default='ko-KR',LaunchOnly=True,IsLaunchArgument=True,DynamicOptions='cs-subtitle-pack-v1')
                assert found==1;p=work/f'menu-{ko}-{wide}.json'
                # Match the already published single-line .NET menu exactly.
                p.write_bytes((json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf-8'))
            else:p=raw
            h=node(2,p);menus[ko,wide]=h;edge(2,vectors['stock'][2],h);edge(2,h,vectors['stock'][2])
    assert menus[True,True]==vectors['full-dub'][2], 'Korean wide menu must match public Alpha2'
    profiles=[]
    for ko in [False,True]:
        for wide in [False,True]:
            for dub in ([False,True] if ko else [False]):
                for caption in (['off','original','dub'] if ko and dub else ['off','original'] if ko else ['off']):
                    ident=f'k{int(ko)}-w{int(wide)}-d{int(dub)}-{caption}'
                    v=vectors['dub-captions' if caption=='dub' else 'full-dub' if dub else 'foundation' if ko else 'stock'][:]
                    b=compose(a.stock/NAME,a.foundation/NAME,a.dub_captions/NAME,a.native_work,ko,wide,caption)
                    p=work/(ident+'.dll');p.write_bytes(b);v[0]=node(0,p)
                    v[1]=vectors['foundation' if wide else 'stock'][1];v[2]=menus[ko,wide]
                    edge(0,vectors['stock'][0],v[0]);edge(0,v[0],vectors['stock'][0])
                    profiles.append(dict(id=ident,korean=ko,wide=wide,dub=dub,captions=caption,hashes=v))
    # Exact stock/public foundation are safe initial baselines. Unowned full
    # dub installations must be restored by their own tool before migration.
    m=dict(schema=1,releaseId=RELEASE,supportedPackage=f['supportedPackage'],tool=dict(path='tools/xdelta3.exe',sha256=sha(shipping_tool)),files=rows,profiles=profiles,inputs=[dict(id=k,hashes=vectors[k]) for k in ['stock','foundation']],knownExternal=[dict(id=k,hashes=vectors[k]) for k in ['full-dub','dub-captions']],guards=[])
    for rel in guard_paths:
        p=a.stock/rel;m['guards'].append(dict(path=rel,bytes=p.stat().st_size,sha256=sha(p)))
    save(bundle/'manifest.json',m)
    compile_setup(bundle,work/'compile')
    for p in [REPO/'LICENSE',REPO/'FONT-NOTICE.txt',REPO/'THIRD-PARTY-NOTICES.txt',REPO/'dubbing/AI-DUB-NOTICE.txt',HERE/'README.md',HERE/'README.en.md',HERE/'SIGNING.md']:shutil.copyfile(p,bundle/p.name)
    shutil.copytree(REPO/'licenses',bundle/'licenses')
    save(out/'build-report.json',dict(schema=1,releaseId=RELEASE,profiles=len(profiles),edges=edge_id,deltaBytes=sum(e['bytes'] for r in rows for e in r['edges']),manifestSha256=sha(bundle/'manifest.json'),gameWrites=0))
    record_preparation(bundle,out/'preparation.json')
    if a.prepare_only:
        print(json.dumps(dict(status='PREPARED',bundle=str(bundle)),ensure_ascii=False),flush=True)
    else:
        print(json.dumps(finalize(bundle,out/'preparation.json',out/'release'),ensure_ascii=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ['stock','foundation','full-dub','dub-captions','native-work','xdelta','out']:p.add_argument('--'+flag,required=True,type=Path)
    p.add_argument('--delta-cache',type=Path,help='Optional previous patches directory; every reused delta is decoded and its complete target hash verified')
    p.add_argument('--signed-xdelta',type=Path,help='Already trusted/timestamped signature on the exact pinned xdelta code; must be finalized before manifest compilation')
    p.add_argument('--prepare-only',action='store_true',help='Stage the bundle without a ZIP, for optional later signing')
    build(p.parse_args())
