# 2611 빌드 호환 시험판

지원 게임은 Windows x64 빌드 **2611.323.502.0**입니다. Xbox 업데이트 후 이 빌드의 원본 파일이 있는 상태에서 시작합니다. 종전 패치의 백업은 해당 빌드용입니다.

게임과 플레이 창을 닫고 ZIP을 완전히 푼 뒤 CrimsonSkiesSetup.exe를 실행합니다. 게임 Content 폴더를 골라 상태 검사를 실행하고 원하는 음성·자막과 와이드스크린을 선택해 적용합니다. 복구는 같은 설치기의 ‘설치 전 복구’를 사용합니다.

빌드에는 소유한 2611 원본 Content, 2608 원본 Native DLL, 공개 Beta 2 압축을 푼 폴더, 기존 CPython 환경의 pefile·Capstone·Keystone이 필요합니다.

```powershell
python unified/build_2611.py --stock "D:\2611\Content" --previous-native "D:\2608\Content\xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll" --beta "D:\Beta2" --out "D:\CS2611-output"
```
