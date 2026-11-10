# Crimson Skies 한국어·와이드스크린 패치

**Crimson Skies: High Road to Revenge**를 한국어 자막·AI 한국어 더빙과 와이드스크린으로 즐기는 비공식 팬 패치입니다.
Windows x64 게임 빌드 **2608.3123.1.0**을 별도로 설치해야 합니다.

**[Beta 2 다운로드](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.14.0-beta.2)** · **[처음부터 설치하기](unified/README.md)** · [English](README.en.md)

## 소개·설치 영상

**[▶ Beta 2 소개·설치 영상 보기 (YouTube · 4분 46초)](https://www.youtube.com/watch?v=3Psn6lNxDho)**

영어·한국어 더빙 라디오와 컷신 비교, 4:3 → 16:9 화면 전환, Beta 2 다운로드·설치·복구 과정을 영상으로 확인할 수 있습니다.

## 처음 설치한다면

**시작 전 SAC 안내를 확인하세요.** 이 배포본은 미서명이며 Windows의 Smart App Control(SAC)이 설치기나 패치된 게임을 차단할 수 있습니다. 보호 기능을 끄면 PC 전체의 앱 실행 보호가 줄어들고, 다시 켜도 패치 게임이 차단될 수 있습니다. 재활성화 가능 여부는 PC·Windows 상태에 따라 다릅니다. 설치기는 보안 설정을 바꾸지 않습니다. [차단 알림과 SAC 안내](unified/README.md#smart-app-control-sac)를 읽고 설치 여부를 결정하세요.

1. 위 **Beta 2 다운로드**에서 **Assets**를 펼치고 `CrimsonSkies-Unified-0.14.0-beta.2.zip`을 받습니다. GitHub의 `Source code`는 개발용 소스입니다.
2. 원본 게임이 실행되는지 확인한 뒤 게임과 **플레이 창**을 모두 닫습니다.
3. ZIP 전체를 새 폴더에 풉니다. 그 안의 `CrimsonSkiesSetup.exe`를 실행합니다.
4. **게임 폴더 선택 → 음성·자막 선택 → 와이드 선택 → 상태 검사 → 선택 항목 설치** 순서로 진행합니다.
5. 설치 완료 메시지를 확인하고 **플레이 창 열기**를 누릅니다. 와이드를 적용했다면 런처에서 **1920×1080 등 16:9 해상도**를 선택합니다.

이전 패치를 사용했다면 **[기존 사용자 안내](unified/README.md#기존-패치를-사용하고-있다면)**부터 확인하세요. 이전 0.14는 **그 버전의 설치 전 복구**를 먼저 사용합니다.

## 무엇을 선택하면 되나요?

음성·자막 하나를 고르고, 와이드스크린은 따로 켜거나 끕니다.

| 원하는 구성 | 설치기에서 고를 항목 |
| --- | --- |
| 영어 음성에 한국어 자막 | **영어 음성 + 한국어 자막** |
| 한국어 음성만 듣기 | **한국어 더빙만 (추가 자막 끔)** |
| 한국어 음성과 더빙에 맞는 자막 | **한국어 더빙 + 맞춤 자막** |
| 화면만 와이드로 | **원본 음성·자막** + **와이드스크린·고해상도** 체크 |

‘더빙만’에서도 기본 영상 자막과 필요한 한글 메뉴·글꼴은 유지합니다. 전체 더빙은 약 **14GB 여유 공간**을 권장합니다. 음성은 제작된 파일로 설치하므로 API 키가 필요 없습니다. 원본 상태에서 바로 시작할 수 있습니다.

## 설치·변경·복구 안내

- [다운로드부터 첫 실행까지](unified/README.md)
- [기존 패치에서 Beta 2로 옮기기](unified/README.md#기존-패치를-사용하고-있다면)
- [설치 옵션 바꾸기와 설치 전 복구](unified/README.md#옵션-변경과-복구)
- [오류가 났을 때](unified/README.md#문제가-생겼을-때)

## Beta 2와 검증 범위

Beta 2는 Xbox 앱의 **검사 및 복구** 후 정상 게임이 거부되던 설치 검사 문제를 수정합니다. 자막·더빙·와이드 콘텐츠는 Beta 1과 같습니다. **SAC 차단을 해결하는 업데이트는 아닙니다.**

첫 임무의 설치·플레이·복구와 파일 해시·저장 데이터 보존을 확인했습니다. 전 캠페인·4K 플레이와 모든 더빙 대사의 최종 청취 검수는 남아 있는 **베타 프리릴리스**입니다. [Beta 2 검증 기록](unified/verification-beta2.json) · [기존 8조합 검증 기록](unified/verification-beta1.json)

## 이전 버전·개발자 자료

처음 설치할 때는 위의 통합 설치기를 사용하세요. 아래 문서는 기존 설치 복구나 개발에 필요한 자료입니다.

- [0.13 더빙·자막의 기존 도구 안내](docs/DUBBING.ko.md)
- [0.12 언어팩 안내](docs/MULTILINGUAL.ko.md) · [기존 프로필 관리자](docs/PROFILE_MANAGER.ko.md)
- [0.11 전용 설치 안내](읽어주세요.txt)
- [통합 설치기 소스 빌드](unified/README.md#개발자용-소스-빌드) · [0.11 소스 재현](docs/REPRODUCING.ko.md)
- [이전 README 보관본](https://github.com/schultz1138/crimson-skies-korean-wide/blob/v0.14.0-beta.2/README.md)
- [기여 안내](CONTRIBUTING.md) · [배포·서명 현황](unified/SIGNING.md)

설치기 소스는 [MIT](LICENSE), 글꼴과 도구는 [동봉 라이선스](THIRD-PARTY-NOTICES.txt)를 따릅니다. 게임 원본은 포함하지 않습니다. Microsoft/Xbox의 공식 프로젝트가 아니며 원작·상표·음성·영상의 권리는 각 권리자에게 있습니다.
