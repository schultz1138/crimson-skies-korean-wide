"""Hash-bound file/settings/cache transactions for the portable BAT installer. MIT."""
from collections import deque
from pathlib import Path
import json, os, re, shutil, subprocess, uuid, xml.etree.ElementTree as ET
import host as H
import cache as C

PROFILES = ['k0-w0-d0-off','k0-w1-d0-off','k1-w0-d0-original','k1-w1-d0-original',
            'k1-w0-d1-off','k1-w1-d1-off','k1-w0-d1-dub','k1-w1-d1-dub']
NATIVE = 'xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll'

class Engine:
    def __init__(self, package, pins, selected, locations=None, log=print):
        self.package, self.pins, self.log = H.guard(package), pins, log
        manifest_path = H.child(self.package, 'manifest.json')
        H.verify(manifest_path, pins['manifestSha256'])
        self.m = H.load_json(manifest_path)
        self.validate()
        self.root = H.guard(selected)
        if not (self.root / NATIVE).is_file(): self.root = H.guard(self.root / 'Content')
        H.need(not self.root.is_relative_to(self.package) and not self.package.is_relative_to(self.root), 'Package/game folders overlap')
        self.loc = locations or H.Locations(self.root)
        self.directory = H.child(H.child(self.loc.backups, H.root_id(self.root)), pins['releaseId'])
        self.states = {v['id']: v for group in ('inputs','profiles') for v in self.m[group]}
        self.node_maps = [{n['sha256']: n['bytes'] for n in f['nodes']} for f in self.m['files']]
        self.legacy_dir = None

    def validate(self):
        m = self.m
        H.need(m['schema'] == 1 and len(m['files']) == 29 and len(m['guards']) == 4, 'Unsupported manifest shape')
        ishash = lambda s: isinstance(s,str) and re.fullmatch('[0-9a-f]{64}',s)
        ids = set()
        for i,f in enumerate(m['files']):
            expected = NATIVE if i == 0 else 'VGPUDX12.dll' if i == 1 else 'EmuMenu/Assets/TitleMenuData.json' if i == 2 else 'Game/DefaultPackage.data/Data%04d' % (i-3)
            H.need(f['path'] == expected, 'Unsupported component path')
            nodes = {n['sha256']:n['bytes'] for n in f['nodes']}
            H.need(len(nodes) == len(f['nodes']) and 0 < len(nodes) <= 32, 'Invalid nodes')
            H.need(all(ishash(h) and isinstance(n,int) and 0 < n <= 8589934592 for h,n in nodes.items()), 'Invalid node metadata')
            for e in f['edges']:
                H.need(e['source'] in nodes and e['target'] in nodes and e['source'] != e['target']
                       and re.fullmatch(r'patches/[0-9]{3}\.vcdiff',e['path']) and ishash(e['sha256'])
                       and isinstance(e['bytes'],int) and 0 < e['bytes'] <= 8589934592, 'Invalid delta')
        for group in ('inputs','profiles','knownExternal'):
            for item in m[group]:
                H.need(item['id'] not in ids, 'Duplicate state'); ids.add(item['id'])
                H.need(len(item['hashes']) == 29 and all(h in {n['sha256'] for n in f['nodes']}
                       for h,f in zip(item['hashes'],m['files'])), 'Invalid state vector')
        H.need({v['id'] for v in m['inputs']} == {'stock','foundation'} and set(PROFILES) <= ids, 'Missing presets')
        H.need(m['tool']['path'] == 'tools/xdelta3.exe' and ishash(m['tool']['sha256']), 'Invalid decoder')
        for g in m['guards']:
            H.child(self.package,g['path']); H.need(ishash(g['sha256']) and 0 < g['bytes'] < 67108864, 'Invalid guard')
        H.need(0 < len(m['cacheFiles']) <= 128, 'Missing cache fingerprints')
        names = set()
        for f in m['cacheFiles']:
            H.need(re.fullmatch('[A-Za-z0-9_ .-]{1,42}',f['name']) and f['name'].lower() not in names, 'Invalid cache name')
            names.add(f['name'].lower())
            H.need(set(f['hashes']) == ids and 0 < len(f['nodes']) <= 32, 'Invalid cache states')
            H.need(all(ishash(n['sha256']) and 0 < n['bytes'] <= C.MAX_ASSET for n in f['nodes']), 'Invalid cache nodes')
            H.need(all(h in {n['sha256'] for n in f['nodes']} for h in f['hashes'].values()), 'Missing cache node')

    def host(self):
        for g in self.m['guards']:
            path=H.child(self.root,g['path'])
            allowed=[g]+self.pins.get('hostGuardAlternates',{}).get(g['path'],[])
            actual=H.sha(path);size=path.stat().st_size
            H.need(any(v['sha256']==actual and v['bytes']==size for v in allowed),'Unsupported host guard: '+g['path'])
        raw = (self.root/'appxmanifest.xml').read_bytes()
        H.need(b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper(), 'XML declarations refused')
        tree = ET.fromstring(raw); ns = '{http://schemas.microsoft.com/appx/manifest/foundation/windows10}'
        identities = list(tree.iter(ns+'Identity')); expected = self.m['supportedPackage']
        H.need(len(identities) == 1 and identities[0] in list(tree), 'Invalid package identity')
        identity = identities[0]
        H.need(all(identity.get(k) == expected[v] for k,v in [('Name','name'),('Version','version'),
               ('ProcessorArchitecture','architecture'),('Publisher','publisher')]), 'Wrong game build')

    def vector(self, state):
        H.need(state in self.states, 'Unknown state'); return self.states[state]['hashes']
    def file(self, i): return H.child(self.root,self.m['files'][i]['path'])
    def original(self, i): return self.directory / ('original-%02d.bin' % i)
    def inspect(self):
        result = []
        for i,f in enumerate(self.m['files']):
            path = self.file(i); H.guard(path)
            H.need(path.stat().st_size in self.node_maps[i].values(), 'Unknown file size: '+f['path'])
            actual = H.sha(path)
            H.need(self.node_maps[i].get(actual) == path.stat().st_size, 'Unknown modified file: '+f['path'])
            result.append(actual)
        return result
    def route(self, i, start, end):
        todo = deque([(start,[])]); seen = {start}
        while todo:
            at, edges = todo.popleft()
            if at == end: return edges
            for edge in self.m['files'][i]['edges']:
                if edge['source'] == at and edge['target'] not in seen:
                    seen.add(edge['target']); todo.append((edge['target'],edges+[edge]))
        return None
    def payload(self, edge): H.verify(H.child(self.package,edge['path']),edge['sha256'],edge['bytes'])
    def receipt(self):
        path = self.directory/'receipt.json'
        if not path.exists(): return None
        r = H.load_json(path,524288)
        H.need(r['schema'] == 1 and r['releaseId'] == self.pins['releaseId'] and r['root'] == str(self.root)
               and r['manifestSha256'] == self.pins['manifestSha256'] and r['original'] in ('stock','foundation'), 'Receipt binding mismatch')
        self.vector(r['current']); H.valid_origin(r['settingsOrigin'])
        if r.get('pending'):
            j = r['pending']; H.need(re.fullmatch('[0-9a-f]{32}',j['id']) and j['phase'] in ('preparing','prepared'), 'Invalid transaction')
            before,after = self.vector(j['from']),self.vector(j['to'])
            H.need(j['changed'] == [i for i in range(29) if before[i] != after[i]], 'Invalid changed-file journal')
            H.decode(j['settingsBefore']); H.decode(j['settingsAfter'])
            c = j.get('cache')
            if c:
                H.need(self.loc.cache is not None and all(re.fullmatch('[0-9a-f]{64}',c[k]) for k in ('before','after')), 'Invalid cache journal')
        return r
    def save(self, r): H.atomic_json(self.directory/'receipt.json',r)
    def backup_verify(self, r):
        for i,h in enumerate(self.vector(r['original'])):
            path = self.original(i)
            if path.exists(): H.verify(path,h,self.node_maps[i][h])
    def initial(self, current, raw_settings):
        baseline = next((v['id'] for v in self.m['inputs'] if v['hashes'] == current),None)
        saved = H.origin(raw_settings); state = baseline
        if baseline is None:
            legacy_dir = H.child(H.child(self.loc.legacy,H.root_id(self.root)),self.m['releaseId'])
            legacy = H.load_json(legacy_dir/'receipt.json',524288)
            H.need(legacy['schema'] == 1 and legacy['root'] == str(self.root) and legacy['releaseId'] == self.m['releaseId']
                   and legacy['manifestSha256'] == self.pins['legacyManifestSha256'] and not legacy.get('pending')
                   and legacy['original'] in ('stock','foundation') and self.vector(legacy['current']) == current, 'Beta 1 migration record differs')
            baseline, state = legacy['original'],legacy['current']
            saved = {'game-language':legacy['settings']['language'],'scaling':legacy['settings']['scaling']}
            H.valid_origin(saved)
            for i,h in enumerate(self.vector(baseline)):
                if current[i] != h: H.verify(legacy_dir/('original-%02d.bin'%i),h,self.node_maps[i][h])
            self.legacy_dir = legacy_dir
            self.log('Beta 1 원본 백업을 검증했습니다 / Verified Beta 1 originals; source backups stay unchanged.')
        return dict(schema=1,releaseId=self.pins['releaseId'],root=str(self.root),manifestSha256=self.pins['manifestSha256'],
                    original=baseline,current=state,settingsOrigin=saved,pending=None,importedBeta1=self.legacy_dir is not None)
    def import_backups(self, r, current):
        if self.legacy_dir is None: return
        H.mkdir(self.directory)
        for i,h in enumerate(self.vector(r['original'])):
            if current[i] == h: continue
            dest = self.original(i)
            if dest.exists(): H.verify(dest,h,self.node_maps[i][h]); continue
            temp = self.directory/('.import-'+uuid.uuid4().hex+'.tmp')
            try:
                H.copy_new(self.legacy_dir/('original-%02d.bin'%i),temp,h); os.rename(temp,dest)
            finally:
                if temp.exists(): H.guard(temp).unlink()
    def materialize(self, i, current, wanted, r, stage):
        source = self.file(i); route = self.route(i,current,wanted)
        backup = self.original(i)
        if backup.exists():
            other = self.route(i,self.vector(r['original'])[i],wanted)
            if other is not None and (route is None or len(other) < len(route)): source,route = backup,other
        H.need(route is not None, 'Original backup/route unavailable')
        source_hash = current if source == self.file(i) else self.vector(r['original'])[i]
        H.verify(source,source_hash)
        previous = source
        for k,edge in enumerate(route):
            ready = stage/('decode-%d-%d.bin'%(i,k)); self.payload(edge)
            H.verify(self.package/self.m['tool']['path'],self.m['tool']['sha256'])
            env = {k:v for k,v in os.environ.items() if k.upper() != 'XDELTA'}
            result = subprocess.run([str(self.package/self.m['tool']['path']),'-d','-D','-R','-s',str(previous),
                                     str(self.package/edge['path']),str(ready)],capture_output=True,timeout=300,
                                    creationflags=subprocess.CREATE_NO_WINDOW,env=env)
            H.need(result.returncode == 0, 'xdelta failed: '+(result.stdout+result.stderr).decode('utf-8','replace'))
            H.verify(ready,edge['target'],self.node_maps[i][edge['target']])
            if previous != source: H.guard(previous).unlink()
            previous = ready
        final = stage/('ready-%d.bin'%i)
        if previous == source: H.copy_new(source,final,wanted)
        else: os.rename(previous,final)
        H.verify(final,wanted,self.node_maps[i][wanted])
        return final
    def stage(self, j): return self.root/('.csbat-'+j['id'])
    def cache_temp(self, j):
        return None if self.loc.cache is None else Path(self.loc.cache).parent/('.csbat-cache-'+j['id']+'.tmp')
    def cleanup(self, j):
        stage = self.stage(j)
        if stage.exists():
            H.guard(stage)
            for path in stage.iterdir():
                H.need(path.is_file() and re.fullmatch(r'(ready|undo|rollback)-\d+\.bin|decode-\d+-\d+\.bin|cache-before\.raw',path.name), 'Unowned stage member; preserve folder')
                H.guard(path)
            for path in stage.iterdir(): path.unlink()
            stage.rmdir()
        temp = self.cache_temp(j)
        if temp is not None and temp.exists(): H.guard(temp).unlink()
        for i in j['changed']:
            temp = self.directory/('.origin-'+j['id']+'-%d.tmp'%i)
            if temp.exists(): H.guard(temp).unlink()
        if self.loc.settings is not None:
            temp = Path(self.loc.settings).parent/('.csbat-settings-'+j['id']+'.tmp')
            if temp.exists(): H.guard(temp).unlink()
    def commit_settings(self, before, after, j):
        H.need(H.read_settings(self.loc.settings) == before, 'Settings changed concurrently')
        if before == after: return
        H.need(before is not None and after is not None, 'Settings creation/deletion refused')
        temp = Path(self.loc.settings).parent/('.csbat-settings-'+j['id']+'.tmp')
        try:
            with temp.open('xb') as stream: stream.write(after); stream.flush(); os.fsync(stream.fileno())
            self.loc.stopped(); H.atomic(self.loc.settings,temp,H.digest(before),H.digest(after))
        finally:
            if temp.exists(): H.guard(temp).unlink()
    def recover(self, r):
        j = r.get('pending'); H.need(j is not None,'No interrupted operation')
        self.loc.stopped(); self.host()
        before, after, now = self.vector(j['from']),self.vector(j['to']),self.inspect()
        H.need(all(h == before[i] or i in j['changed'] and h == after[i] for i,h in enumerate(now)), 'Recovery refused unknown files')
        if j['phase'] == 'preparing':
            H.need(now == before, 'Preparing journal has changed game files')
            self.cleanup(j); r['pending'] = None; self.save(r); return
        stage = H.guard(self.stage(j))
        for i in j['changed']: H.verify(stage/('undo-%d.bin'%i),before[i],self.node_maps[i][before[i]])
        cache = j.get('cache')
        if cache:
            H.verify(stage/'cache-before.raw',cache['before'])
            H.need(H.sha(self.loc.cache) in (cache['before'],cache['after']), 'Recovery refused concurrent cache changes')
        current_settings = H.read_settings(self.loc.settings)
        recovered_settings = H.rollback_settings(current_settings,H.decode(j['settingsBefore']),H.decode(j['settingsAfter']))
        self.backup_verify(r)
        for i in reversed(j['changed']):
            if now[i] == before[i]: continue
            temp = stage/('rollback-%d.bin'%i)
            if temp.exists(): H.verify(temp,before[i]); temp.unlink()
            H.copy_new(stage/('undo-%d.bin'%i),temp,before[i]); self.loc.stopped()
            H.atomic(self.file(i),temp,after[i],before[i])
        if cache and H.sha(self.loc.cache) == cache['after']:
            temp = self.cache_temp(j)
            if temp.exists(): H.verify(temp,cache['after']); temp.unlink()
            H.copy_new(stage/'cache-before.raw',temp,cache['before']); self.loc.stopped()
            H.atomic(self.loc.cache,temp,cache['after'],cache['before'])
        self.commit_settings(current_settings,recovered_settings,j)
        H.need(self.inspect() == before,'Recovery readback differs')
        r['current'],r['pending'] = j['from'],None; self.save(r); self.cleanup(j)
        self.log('PASS: 중단 전 상태로 복구 / Interrupted operation recovered')

    def run(self, action, profile=None):
        H.need(action in ('check','apply','restore','recover'),'Unknown action')
        with H.mutex(self.root):
            self.loc.stopped(); self.host()
            r = self.receipt()
            if action == 'recover': H.need(r is not None,'No recovery receipt'); return self.recover(r)
            H.need(r is None or not r.get('pending'),'중단 작업 복구를 먼저 실행하세요 / Run recovery first')
            current = self.inspect(); raw = H.read_settings(self.loc.settings)
            if r is None and self.pins.get('stockNativeMode'):
                H.need(current == self.vector('stock'), 'Stock-DLL package requires an exact original installation; use official game repair first')
            if r is None: r = self.initial(current,raw)
            H.need(not self.pins.get('stockNativeMode') or r['original']=='stock', 'Original game baseline required for stock-DLL voices mode')
            H.need(current == self.vector(r['current']),'Files differ from owned receipt')
            self.backup_verify(r)
            H.verify(self.package/self.m['tool']['path'],self.m['tool']['sha256'])
            entries = C.verify_target(self.loc.cache,self.m)
            if action == 'check':
                for f in self.m['files']:
                    for edge in f['edges']: self.payload(edge)
                self.log('PASS: '+r['current']+'; 29 files + 4 guards; '+str(len(entries))+' cached assets checked')
                return r['current']
            H.need(action != 'restore' or (self.directory/'receipt.json').exists(),'No owned restoration history')
            if action == 'apply': H.need(profile in self.pins.get('allowedProfiles',PROFILES),'Preset unavailable in this package')
            target = r['original'] if action == 'restore' else profile
            target_vector = self.vector(target); choice = self.states[target]
            korean = choice.get('korean',target == 'foundation'); wide = choice.get('wide',target == 'foundation')
            desired_settings = H.plan_settings(raw,r['settingsOrigin'],korean,wide,action == 'restore')
            changed = [i for i in range(29) if current[i] != target_vector[i]]
            for i in changed:
                route = self.route(i,current[i],target_vector[i])
                origin_hash = self.vector(r['original'])[i]
                if self.original(i).exists() or self.legacy_dir is not None and current[i] != origin_hash:
                    other = self.route(i,origin_hash,target_vector[i])
                    if other is not None and (route is None or len(other) < len(route)): route = other
                H.need(route is not None,'Required original backup is unavailable')
                for edge in route: self.payload(edge)
            game_space = sum(max(self.node_maps[i].values()) for i in changed)*4 + 268435456
            H.need(shutil.disk_usage(self.root).free >= game_space,'Insufficient game staging space')
            H.mkdir(self.directory)
            original_bytes = sum(self.node_maps[i][self.vector(r['original'])[i]] for i in changed if not self.original(i).exists())
            cache_size = Path(self.loc.cache).stat().st_size if self.loc.cache is not None and Path(self.loc.cache).exists() else 0
            H.need(shutil.disk_usage(self.directory).free >= original_bytes + 3*cache_size + 268435456,'Insufficient backup/cache space')
            self.import_backups(r,current)
            j = dict(id=uuid.uuid4().hex,phase='preparing',**{'from':r['current']},to=target,changed=changed,
                     settingsBefore=H.encode(raw),settingsAfter=H.encode(desired_settings),cache=None)
            stage = H.mkdir(self.stage(j)); r['pending'] = j; self.save(r)
            committed = False
            try:
                self.loc.point('preparing')
                paths = {f['path']:self.file(i) for i,f in enumerate(self.m['files'])}
                for i in changed:
                    H.copy_new(self.file(i),stage/('undo-%d.bin'%i),current[i])
                    paths[self.m['files'][i]['path']] = self.materialize(i,current[i],target_vector[i],r,stage)
                    original = self.original(i); h = self.vector(r['original'])[i]
                    if not original.exists():
                        H.need(current[i] == h,'Missing original backup')
                        temp = self.directory/('.origin-'+j['id']+'-%d.tmp'%i)
                        try: H.copy_new(self.file(i),temp,h); os.rename(temp,original)
                        finally:
                            if temp.exists(): H.guard(temp).unlink()
                    H.verify(original,h,self.node_maps[i][h]); self.log('준비 / Ready: '+self.m['files'][i]['path'])
                j['cache'] = C.prepare(self.loc.cache,self.m,target,paths,self.cache_temp(j),self.log)
                if j['cache']:
                    H.copy_new(self.loc.cache,stage/'cache-before.raw',j['cache']['before'])
                    archive = self.directory/('cache-'+j['id']+'.raw')
                    H.copy_new(stage/'cache-before.raw',archive,j['cache']['before'])
                self.loc.stopped(); H.need(self.inspect() == current,'Game changed while preparing')
                H.need(H.read_settings(self.loc.settings) == raw,'Settings changed while preparing')
                if j['cache']: H.verify(self.loc.cache,j['cache']['before'])
                j['phase'] = 'prepared'; self.save(r); committed = True; self.loc.point('prepared')
                for i in changed:
                    self.loc.stopped(); H.atomic(self.file(i),stage/('ready-%d.bin'%i),current[i],target_vector[i])
                    self.log('적용 / Applied: '+self.m['files'][i]['path']); self.loc.point('file-'+str(i))
                H.need(self.inspect() == target_vector,'Final game hashes differ')
                if j['cache']:
                    self.loc.stopped(); H.atomic(self.loc.cache,self.cache_temp(j),j['cache']['before'],j['cache']['after'])
                self.loc.point('cache'); self.commit_settings(raw,desired_settings,j); self.loc.point('settings')
                C.verify_target(self.loc.cache,self.m,target)
                r['current'],r['pending'] = target,None; self.save(r); committed = False; self.cleanup(j)
                self.log('PASS: '+target+'; files/settings/cache verified. Backup: '+str(self.directory))
            except BaseException:
                if committed:
                    r['pending'] = j
                    try: self.recover(r)
                    except BaseException as recovery:
                        self.log('RECOVERY REQUIRED: '+str(recovery)+'; '+str(self.directory))
                else:
                    # An initial receipt still owns preparation, even when decode fails.
                    r['pending'] = j
                    try: self.recover(r)
                    except BaseException as recovery: self.log('PREPARATION CLEANUP REQUIRED: '+str(recovery))
                raise
            return target
