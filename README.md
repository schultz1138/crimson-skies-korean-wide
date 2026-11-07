# Crimson Skies 한국어·와이드스크린 통합 패치

**Crimson Skies: High Road to Revenge**의 하단 한국어 자막, 4:3·16:9 해상도 선택,
HUD 보정과 4K AA 수정을 묶은 비공식 커뮤니티 패치입니다.

**[0.11.0 베타 1 다운로드](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.11.0-beta.1)** ·
[설치·복구 안내](읽어주세요.txt) · [검증 범위](검증%20결과.txt)

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
[재현용 소스 스냅샷](https://github.com/schultz1138/crimson-skies-korean-wide/tree/source-v0.11.0-beta.1-r1)

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
전체 재현 소스는 `source-v0.11.0-beta.1-r1` 스냅샷 또는 릴리즈의 별도 소스 ZIP을 받으세요.

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
