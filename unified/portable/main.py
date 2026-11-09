"""Portable console UI. Run through the generated, hash-checking BAT. MIT."""
from pathlib import Path
import argparse, hashlib, json, os, sys, traceback

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
sys.path.insert(0, str(HERE))
def bootstrap():
    pins = json.loads((PACKAGE/'pins.json').read_text('utf-8'))
    for name, expected in pins['files'].items():
        path = PACKAGE.joinpath(*name.split('/'))
        if not path.is_relative_to(PACKAGE) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Package verification failed: ' + name)
    return pins

def main():
    pins = bootstrap()
    import host as H
    from engine import Engine, PROFILES
    parser = argparse.ArgumentParser(description='Crimson Skies BAT installer')
    parser.add_argument('--root', type=Path)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--check', action='store_true')
    allowed = pins.get('allowedProfiles',PROFILES)
    action.add_argument('--apply', choices=allowed)
    action.add_argument('--restore', action='store_true')
    action.add_argument('--recover', action='store_true')
    args = parser.parse_args()
    logs = PACKAGE/'Logs'
    H.mkdir(logs)
    import datetime
    log_path = logs/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid())+'.log')
    def log(message):
        print(message, flush=True)
        with log_path.open('a',encoding='utf-8') as stream: stream.write(message+'\n')
    root = args.root or H.registered_root()
    log('Crimson Skies BAT '+pins['releaseId']+' | SAC state='+str(H.sac_state()))
    if args.check or args.apply or args.restore or args.recover:
        H.need(root is not None,'Game registration missing; supply --root')
        try:
            return Engine(PACKAGE,pins,root,log=log).run('check' if args.check else 'apply' if args.apply else 'restore' if args.restore else 'recover',args.apply)
        except Exception as error:
            log('FAILED: '+str(error)); raise
    print('선택형 BAT 설치기 / Portable installer\n보안 설정은 변경하지 않습니다. 설치 중에는 게임과 이전 설치기를 닫아 주세요.')
    answer = input('게임 폴더 (Enter=자동 감지) / Game folder: ').strip().strip('"')
    if answer: root = Path(answer)
    H.need(root is not None,'게임을 찾지 못했습니다 / Game not found')
    while True:
        print('\n대상 / Game: '+str(root))
        print('1. 상태 검사 / Check\n2. 선택 항목 설치 / Install\n3. 설치 전 상태로 복구 / Restore\n4. 중단 작업 복구 / Recover\n5. 종료 / Exit')
        mode = input('작업 / Action [1-5]: ').strip()
        if mode == '5': return
        if mode not in ('1','2','3','4'): continue
        target = None
        if mode == '2':
            if pins.get('stockNativeMode'):
                print('1. 원본 음성·자막 / 4:3\n2. 한국어 더빙만 / 원본 DLL 유지 / 4:3')
                preset=input('프리셋 / Preset [1-2]: ').strip()
                if preset not in ('1','2'):continue
                target=allowed[int(preset)-1]
            else:
                print('1. 원본 음성·자막\n2. 영어 음성 + 한국어 자막\n3. 한국어 더빙만\n4. 한국어 더빙 + 맞춤 자막')
                preset = input('프리셋 / Preset [1-4]: ').strip()
                if preset not in ('1','2','3','4'): continue
                wide = input('와이드스크린 / Widescreen [Y/N]: ').strip().upper()
                if wide not in ('Y','N'): continue
                target = PROFILES[(int(preset)-1)*2 + (wide == 'Y')]
            print('설치할 구성 / Selected: '+target)
        try: Engine(PACKAGE,pins,root,log=log).run({'1':'check','2':'apply','3':'restore','4':'recover'}[mode],target)
        except Exception as error: log('FAILED: '+str(error)); log('중단 기록이 있다면 작업 4로 복구하세요. 백업을 보존하세요.')
        input('Enter를 누르면 메뉴로 돌아갑니다 / Enter to continue: ')

if __name__ == '__main__':
    try: main()
    except (Exception, KeyboardInterrupt) as error:
        print('FAILED: '+str(error),file=sys.stderr)
        sys.exit(1)
