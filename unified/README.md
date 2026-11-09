# Crimson Skies 선택형 통합 설치기 — 0.14.0 Alpha 1

소유한 Windows x64 게임 **2608.3123.1.0**에 필요한 기능을 한 번에
설치하는 오프라인 시험본입니다. 원본 게임 파일은 포함하지 않습니다.
더빙 음성은 제작 완료된 차분 데이터로 적용합니다. API 키가 필요 없습니다.

[GitHub 다운로드](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.14.0-alpha.1) · [English](README.en.md)
실행용 ZIP은 `CrimsonSkies-Unified-0.14.0-alpha.1.zip`이며 소스 ZIP은 별도입니다.

## Code signing policy

현재 공개 Alpha 1의 설치기와 동봉 xdelta는 미서명 상태이며, Smart App Control이
켜진 PC에서 설치기 실행 차단을 재현했습니다. [서명 준비와 남은 조건](SIGNING.md)을
확인하세요. Alpha 2는 서명 준비 후보이며 아직 서명된 수정 배포본이 아닙니다.

## 설치

1. 게임과 `플레이` 창을 종료하고 ZIP 전체를 새 폴더에 풉니다.
2. `CrimsonSkiesSetup.exe`를 실행하고 게임 폴더 또는 `Content`를 선택합니다.
3. 필요한 항목을 고른 뒤 **상태 검사 → 선택 항목 설치**를 누릅니다.
4. 완료 후 **플레이 창 열기**로 기존 실행기를 열어 플레이합니다.

별도의 0.11 설치 과정을 거치지 않고 정확한 원본에서 시작할 수 있습니다.
기존 0.11 기반 패치도 지원합니다. 기존 Alpha2 더빙/자막이나 0.12 언어팩은
이전 도구로 먼저 복구하세요. Alpha2는 **자막 복구 → 음성 복구** 순서입니다.
이전 도구의 백업 기록을 통합 설치기의 복구 기록으로 가져오지는 않습니다.

## 선택 항목

| 항목 | 동작 |
| --- | --- |
| 한글화 | 한글 메뉴·글꼴·기본 영상 번역 데이터 |
| 와이드스크린·고해상도 | 4:3/16:9 자동 전환, 최대 4K, HUD 보정, 4K AA 유지 |
| 한국어 더빙 | 무전·컷신 한국어 음성. 필요한 한글화가 함께 선택됩니다. |
| 원문 번역 자막 | 기존 번역의 무전·게임 내 컷신·영상 자막 |
| 더빙 대사 자막 | 실제 한국어 더빙 스크립트에 맞춘 자막. 한글화·더빙이 함께 선택됩니다. |
| 기본 영상 자막만 | 추가 무전·게임 내 컷신 자막을 끄고 게임의 영상 자막은 유지 |

와이드스크린은 단독으로 설치할 수 있습니다. 모두 해제하고 설치하면 원본
구성으로 전환합니다. 설치 이후 항목을 바꾸고 같은 도구에서 다시 설치할 수
있습니다. 내장 언어 설정은 한글화 선택에 맞춰 연결됩니다.

## 백업과 복구

전체 더빙은 약 **14GB**의 추가 여유 공간을 권장합니다. 필요한 공간을
설치 전에 확인하고, 바뀌는 파일만 백업·준비합니다. 파일 전체 SHA-256을
확인하고 모든 결과를 준비한 뒤 교체합니다. 영상 음성 캐시는 기존 Alpha2와
동일한 제한된 갱신을 사용하며 다른 캐시 데이터와 체크포인트를 보존합니다.

**설치 전 복구**는 이 설치기 첫 실행 직전의 원본 또는 0.11 상태로 돌아갑니다.
중단 기록이 있으면 **중단 작업 복구**를 먼저 실행하세요. 알 수 없는 변경은
덮어쓰지 않습니다. 백업은 아래 위치에 보관되므로 지우지 마세요.

`%LOCALAPPDATA%\CrimsonSkiesUnified\Backups`

설정에서는 언어·해상도 선택만 다룹니다. AA 등 다른 설정과 저장 프로필은
변경하지 않습니다. 설치 중에는 다른 설치기나 게임을 실행하지 마세요.
이 도구가 소유한 설치 상태를 이전 개별 설치기로 변경하면 상태가 달라져
복구가 거부될 수 있으므로 구성 변경은 이 통합 도구에서 진행하세요.

## 소스 빌드

기존 `pipeline/build.py --game-only`로 원본에서 0.11을 재현하고,
`dubbing/build_audio.py`, `dubbing/build_captions.py`로 더빙/자막 대상 파일을
준비합니다. 음성 생성 자체는 이 패키저의 역할이 아닙니다.

```powershell
python unified/build.py --stock D:\owned-stock\Content --foundation D:\source-011\generated-content --full-dub D:\full-dub\Content --dub-captions D:\caption-build\Content --native-work D:\source-011\native-work --xdelta D:\deps\xdelta3.exe --out D:\unified-014-build
```

`stock`, `foundation`, `full-dub`에는 26개 원본 볼륨과 런처/패키지 식별 파일도
준비해야 합니다. 파이프라인이 생성한 변경 파일만 별도 출력에 있다면, 소유한
원본의 **별도 복사본**에 그 결과를 덮어 각 입력 트리를 만드세요. 실제 게임
설치 폴더를 출력으로 사용하지 마세요. `dub-captions`에는 세 변경 파일만 있어도
됩니다. 새로운 출력 폴더를 사용하세요. 배포 ZIP에는 차분·도구·안내만 들어갑니다.

현재 소스 빌드는 Alpha 2 서명 준비 폴더와 `preparation.json`까지만 생성합니다.
공개 ZIP 생성은 두 실행 파일의 신뢰된 서명·타임스탬프를 검사하는
`release.py finalize` 단계로 옮겼습니다. 도구 서명은 manifest 생성 전에
`--signed-xdelta`로 제공해야 합니다. 자세한 순서는 [SIGNING.md](SIGNING.md)를 따릅니다.

선택형 Native는 공개 캡션 컴파일러가 선언한 후크와 디스패치 범위만 원본
명령으로 복구합니다. 와이드스크린을 끄면 공개 0.10 캡션 단계의 Native와
원본 GPU/해상도 메뉴를 사용합니다. 기본 전체 선택의 Native/게임 볼륨은
기존 Alpha2와 같습니다. 기본 전체 선택으로 재설치한 뒤 정상 플레이를 확인했습니다.
다른 선택 조합의 실제 화면과 엔딩까지의 전 구간 검증은 별도로 필요합니다.

설치 소스 MIT, 글꼴 SIL OFL. 원작 및 AI 음성 고지는 포함한 라이선스를 확인하세요.

## 설치기 검사

`tests/transactions.py`는 게임 데이터 대신 작은 합성 파일을 사용하되 실제
구성 그래프와 설치 엔진을 검사합니다. 모든 선택 조합, 오류 시 롤백,
프로세스 강제 종료 후 복구, 백업·차분·원본 변조 거부, 설정 보존을 포함합니다.
`UNIFIED_TEST`로 컴파일하는 테스트 실행기는 배포하지 않습니다.

```powershell
python unified/tests/transactions.py --package D:\unified-014-build\CrimsonSkies-Unified-0.14.0-alpha.2 --out D:\unified-synthetic-001
python unified/tests/owned_roundtrip.py --package D:\unified-014-build\CrimsonSkies-Unified-0.14.0-alpha.2 --stock D:\owned-stock\Content --out D:\unified-owned-test-001
```

두 검사 모두 새 출력 폴더를 요구합니다. 실제 크기 검사는 원본 입력을 별도로
복사하고 테스트 전용 백업·설정 경로를 사용합니다. 설치된 게임을 변경하지 않습니다.
게임 플레이 검사를 대신하는 검사는 아닙니다. 프로필 관리는 기존 별도 런처의
기능이며, 이 시험본 설치 화면에는 포함하지 않습니다.
