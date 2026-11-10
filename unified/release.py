"""Build a verified fan-patch ZIP, with optional strict signature verification.

No installed game files are opened. No certificate is installed, no executable
from the input bundle is launched, and no security policy is changed.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
PRODUCT = 'Crimson Skies Korean Wide'
NEXT_RELEASE = 'CrimsonSkies-Unified-0.14.0-beta.2'
PUBLISHED_RELEASES = {'CrimsonSkies-Unified-0.14.0-alpha.1', 'CrimsonSkies-Unified-0.14.0-beta.1'}
BASE_MANIFEST = '5c7c84d7cc31444ef1b9d54a2bf14d50f8f3de749c3743314ea93fb4484a03cd'
BASE_SETUP = '383a5b8c2e0b8922859e788c18d2b895a2e891e939b77188c72c8673ec1cf886'
BASE_TOOL = '732980d52f9220dc81817ccdd0c295eadce8a0048a24c2a771a73f791ac824e9'
BINARIES = {'CrimsonSkiesSetup.exe', 'tools/xdelta3.exe'}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def load(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def version(release_id):
    match = re.fullmatch(r'CrimsonSkies-Unified-(\d+)\.(\d+)\.(\d+)-(?:alpha|beta)\.(\d+)', release_id)
    need(match is not None, 'Expected a versioned CrimsonSkies-Unified alpha or beta release ID')
    parts = [int(x) for x in match.groups()]
    need(all(x < 65535 for x in parts), 'Version field exceeds assembly limits')
    return '.'.join(str(x) for x in parts)


def pins_source(manifest_sha, release_id):
    version(release_id)
    need(re.fullmatch('[0-9a-f]{64}', manifest_sha), 'Invalid manifest hash')
    return ('namespace CrimsonSkiesUnified {public static class Pins {'
            'public const string Manifest="' + manifest_sha + '";'
            'public const string ReleaseId="' + release_id + '";}}')


def assembly_metadata(release_id):
    numeric = version(release_id)
    informational = release_id.removeprefix('CrimsonSkies-Unified-')
    values = {
        'AssemblyVersion': numeric, 'AssemblyFileVersion': numeric,
        'AssemblyInformationalVersion': informational,
        'AssemblyProduct': PRODUCT,
        'AssemblyTitle': 'Crimson Skies Selective Unified Setup',
        'AssemblyDescription': 'Offline community patch installer for an owned game',
        'AssemblyCompany': 'Crimson Skies Korean Wide contributors',
    }
    return 'using System.Reflection;\n' + ''.join(
        '[assembly:' + key + '("' + value + '")]\n' for key, value in values.items())


def child(root, relative):
    need(isinstance(relative, str) and relative and '\\' not in relative and ':' not in relative,
         'Invalid package path')
    parts = relative.split('/')
    need(all(part not in ('', '.', '..') for part in parts), 'Invalid package path')
    need(not PurePosixPath(relative).is_absolute(), 'Absolute package path')
    path = root.joinpath(*parts)
    need(path.resolve().is_relative_to(root.resolve()), 'Package path escaped root')
    return path


def inventory(bundle):
    """Reject linked files and executable content outside the two known binaries."""
    need(bundle.is_dir(), 'Missing bundle')
    result = {}
    for path in [bundle, *sorted(bundle.rglob('*'))]:
        info = path.lstat()
        need(not path.is_symlink() and not (getattr(info, 'st_file_attributes', 0) & 0x400),
             'Reparse/symlink package entries are not supported')
        if not path.is_file():
            continue
        rel = path.relative_to(bundle).as_posix()
        need(rel in BINARIES or rel in {'manifest.json', 'VERIFICATION.json', 'LICENSE'} or
             (rel.startswith('patches/') and re.fullmatch(r'patches/\d{3}\.vcdiff', rel)) or
             (rel.startswith('licenses/') and path.suffix.lower() == '.txt') or
             ('/' not in rel and path.suffix.lower() in {'.md', '.txt'}),
             'Unexpected package file: ' + rel)
        with path.open('rb') as stream:
            if stream.read(2) == b'MZ':
                need(rel in BINARIES, 'Undeclared executable content: ' + rel)
        result[rel] = sha(path)
    need(BINARIES.issubset(result), 'Missing installer or xdelta tool')
    return result


def verify_bundle(bundle):
    files = inventory(bundle)
    manifest = load(bundle / 'manifest.json')
    version(manifest['releaseId'])
    need(manifest['schema'] == 1 and len(manifest['files']) == 29 and
         len(manifest['profiles']) == 12 and len(manifest['guards']) == 4, 'Unexpected component graph')
    need(manifest['tool']['path'] == 'tools/xdelta3.exe', 'Unexpected decoder path')
    need(files['tools/xdelta3.exe'] == manifest['tool']['sha256'],
         'Decoder hash changed: sign xdelta BEFORE preparing/compiling the installer')
    expected_patches = set()
    for file in manifest['files']:
        for edge in file['edges']:
            rel = edge['path']
            path = child(bundle, rel)
            need(rel in files and files[rel] == edge['sha256'] and path.stat().st_size == edge['bytes'],
                 'Delta hash/size mismatch: ' + rel)
            expected_patches.add(rel)
    need({name for name in files if name.startswith('patches/')} == expected_patches,
         'Unexpected or missing delta files')
    return manifest, files


def pe_code_identity(path):
    """Compare bytes before/after signing, not a replacement for WinVerifyTrust.

    Only the PE checksum, certificate-table directory and appended certificate
    table/alignment are ignored. All code, resources and pre-existing overlays
    must remain identical. This deliberately rejects certificate-table overlays.
    """
    data = bytearray(Path(path).read_bytes())
    need(len(data) >= 64 and data[:2] == b'MZ', 'Not a PE file')
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    need(pe >= 64 and pe + 24 <= len(data) and data[pe:pe+4] == b'PE\0\0', 'Invalid PE header')
    optional = pe + 24
    size = struct.unpack_from('<H', data, pe + 20)[0]
    need(optional + size <= len(data) and size >= 2, 'Truncated optional header')
    magic = struct.unpack_from('<H', data, optional)[0]
    need(magic in (0x10b, 0x20b), 'Unsupported PE format')
    directories = optional + (96 if magic == 0x10b else 112)
    security = directories + 4 * 8
    need(security + 8 <= optional + size, 'Missing certificate directory')
    need(struct.unpack_from('<I', data, directories - 4)[0] >= 5, 'Missing certificate directory')
    offset, length = struct.unpack_from('<II', data, security)
    need((offset == 0) == (length == 0), 'Malformed certificate table')
    if offset:
        need(offset >= optional + size and offset % 8 == 0 and length >= 8 and
             length % 8 == 0 and offset + length == len(data), 'Unsupported certificate table bounds/overlay')
        del data[offset:]
    data[optional+64:optional+68] = b'\0' * 4
    data[security:security+8] = b'\0' * 8
    data.extend(b'\0' * (-len(data) % 8))
    return hashlib.sha256(data).hexdigest()


def verify_signature(path):
    need(os.name == 'nt', 'Trusted Authenticode verification requires Windows')
    # This developer tool requires PowerShell 7, like the GitHub workflow.
    # Never change execution policy or retry a denied script with bypass flags.
    powershell = shutil.which('pwsh')
    need(powershell is not None, 'PowerShell 7 (pwsh) is required for release signature verification')
    process = subprocess.run([powershell, '-NoLogo', '-NoProfile', '-NonInteractive',
                              '-File', str(HERE / 'verify-signature.ps1'), '-LiteralPath', str(path)],
                             capture_output=True, encoding='utf-8-sig', errors='replace', timeout=60)
    if process.returncode:
        raise ValueError('Trusted timestamped signature required for ' + path.name + ': ' +
                         process.stdout.strip() + ' ' + process.stderr.strip())
    result = json.loads(process.stdout)
    need(result.get('Accepted') is True and result.get('Status') == 'Valid' and
         result.get('SignatureType') == 'Authenticode', 'Signature verifier did not accept embedded trust')
    return result


def check_signed_tool(original, signed):
    need(sha(original) == BASE_TOOL, 'Unexpected original xdelta input')
    need(pe_code_identity(original) == pe_code_identity(signed), 'Signed xdelta code differs from the pinned tool')
    return verify_signature(signed)


def source_hashes():
    paths = [*sorted((HERE / 'source').glob('*.cs')), HERE / 'build.py', HERE / 'release.py',
             HERE / 'voice_only_assets.py', HERE / 'caption_off_overlay.py',
             HERE / 'build_caption_off_overlay.py', HERE / 'caption-off-overlay/overlay.json',
             HERE / 'cache_assets.py', HERE / 'build_cache_assets.py', HERE / 'cache-assets.json',
             HERE / 'verify-signature.ps1', REPO / 'dubbing/audio/VoiceCache.cs',
             REPO / 'source/SelectionMigration.cs']
    return {path.relative_to(REPO).as_posix(): sha(path) for path in paths}


def record_preparation(bundle, report):
    manifest, files = verify_bundle(bundle)
    save(report, dict(schema=1, status='PREPARED',
                     releaseId=manifest['releaseId'], files=files,
                     installerCodeIdentity=pe_code_identity(bundle / 'CrimsonSkiesSetup.exe'),
                     toolCodeIdentity=pe_code_identity(bundle / 'tools/xdelta3.exe'),
                     sourceHashes=source_hashes(), gameplayVerified=False))


def require_new_output(out, inputs):
    need(not out.exists(), 'Use a new output directory')
    for path in [REPO, *inputs]:
        path = path.resolve()
        need(not out.is_relative_to(path) and not path.is_relative_to(out), 'Output overlaps an input/source')


def prepare(bundle, out, signed_xdelta=None, release_id=NEXT_RELEASE):
    """Rebuild only the installer from pinned public deltas; never decode them."""
    version(release_id)
    need(release_id not in PUBLISHED_RELEASES, 'Keep published releases immutable; use a new release ID')
    bundle, out = bundle.resolve(), out.resolve()
    require_new_output(out, [bundle])
    need(sha(bundle / 'manifest.json') == BASE_MANIFEST and sha(bundle / 'CrimsonSkiesSetup.exe') == BASE_SETUP,
         'Use the exact public alpha.1 input bundle')
    manifest, _ = verify_bundle(bundle)
    need(manifest['tool']['sha256'] == BASE_TOOL, 'Unexpected baseline tool')
    if signed_xdelta:
        check_signed_tool(bundle / 'tools/xdelta3.exe', signed_xdelta)
    out.mkdir(parents=True)
    target = out / release_id
    shutil.copytree(bundle, target, ignore=shutil.ignore_patterns('VERIFICATION.json'))
    if '-beta.' in release_id:
        if str(HERE) not in sys.path:
            sys.path.insert(0, str(HERE))
        from caption_off_overlay import apply
        manifest = apply(manifest, target)
        from cache_assets import inject
        manifest = inject(manifest)
    if signed_xdelta:
        shutil.copyfile(signed_xdelta, target / 'tools/xdelta3.exe')
    manifest['releaseId'] = release_id
    manifest['tool']['sha256'] = sha(target / 'tools/xdelta3.exe')
    save(target / 'manifest.json', manifest)
    for name in ['README.md', 'README.en.md']:
        text = (HERE / name).read_text('utf-8')
        text = text.replace('0.14.0-alpha.1', release_id.removeprefix('CrimsonSkies-Unified-'))
        text = text.replace('0.14.0 Alpha 1', release_id.removeprefix('CrimsonSkies-Unified-'))
        (target / name).write_text('> Packaging checks do not certify gameplay. See the separate release verification record.\n\n' + text, encoding='utf-8')
    shutil.copyfile(HERE / 'SIGNING.md', target / 'SIGNING.md')
    # Also work with isolated/embedded Python distributions that omit script dirs.
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    from build import compile_setup
    compile_setup(target, out / 'compile')
    record_preparation(target, out / 'preparation.json')
    return dict(status='PREPARED', bundle=str(target),
                signedDecoderProvided=bool(signed_xdelta), archiveCreated=False)


def finalize(bundle, preparation, out, require_signatures=False, require_installer_signature=False):
    need(not (require_signatures and require_installer_signature), 'Choose one signature scope')
    bundle, preparation, out = bundle.resolve(), preparation.resolve(), out.resolve()
    require_new_output(out, [bundle, preparation])
    report = load(preparation)
    need(report['schema'] == 1 and report['status'] in {'PREPARED', 'PREPARED_NOT_A_SIGNED_RELEASE'}, 'Invalid preparation report')
    manifest, files = verify_bundle(bundle)
    need(manifest['releaseId'] == report['releaseId'], 'Release identity changed')
    need(manifest['releaseId'] not in PUBLISHED_RELEASES, 'Keep published releases immutable; use a new release ID')
    need(set(files) == set(report['files']), 'Package inventory changed after preparation')
    for rel, digest in files.items():
        if rel != 'CrimsonSkiesSetup.exe':
            need(digest == report['files'][rel], 'Package changed after preparation: ' + rel)
    need(pe_code_identity(bundle / 'CrimsonSkiesSetup.exe') == report['installerCodeIdentity'],
         'Installer code/resources changed after preparation')
    need(pe_code_identity(bundle / 'tools/xdelta3.exe') == report['toolCodeIdentity'], 'Decoder code changed')
    signatures = {}
    signed_mode = require_signatures or require_installer_signature
    if signed_mode:
        scope = sorted(BINARIES) if require_signatures else ['CrimsonSkiesSetup.exe']
        signatures = {rel: verify_signature(bundle / rel) for rel in scope}
        installer = signatures['CrimsonSkiesSetup.exe']
        need(installer['ProductName'] == PRODUCT and installer['FileVersion'] == version(manifest['releaseId']),
             'Installer product/version metadata mismatch')
    else:
        # The normal unsigned path requires every prepared byte to stay exact.
        # Only the opt-in signed path permits a post-build Authenticode change.
        need(files['CrimsonSkiesSetup.exe'] == report['files']['CrimsonSkiesSetup.exe'],
             'Installer file changed after preparation')
    # Validation above must succeed before creating any publishable archive.
    out.mkdir(parents=True)
    archive = out / (manifest['releaseId'] + '.zip')
    temporary = out / (archive.name + '.partial')
    try:
        with zipfile.ZipFile(temporary, 'x', zipfile.ZIP_DEFLATED, compresslevel=9) as packed:
            for rel in sorted(files):
                packed.write(child(bundle, rel), manifest['releaseId'] + '/' + rel)
        # Confirm that compression read exactly the bytes already verified.
        with zipfile.ZipFile(temporary) as packed:
            for rel, expected in files.items():
                digest = hashlib.sha256()
                with packed.open(manifest['releaseId'] + '/' + rel) as stream:
                    for block in iter(lambda: stream.read(1048576), b''):
                        digest.update(block)
                need(digest.hexdigest() == expected, 'Package changed while archiving: ' + rel)
        temporary.rename(archive)
    finally:
        if temporary.exists():
            temporary.unlink()
    status = ('SIGNATURES_VERIFIED_GAMEPLAY_PENDING' if require_signatures else
              'INSTALLER_SIGNATURE_VERIFIED_GAMEPLAY_PENDING' if require_installer_signature else
              'PACKAGE_VERIFIED_GAMEPLAY_PENDING')
    result = dict(schema=1, status=status, releaseId=manifest['releaseId'],
                  archive=archive.name, bytes=archive.stat().st_size, sha256=sha(archive),
                  manifestSha256=files['manifest.json'], files=files, signatures=signatures,
                  sourceHashes=report['sourceHashes'], gameplayVerified=False, automaticallyPublished=False)
    result['signatureVerification'] = ('verified' if require_signatures else
                                       'installer-only' if require_installer_signature else 'not-requested')
    save(out / 'release-report.json', result)
    (out / 'SHA256SUMS.txt').write_text(result['sha256'] + '  ' + archive.name + '\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare', help='Compile a candidate from the pinned public bundle')
    prep.add_argument('--bundle', required=True, type=Path)
    prep.add_argument('--out', required=True, type=Path)
    prep.add_argument('--signed-xdelta', type=Path)
    prep.add_argument('--release-id', default=NEXT_RELEASE)
    final = sub.add_parser('finalize', help='Verify pinned package files and create the normal fan-patch ZIP')
    final.add_argument('--bundle', required=True, type=Path)
    final.add_argument('--preparation', required=True, type=Path)
    final.add_argument('--out', required=True, type=Path)
    signing = final.add_mutually_exclusive_group()
    signing.add_argument('--require-signatures', action='store_true', help='Optional: require trusted timestamped signatures on both EXEs')
    signing.add_argument('--require-installer-signature', action='store_true', help='Verify only the project-owned installer signature; keep decoder hash/code verification')
    args = parser.parse_args()
    if args.command == 'prepare':
        result = prepare(args.bundle, args.out, args.signed_xdelta, args.release_id)
    else:
        result = finalize(args.bundle, args.preparation, args.out, args.require_signatures, args.require_installer_signature)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
