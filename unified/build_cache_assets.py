"""Rebuild source-owned asset cache hashes; never write installed game/cache."""
from pathlib import Path
import argparse
import collections
import os
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cache_assets import build, states
from release import verify_bundle, sha, save, BASE_TOOL


def generate(bundle, roots, out):
    bundle, out = Path(bundle).resolve(), Path(out).resolve()
    roots = [Path(root).resolve() for root in roots]
    if out.exists() or any(out.is_relative_to(root) or root.is_relative_to(out) for root in [bundle, *roots]):
        raise ValueError('Use a new separate build output')
    manifest, _ = verify_bundle(bundle)
    tool = bundle / 'tools/xdelta3.exe'
    if sha(tool) != BASE_TOOL:
        raise ValueError('Pinned decoder required')
    sources = {}
    for index, row in enumerate(manifest['files'][3:]):
        for root in roots:
            path = root / row['path']
            if path.is_file():
                digest = sha(path)
                if digest in {node['sha256'] for node in row['nodes']}:
                    sources.setdefault((index, digest), path)
    out.mkdir(parents=True)
    environment = os.environ.copy()
    environment.pop('XDELTA', None)
    for index, row in enumerate(manifest['files'][3:]):
        for desired in {vector[index] for vector in states(manifest).values()}:
            if (index, desired) in sources:
                continue
            queue = collections.deque([(digest, []) for file, digest in sources if file == index])
            visited = set()
            route = None
            while queue:
                current, path = queue.popleft()
                if current in visited:
                    continue
                visited.add(current)
                if current == desired:
                    route = path
                    break
                for edge in row['edges']:
                    if edge['source'] == current:
                        queue.append((edge['target'], path + [edge]))
            if route is None:
                raise ValueError('Owned source cannot reach cache fingerprint state')
            for edge in route:
                key = index, edge['target']
                if key in sources:
                    continue
                patch = bundle / edge['path']
                if sha(patch) != edge['sha256']:
                    raise ValueError('Delta fingerprint mismatch')
                target = out / f'decoded-{index}-{edge["target"]}' / row['path']
                target.parent.mkdir(parents=True)
                subprocess.run([str(tool), '-d', '-D', '-R', '-s', str(sources[index, edge['source']]),
                                str(patch), str(target)], check=True, env=environment,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                if sha(target) != edge['target']:
                    raise ValueError('Decoded cache source mismatch')
                sources[key] = target
    result = build(manifest, sources)
    save(out / 'cache-assets.json', result)
    return dict(states=len(result['gameVectors']), files=len(result['files']),
                metadata=str(out / 'cache-assets.json'))


if __name__ == '__main__':
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--owned-source', type=Path, action='append', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.bundle, args.owned_source, args.out), indent=2))
