Crimson Skies BAT 설치기 — 0.14.0-beta.2-bat.1 시험 배포 후보

CrimsonSkies-Install.cmd를 실행하세요. Python을 별도로 설치할 필요가 없습니다.
공식 Python Software Foundation 서명 런타임 3.15.2와 공식 xdelta3 3.2.2를 동봉합니다.
설치기 자체는 공개 Python 소스와 BAT로 제공하며, 자체 설치기 EXE는 만들지 않습니다.
보안 설정·인증서·실행 정책·다운로드 출처 표식을 변경하지 않습니다.
Windows가 차단하면 그 상태에서 중단하고 오류와 차단 파일 이름을 확인하세요.

지원 게임: 소유한 Windows x64 2608.3123.1.0 빌드. 게임 원본은 포함하지 않습니다.
게임과 플레이 창, 이전 설치기를 종료하고 ZIP 전체를 새 로컬 폴더에 푸세요.
경로에는 공백과 한글을 쓸 수 있습니다. %, !, &, ^, 괄호 등 특수문자는 피하세요.

사용 순서
1. 게임 폴더를 자동 감지하거나 직접 입력합니다.
2. 상태 검사 후 선택 항목 설치를 실행합니다.
3. 원본 / 영어 음성+한국어 자막 / 한국어 더빙만 / 더빙+맞춤 자막 중 고릅니다.
4. 와이드스크린 켜기/끄기를 선택합니다. 총 8가지 조합입니다.
5. PASS 뒤 기존 Xbox 실행기로 게임을 실행합니다.

파일·설정·캐시
- 29개 대상 파일과 4개 가드를 전체 SHA-256으로 검사합니다.
- 모든 파일, 설정, 기존 캐시의 변경 결과를 준비한 뒤 교체합니다.
- 등록된 게임의 기존 언어/해상도 키만 변경합니다. AA와 다른 설정은 유지합니다.
- 알려진 72종 자산의 기존 캐시를 선택한 구성과 일치하도록 갱신합니다.
- 체크포인트, FAT, 미소유 캐시 영역은 그대로 유지합니다. 저장 프로필은 변경하지 않습니다.
- 모르는 파일·캐시 내용, 부족한 할당 공간, 실행 중인 게임, 연결 경로는 거부합니다.
- 단순 복사본/미등록 게임은 실제 PC의 설정·캐시에 접근하지 않습니다.

백업과 복구
백업은 %LOCALAPPDATA%\CrimsonSkiesBAT\Backups에 보존됩니다. 지우지 마세요.
설치 전 복구는 원본 또는 0.11 기반 상태로 돌아갑니다.
Beta 1 사용자는 정확한 Beta 1 기록과 원본 백업이 일치하면 새 독립 백업으로 복사해 전환합니다.
이전 기록·백업 자체는 변경하지 않습니다. 다른 알파 버전은 해당 도구로 먼저 복구하세요.
중단 작업이 있으면 중단 작업 복구를 먼저 실행합니다. 모르는 동시 변경은 덮어쓰지 않습니다.
적용/복구 중에는 게임과 다른 설치기를 실행하지 마세요. 전체 더빙은 14GB 이상 여유 공간을 권장합니다.

명령줄
CrimsonSkies-Install.cmd --check --root "D:\XboxGames\Crimson Skies- High Road to Revenge\Content"
CrimsonSkies-Install.cmd --apply k1-w1-d1-dub --root "D:\XboxGames\Crimson Skies- High Road to Revenge\Content"
CrimsonSkies-Install.cmd --restore --root "D:\XboxGames\Crimson Skies- High Road to Revenge\Content"
CrimsonSkies-Install.cmd --recover --root "D:\XboxGames\Crimson Skies- High Road to Revenge\Content"

검증 현황은 별도 검증 보고서를 확인하세요. 모든 PC의 SAC 허용을 보장하지 않습니다.
배포한 후보 ZIP으로 설치·실행까지 확인하기 전에는 정식 릴리스로 안내하지 않습니다.
오류 기록은 이 폴더의 Logs에 남습니다.

원본 게임과 음성/글꼴 권리는 각 고지를 따릅니다. 설치 코드 MIT, Python PSF,
xdelta Apache 2.0 및 동봉 라이선스를 확인하세요. 설치 중 네트워크 다운로드는 하지 않습니다.
