"""Bounded XTAF/SVOD cache refresh; checkpoints and unowned bytes remain exact. MIT."""
from pathlib import Path
import hashlib, struct
from host import need, reading, guard, sha, digest

CLUSTER, DATA, FAT = 65536, 0x12000, 4096
MAX_ASSET = 268435456

def read(stream, offset, count):
    need(offset >= 0 and count >= 0 and offset + count <= stream.seek(0, 2), 'Cache read out of bounds')
    stream.seek(offset); result = stream.read(count)
    need(len(result) == count, 'Short cache read'); return result

def be16(data, at): return struct.unpack_from('>H', data, at)[0]
def be32(data, at): return struct.unpack_from('>I', data, at)[0]

def inspect(stream, manifest):
    length = stream.seek(0, 2)
    if not length: return []
    need(DATA + CLUSTER <= length <= 4294967296, 'Unsupported XTAF partition size')
    head = read(stream, 0, 16); fat = read(stream, FAT, DATA - FAT)
    need(head[:4] == b'XTAF' and be32(head, 8) == 128 and be32(head, 12) == 1, 'Unsupported XTAF layout')
    need(be16(fat, 0) == 0xfff8 and be16(fat, 2) >= 0xfff8, 'Unsupported FAT header')
    used = set()
    def chain(first):
        result, seen, current = [], set(), first
        while True:
            need(0 < current < len(fat)//2 and current not in seen, 'Invalid/cyclic cache allocation')
            seen.add(current); result.append(current)
            following = be16(fat, current * 2)
            if following >= 0xfff8: break
            need(0 < following < 0xfff0, 'Free/reserved cache cluster')
            current = following
        return result
    def claim(clusters):
        need(not used.intersection(clusters), 'Cross-linked cache allocation')
        used.update(clusters)
    def directory(first):
        clusters = chain(first); need(len(clusters) <= 8, 'Oversized cache directory'); claim(clusters)
        entries = []
        for cluster in clusters:
            base = DATA + (cluster-1)*CLUSTER; data = read(stream, base, CLUSTER)
            for at in range(0, CLUSTER, 64):
                length = data[at]
                if length in (0, 255): return entries
                if length == 229: continue
                need(length <= 42, 'Invalid cache name length')
                name = data[at+2:at+2+length].decode('ascii')
                need(all(32 <= ord(c) <= 126 and c not in '\\/:' for c in name), 'Invalid cache name')
                entries.append(dict(name=name, flags=data[at+1], cluster=be32(data,at+44),
                                    size=be32(data,at+48), record=base+at))
        return entries
    definitions = {d['name'].lower(): d for d in manifest['cacheFiles']}
    roots = directory(1); need(len(roots) <= 3, 'Unexpected cache roots')
    found = []
    for root in roots:
        need(root['flags'] & 16 and root['name'].lower() in ('xbox0','xbox1','xbox2'), 'Unknown cache root')
        for entry in directory(root['cluster']):
            need(not entry['flags'] & 16, 'Nested cache directory unsupported')
            if entry['cluster'] == 0:
                need(entry['size'] == 0, 'Missing cache cluster'); continue
            clusters = chain(entry['cluster']); claim(clusters)
            need(entry['size'] <= len(clusters)*CLUSTER, 'Cached file exceeds allocation')
            definition = definitions.get(entry['name'].lower())
            if definition is None: continue
            need(entry['size'] <= MAX_ASSET, 'Cached asset too large')
            h = hashlib.sha256(); left = entry['size']
            for cluster in clusters:
                take = min(left, CLUSTER)
                if not take: break
                h.update(read(stream, DATA+(cluster-1)*CLUSTER, take)); left -= take
            actual = h.hexdigest()
            need(any(n['sha256'] == actual and n['bytes'] == entry['size'] for n in definition['nodes']),
                 'Unknown cached bytes: ' + entry['name'])
            entry.update(clusters=clusters, definition=definition, sha256=actual)
            found.append(entry)
    return found

class GameFS:
    def __init__(self, files): self.files, self.table = files, None
    def read(self, logical, count):
        need(logical >= 0 and 0 <= count <= MAX_ASSET, 'Invalid game source range')
        result = bytearray()
        while len(result) < count:
            offset = logical + len(result); page, within = divmod(offset, 4096)
            volume, local = divmod(page, 41412); group, slot = divmod(local, 204)
            need(volume < 26, 'Game source escaped volume set')
            take = min(count-len(result), (204-slot)*4096-within)
            with reading(self.files['Game/DefaultPackage.data/Data%04d' % volume]) as stream:
                result.extend(read(stream, (2+group*205+slot)*4096+within, take))
        return bytes(result)
    def payload(self, name):
        if self.table is None:
            head = self.read(0, 2048)
            need(head[:20] == b'MICROSOFT*XBOX*MEDIA', 'Unknown game volume')
            root, size = struct.unpack_from('<II', head, 20)
            need(0 < size <= 1048576 and root >= 32, 'Invalid game root table')
            table = self.read((root-32)*2048, size)
            names, todo, seen = {}, [0], set()
            while todo:
                at = todo.pop()
                need(0 <= at and at+14 <= len(table) and at not in seen, 'Invalid/cyclic game root tree')
                seen.add(at); left, right = struct.unpack_from('<HH', table, at)
                if left: todo.append(left*4)
                if right: todo.append(right*4)
                length = table[at+13]
                need(length > 0 and at+14+length <= len(table), 'Invalid game filename')
                if not table[at+12] & 16:
                    key = table[at+14:at+14+length].decode('ascii').lower()
                    need(key not in names, 'Duplicate root asset')
                    sector, size = struct.unpack_from('<II', table, at+4)
                    need(sector >= 32 and 0 < size <= MAX_ASSET, 'Invalid root asset extent')
                    names[key] = ((sector-32)*2048, size)
            self.table = names
        need(name.lower() in self.table, 'Missing game root asset: ' + name)
        return self.read(*self.table[name.lower()])

def verify_target(path, manifest, target=None):
    if path is None or not Path(path).exists(): return []
    with reading(path) as stream: entries = inspect(stream, manifest)
    if target is not None:
        need(all(e['sha256'] == e['definition']['hashes'][target] for e in entries), 'Stale game cache after install')
    return entries

def prepare(path, manifest, target, files, temporary, log=print, payload_reader=None):
    if path is None or not Path(path).exists(): return None
    path = guard(path); temporary = guard(temporary, False)
    fs = GameFS(files)
    payload_reader = payload_reader or fs.payload
    with reading(path) as source:
        entries = inspect(source, manifest); updates, parts = [], []
        for entry in entries:
            wanted = entry['definition']['hashes'][target]
            if entry['sha256'] == wanted: continue
            payload = payload_reader(entry['definition']['name'])
            need(digest(payload) == wanted and any(n['sha256'] == wanted and n['bytes'] == len(payload)
                 for n in entry['definition']['nodes']), 'Replacement cache payload differs')
            need(len(payload) <= len(entry['clusters'])*CLUSTER, 'Existing cache allocation too small')
            updates.append((entry, payload)); log('캐시 준비 / Cache staged: ' + entry['name'])
        if not updates: return None
        source.seek(0); before = hashlib.file_digest(source, 'sha256').hexdigest(); source.seek(0)
        with temporary.open('xb') as dst:
            while block := source.read(1048576): dst.write(block)
        with temporary.open('r+b') as dst:
            for entry, payload in updates:
                at = 0
                for cluster in entry['clusters']:
                    count = min(CLUSTER, len(payload)-at)
                    if not count: break
                    offset = DATA+(cluster-1)*CLUSTER
                    dst.seek(offset); dst.write(payload[at:at+count]); parts.append((offset,count)); at += count
                need(at == len(payload), 'Short cache write')
                if entry['size'] != len(payload):
                    dst.seek(entry['record']+48); dst.write(struct.pack('>I',len(payload)))
                    parts.append((entry['record']+48, 4))
            dst.flush()
            import os
            os.fsync(dst.fileno())
        verify_target(temporary, manifest, target)
        # Prove every byte outside exactly owned payload/size ranges is equal.
        parts.sort(); need(all(a+n <= b for (a,n),(b,m) in zip(parts, parts[1:])), 'Overlapping cache writes')
        source.seek(0)
        with reading(temporary) as staged:
            position = 0
            while before_bytes := source.read(1048576):
                after_bytes = staged.read(len(before_bytes)); need(len(before_bytes) == len(after_bytes), 'Short cache copy')
                if before_bytes != after_bytes:
                    a,b = bytearray(before_bytes),bytearray(after_bytes)
                    for offset,count in parts:
                        lo,hi = max(position,offset),min(position+len(a),offset+count)
                        if lo < hi: a[lo-position:hi-position] = b[lo-position:hi-position] = bytes(hi-lo)
                    need(a == b, 'Checkpoint or unowned cache bytes changed')
                position += len(before_bytes)
            need(not staged.read(1), 'Cache length changed')
        need(sha(path) == before, 'Cache changed concurrently')
    return dict(before=before, after=sha(temporary), changedAssets=len(updates), unownedBytesExact=True)
