"""Apply reviewed caption-off deltas to the pinned public package graph."""
import copy
from pathlib import Path
import json
import hashlib
import shutil

BASE_MANIFEST = '5c7c84d7cc31444ef1b9d54a2bf14d50f8f3de749c3743314ea93fb4484a03cd'
PROFILE_IDS = {f'k1-w{wide}-d{dub}-off' for wide in (0, 1) for dub in (0, 1)}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def apply(manifest, target, folder=None):
    folder = Path(folder) if folder else Path(__file__).with_name('caption-off-overlay')
    overlay = json.loads((folder / 'overlay.json').read_text('utf-8'))
    if overlay.get('schema') != 1 or overlay.get('baseManifestSha256') != BASE_MANIFEST:
        raise ValueError('Unexpected caption-off overlay baseline')
    if overlay.get('fileIndex') != 8 or manifest['files'][8]['path'] != 'Game/DefaultPackage.data/Data0005':
        raise ValueError('Overlay must affect only Data0005')
    updates = overlay['profileUpdates']
    if len(updates) != 4 or {item['id'] for item in updates} != PROFILE_IDS:
        raise ValueError('Overlay must update exactly the four Korean caption-off profiles')
    result = copy.deepcopy(manifest)
    row = result['files'][8]
    old_nodes = {node['sha256'] for node in row['nodes']}
    additions = overlay['nodes']
    new_nodes = {node['sha256'] for node in additions}
    if len(additions) != 2 or len(new_nodes) != 2 or new_nodes & old_nodes:
        raise ValueError('Expected two new caption-off asset identities')
    for item in updates:
        profiles = [profile for profile in result['profiles'] if profile['id'] == item['id']]
        if len(profiles) != 1 or profiles[0]['hashes'][8] != item['before'] or item['after'] not in new_nodes:
            raise ValueError('Caption-off profile source changed')
        profiles[0]['hashes'][8] = item['after']
    expected_pairs = {(item['before'], item['after']) for item in updates}
    expected_pairs |= {(after, before) for before, after in expected_pairs.copy()}
    edges = overlay['edges']
    if len(edges) != 4 or {(edge['source'], edge['target']) for edge in edges} != expected_pairs:
        raise ValueError('Expected forward and reverse caption-off transitions')
    existing = {edge['path'] for file in result['files'] for edge in file['edges']}
    pending = []
    for edge in edges:
        rel = Path(edge['path'])
        if len(rel.parts) != 2 or rel.parts[0] != 'patches' or not rel.stem.isdigit() or len(rel.stem) != 3 or rel.suffix != '.vcdiff':
            raise ValueError('Invalid overlay patch path')
        if edge['path'] in existing or (Path(target) / rel).exists():
            raise ValueError('Overlay patch already exists')
        source = folder / rel
        if source.stat().st_size != edge['bytes'] or sha(source) != edge['sha256']:
            raise ValueError('Overlay delta checksum mismatch')
        pending.append((source, Path(target) / rel))
        existing.add(edge['path'])
    for source, destination in pending:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    row['nodes'].extend(copy.deepcopy(additions))
    row['edges'].extend(copy.deepcopy(edges))
    return result
