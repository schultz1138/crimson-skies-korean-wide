"""Build a draft 2611 unified package from exact owned game files and Beta 2 deltas."""
import argparse
from collections import deque
import json
from pathlib import Path
import shutil

from build import compile_setup, load, run, save, sha, TOOL_SHA
from port_2611_gpu import GPU_SHA, port_gpu
from port_2611_native import NEW_NATIVE, OLD_NATIVE, port_native, require
from release import finalize, record_preparation, require_new_output, verify_bundle

RELEASE = 'CrimsonSkies-Unified-0.14.1-alpha.1'
BASE_MANIFEST = '9ab4e7cb79064491500d977fa0287fc28f7323900e8dbe33d9cd8c1b71b4aecd'
BUILD = '2611.323.502.0'
NATIVE = 'xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll'
NEW_GUARDS = {
    'appxmanifest.xml': 'b2bc453cc00c3a89d968f9106a9c71393a49e558570902561608944b8551c284',
    'EmuMenu/EmuMenu.dll': 'c90fdefb9a87030c324a18af05df4900805a8f3878dc48274e33efa1098f63af',
}


def route(edges, start, target):
    pending = deque([(start, [])])
    seen = {start}
    while pending:
        current, path = pending.popleft()
        if current == target:
            return path
        for edge in edges:
            if edge['source'] == current and edge['target'] not in seen:
                seen.add(edge['target'])
                pending.append((edge['target'], path+[edge]))
    raise ValueError('No pinned delta path to ' + target)


def build(stock, previous_native, beta, out):
    stock, previous_native, beta, out = (p.resolve() for p in (stock,previous_native,beta,out))
    require_new_output(out, [stock, previous_native.parent, beta, Path(__file__).resolve().parent.parent])
    require(sha(beta/'manifest.json') == BASE_MANIFEST, 'Use the public Beta 2 bundle')
    manifest, members = verify_bundle(beta)
    tool = beta/'tools/xdelta3.exe'
    require(sha(tool) == TOOL_SHA and sha(previous_native) == OLD_NATIVE, 'Unexpected build source')
    previous_stock = next(x['hashes'] for x in manifest['inputs'] if x['id']=='stock')
    new_hashes = [NEW_NATIVE, GPU_SHA, *previous_stock[2:]]
    for file, expected in zip(manifest['files'], new_hashes):
        require(sha(stock/file['path']) == expected, 'Unexpected stock input: '+file['path'])
    for guard in manifest['guards']:
        path = stock/guard['path']
        require(sha(path) == NEW_GUARDS.get(guard['path'], guard['sha256']),
                'Unexpected guard: '+guard['path'])
        guard.update(sha256=sha(path), bytes=path.stat().st_size)

    work = out/'work'
    work.mkdir(parents=True)
    bundle = out/RELEASE
    for rel in members:
        if rel in ('CrimsonSkiesSetup.exe', 'VERIFICATION.json', 'manifest.json', 'README.md', 'README.en.md'):
            continue
        dest = bundle/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(beta/rel,dest)
    for file in manifest['files'][:2]:
        for edge in file['edges']:
            (bundle/edge['path']).unlink()

    next_id = 1+max(int(Path(e['path']).stem) for file in manifest['files'] for e in file['edges'])
    data = manifest['files'][0]
    variant_paths = {OLD_NATIVE:previous_native}
    native_targets = {OLD_NATIVE:NEW_NATIVE}
    proof = {}
    for old_hash in dict.fromkeys(p['hashes'][0] for p in manifest['profiles']):
        if old_hash == OLD_NATIVE:
            continue
        source = previous_native
        for edge in route(data['edges'], OLD_NATIVE, old_hash):
            key = edge['target']
            if key not in variant_paths:
                decoded = work/(key[:16]+'.old.dll')
                run([tool,'-d','-D','-R','-s',source,beta/edge['path'],decoded])
                require(sha(decoded)==key,'Beta 2 Native decode mismatch')
                variant_paths[key] = decoded
            source = variant_paths[key]
        result, evidence = port_native(previous_native,stock/NATIVE,source)
        dest = work/(old_hash[:16]+'.new.dll')
        dest.write_bytes(result)
        native_targets[old_hash] = sha(dest)
        proof[old_hash] = dict(evidence,target=native_targets[old_hash])
    gpu,diff = port_gpu(stock/'VGPUDX12.dll')
    gpu_path = work/'gpu2611.dll'
    gpu_path.write_bytes(gpu)
    gpu_target = sha(gpu_path)

    def replace_edges(index, variants):
        nonlocal next_id
        row = manifest['files'][index]
        original = stock/row['path']
        paths = {sha(p):p for p in [original,*variants]}
        row['nodes'] = [dict(sha256=h,bytes=p.stat().st_size) for h,p in paths.items()]
        row['edges'] = []
        for variant in variants:
            for source, target in [(original, variant),(variant, original)]:
                rel = f'patches/{next_id:03d}.vcdiff'
                next_id += 1
                delta = bundle/rel
                run([tool,'-e','-9','-D','-R','-s',source,target,delta])
                check = work/'decoded.dll'
                run([tool,'-d','-D','-R','-s',source,delta,check])
                require(sha(check)==sha(target),'2611 generated delta failed reconstruction')
                check.unlink()
                row['edges'].append(dict(source=sha(source),target=sha(target),path=rel,
                                         bytes=delta.stat().st_size,sha256=sha(delta)))

    replace_edges(0,[work/(h[:16]+'.new.dll') for h in proof])
    replace_edges(1,[gpu_path])
    manifest['inputs'] = [dict(id='stock',hashes=new_hashes)]
    manifest['knownExternal'] = []
    for profile in manifest['profiles']:
        hashes = profile['hashes']
        hashes[0] = native_targets[hashes[0]]
        hashes[1] = gpu_target if profile['wide'] else GPU_SHA
    cache_ids = {'stock', *(p['id'] for p in manifest['profiles'])}
    for file in manifest['cacheFiles']:
        file['hashes'] = {key:value for key,value in file['hashes'].items() if key in cache_ids}
    manifest['releaseId'] = RELEASE
    manifest['supportedPackage']['version'] = BUILD
    save(bundle/'manifest.json',manifest)
    compile_setup(bundle,work/'compile')
    docs = Path(__file__).resolve().parent
    for doc in ['README.2611.ko.md','README.2611.en.md']:
        shutil.copyfile(docs/doc,bundle/doc)
    evidence = dict(status='OFFLINE_2611_RECONSTRUCTION',gameBuild=BUILD,
                    dataVolumesReused=26,previousBeta2AssetDeltaCount=sum(len(f['edges']) for f in manifest['files'][2:]),
                    nativeVariants=proof,gpu=diff,gameplayVerified=False)
    save(bundle/'VERIFICATION.json',evidence)
    record_preparation(bundle,out/'preparation.json')
    artifact = finalize(bundle,out/'preparation.json',out/'release')
    print(json.dumps(artifact,ensure_ascii=False),flush=True)


if __name__=='__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('stock','previous-native','beta','out'):
        cli.add_argument('--'+name,type=Path,required=True)
    args = cli.parse_args()
    build(args.stock,args.previous_native,args.beta,args.out)
