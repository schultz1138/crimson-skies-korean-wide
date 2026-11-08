# 더빙·자막 소스 빌드

[English](README.en.md) · [플레이어 설치 안내](../docs/DUBBING.ko.md)

`audio/`에는 차분 21개를 설치·복구하는 도구의 C# 소스와 고정 해시 목록이 있습니다. `captions/`에는 무전 1,901구간, 튜토리얼 42문구, 영상 자막 328개 단일 행 노드, 최종 영상 발화·배역·시간, 줄바꿈, 자막 카탈로그와 실행기·프로필 관리·로컬 준비 도구의 소스가 있습니다.

음성은 확정한 생성 결과를 차분으로 배포합니다. 음성 재포장 스크립트는 소유한 설치 전·후 게임에서 같은 차분을 다시 만드는 도구이며 TTS를 호출하지 않습니다. 이번 소스에는 개인 TTS 요청 로그와 키를 포함하지 않으며, 외부 생성 API에서 같은 음성을 바이트 단위로 다시 합성할 수 있다고 주장하지 않습니다.

자막은 완성 Native를 대체 데이터로 읽거나 배포 차분을 입력으로 쓰지 않고 선언형 대본·타이밍·글꼴 소스에서 재빌드합니다. Windows x64 / Python3.12 및 기존 [재현 가이드](../docs/REPRODUCING.ko.md)의 해시 고정 의존성을 사용하세요. Noto·xdelta의 정확한 버전과 해시는 [영문 빌드 안내](README.en.md)에 있습니다.

## 자막 빌드

입력은 전체 더빙 설치 후 **기존 번역 자막** 상태의 소유한 게임 복사본입니다. 출력은 입력 게임 폴더 밖의 새 경로여야 합니다.

```powershell
python dubbing/build_captions.py --full-dub-content D:\FullDub-original-captions\Content --font D:\deps\NotoSansCJKkr-Bold.otf --out D:\build\alpha2-captions
python dubbing/package_captions.py --full-dub-content D:\FullDub-original-captions\Content --caption-content D:\build\alpha2-captions\Content --xdelta D:\deps\xdelta3.exe --out D:\build\caption-package
```

첫 명령은 글꼴·Unicode·영상 DB·Native 고정 자막 표와 캐시 갱신 크기를 재생성하고, 검증된 Native·Data0000·Data0005 해시와 대조합니다. 두 번째 명령은 실행기와 준비 도구, 정방향·역방향 차분 6개를 만듭니다. 로컬 자막 범위 데이터 15MB 두 개는 배포하지 않으며 준비 도구가 유저의 게임에서 생성합니다.

## 확정 음성의 설치팩 재포장

```powershell
python dubbing/build_audio.py --source-content D:\Foundation011\Content --dubbed-content D:\FullDub-original-captions\Content --xdelta D:\deps\xdelta3.exe --out D:\build\audio-package
```

입력은 정확한 공개 0.11 기반과 최종 전체 더빙 게임입니다. 고정 원본·대상·차분 해시와 모두 일치해야 합니다. 배포 도구는 모든 파일을 검증·준비한 뒤 교체하고 백업으로 복구합니다. `AUDIO_TRANSACTION_FIXTURE`는 별도 복사본의 테스트용 컴파일 심볼이며 배포 빌드에서는 사용하지 않습니다.

프로필 백업·삭제·복원 기능은 기존 C# 구현을 유지합니다. 자막 문구를 변경할 때에는 글꼴 범위·폭·줄바꿈·카탈로그·차분·고정 해시를 함께 갱신해야 합니다. Native의 고정 데이터 공간을 넘기면 빌드를 거부합니다. 영상은 LF 대신 위치를 지정한 단일 행 노드로 표시합니다. 다음 수정판도 직전 판과 다른 `data.zip` 논리 크기를 선택하고, EOCD가 파일 끝에서 정확히22바이트 앞에 있도록 유지하세요.

실제 크기 설치·복구와 소스 재현 결과는 [검증 기록](../docs/dubbing-alpha2-verification.json)에 있습니다. 생성된 게임 파일·원본 영상·음성·개인 백업·로컬 경로 증거·키는 저장소에 올리지 마세요. 설치 도구와 폰트·외부 도구 라이선스 안내는 함께 보존하세요.
