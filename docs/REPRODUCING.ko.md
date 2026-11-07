# 소스에서 0.11.0 베타 1 재현하기

이 빌드는 공개된 VCDIFF를 디코딩해서 완성 파일을 가져오는 방식이 아닙니다.
직접 작성한 번역·타이밍·글꼴 설정과 코드 생성기를 사용해 게임 파일을 새로 만들고,
그 결과에서 차분 6개와 설치용 ZIP을 다시 생성합니다.

## 필요한 입력

- Windows x64, CPython **3.12 x64**, `pipeline/requirements-win-cp312.txt`의 고정 휠
- 지원 빌드 **2608.3123.1.0의 수정하지 않은 Content 복사본**
- 고정된 Noto Sans CJK KR Bold와 xdelta3 3.2.2
- 설치기·ZIP까지 재현할 때 Windows .NET Framework의 C# 컴파일러

게임 원본은 이 저장소나 소스 ZIP에 포함하지 않습니다. 한글 패치가 적용된 현재
게임 폴더 대신 합법적으로 보유한 **원본 복사본**을 입력으로 사용하세요.
입력 파일 5개의 해시는 `manifest.json`의 `stock` 프로필과 일치해야 합니다.
빌드는 입력을 읽기만 하고 별도의 새 출력 폴더에 결과를 만듭니다.
게임 실행·메모리 수정·저장 데이터 접근은 하지 않습니다.

## 준비

저장소 루트에서 PowerShell을 열고 실행합니다. 아래 경로는 예시입니다.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r pipeline\requirements-win-cp312.txt
.\.venv\Scripts\python.exe pipeline\fetch_dependencies.py --out .deps
```

휠은 Windows x64 / CPython3.12용으로 해시를 고정했습니다. 네트워크를 사용하지
않으려면 같은 휠을 별도로 받아 `--no-index --find-links wheelhouse`로 설치하고,
고정된 `NotoSansCJKkr-Bold.otf`와 `xdelta3.exe`를 의존성 폴더에 준비하세요.
Noto 원본 커밋·해시와 xdelta 공식 ZIP·실행 파일 해시는
`pipeline/fetch_dependencies.py`에 명시되어 있습니다.
라이선스는 저장소의 `licenses/`와 각 도구의 배포 문서를 확인하세요.

## 전체 빌드

```powershell
.\.venv\Scripts\python.exe pipeline\build.py `
  --input-content D:\CrimsonSkies-original\Content `
  --dependencies .deps `
  --out D:\CrimsonSkies-build-001
```

출력 폴더는 **존재하지 않는 새 경로**여야 합니다. 원본 폴더 내부나 그 상위
폴더를 출력으로 지정할 수 없습니다. 공간이 충분한 짧은 경로를 권장합니다.
생성되는 게임 파일과 작업 중간물은 개인 작업 폴더에 보관하고 Git에 올리지 마세요.

주요 결과:

- `generated-content/`: 소스에서 생성한 최종 게임 파일 5개
- `native-work/intermediate-beta1-native/`: 이전 베타 업그레이드 차분의 생성용 기반
- `distribution/CrimsonSkies-KO-Wide-0.11.0-beta.1.zip`: 다시 생성한 설치용 ZIP
- `reproduction-report.json`: 최종 파일·도구·원본 보존·패키지 검증 결과

게임 파일 5개만 검증하려면 같은 명령에 `--game-only`를 붙이세요. 이 모드는
C# 컴파일과 설치용 ZIP 생성을 생략합니다.

## 단계별 소스

- `pipeline/assets/localization/`: 번역과 대사 타이밍·분할 자료
- `pipeline/assets/`: 소유한 원본에서 패키지 추출, 자막·튜토리얼·UI 데이터 편집,
  Noto 글꼴 렌더링, 데이터 아카이브와 Data0000·Data0005 재생성
- `pipeline/native/`: 원본에서 한국어 무전 AOT·하단 자막, UI/HUD·해상도·화면비,
  GPU·4K AA·PE 섹션/예외 처리 정보를 순서대로 생성하는 코드
- `pipeline/package_release.py`: 새 결과에서 VCDIFF 6개·설치기·배포 ZIP 생성
- `pipeline/installer_repro.py`: C# 컴파일러의 두 빌드 식별 필드 정규화

원본 자산은 빌드할 때 소유한 게임에서 추출합니다. 원본 글꼴의 글리프 비트맵을
공개 소스로 복사하지 않습니다. 새 글꼴은 고정된 Noto에서 렌더링합니다.

## 바이트 단위 재현 기준

최종 게임 파일은 `manifest.json`의 대상 해시와 일치해야 합니다. 생성한 이전
베타 Native도 공개된 입력 해시와 대조합니다. 이어서 차분 6개, 설치기와 라이선스·
안내문 등 28개 파일, 마지막 ZIP 전체를 기존 배포본의 해시와 비교합니다.

정확한 설치 ZIP의 SHA-256:

```text
a53382986c5e78aa189a8936249d9771bed7d357019e31c8b219c904f304dc42
```

참조 환경은 CPython3.12.14 / zlib1.3.2, Pillow13.0.0 / FreeType2.14.3 / BASIC
레이아웃, fontTools4.68.0입니다. 네이티브 생성 도구와 Windows C# 컴파일러·참조
어셈블리의 버전·해시는 잠금 파일과 `pipeline/reference-toolchain.json`에 있습니다.
실제 파일 해시가 최종 판정 기준입니다. 다른 압축기·렌더러·컴파일러가 다른
바이트를 만들면 성공으로 간주하지 않고 해당 단계에서 중단합니다.

기존 C# 컴파일러는 COFF 시간과 Module MVID를 매번 다르게 만듭니다.
`installer_repro.py`는 PE/CLI 메타데이터에서 이 두 필드만 찾아 기존 릴리즈의
문서화된 식별값으로 맞춥니다. 코드나 리소스는 패치하지 않으며, 정규화한 EXE의
전체 해시가 기존 설치기와 다르면 결과를 저장하지 않고 실패합니다.

## 번역·후크를 수정할 때

이 빌드의 기본 모드는 이미 공개한 베타를 **정확히 재현**하는 것입니다.
번역이나 코드를 수정하면 기존 대상 해시와 달라지므로 검증 단계가 실패하는 것이
정상입니다. 새 버전의 패치를 만들 때는 수정한 글자 집합·줄바꿈·타이밍·ABI·
HUD 동작을 검증한 뒤 버전·manifest·설치기 고정 해시·재현 기대값을 함께 갱신해야 합니다.
단순히 해시 검사를 끄고 기존 버전으로 배포하지 마세요.

소스 재현 성공은 엔딩까지 모든 장면의 플레이 검증을 뜻하지 않습니다.
게임 내 검증 범위와 남은 항목은 기존 `검증 결과.txt`를 따릅니다.
