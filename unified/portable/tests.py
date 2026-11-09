"""Isolated integration/fault tests. Never run faults on an installed game. MIT."""
from pathlib import Path
import argparse, copy, json, os, shutil, struct, subprocess, sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import host as H
import cache as C
from engine import Engine, PROFILES

ORIGINAL_PREPARE = C.prepare
INITIAL = b'game-language = English\r\nscaling = 2x - 1280x960\r\nantialiasing = 4x MSAA\r\ncustom-key = preserve me\r\n'

def image(payload, crosslink=False):
    raw = bytearray(b'Z'*(C.DATA+7*C.CLUSTER)); raw[:16] = b'XTAF'+struct.pack('>III',1234,128,1)
    raw[4096:C.DATA] = bytes(C.DATA-4096)
    for i,v in enumerate((0xfff8,0xffff,0xffff,0xffff,0xffff)): struct.pack_into('>H',raw,4096+i*2,v)
    raw[C.DATA:C.DATA+2*C.CLUSTER] = bytes(2*C.CLUSTER)
    def entry(at,name,flags,cluster,size):
        name=name.encode(); raw[at:at+64]=bytes(64);raw[at:at+2]=bytes((len(name),flags));raw[at+2:at+2+len(name)]=name
        struct.pack_into('>II',raw,at+44,cluster,size)
    entry(C.DATA,'Xbox2',16,2,0);entry(C.DATA+C.CLUSTER,'data.zip',0,3,len(payload))
    entry(C.DATA+C.CLUSTER+64,'checkpoint.dat',0,3 if crosslink else 4,32)
    entry(C.DATA+C.CLUSTER+128,'cache_good.txt',0,0,0)
    raw[C.DATA+2*C.CLUSTER:C.DATA+2*C.CLUSTER+len(payload)]=payload
    raw[C.DATA+3*C.CLUSTER:C.DATA+3*C.CLUSTER+32]=b'USER CHECKPOINT DO NOT MODIFY!!!'
    return bytes(raw)

class Locations:
    def __init__(self, root, fault=None, crash=False):
        self.backups,self.legacy = root/'backups',root/'legacy'
        self.settings,self.cache = root/'settings.ini',root/'cache.raw'
        self.fault,self.crash = fault,crash
    def stopped(self): pass
    def point(self, name):
        if name == self.fault:
            self.fault = None
            if self.crash: os._exit(73)
            raise RuntimeError('Injected failure: '+name)

def payloads(m):
    return {v['id']:('artificial cached asset '+v['id']+'\n').encode()*64
            for group in ('inputs','profiles','knownExternal') for v in m[group]}
def configure_cache(m):
    p=payloads(m)
    def prepare(path,manifest,target,files,temp,log=print):
        return ORIGINAL_PREPARE(path,manifest,target,files,temp,log,payload_reader=lambda _:p[target])
    C.prepare=prepare
    return p

def run(out, fixture, stock):
    H.need(not out.exists(),'Use a fresh test output'); out.mkdir(parents=True)
    package=out/'package';package.mkdir();shutil.copytree(fixture/'patches',package/'patches');shutil.copytree(fixture/'tools',package/'tools')
    m=copy.deepcopy(H.load_json(fixture/'manifest.json'));p=payloads(m)
    m['cacheFiles']=[dict(name='data.zip',nodes=[dict(sha256=H.digest(b),bytes=len(b)) for b in p.values()],
                        hashes={k:H.digest(b) for k,b in p.items()})]
    H.atomic_json(package/'manifest.json',m)
    pins=dict(releaseId='portable-fixture',manifestSha256=H.sha(package/'manifest.json'),legacyManifestSha256=H.sha(package/'manifest.json'))
    H.atomic_json(package/'pins.json',pins);configure_cache(m)
    results=[]
    def record(name): results.append(dict(test=name,passed=True)); print('PASS '+name,flush=True)
    def case(name):
        root=out/name;content=root/'Content';content.mkdir(parents=True)
        for f in [*m['files'],*m['guards']]:
            dest=content/f['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(stock/f['path'],dest)
        (content/'unowned-sentinel.txt').write_bytes(b'leave game data alone')
        (root/'settings.ini').write_bytes(INITIAL);(root/'cache.raw').write_bytes(image(p['stock']))
        return root
    def engine(root, fault=None, crash=False):return Engine(package,pins,root/'Content',Locations(root,fault,crash),log=lambda _:None)
    def verify(root,state='stock',exact=False):
        e=engine(root);assert e.inspect()==e.vector(state)
        for g in m['guards']:H.verify(root/'Content'/g['path'],g['sha256'])
        assert (root/'Content/unowned-sentinel.txt').read_bytes()==b'leave game data alone'
        raw=(root/'cache.raw').read_bytes();assert raw[C.DATA+3*C.CLUSTER:C.DATA+3*C.CLUSTER+32]==b'USER CHECKPOINT DO NOT MODIFY!!!'
        C.verify_target(root/'cache.raw',m,state)
        settings=(root/'settings.ini').read_bytes();assert b'antialiasing = 4x MSAA' in settings and b'custom-key = preserve me' in settings
        if exact: assert settings==INITIAL and raw==image(p['stock'])
        r=e.receipt();assert r is None or not r['pending']
        assert not list((root/'Content').glob('.csbat-*'))
    def snapshot(root):return {str(f.relative_to(root)):H.sha(f) for f in (root/'Content').rglob('*') if f.is_file()}
    root=case('matrix');e=engine(root);assert e.run('check')=='stock';assert not (root/'backups').exists();record('read-only-check')
    for target in [PROFILES[i] for i in (7,0,5,2,3,4,6,1)]:
        e.run('apply',target);verify(root,target);e.run('check');record('switch-'+target)
    e.run('restore');verify(root,'stock');assert (root/'settings.ini').read_bytes()==INITIAL;record('restore-and-preserve-settings')
    for point in ('preparing','prepared','file-0','cache','settings'):
        root=case('exception-'+point)
        try:engine(root,point).run('apply',PROFILES[7])
        except RuntimeError:pass
        else:raise AssertionError('Fault did not fire')
        verify(root,exact=True);record('exception-rollback-'+point)
    for point in ('preparing','prepared','file-0','cache','settings'):
        root=case('crash-'+point)
        r=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',str(root),'--package',str(package),'--fault',point,'--crash'],capture_output=True)
        assert r.returncode==73,(point,r.stdout,r.stderr)
        e=engine(root);assert e.receipt()['pending']
        e.run('recover');verify(root,exact=True);record('force-exit-recovery-'+point)
    for bad in ('unknown-file','unknown-cache','crosslink-cache','duplicate-settings','bad-delta','bad-tool'):
        root=case(bad);e=engine(root);fix=None
        if bad=='unknown-file':
            f=e.file(3);b=f.read_bytes();f.write_bytes(bytes([b[0]^1])+b[1:])
        elif bad=='unknown-cache':(root/'cache.raw').write_bytes(image(b'not a known asset'))
        elif bad=='crosslink-cache':(root/'cache.raw').write_bytes(image(p['stock'],True))
        elif bad=='duplicate-settings':(root/'settings.ini').write_bytes(INITIAL+b'GAME-LANGUAGE=English\r\n')
        else:
            edge=e.route(0,e.vector('stock')[0],e.vector(PROFILES[7])[0])[0]
            f=package/('tools/xdelta3.exe' if bad=='bad-tool' else edge['path']);old=f.read_bytes();f.write_bytes(old+b'tamper');fix=(f,old)
        before=snapshot(root);raw=(root/'cache.raw').read_bytes();settings=(root/'settings.ini').read_bytes()
        try:
            try:e.run('apply',PROFILES[7])
            except (ValueError,OSError):pass
            else:raise AssertionError('Expected refusal: '+bad)
            assert snapshot(root)==before and (root/'cache.raw').read_bytes()==raw and (root/'settings.ini').read_bytes()==settings
            record('refused-without-writes-'+bad)
        finally:
            if fix:fix[0].write_bytes(fix[1])
    root=case('concurrent-lock')
    with H.mutex(root/'Content'):
        r=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',str(root),'--package',str(package)],capture_output=True)
        assert r.returncode!=0
    verify(root,exact=True);record('concurrent-installer-refused')
    root=case('concurrent-setting');e=engine(root);loc=e.loc
    def fault(name):
        if name=='settings':
            loc.point=lambda _:None
            path=root/'settings.ini';path.write_bytes(path.read_bytes()+b'external-key=keep\r\n')
            raise RuntimeError('external unrelated change')
    loc.point=fault
    try:e.run('apply',PROFILES[7])
    except RuntimeError:pass
    verify(root);assert (root/'settings.ini').read_bytes()==INITIAL+b'external-key=keep\r\n';record('recovery-preserves-unrelated-concurrent-setting')
    root=case('legacy-migration');old=engine(root);old.run('apply',PROFILES[7]);old_r=old.receipt()
    legacy=H.mkdir(root/'legacy'/H.root_id(root/'Content')/m['releaseId'])
    saved=old_r['settingsOrigin']
    legacy_r=dict(schema=1,releaseId=m['releaseId'],root=str(root/'Content'),manifestSha256=pins['legacyManifestSha256'],
                  original='stock',current=PROFILES[7],pending=None,settings=dict(language=saved['game-language'],scaling=saved['scaling']))
    H.atomic_json(legacy/'receipt.json',legacy_r)
    for f in old.directory.glob('original-*.bin'):shutil.copyfile(f,legacy/f.name)
    legacy_before={f.name:H.sha(f) for f in legacy.iterdir()}
    loc=Locations(root);loc.backups=root/'migrated-backups';new=Engine(package,pins,root/'Content',loc,log=lambda _:None)
    new.run('apply',PROFILES[1]);assert new.inspect()==new.vector(PROFILES[1]);new.run('restore')
    assert new.inspect()==new.vector('stock') and (root/'settings.ini').read_bytes()==INITIAL
    assert {f.name:H.sha(f) for f in legacy.iterdir()}==legacy_before;record('legacy-beta1-verified-independent-backups')
    safe_package=out/'stock-dll-package';safe_package.mkdir()
    shutil.copytree(package/'tools',safe_package/'tools');shutil.copytree(package/'patches',safe_package/'patches')
    safe_m=copy.deepcopy(m);safe_profile=next(v for v in safe_m['profiles'] if v['id']==PROFILES[4])
    safe_profile['hashes'][0]=m['inputs'][0]['hashes'][0]
    H.atomic_json(safe_package/'manifest.json',safe_m)
    safe_pins=dict(pins,releaseId='portable-stock-dll-fixture',manifestSha256=H.sha(safe_package/'manifest.json'),
                   stockNativeMode=True,allowedProfiles=[PROFILES[0],PROFILES[4]])
    root=case('stock-dll-voices');safe=Engine(safe_package,safe_pins,root/'Content',Locations(root),log=lambda _:None)
    before_ids=[(safe.file(i).stat().st_ino,H.sha(safe.file(i))) for i in (0,1)]
    safe.run('apply',PROFILES[4]);assert safe.inspect()==safe.vector(PROFILES[4])
    assert [(safe.file(i).stat().st_ino,H.sha(safe.file(i))) for i in (0,1)]==before_ids
    C.verify_target(root/'cache.raw',safe_m,PROFILES[4]);record('voices-only-keeps-original-native-and-gpu-file-identities')
    before=snapshot(root)
    try:safe.run('apply',PROFILES[7])
    except ValueError:pass
    else:raise AssertionError('Unavailable preset accepted')
    assert snapshot(root)==before;record('stock-dll-package-rejects-unavailable-preset')
    safe.run('restore');assert safe.inspect()==safe.vector('stock')
    assert [(safe.file(i).stat().st_ino,H.sha(safe.file(i))) for i in (0,1)]==before_ids
    assert (root/'settings.ini').read_bytes()==INITIAL;C.verify_target(root/'cache.raw',safe_m,'stock')
    record('stock-dll-package-restores-assets-and-settings-without-replacing-dlls')
    root=case('known-xml-variant');xml=root/'Content/appxmanifest.xml';xml.write_bytes(b'\n'+xml.read_bytes())
    extra=dict(sha256=H.sha(xml),bytes=xml.stat().st_size)
    xml_pins=dict(pins,hostGuardAlternates={'appxmanifest.xml':[extra]})
    Engine(package,xml_pins,root/'Content',Locations(root),log=lambda _:None).run('check')
    record('exact-allowlisted-xml-format-retains-identity-check')
    raw=xml.read_bytes().replace(m['supportedPackage']['version'].encode(),b'9999.1.1.1')
    xml.write_bytes(raw);xml_pins['hostGuardAlternates']['appxmanifest.xml']=[dict(sha256=H.sha(xml),bytes=len(raw))]
    try:Engine(package,xml_pins,root/'Content',Locations(root),log=lambda _:None).run('check')
    except ValueError:pass
    else:raise AssertionError('Wrong package identity accepted')
    record('wrong-identity-refused-even-with-allowlisted-xml-digest')
    report=dict(status='PASS',assertions=len(results),tests=results,SACState=H.sac_state(),faultsOnlyArtificial=True,
                noInstalledGameChanges=True,cacheAndSettingsRollbackExact=True)
    H.atomic_json(out/'report.json',report);print(json.dumps(report),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker',type=Path);parser.add_argument('--package',type=Path);parser.add_argument('--fault');parser.add_argument('--crash',action='store_true')
    parser.add_argument('--out',type=Path);parser.add_argument('--fixture',type=Path);parser.add_argument('--stock',type=Path)
    a=parser.parse_args()
    if a.worker:
        m=H.load_json(a.package/'manifest.json');configure_cache(m)
        Engine(a.package,H.load_json(a.package/'pins.json'),a.worker/'Content',Locations(a.worker,a.fault,a.crash),log=lambda _:None).run('apply',PROFILES[7])
    else:run(a.out.resolve(),a.fixture.resolve(),a.stock.resolve())
