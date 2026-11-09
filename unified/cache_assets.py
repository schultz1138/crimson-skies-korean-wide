"""Fingerprint cached root assets for each owned game-data configuration."""
from pathlib import Path
import hashlib
import json
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / 'pipeline/assets'))
from package_io import Package, locate


def states(manifest):
    return {item['id']: item['hashes'][3:] for group in ('inputs', 'profiles', 'knownExternal')
            for item in manifest[group]}


class ProfilePackage(Package):
    def __init__(self, paths):
        self.paths = paths
        super().__init__(Path(paths[0]).parents[2], verify=False)

    def read(self, offset, length):
        if offset < 0 or not 0 <= length <= 268435456:
            raise ValueError('Unbounded asset read')
        result = bytearray()
        while len(result) < length:
            name, physical, within = locate(offset + len(result))
            index = int(name[4:])
            if index not in self.paths:
                raise ValueError('Unknown data volume')
            if name not in self.handles:
                self.handles[name] = Path(self.paths[index]).open('rb')
            stream = self.handles[name]
            stream.seek(physical)
            count = min(length - len(result), 4096 - within)
            part = stream.read(count)
            if len(part) != count:
                raise ValueError('Short owned asset read')
            result += part
        return bytes(result)


def build(manifest, sources):
    vectors = states(manifest)
    packages = {}
    output = {}
    hashed = {}
    try:
        for ident, vector in vectors.items():
            key = tuple(vector)
            if key not in packages:
                packages[key] = ProfilePackage({index: sources[index, digest]
                                                for index, digest in enumerate(vector)})
            package = packages[key]
            for entry in package.entries:
                name, size = entry['name'], entry['size']
                if entry['directory'] or not name.lower().endswith(('.zip', '.bin')):
                    continue
                if not 0 < size <= 268435456 or len(name) > 42 or any(c in name for c in '/\\:'):
                    raise ValueError('Unsupported root cache asset')
                first = (entry['sector'] - 32) * 2048
                lo = (first // 4096) // 41412
                hi = ((first + size - 1) // 4096) // 41412
                identity = (name, first, size, tuple(vector[lo:hi + 1]))
                if identity not in hashed:
                    hashed[identity] = hashlib.sha256(package.read(first, size)).hexdigest()
                digest = hashed[identity]
                row = output.setdefault(name.lower(), dict(name=name, nodes=[], hashes={}))
                node = dict(sha256=digest, bytes=size)
                if node not in row['nodes']:
                    row['nodes'].append(node)
                row['hashes'][ident] = digest
        rows = [output[name] for name in sorted(output)]
        if any(set(row['hashes']) != set(vectors) for row in rows):
            raise ValueError('Cache asset missing from a supported state')
        return dict(schema=1, gameVectors=vectors, files=rows)
    finally:
        for package in packages.values():
            package.close()


def inject(manifest, path=None):
    path = Path(path) if path else Path(__file__).with_name('cache-assets.json')
    metadata = json.loads(path.read_text('utf-8'))
    if metadata.get('schema') != 1 or metadata.get('gameVectors') != states(manifest):
        raise ValueError('Cache fingerprints do not match this package graph')
    manifest['cacheFiles'] = metadata['files']
    return manifest
