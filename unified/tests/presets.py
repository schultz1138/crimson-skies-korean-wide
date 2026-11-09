"""Compile/test the real preset policy and own UI; never operate on game files.

Run on Windows CI. --compile-only prepares the fixture without executing it
on a host whose policy does not allow unsigned development test programs.
"""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from build import compile_setup
from release import load, require_new_output, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--compile-only', action='store_true')
    args = parser.parse_args()
    out = args.out.resolve()
    require_new_output(out, [args.package.resolve()])
    manifest = load(args.package / 'manifest.json')
    out.mkdir(parents=True)
    fixture = out / 'fixture'
    fixture.mkdir()
    # Compile against the real manifest/release pins, but copy no game/delta data.
    shutil.copyfile(args.package / 'manifest.json', fixture / 'manifest.json')
    compile_dir = out / 'compile'
    compile_setup(fixture, compile_dir)
    shutil.copyfile(HERE / 'PresetTests.cs', compile_dir / 'PresetTests.cs')
    executable = fixture / 'PresetTests.exe'
    compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    command = [str(compiler), '/nologo', '/codepage:65001', '/target:exe', '/main:PresetTests',
               '/out:' + str(executable), *['/r:' + x for x in ['System.Core.dll',
               'System.Windows.Forms.dll', 'System.Drawing.dll', 'System.Web.Extensions.dll', 'System.Xml.dll']],
               *[str(p) for p in sorted(compile_dir.glob('*.cs'))]]
    result = subprocess.run(command, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError((result.stdout + result.stderr).decode('utf-8', 'replace'))
    if args.compile_only:
        print('COMPILED_ONLY: preset UI fixture not executed')
        return
    screenshots = out / 'screenshots'
    result = subprocess.run([str(executable), str(screenshots)], capture_output=True,
                            encoding='utf-8-sig', errors='replace', timeout=60)
    (out / 'results.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    profiles = [line.removeprefix('PROFILE ') for line in result.stdout.splitlines() if line.startswith('PROFILE ')]
    if len(set(profiles)) != 8 or not set(profiles).issubset({p['id'] for p in manifest['profiles']}):
        raise ValueError('Preset UI produced a missing or unexpected profile')
    report = dict(status='PASS_PRESET_UI', profiles=profiles, gameWrites=0,
                  fixturesDistributed=False, manifestSha256=sha(fixture / 'manifest.json'))
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(result.stdout)


if __name__ == '__main__':
    main()
