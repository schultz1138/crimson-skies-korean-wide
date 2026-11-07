# Transaction fixtures

From the repository root, on Windows with Python 3.12, the .NET Framework C#
compiler and the pinned xdelta3 dependency:

```powershell
python multilingual/tests/run_core_fixtures.py --source-dir multilingual/launcher --xdelta .deps/xdelta3.exe --work D:/CrimsonSkies-fixtures-001
```

Use a new workspace, separate from the repository. No original game files are
required. The runner creates synthetic Content files and compiles a **fixture
copy** of the production C# core/helper. It never starts the original game/menu,
reads actual user settings, or changes the production sources.

Explicit source clamps replace known file hashes/sizes, private storage paths,
process inventory, launch callbacks and fault-injection hooks. The fixture backup
path is shortened while retaining root/release/catalog separation. Catalog,
ownership, settings, staging, commit and recovery method bodies remain in the
copied production code. Real pinned xdelta decoding and Windows file locks are
used. The generated `results.json` records the exact production and fixture
source identities and clamps.

The current bound run passed **124 outcomes**, including 64 distinct partial
file/settings/receipt states, language roundtrips, launch-failure rollback,
concurrent AA edits, process guards, mutex/held-file checks, tamper rejection and
old-catalog restore before new-catalog activation. This synthetic test does not
prove packaged-app launch context, the native game renderer or physical gameplay.
Full-size production-bundle observations are recorded separately in
[the verification record](../../docs/multilingual-verification.json).

한국어: 새 검사 폴더에서 합성 파일만 생성합니다. 실제 게임·플레이 창·사용자
설정에는 접근하지 않습니다. 테스트용 상수·경로·실행 콜백 치환 범위는 결과 JSON에
기록하며, 실제 게임 화면 검증과 구분합니다.
