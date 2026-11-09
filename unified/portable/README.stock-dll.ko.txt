Crimson Skies — 원본 DLL 유지 더빙 전용 실험 후보

CrimsonSkies-Install.cmd를 실행합니다. Python을 따로 설치할 필요가 없습니다.
공식 PSF 서명 Python 3.15.2와 공식 xdelta3 3.2.2를 동봉합니다.
설치 프로그램 자체는 BAT와 Python 소스로 제공하며 자체 EXE는 없습니다.
라이선스와 바이너리 해시는 THIRD-PARTY-NOTICES.txt / FILE-HASHES.json을 확인하세요.

이 후보가 제공하는 선택
1. 원본 음성·자막 / 4:3
2. 한국어 더빙만 / 원본 Native·GPU DLL 유지 / 4:3

와이드스크린과 추가 무전·맞춤 자막 선택은 제공하지 않습니다.
기본 영상 자막과 필요한 한글 게임 자산은 유지합니다.
이 구성이 SAC 켜진 상태의 실제 게임 실행까지 통과했는지는 별도 검증 보고서를 확인하세요.
다른 PC에서도 허용됨을 보장하는 배포본은 아닙니다.

준비와 실행
- 지원 게임: 소유한 Windows x64 2608.3123.1.0.
- 게임과 플레이 창, 다른 설치기를 모두 종료합니다.
- 정확한 원본 파일 상태에서 시작해야 합니다. 기존 패치는 이전 도구로 복구하세요.
- 해시 복원 뒤에도 원본 DLL이 차단되는 경우에는 Xbox의 공식 확인·복구가 필요할 수 있습니다.
- ZIP 전체를 공백·한글을 포함할 수 있는 새 로컬 폴더에 풉니다.
  %, !, &, ^, 괄호 등 특수문자가 있는 폴더는 피하세요.
- CrimsonSkies-Install.cmd → 게임 경로 자동 감지/입력 → 상태 검사 → 선택 항목 설치 순서입니다.

백업과 보존
바뀌는 데이터 파일만 백업·준비하고, 모두 검증한 뒤 교체합니다.
원본 Native·GPU DLL은 해시뿐 아니라 파일 자체를 교체하지 않습니다.
설정의 기존 언어·해상도 키만 처리하며 AA 등 다른 값과 저장 프로필은 변경하지 않습니다.
알려진 기존 캐시 자산만 갱신하고 체크포인트와 그 밖의 캐시 바이트는 보존합니다.
모르는 파일·캐시 내용, 부족한 공간/할당, 동시 실행은 덮어쓰지 않고 중단합니다.
전체 더빙을 위해 14GB 이상 여유 공간을 권장합니다.

백업: %LOCALAPPDATA%\CrimsonSkiesBAT\Backups
설치 전 복구는 이 후보의 첫 설치 전 원본 상태로 돌아갑니다.
중단 기록이 있으면 중단 작업 복구를 먼저 실행하세요. 백업과 작업 기록을 지우지 마세요.
단순 복사본은 실제 PC의 설정·캐시에 접근하지 않습니다.
보안 설정·인증서·실행 정책·다운로드 출처 표식을 변경하는 기능은 없습니다.
차단된다면 보안 설정을 바꾸지 말고 차단된 파일 이름과 오류를 기록하세요.

명령줄 예
CrimsonSkies-Install.cmd --check --root "C:\XboxGames\Crimson Skies- High Road to Revenge\Content"
CrimsonSkies-Install.cmd --apply k1-w0-d1-off --root "C:\XboxGames\Crimson Skies- High Road to Revenge\Content"
CrimsonSkies-Install.cmd --restore --root "C:\XboxGames\Crimson Skies- High Road to Revenge\Content"
CrimsonSkies-Install.cmd --recover --root "C:\XboxGames\Crimson Skies- High Road to Revenge\Content"

게임 원본은 포함하지 않습니다. 음성·글꼴 고지는 동봉 문서를 따릅니다.
현재는 미공개 개발 시험 후보이며, 검증되지 않은 기능을 정식 릴리스로 안내하지 않습니다.
