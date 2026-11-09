# Crimson Skies 한국어·와이드스크린 통합 패치

## Code signing policy

공개 0.14 Alpha 1 설치기와 xdelta는 미서명이며 Smart App Control 환경에서
설치기 차단이 확인되었습니다. 일반 팬 패치 ZIP 배포에 SignPath 신청이나 서명은
필수가 아닙니다. [일반 배포와 선택적 서명 안내](unified/SIGNING.md)를 확인하세요.

> [!WARNING]
> **설치 전 확인: 현재 공개 배포본은 미서명입니다.**
> Smart App Control(SAC)이 켜져 있고 이 설치기를 차단한다면, 현재 배포본을 설치하려면 SAC를 꺼야 합니다. SAC에는 이 앱만 허용하는 예외 기능이 없습니다.
> **SAC를 끄면 PC 전체의 앱 실행 보호가 줄어들며, 환경에 따라 다시 켤 수 없고 Windows 초기화 또는 재설치가 필요할 수 있습니다.** ‘설치 후 다시 켜기’를 보장하지 않습니다. 실제 Windows 확인창의 안내를 먼저 확인하세요.
> 이 영향을 이해하고 동의하는 사용자만 설치를 진행하세요. SAC를 유지하려면 설치를 보류하고 서명된 업데이트를 기다려 주세요. 이미 SAC가 꺼진 PC에서는 SAC 설정을 바꿀 필요가 없습니다.
> 설치기는 보안 설정을 자동으로 변경하지 않습니다. 설치기만 대상으로 무료 서명 신청을 준비 중이며, 아직 제출·승인되지 않았고 서명본 제공 시점도 확정되지 않았습니다.
>
> [Microsoft SAC 안내](https://support.microsoft.com/en-us/windows/security/threat-malware-protection/smart-app-control-frequently-asked-questions) · [서명 준비 현황](unified/SIGNING.md)

## 0.14.0 Alpha 1: 선택형 통합 설치기

**[통합 설치기 다운로드](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.14.0-alpha.1)** · [설치·복구·소스 빌드 안내](unified/README.md) · [검증 기록](unified/verification.json)

`CrimsonSkies-Unified-0.14.0-alpha.1.zip` 하나를 풀고 `CrimsonSkiesSetup.exe`를 실행하세요. 원본에서 **한글화·와이드스크린·한국어 더빙·자막 종류**를 한 화면에서 선택하고 설치할 수 있습니다. 별도의 0.11 기반 설치나 API 키가 필요 없습니다. 이후 구성 변경·자동 백업·복구도 같은 도구에서 수행합니다.

정확한 원본 또는 공개 0.11 기반 상태를 지원합니다. 기존 0.12 언어팩은 이전 실행기에서 복구하고, 0.13 더빙은 **자막 → 음성 복구** 후 전환하세요. 전체 더빙은 약 14GB의 추가 여유 공간을 권장합니다. 프로필 관리는 기존 별도 런처의 기능입니다.

12가지 구성의 설치기 검사와 실제 크기 파일의 설치·복구 검증을 통과했습니다. **기본 전체 선택으로 재설치한 뒤 정상 플레이도 확인했습니다.** 다른 선택 조합의 실제 화면과 엔딩까지의 전 구간 검증은 진행 중이므로 알파 프리릴리즈입니다.

## 0.13.0 Alpha 2: 전체 한국어 더빙과 더빙 대사 자막

**[Alpha 2 다운로드](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.13.0-alpha.2)** · [설치·복구 안내](docs/DUBBING.ko.md) · [소스 빌드](dubbing/README.md)

무전 WAV 1,847개와 영상 56개의 한국어 AI 더빙, 최종 발화에 맞는 자막 선택, 영상 자막 캐시 수정을 제공합니다. 설치 순서는 **0.11 기반 패치 → 전체 더빙 ZIP의 `KoreanDubInstaller.exe` → 자막 ZIP의 `PrepareSubtitleLauncher.exe`**입니다. 준비 후 **한국어 — 더빙 대사 자막**을 선택하세요. API 키나 음성 재생성은 필요 없습니다.

0.12 언어팩 사용자는 기존 실행기로 원본 언어팩 상태를 복구해 0.11 기반으로 돌아온 뒤 설치하세요. 원음을 복구할 때는 **원본 자막 복구 → 더빙 설치기의 복구** 순서입니다. 프로필 관리 기능은 유지됩니다. 전체 구간 플레이 검증은 진행 중이므로 프리릴리즈로 공개합니다.

## 0.12.2 알파 1: 프로필 백업·삭제·복원

**[0.12.2 알파 다운로드](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.12.2-alpha.1)** · [프로필 관리자 안내](docs/PROFILE_MANAGER.ko.md)

런처에서 선택한 프로필만 ZIP으로 백업하고, 백업 검증·확인 후 삭제하거나 백업 ZIP에서 복원할 수 있습니다. 기존 프로필은 덮어쓰지 않으며 다른 프로필과 공유 타이틀 데이터를 검증합니다. 중단 작업 복구도 포함합니다. Windows x64 **2608.3123.1.0**과 백업의 원래 계정·저장소 환경을 지원합니다.

자막 언어팩을 적용하려면 **0.11.0 베타 1 기반 패치를 먼저 설치**하세요. 기존 0.12 사용자는 게임과 Play 창을 닫고 새 ZIP을 별도 폴더에 풀어 사용할 수 있습니다. 기존 언어팩 카탈로그와 복구 식별자는 유지됩니다. [512개 합성 검증 및 별도 저장 공급자 시험 기록](docs/profile-manager-verification.json) · [공개 테스트 실행 안내](multilingual/tests/profile_manager/README.md).

**한국어** | [English](README.en.md)

**Crimson Skies: High Road to Revenge**의 하단 한국어 자막, 4:3·16:9 해상도 선택,
HUD 보정과 4K AA 수정을 묶은 비공식 커뮤니티 패치입니다.

**[0.11.0 베타 1 다운로드](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.11.0-beta.1)** ·
[설치·복구 안내](읽어주세요.txt) · [검증 범위](검증%20결과.txt)

새 [0.12 다국어 알파 안내](docs/MULTILINGUAL.ko.md): 언어팩 JSON 추가·런처 선택을
지원하는 별도 추가 기능입니다. 영어·스페인어는 부분 번역 예제로 제공합니다.

> Windows x64 패키지 **2608.3123.1.0 전용**입니다. 게임은 별도로 필요합니다.
> 엔딩까지 모든 장면의 실제 플레이 검증은 아직 끝나지 않아 베타로 공개합니다.

## 포함 기능

- 무전·게임 내 컷신의 내장 하단 한글 자막과 줄바꿈
- 영상·크레딧 자막 데이터, Noto Sans CJK KR Bold에서 변환한 CS Korean Sans
- 640×480부터 3840×2160까지 11개 렌더링 해상도와 화면비 자동 전환
- 레이더 지도·로켓 숫자·적 체력바·일시정지 목표창 보정
- 4K에서도 선택한 AA 유지
- SHA-256 검사, 설치 전 백업, 중단 후 재개·복구 및 설치 전 상태로 되돌리기

4K 옵션은 **내부 렌더링 해상도**입니다. 최종 출력은 창·모니터 크기를 따릅니다.

## 설치

1. [릴리즈](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.11.0-beta.1)에서 `CrimsonSkies-KO-Wide-0.11.0-beta.1.zip`을 받습니다.
   GitHub의 자동 생성 `Source code` ZIP은 설치용 배포본이 아닙니다.
2. 게임과 '플레이' 버튼이 있는 실행기를 종료하고 ZIP 전체를 풉니다.
3. `KoreanWidePatchInstaller.exe` → 게임 폴더 또는 `Content` 선택 → **상태 검사**
   → **통합 패치 설치** 순서로 진행합니다.
4. 평소 사용하던 방법으로 실행하고 게임 언어를 한국어로 선택합니다.

지원하는 입력은 정확한 원본 또는 공개 한글 베타 `0.10.0-beta.1`입니다.
다른 모드·빌드·중간 시험본을 섞은 상태는 거부합니다.
복구는 **이 버전을 설치하기 직전 상태**로 돌아갑니다. 이전 한글 베타에서
업그레이드했다면 복구 대상도 이전 베타입니다. [자세한 안내](읽어주세요.txt)를 확인하세요.

## 공개 소스와 전체 재현 빌드

**[소스 재현 가이드](docs/REPRODUCING.ko.md)** · [독립 재현 결과](docs/source-reproduction.json) ·
[재현용 소스 스냅샷](https://github.com/schultz1138/crimson-skies-korean-wide/tree/source-v0.11.0-beta.1-r2)

- `pipeline/assets/`: 읽을 수 있는 번역·타이밍·글꼴 설정, 원본 추출과 Data0000·Data0005 생성
- `pipeline/native/`: 무전 자막 AOT·UI/HUD·해상도·GPU·4K AA 코드 및 PE 생성
- `source/`: 설치·복구 도구의 C# 전체 소스
- `pipeline/package_release.py`: 새 결과에서 차분 6개·설치기·28개 파일의 배포 ZIP 재생성
- `pipeline/requirements-win-cp312.txt`: Windows x64 / CPython3.12 의존성 휠 버전·해시 고정
- `licenses/`: 글꼴·xdelta·정적 의존 라이브러리와 설치기 라이선스

빌드 입력은 소유한 정확한 원본 게임 5개, 고정 Noto와 명시한 개발 도구입니다.
공개된 VCDIFF나 완성 DLL을 빌드 입력으로 쓰지 않습니다. 기존 무전 한글 베타의
중간 Native도 소스에서 생성해서 업그레이드용 차분을 다시 만듭니다.

Windows x64 / Python3.12 환경에서 가이드의 의존성을 준비한 뒤 실행합니다:

```powershell
.\.venv\Scripts\python.exe pipeline\build.py --input-content D:\CrimsonSkies-original\Content --dependencies .deps --out D:\CrimsonSkies-build-001
```

기본 빌드는 최종 게임 파일 5개, 차분 6개, 설치기와 최종 ZIP을 기존 릴리즈 해시와
대조합니다. `--game-only`는 게임 파일 생성·검증까지만 수행합니다.
참조 컴파일러·FreeType·압축기와 메타데이터 정규화 범위는 가이드에 명시했습니다.

`hooks/`에는 이전 공개 시점의 핵심 후크 참고 목록도 남아 있습니다. 실제 전체
생성 파이프라인은 `pipeline/`을 사용하세요. 기존 `v0.11.0-beta.1` 태그는 보존하며,
전체 재현 소스는 `source-v0.11.0-beta.1-r2` 스냅샷 또는 릴리즈의 별도 소스 ZIP을 받으세요.

## 검증과 알려진 범위

최종 설치기 소스의 독립 검증 **191개**, 원본·이전 베타의 실제 크기
설치→복구 **2회**, 차분 6개의 바이트 단위 복원을 확인했습니다.
튜토리얼, 씨헤이븐 보스 컷신·이후 임무, HUD 보정과 최종 4K·4x MSAA 플레이의
정상 동작을 사용자에게 확인받았습니다.

- 엔딩까지 전 구간의 실제 플레이 검증은 남아 있습니다.
- 짧은 외국어 외침 4개의 원문 확인이 남아 있습니다.
- 물리적인 4K 모니터 출력과 다양한 PC의 장시간 플레이는 별도 검증 대상입니다.

릴리즈 ZIP SHA-256:
```
a53382986c5e78aa189a8936249d9771bed7d357019e31c8b219c904f304dc42
```

## 기여

재현 가능한 자막 누락·오탈자·HUD 문제 제보와 설치기 개선 PR을 환영합니다.
[CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.

## 다른 언어 자막 기여

[영어 기여 안내](CONTRIBUTING.en.md)와 [언어 포팅 가이드](docs/LOCALIZATION.en.md)에
번역·타이밍·글꼴 수정 위치와 예제를 정리했습니다. 현재 빌드는 한국어 리소스 슬롯과
기존 출력 해시에 고정되어 있어, 새 언어는 리소스·글꼴·버전/검증값을 함께 정리한
별도 포팅이 필요합니다. 이 설명은 기존 0.11 릴리즈 기준입니다.

새 [0.12 다국어 알파](docs/MULTILINGUAL.ko.md)는 JSON 언어팩 자동 검색과 패치 런처의
언어 선택을 제공합니다. 한국어 기본팩과 영어·스페인어 부분 번역 예제를 포함하며,
0.11 통합판 위에 적용하는 별도 추가 기능입니다.

## 라이선스

이 프로젝트의 설치기와 직접 작성한 참고 소스는 [MIT](LICENSE)입니다.
글꼴은 SIL OFL 1.1, xdelta3 3.2.2 및 포함 의존물은 각각의 동봉 라이선스를 따릅니다.
[글꼴 고지](FONT-NOTICE.txt)와 [서드파티 고지](THIRD-PARTY-NOTICES.txt)를 확인하세요.
MIT 표기는 원본 게임·음성·영상·상표에 대한 권리를 부여하지 않습니다.
Microsoft 또는 원작 개발사의 공식 프로젝트가 아닙니다.

---

Unofficial Korean subtitles, widescreen resolutions, HUD alignment and 4K AA fixes
for the exact Windows packaged x64 build `2608.3123.1.0`. Use the named installer ZIP
from Releases. Original game files are required and are not distributed here.
The installer source is MIT; third-party assets retain their own licenses.
This is a beta, with full ending-to-ending gameplay verification still pending.
