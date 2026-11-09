"""Make a small portable compatibility probe with artificial data, no game bytes."""
from pathlib import Path
import argparse, json, shutil, sys, zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_sandbox import TOOL, build, relative, sha

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--fixture-bundle', type=Path, required=True)
parser.add_argument('--fixture-stock', type=Path, required=True)
parser.add_argument('--notices-from', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()

assert sha(args.notices_from / 'tools/xdelta3.exe') == TOOL
# Do not let a mistaken --fixture-stock argument package owned game assets.
# These exact synthetic strings come from unified/tests/transactions.py.
fixture = json.loads((args.fixture_bundle / 'manifest.json').read_text('utf-8-sig'))
assert len(fixture['files']) == 29
for i, file in enumerate(fixture['files']):
    relative(file['path'])
    with (args.fixture_stock / file['path']).open('rb') as stream:
        data = stream.read(4097)
    prefix = ('owned synthetic fixture / file%d / ' % i).encode('ascii')
    line = data[:len(prefix) + 65]
    assert len(data) <= 4096 and line.startswith(prefix) and line.endswith(b'\n')
    assert len(line) == len(prefix) + 65 and data == line * 16
    assert all(c in b'0123456789abcdef' for c in line[len(prefix):-1])
for guard in fixture['guards']:
    relative(guard['path'])
    if guard['path'] == 'appxmanifest.xml':
        x = fixture['supportedPackage']
        expected = ('<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"><Identity Name="'
                    + x['name'] + '" Version="' + x['version'] + '" ProcessorArchitecture="'
                    + x['architecture'] + '" Publisher="' + x['publisher'] + '"/></Package>').encode()
    else:
        expected = ('synthetic guard: ' + guard['path']).encode()
    assert (args.fixture_stock / guard['path']).read_bytes() == expected
build(args.fixture_bundle, args.fixture_stock, args.out, fixture=True)
shutil.copytree(args.notices_from / 'licenses', args.out / 'licenses', dirs_exist_ok=True)
for name in ['LICENSE', 'THIRD-PARTY-NOTICES.txt', 'FONT-NOTICE.txt']:
    shutil.copyfile(args.notices_from / name, args.out / name)
instructions = '''SAC 켜진 PC에서 BAT + xdelta 실제 패치 동작 확인하기

이 ZIP은 인위적으로 만든 시험 파일만 포함합니다. 게임을 설치할 필요가 없습니다.
실제 설치된 게임, 설정, 캐시, 저장 데이터에는 접근하지 않습니다.

1. SAC가 켜진 PC에서 이 ZIP을 다운로드하고 Windows 기본 압축 풀기로 해제합니다.
   경로에는 공백·한글을 사용할 수 있습니다. 괄호, %, !, & 등 특수문자는 피하세요.
2. Sandbox-Test.cmd를 더블 클릭합니다. 차단된다면 그 화면과 차단 파일 이름을 기록합니다.
   보안 설정이나 다운로드 출처 표식을 바꾸지 않은 결과가 필요합니다.
3. 첫 메뉴에서 3(한국어 더빙만), 와이드 Y, 작업 2(복사본에 적용)를 고릅니다.
   실제 게임 음성 대신 작은 가상 파일에 동일한 xdelta 경로를 적용합니다.
4. RESULT: PASS를 확인합니다. 이는 버전 조회가 아니라 실제 차분 적용·해시 검증입니다.
5. 아무 키나 누르고, 첫 메뉴 1, 와이드 N, 작업 1(상태 검사)을 고릅니다.
   현재 적용된 상태 6의 29개 파일과 4개 가드가 맞는지 검사합니다.
6. 다시 메뉴에서 첫 메뉴 1, 와이드 N, 작업 3(원복)을 고릅니다.
   RESULT: PASS 뒤 작업 4로 종료합니다.

메뉴 1..4와 와이드 Y/N을 조합하면 8개 프리셋을 시험할 수 있습니다.
다른 프리셋을 적용하기 전에는 원복하세요. State/original 백업은 보존됩니다.
시험 뒤 이 폴더 안 Sandbox/Content만 변경됩니다.

주의: 실제 SAC 상태와 실행 결과는 별도 검증 기록에서 확인하세요.
특정 PC에서 허용되어도 다운로드 경로·다른 PC·수정된 게임 DLL까지 허용된다는 보장은 아닙니다.
한글 메뉴는 별도 UTF-8 텍스트로 표시하며, 실행되는 CMD 명령문은 ASCII만 사용합니다.
현재 공개된 Beta 1 게임 설치기와 별개의 실험입니다.
'''
(args.out / 'START_HERE.ko.txt').write_text(instructions, encoding='utf-8')
executables = sorted(str(p.relative_to(args.out)).replace('\\', '/') for p in args.out.rglob('*.exe'))
assert executables == ['tools/xdelta3.exe'], executables
assert not (args.out / 'State').exists()
assert not list(args.out.rglob('*.py'))
inventory = {str(p.relative_to(args.out)).replace('\\', '/'): sha(p)
             for p in args.out.rglob('*') if p.is_file()}
(args.out / 'FILE-HASHES.json').write_text(json.dumps(inventory, indent=2) + '\n', encoding='utf-8')
archive = args.out.with_suffix('.zip')
assert not archive.exists()
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as stream:
    for path in sorted(args.out.rglob('*')):
        if path.is_file():
            stream.write(path, str(Path(args.out.name) / path.relative_to(args.out)))
report = dict(zip=str(archive), bytes=archive.stat().st_size, sha256=sha(archive),
              files=len(inventory) + 1, executables=executables,
              gameBytesIncluded=False, SACCompatibility='UNVERIFIED')
archive.with_suffix('.zip.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report), flush=True)
