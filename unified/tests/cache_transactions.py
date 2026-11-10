"""Exercise atomic title-cache updates on an isolated synthetic XTAF image."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CLUSTER, DATA = 65536, 0x12000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def image(payload, crosslink=False):
    raw = bytearray(b'\x5a' * (DATA + 7 * CLUSTER))
    raw[:16] = b'XTAF' + struct.pack('>III', 1234, 128, 1)
    raw[4096:DATA] = bytes(DATA - 4096)
    for index, value in enumerate((0xfff8, 0xffff, 0xffff, 0xffff, 0xffff)):
        struct.pack_into('>H', raw, 4096 + index * 2, value)
    def entry(at, name, flags, cluster, size):
        name = name.encode('ascii')
        raw[at:at + 64] = bytes(64)
        raw[at:at + 2] = bytes((len(name), flags))
        raw[at + 2:at + 2 + len(name)] = name
        struct.pack_into('>II', raw, at + 44, cluster, size)
    raw[DATA:DATA + CLUSTER] = bytes(CLUSTER)
    raw[DATA + CLUSTER:DATA + 2 * CLUSTER] = bytes(CLUSTER)
    entry(DATA, 'Xbox2', 16, 2, 0)
    entry(DATA + CLUSTER, 'data.zip', 0, 3, len(payload))
    entry(DATA + CLUSTER + 64, 'checkpoint.dat', 0, 3 if crosslink else 4, 32)
    entry(DATA + CLUSTER + 128, 'cache_good.txt', 0, 0, 0)
    raw[DATA + 2 * CLUSTER:DATA + 2 * CLUSTER + len(payload)] = payload
    raw[DATA + 3 * CLUSTER:DATA + 3 * CLUSTER + 32] = b'USER CHECKPOINT DO NOT MODIFY!!!\0'
    return bytes(raw)


HARNESS = r'''
using System;using System.IO;using CrimsonSkiesUnified;
class CacheHarness {static int Main(string[] args){try{
 PatchEngine.BackupOverride=Path.Combine(args[0],"backups");
 PatchEngine.GameCacheFixturePath=Path.Combine(args[0],"cache.raw");
 PatchEngine.GameCacheFixturePayload=Path.Combine(args[0],"payload.bin");
 new PatchEngine(AppDomain.CurrentDomain.BaseDirectory,Console.WriteLine).FixtureGameCache(Path.Combine(args[0],"Content"),args[1],args[2]=="rollback");
 return 0;
}catch(Exception e){Console.Error.WriteLine(e.Message);return 1;}}}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or out.is_relative_to(REPO):
        raise ValueError('Use a new isolated fixture output')
    out.mkdir(parents=True)
    package, compile_dir = out / 'package', out / 'compile'
    package.mkdir(); compile_dir.mkdir()
    original, updated = b'old owned asset', b'new owned asset with a longer payload'
    manifest = json.loads((args.package / 'manifest.json').read_text('utf-8-sig'))
    ids = {item['id'] for group in ('inputs', 'profiles', 'knownExternal') for item in manifest[group]}
    manifest['cacheFiles'] = [dict(name='data.zip', nodes=[dict(sha256=sha(payload), bytes=len(payload))
                                                      for payload in (original, updated)],
                                 hashes={ident: sha(original if ident == 'stock' else updated) for ident in ids})]
    def save_manifest(value):
        (package / 'manifest.json').write_text(json.dumps(value), encoding='utf-8')
        (compile_dir / 'Pins.cs').write_text('namespace CrimsonSkiesUnified {public static class Pins {public const string Manifest="' +
                                           sha((package / 'manifest.json').read_bytes()) + '";public const string ReleaseId="' + value['releaseId'] + '";}}')
    save_manifest(manifest)
    for name in ('Engine.cs', 'HostManifest.cs', 'Settings.cs', 'Selection.cs', 'GameCache.cs'):
        shutil.copyfile(REPO / 'unified/source' / name, compile_dir / name)
    for name, source in (('VoiceCache.cs', 'dubbing/audio/VoiceCache.cs'), ('Resolution.cs', 'source/SelectionMigration.cs')):
        (compile_dir / name).write_text((REPO / source).read_text('utf-8').replace('namespace CrimsonSkiesKoreanPatch', 'namespace CrimsonSkiesUnified'), encoding='utf-8')
    (compile_dir / 'Harness.cs').write_text(HARNESS)
    exe = package / 'CacheHarness.exe'
    compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    def compile_fixture():
        result = subprocess.run([str(compiler), '/nologo', '/codepage:65001', '/define:UNIFIED_TEST', '/target:exe', '/out:' + str(exe),
                                 '/r:System.Core.dll', '/r:System.Web.Extensions.dll', '/r:System.Xml.dll',
                                 *map(str, compile_dir.glob('*.cs'))], capture_output=True)
        if result.returncode:
            raise RuntimeError((result.stdout + result.stderr).decode('utf-8', 'replace'))
    compile_fixture()
    assertions = 0
    results = []
    def check(condition, message):
        nonlocal assertions
        assertions += 1
        if not condition:
            raise AssertionError(message)
    def run(name, payload=original, desired=updated, target='k1-w1-d1-off', rollback=False, bad_link=False, expect=0):
        root = out / name
        root.mkdir(); (root / 'Content').mkdir()
        before = image(payload, bad_link)
        (root / 'cache.raw').write_bytes(before)
        (root / 'payload.bin').write_bytes(desired)
        result = subprocess.run([str(exe), str(root), target, 'rollback' if rollback else 'commit'],
                                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=30)
        (root / 'fixture.log').write_bytes(result.stdout + result.stderr)
        check(result.returncode == expect, name + ': ' + (result.stdout + result.stderr).decode('utf-8', 'replace'))
        after = (root / 'cache.raw').read_bytes()
        if expect != 0 or rollback or target == 'stock':
            check(after == before, name + ': source cache changed')
        else:
            start = DATA + 2 * CLUSTER
            check(after[start:start + len(desired)] == desired, 'desired bytes not applied')
            check(struct.unpack_from('>I', after, DATA + CLUSTER + 48)[0] == len(desired), 'directory size not updated')
            masked_before, masked_after = bytearray(before), bytearray(after)
            for at, count in ((start, len(desired)), (DATA + CLUSTER + 48, 4)):
                masked_before[at:at + count] = masked_after[at:at + count] = bytes(count)
            check(masked_before == masked_after, 'checkpoint/FAT/marker/unowned bytes changed')
            backups = list((root / 'backups').rglob('before.raw'))
            check(len(backups) == 1 and backups[0].read_bytes() == before, 'missing exact cache backup')
        check(after[DATA + 3 * CLUSTER:DATA + 3 * CLUSTER + 32] == before[DATA + 3 * CLUSTER:DATA + 3 * CLUSTER + 32], 'checkpoint changed')
        check(not list(root.glob('.csassets*')), 'temporary cache files left behind')
        results.append(dict(case=name, exitCode=result.returncode))
    run('update')
    run('rollback', rollback=True)
    run('noop', target='stock')
    run('unknown-cached-bytes', payload=b'unknown asset!!', expect=1)
    run('cross-linked-checkpoint', bad_link=True, expect=1)
    run('unexpected-target-payload', desired=b'unrecognized replacement', expect=1)
    large = b'L' * (CLUSTER + 1)
    manifest['cacheFiles'][0]['nodes'].append(dict(sha256=sha(large), bytes=len(large)))
    manifest['cacheFiles'][0]['hashes']['k1-w1-d1-off'] = sha(large)
    save_manifest(manifest); compile_fixture()
    run('allocation-too-small', desired=large, expect=1)
    report = dict(status='PASS_CACHE_TRANSACTIONS', assertions=assertions, operations=results,
                  checkpointAndUnownedBytesPreserved=True)
    (out / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
