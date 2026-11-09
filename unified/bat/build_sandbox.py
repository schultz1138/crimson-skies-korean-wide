"""Prepare a BAT-only experiment on a deliberately separate Content copy.

Python is a maintainer build tool only. Runtime uses cmd/choice/certutil/findstr
and the pinned upstream xdelta. Never modifies the registered installation,
settings, Xbox cache or save data. This is NOT a replacement shipping installer.
"""
from pathlib import Path
from collections import deque
import argparse, hashlib, json, os, shutil

HERE=Path(__file__).resolve().parent
MANIFEST='c2bd4fa525a2ae0cec2339ca9eb85783a4aaf39d695704cce7695c67f877d4cb'
TOOL='732980d52f9220dc81817ccdd0c295eadce8a0048a24c2a771a73f791ac824e9'
PROFILES=['k0-w0-d0-off','k0-w1-d0-off','k1-w0-d0-original','k1-w1-d0-original',
          'k1-w0-d1-off','k1-w1-d1-off','k1-w0-d1-dub','k1-w1-d1-dub']
LABELS=['Original / 4:3','Widescreen only / 16:9','English voices + Korean captions / 4:3',
        'English voices + Korean captions / 16:9','Korean voices only / 4:3',
        'Korean voices only / 16:9','Korean voices + matched captions / 4:3',
        'Korean voices + matched captions / 16:9']
MENU_KO='''한국어 / English: 실제 설치된 게임은 변경하지 않습니다.

1. Original voices and captions / 원본
2. English voices + Korean captions / 한국어 자막
3. Korean voices only / 한국어 더빙만
4. Korean voices + matched captions / 더빙 + 맞춤 자막
'''
ACTIONS_KO='''1. Check / 상태 검사
2. Apply to sandbox / 복사본에 적용
3. Restore sandbox / 복사본 원복
4. Exit / 종료
'''

def need(ok,message):
    if not ok:raise ValueError(message)
def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    return digest.hexdigest()
def clean(path):
    # Examine the lexical ancestors before resolve() can hide a junction.
    path=Path(os.path.abspath(path))
    for item in [path,*path.parents]:
        if item.exists():need(not item.is_symlink() and not getattr(item.lstat(),'st_file_attributes',0)&0x400,'Linked path refused')
    return path.resolve()
def relative(value):
    need(isinstance(value,str) and value and '\\' not in value and ':' not in value,'Bad relative path')
    need(all(p not in ('','.','..') for p in value.split('/')) and all(c.isalnum() or c in '/_.-' for c in value),'Bad package path')
    return value.replace('/','\\')
def route(file,start,end):
    todo=deque([(start,[]) ]);seen={start}
    while todo:
        current,edges=todo.popleft()
        if current==end:return edges
        for edge in file['edges']:
            if edge['source']==current and edge['target'] not in seen:
                seen.add(edge['target']);todo.append((edge['target'],edges+[edge]))
    raise ValueError('No stock-to-profile route')

HEADER=r'''@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
set "XDELTA="
set "CSBAT_BASE=%~dp0"
set "CSBAT_ROOT=%~dp0Sandbox\Content"
set "CSBAT_STATE_DIR=%~dp0State"
set "CSBAT_STAGE=%~dp0State\stage"
set "CSBAT_BACKUP=%~dp0State\original"
set "CSBAT_TOOL=%~dp0tools\xdelta3.exe"
set "CSBAT_CERT=%SystemRoot%\System32\certutil.exe"
set "CSBAT_FIND=%SystemRoot%\System32\findstr.exe"
set "CSBAT_CHOICE=%SystemRoot%\System32\choice.exe"
set CSBAT_BASE | "%CSBAT_FIND%" /l /c:"%%" /c:"!" /c:"&" /c:"^" /c:"(" /c:")" /c:"|" /c:"<" /c:">" >nul
if not errorlevel 1 goto UnsafePath
if "%~1"=="" goto Menu
set "CSBAT_ACTION=%~1"
set CSBAT_ACTION | "%CSBAT_FIND%" /l /x /c:"CSBAT_ACTION=--list" /c:"CSBAT_ACTION=--check" /c:"CSBAT_ACTION=--apply" /c:"CSBAT_ACTION=--restore" >nul
if errorlevel 1 goto Usage
if "%CSBAT_ACTION%"=="--list" goto List
if "%CSBAT_ACTION%"=="--check" goto Check
if "%CSBAT_ACTION%"=="--restore" goto Restore
set "CSBAT_SELECTION=%~2"
goto Apply

:Menu
cls
echo Crimson Skies BAT experiment - SANDBOX COPY ONLY
echo The selected files live ONLY in:
echo "%CSBAT_ROOT%"
echo.
if not exist "%CSBAT_BASE%Menu.ko.txt" goto MissingMenu
if not exist "%CSBAT_BASE%Actions.ko.txt" goto MissingMenu
type "%CSBAT_BASE%Menu.ko.txt"
"%CSBAT_CHOICE%" /c 1234 /n /m "Voice/caption preset [1-4]: "
set "CSBAT_PRESET=%errorlevel%"
set CSBAT_PRESET | "%CSBAT_FIND%" /r /x /c:"CSBAT_PRESET=[1-4]" >nul
if errorlevel 1 exit /b 1
"%CSBAT_CHOICE%" /c YN /n /m "Widescreen [Y/N]: "
set "CSBAT_WIDE_CHOICE=%errorlevel%"
set CSBAT_WIDE_CHOICE | "%CSBAT_FIND%" /r /x /c:"CSBAT_WIDE_CHOICE=[1-2]" >nul
if errorlevel 1 exit /b 1
set "CSBAT_WIDE=0"
if "%CSBAT_WIDE_CHOICE%"=="2" goto MenuWideReady
set "CSBAT_WIDE=1"
:MenuWideReady
set /a CSBAT_SELECTION=(CSBAT_PRESET-1)*2+CSBAT_WIDE+1
echo.
type "%CSBAT_BASE%Actions.ko.txt"
"%CSBAT_CHOICE%" /c 1234 /n /m "Action [1-4]: "
set "CSBAT_MENU_ACTION=%errorlevel%"
set CSBAT_MENU_ACTION | "%CSBAT_FIND%" /r /x /c:"CSBAT_MENU_ACTION=[1-4]" >nul
if errorlevel 1 exit /b 1
if "%CSBAT_MENU_ACTION%"=="4" exit /b 0
set "CSBAT_INTERACTIVE=1"
if "%CSBAT_MENU_ACTION%"=="3" goto Restore
if "%CSBAT_MENU_ACTION%"=="2" goto Apply
goto Check

:MissingMenu
echo Missing menu text. Extract the complete package before running it.
exit /b 2
:Usage
echo Usage: Sandbox-Test.cmd --list ^| --check ^| --apply 1..8 ^| --restore
exit /b 2
:UnsafePath
echo Use a simple local folder path without percent, exclamation, or shell metacharacters.
exit /b 2
:Check
if exist "%CSBAT_STATE_DIR%\.lock" goto Locked
call :Common
if errorlevel 1 goto Failed
if exist "%CSBAT_STATE_DIR%\pending.txt" goto Pending
call :Check-%CSBAT_STATE%
if errorlevel 1 goto Failed
echo PASS: all 29 components and 4 guards match state %CSBAT_STATE%.
set "CSBAT_RESULT=0"
goto Finish
:Apply
set CSBAT_SELECTION | "%CSBAT_FIND%" /r /x /c:"CSBAT_SELECTION=[1-8]" >nul
if errorlevel 1 goto Usage
call :Common
if errorlevel 1 goto Failed
if exist "%CSBAT_STATE_DIR%\pending.txt" goto Pending
if not "%CSBAT_STATE%"=="0" goto RestoreFirst
call :Lock
if errorlevel 1 goto Locked
call :Apply-%CSBAT_SELECTION%
set "CSBAT_RESULT=%errorlevel%"
call :Unlock
goto Finish
:Restore
call :Common
if errorlevel 1 goto Failed
if exist "%CSBAT_STATE_DIR%\pending.txt" call :ReadPending
if errorlevel 1 goto Failed
if "%CSBAT_STATE%"=="0" goto AlreadyStock
call :Lock
if errorlevel 1 goto Locked
call :Restore-%CSBAT_STATE%
set "CSBAT_RESULT=%errorlevel%"
call :Unlock
goto Finish
:AlreadyStock
call :Check-0
if errorlevel 1 goto Failed
echo PASS: sandbox already matches stock.
set "CSBAT_RESULT=0"
goto Finish
:RestoreFirst
echo Restore this sandbox to stock before changing a preset.
goto Failed
:Locked
echo Another operation or an interrupted session owns State\.lock.
echo Close all test consoles before inspecting an interrupted test.
goto Failed
:Pending
echo Interrupted test recorded. Use --restore after closing the old test console.
goto Failed
:Failed
set "CSBAT_RESULT=1"
:Finish
if "%CSBAT_RESULT%"=="0" echo RESULT: PASS
if not "%CSBAT_RESULT%"=="0" echo RESULT: FAILED - preserve State and backups for diagnosis.
if not defined CSBAT_INTERACTIVE exit /b %CSBAT_RESULT%
pause
goto Menu

:Hash
if not exist "%~1" exit /b 1
"%CSBAT_CERT%" -hashfile "%~1" SHA256 2>nul | "%CSBAT_FIND%" /l /i /x /c:"%~2" >nul
exit /b %errorlevel%
:LoadState
set "CSBAT_STATE=0"
if not exist "%CSBAT_STATE_DIR%\state.txt" exit /b 0
for %%F in ("%CSBAT_STATE_DIR%\state.txt") do if not "%%~zF"=="3" exit /b 1
set /p CSBAT_STATE=<"%CSBAT_STATE_DIR%\state.txt"
set CSBAT_STATE | "%CSBAT_FIND%" /r /x /c:"CSBAT_STATE=[0-8]" >nul
exit /b %errorlevel%
:ReadPending
for %%F in ("%CSBAT_STATE_DIR%\pending.txt") do if not "%%~zF"=="3" exit /b 1
set /p CSBAT_STATE=<"%CSBAT_STATE_DIR%\pending.txt"
set CSBAT_STATE | "%CSBAT_FIND%" /r /x /c:"CSBAT_STATE=[1-8]" >nul
exit /b %errorlevel%
:Lock
if not exist "%CSBAT_STATE_DIR%" mkdir "%CSBAT_STATE_DIR%" || exit /b 1
mkdir "%CSBAT_STATE_DIR%\.lock" 2>nul
exit /b %errorlevel%
:Unlock
if exist "%CSBAT_STATE_DIR%\.lock" rmdir "%CSBAT_STATE_DIR%\.lock"
exit /b 0
:EitherHash
call :Hash "%~1" %~2
if not errorlevel 1 exit /b 0
call :Hash "%~1" %~3
exit /b %errorlevel%
:Backup
if exist "%CSBAT_BACKUP%\original-%~1.bin" goto BackupVerify
copy /b "%CSBAT_ROOT%\%~2" "%CSBAT_BACKUP%\original-%~1.bin" >nul
if errorlevel 1 exit /b 1
:BackupVerify
call :Hash "%CSBAT_BACKUP%\original-%~1.bin" %~3
exit /b %errorlevel%
:Decode
call :Hash "%CSBAT_TOOL%" @TOOL@
if errorlevel 1 exit /b 1
call :Hash "%~1" %~4
if errorlevel 1 exit /b 1
call :Hash "%CSBAT_BASE%%~2" %~5
if errorlevel 1 exit /b 1
"%CSBAT_TOOL%" -d -D -R -s "%~1" "%CSBAT_BASE%%~2" "%~3"
if errorlevel 1 exit /b 1
call :Hash "%~3" %~6
exit /b %errorlevel%
:Commit
call :Hash "%CSBAT_ROOT%\%~2" %~3
if errorlevel 1 exit /b 1
call :Hash "%CSBAT_STAGE%\ready-%~1.bin" %~4
if errorlevel 1 exit /b 1
move /y "%CSBAT_STAGE%\ready-%~1.bin" "%CSBAT_ROOT%\%~2" >nul
if errorlevel 1 exit /b 1
call :Hash "%CSBAT_ROOT%\%~2" %~4
exit /b %errorlevel%
:RestoreFile
call :Hash "%CSBAT_ROOT%\%~2" %~3
if not errorlevel 1 exit /b 0
call :Hash "%CSBAT_ROOT%\%~2" %~4
if errorlevel 1 exit /b 1
copy /b /y "%CSBAT_BACKUP%\original-%~1.bin" "%CSBAT_STAGE%\restore-%~1.bin" >nul
if errorlevel 1 exit /b 1
call :Hash "%CSBAT_STAGE%\restore-%~1.bin" %~3
if errorlevel 1 exit /b 1
move /y "%CSBAT_STAGE%\restore-%~1.bin" "%CSBAT_ROOT%\%~2" >nul
if errorlevel 1 exit /b 1
call :Hash "%CSBAT_ROOT%\%~2" %~3
exit /b %errorlevel%
:ApplyFail
echo Apply failed. Verified original backups have been retained.
if not defined CSBAT_COMMIT goto StagingFail
echo Restoring the verified stock copy...
call :Restore-%CSBAT_TARGET%
if errorlevel 1 echo Recovery incomplete. Keep State and close all test consoles.
exit /b 1
:StagingFail
call :Cleanup
exit /b 1
'''

def script(manifest,marker_hash):
    stock=next(x['hashes'] for x in manifest['inputs'] if x['id']=='stock')
    profiles=[next(x for x in manifest['profiles'] if x['id']==ident) for ident in PROFILES]
    files=manifest['files'];guards=manifest['guards']
    need(len(files)==29 and len(guards)==4,'Expected 29 files and four guards')
    lines=HEADER.replace('@TOOL@',TOOL).splitlines()
    def emit(*values):lines.extend(values)
    def call(label,*args):
        emit('call :'+label+' '+' '.join(args),'if errorlevel 1 exit /b 1')
    def quoted(value):return '"'+value+'"'
    emit(':List')
    for i,label in enumerate(LABELS,1):emit(f'echo {i}. {label}')
    emit('exit /b 0',':Common')
    call('Hash',quoted('%CSBAT_ROOT%\\.sandbox-approved'),marker_hash)
    call('Hash',quoted('%CSBAT_TOOL%'),TOOL)
    emit('"%CSBAT_TOOL%" -V','if errorlevel 1 exit /b 1')
    call('Guards');emit('call :LoadState','exit /b %errorlevel%',':Guards')
    for guard in guards:call('Hash',quoted('%CSBAT_ROOT%\\'+relative(guard['path'])),guard['sha256'])
    emit('exit /b 0')
    states=[stock]+[p['hashes'] for p in profiles]
    for n,vector in enumerate(states):
        emit(f':Check-{n}')
        for i,file in enumerate(files):call('Hash',quoted('%CSBAT_ROOT%\\'+relative(file['path'])),vector[i])
        call('Guards');emit('exit /b 0')
    temporary=set()
    for n,profile in enumerate(profiles,1):
        vector=profile['hashes'];changed=[i for i in range(29) if stock[i]!=vector[i]]
        routes={i:route(files[i],stock[i],vector[i]) for i in changed}
        emit(f':Apply-{n}',f'echo Applying {profile["id"]} to the SANDBOX COPY.',f'set "CSBAT_TARGET={n}"','set "CSBAT_COMMIT="')
        call('Check-0')
        for i,edges in routes.items():
            for edge in edges:call('Hash',quoted('%CSBAT_BASE%'+relative(edge['path'])),edge['sha256'])
        emit('if exist "%CSBAT_STAGE%" exit /b 1','mkdir "%CSBAT_STAGE%"','if errorlevel 1 exit /b 1',
             'if not exist "%CSBAT_BACKUP%" mkdir "%CSBAT_BACKUP%"','if errorlevel 1 goto ApplyFail')
        for i in changed:
            emit(f'call :Backup {i} "{relative(files[i]["path"])}" {stock[i]}','if errorlevel 1 goto ApplyFail')
        for i,edges in routes.items():
            source='%CSBAT_ROOT%\\'+relative(files[i]['path'])
            for k,edge in enumerate(edges):
                name=f'step-{i}-{k}.bin';dest='%CSBAT_STAGE%\\'+name;temporary.add(name)
                emit('call :Decode '+quoted(source)+' '+quoted(relative(edge['path']))+' '+quoted(dest)+' '+edge['source']+' '+edge['sha256']+' '+edge['target'],
                     'if errorlevel 1 goto ApplyFail');source=dest
            name=f'ready-{i}.bin';temporary.add(name)
            emit('move /y '+quoted(source)+' '+quoted('%CSBAT_STAGE%\\'+name)+' >nul','if errorlevel 1 goto ApplyFail')
        emit('call :Check-0','if errorlevel 1 goto ApplyFail',fr'>"%CSBAT_STATE_DIR%\pending.txt" echo {n}',
             'if errorlevel 1 goto ApplyFail','set "CSBAT_COMMIT=1"')
        for i in changed:emit(f'call :Commit {i} "{relative(files[i]["path"])}" {stock[i]} {vector[i]}','if errorlevel 1 goto ApplyFail')
        emit(f'call :Check-{n}','if errorlevel 1 goto ApplyFail',fr'>"%CSBAT_STATE_DIR%\state.txt" echo {n}',
             'if errorlevel 1 goto ApplyFail',r'del /q "%CSBAT_STATE_DIR%\pending.txt"','call :Cleanup','exit /b %errorlevel%',f':Restore-{n}')
        # Verify the entire mixed input and every backup before any restore write.
        call('Guards')
        for i,file in enumerate(files):call('EitherHash',quoted('%CSBAT_ROOT%\\'+relative(file['path'])),stock[i],vector[i])
        for i in changed:call('Hash',quoted(f'%CSBAT_BACKUP%\\original-{i}.bin'),stock[i])
        emit('if not exist "%CSBAT_STAGE%" mkdir "%CSBAT_STAGE%"','if errorlevel 1 exit /b 1')
        for i in changed:
            temporary.add(f'restore-{i}.bin')
            call('RestoreFile',str(i),quoted(relative(files[i]['path'])),stock[i],vector[i])
        call('Check-0')
        emit(r'>"%CSBAT_STATE_DIR%\state.txt" echo 0','if errorlevel 1 exit /b 1',
             r'if exist "%CSBAT_STATE_DIR%\pending.txt" del /q "%CSBAT_STATE_DIR%\pending.txt"','call :Cleanup','exit /b %errorlevel%')
    emit(':Cleanup','if not exist "%CSBAT_STAGE%" exit /b 0')
    for name in sorted(temporary):emit(f'if exist "%CSBAT_STAGE%\\{name}" del /q "%CSBAT_STAGE%\\{name}"')
    emit('rmdir "%CSBAT_STAGE%"','exit /b %errorlevel%')
    # Keep executable command lines ASCII-only. Display UTF-8 Korean using TYPE
    # from separate text files, avoiding CMD's inline multibyte parsing issues.
    return ('\r\n'.join(lines)+'\r\n').encode('ascii')

def build(bundle,stock,out,fixture=False):
    bundle=clean(bundle);stock=clean(stock);out=clean(out)
    need(not out.exists(),'Use a new output directory')
    for source in [bundle,stock,HERE.parents[1]]:
        need(not out.is_relative_to(source) and not source.is_relative_to(out),'Output overlaps source')
    need(not any(c in str(out) for c in '%!&^()|<>') and all(ord(c)>=32 for c in str(out)),'Use a simple output path')
    need(fixture or sha(bundle/'manifest.json')==MANIFEST,'Use the exact tested Beta 1 manifest')
    manifest=json.loads((bundle/'manifest.json').read_text('utf-8-sig'))
    need(sha(bundle/'tools/xdelta3.exe')==TOOL,'Unexpected decoder')
    original=next(v['hashes'] for v in manifest['inputs'] if v['id']=='stock')
    for i,file in enumerate(manifest['files']):relative(file['path']);need(sha(stock/file['path'])==original[i],'Stock input differs: '+file['path'])
    for guard in manifest['guards']:relative(guard['path']);need(sha(stock/guard['path'])==guard['sha256'],'Stock guard differs')
    for file in manifest['files']:
        for edge in file['edges']:relative(edge['path']);need(sha(bundle/edge['path'])==edge['sha256'],'Delta differs')
    out.mkdir(parents=True);content=out/'Sandbox/Content';content.mkdir(parents=True)
    for file in [*manifest['files'],*manifest['guards']]:
        target=content/file['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(stock/file['path'],target)
    for folder in ['tools','patches']:
        (out/folder).mkdir()
    shutil.copyfile(bundle/'tools/xdelta3.exe',out/'tools/xdelta3.exe')
    for file in manifest['files']:
        for edge in file['edges']:
            target=out/edge['path']
            if not target.exists():shutil.copyfile(bundle/edge['path'],target)
    if (bundle/'licenses').exists():shutil.copytree(bundle/'licenses',out/'licenses')
    for name in ['LICENSE','THIRD-PARTY-NOTICES.txt']:
        if (bundle/name).exists():shutil.copyfile(bundle/name,out/name)
    marker=content/'.sandbox-approved'
    marker.write_bytes(('CSBAT-SANDBOX-v1\n'+sha(bundle/'manifest.json')+'\n'+('artificial fixture' if fixture else 'owned game copy')+'\n').encode('ascii'))
    (out/'Sandbox-Test.cmd').write_bytes(script(manifest,sha(marker)))
    for name,text in [('Menu.ko.txt',MENU_KO),('Actions.ko.txt',ACTIONS_KO)]:
        (out/name).write_bytes(text.replace('\n','\r\n').encode('utf-8'))
    (out/'manifest-reference.json').write_bytes((bundle/'manifest.json').read_bytes())
    shutil.copyfile(HERE/'README.ko.txt',out/'READ_ME_FIRST.ko.txt')
    info=dict(schema=1,kind='ARTIFICIAL_COMPATIBILITY_PROBE' if fixture else 'OWNED_GAME_SANDBOX',
        sourceManifestSha256=sha(bundle/'manifest.json'),decoderSha256=TOOL,batchSha256=sha(out/'Sandbox-Test.cmd'),
        profiles=PROFILES,installedGameWrites=0,settingsCacheSaveWrites=0,
        runtime='cmd.exe, choice.exe, certutil.exe, findstr.exe, pinned xdelta3.exe; no Python/PowerShell/custom EXE',
        SACCompatibility='UNVERIFIED: see a separate runtime test receipt; building is not a compatibility test')
    (out/'experiment.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(out=str(out),kind=info['kind'],profiles=len(PROFILES))),flush=True)
    return info

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['bundle','stock','out']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--fixture',action='store_true')
    args=parser.parse_args();build(args.bundle,args.stock,args.out,args.fixture)
