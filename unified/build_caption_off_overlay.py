"""Rebuild caption-off patch data from the maintainer's owned inputs."""
from pathlib import Path
import argparse
import copy
import json
import os
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from voice_only_assets import build_variant
from caption_off_overlay import BASE_MANIFEST
from release import load, save, sha, BASE_TOOL, verify_bundle


def build(stock, full_dub, bundle, out):
    stock, full_dub, bundle, out = [Path(path).resolve() for path in (stock, full_dub, bundle, out)]
    if out.exists() or any(out.is_relative_to(path) or path.is_relative_to(out) for path in (stock, full_dub, bundle)):
        raise ValueError('Use a new separate output')
    manifest, _ = verify_bundle(bundle)
    tool = bundle / 'tools/xdelta3.exe'
    if sha(tool) != BASE_TOOL:
        raise ValueError('Decoder pin mismatch')
    environment = os.environ.copy()
    environment.pop('XDELTA', None)
    def run(arguments):
        subprocess.run([str(tool), *map(str, arguments)], check=True, env=environment,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    out.mkdir(parents=True)
    foundation = out / 'foundation'
    for index in (3, 8):
        row = manifest['files'][index]
        baseline = next(item for item in manifest['inputs'] if item['id'] == 'stock')['hashes'][index]
        desired = next(item for item in manifest['profiles'] if item['id'] == 'k1-w1-d0-original')['hashes'][index]
        source = stock / row['path']
        if sha(source) != baseline:
            raise ValueError('Owned stock input mismatch')
        edge = next(item for item in row['edges'] if item['source'] == baseline and item['target'] == desired)
        patch = bundle / edge['path']
        if sha(patch) != edge['sha256']:
            raise ValueError('Foundation delta mismatch')
        destination = foundation / row['path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        run(['-d', '-D', '-R', '-s', source, patch, destination])
        if sha(destination) != desired:
            raise ValueError('Foundation decode mismatch')
    overlay_dir = out / 'overlay'
    (overlay_dir / 'patches').mkdir(parents=True)
    rows, nodes, edges, updates = [], [], [], []
    edge_id = max(int(Path(edge['path']).stem) for file in manifest['files'] for edge in file['edges']) + 1
    for variant, localized, dubbed in [('foundation', foundation, False), ('full-dub', full_dub, True)]:
        fixed = out / (variant + '-fixed')
        proof = build_variant(stock, localized, fixed, variant)
        rows.append(proof)
        relative = proof['path']
        source, target = localized / relative, fixed / relative
        before, after = sha(source), sha(target)
        nodes.append(dict(sha256=after, bytes=target.stat().st_size))
        for fr, to in ((source, target), (target, source)):
            rel = f'patches/{edge_id:03d}.vcdiff'
            edge_id += 1
            patch = overlay_dir / rel
            run(['-e', '-9', '-D', '-R', '-s', fr, to, patch])
            decoded = out / 'roundtrip.bin'
            run(['-d', '-D', '-R', '-s', fr, patch, decoded])
            if sha(decoded) != sha(to):
                raise ValueError('Caption-off delta roundtrip mismatch')
            decoded.unlink()
            edges.append(dict(source=sha(fr), target=sha(to), path=rel,
                              bytes=patch.stat().st_size, sha256=sha(patch)))
        for widescreen in (0, 1):
            updates.append(dict(id=f'k1-w{widescreen}-d{int(dubbed)}-off', before=before, after=after))
    overlay = dict(schema=1, baseManifestSha256=BASE_MANIFEST, fileIndex=8,
                   nodes=nodes, edges=edges, profileUpdates=updates, proofs=rows)
    save(overlay_dir / 'overlay.json', overlay)
    return dict(overlay=str(overlay_dir), nodes=nodes, deltas=len(edges))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('stock', 'full-dub', 'bundle', 'out'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.stock, args.full_dub, args.bundle, args.out), indent=2))
