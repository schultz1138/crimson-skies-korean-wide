"""Package public deltas + verified upstream runtime + source; no game inputs."""
from pathlib import Path
import argparse, hashlib, json, shutil, zipfile

HERE = Path(__file__).resolve().parent
MANIFEST = 'c2bd4fa525a2ae0cec2339ca9eb85783a4aaf39d695704cce7695c67f877d4cb'
RUNTIME = 'd012f3aa29cf07436dae8aea1fec0fd195c2612a0b059b1f915ae0afb9ad1f62'
RELEASE = '0.14.0-beta.2-bat.1'
# Exact manifest emitted by Xbox Verify and Repair on 2608.3123.1.0. Identity
# is independently validated at runtime. No XML file is modified or distributed.
REPAIRED_APPX = dict(bytes=4767,sha256='00e65011722a9efb2ad75a197398cef798311ce5d7f08bde47c8cc96aacf6633')
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def build(bundle, runtime, out, fixture=False, stock_native_voices=False):
    for source in ('main.py','host.py','cache.py','engine.py'):
        compile((HERE/source).read_text('utf-8'), str(HERE/source), 'exec')
    assert not out.exists() and not out.is_relative_to(bundle) and not bundle.is_relative_to(out)
    assert fixture or sha(bundle/'manifest.json') == MANIFEST
    assert sha(runtime) == RUNTIME
    m = json.loads((bundle/'manifest.json').read_text('utf-8-sig'))
    source_manifest = sha(bundle/'manifest.json')
    out.mkdir(parents=True); (out/'tools').mkdir(); (out/'patches').mkdir(); (out/'installer').mkdir()
    if stock_native_voices:
        stock = next(v['hashes'] for v in m['inputs'] if v['id']=='stock')
        voices = next(v for v in m['profiles'] if v['id']=='k1-w0-d1-off')
        assert voices['hashes'][1] == stock[1]
        voices['hashes'][0] = stock[0]
        (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    else:
        shutil.copyfile(bundle/'manifest.json',out/'manifest.json')
    assert sha(bundle/m['tool']['path']) == m['tool']['sha256']
    shutil.copyfile(bundle/m['tool']['path'],out/m['tool']['path'])
    for file in m['files']:
        for edge in file['edges']:
            assert sha(bundle/edge['path']) == edge['sha256']
            shutil.copyfile(bundle/edge['path'],out/edge['path'])
    for name in ['main.py','host.py','cache.py','engine.py']:
        shutil.copyfile(HERE/name,out/'installer'/name)
    (out/'runtime').mkdir()
    with zipfile.ZipFile(runtime) as archive:
        for name in archive.namelist():
            assert '/' not in name and '\\' not in name and ':' not in name and name not in ('.','..')
        archive.extractall(out/'runtime')
    # Upstream files remain byte-exact, including its restricted ._pth.
    for name in ['licenses']:
        if (bundle/name).exists(): shutil.copytree(bundle/name,out/name)
    for name in ['LICENSE','THIRD-PARTY-NOTICES.txt','FONT-NOTICE.txt','AI-DUB-NOTICE.txt']:
        if (bundle/name).exists(): shutil.copyfile(bundle/name,out/name)
    with (out/'THIRD-PARTY-NOTICES.txt').open('a',encoding='utf-8') as notices:
        notices.write('\nPython 3.15.2 Windows x64 embeddable distribution, Python Software Foundation.\n'
                      'Official upstream binaries are unchanged; license: runtime/LICENSE.txt.\n'
                      'https://www.python.org/downloads/release/python-3152/\n'
                      'Archive SHA-256: '+RUNTIME+'\n')
    shutil.copyfile(HERE/'README.ko.txt',out/'README.ko.txt')
    if stock_native_voices:
        shutil.copyfile(HERE/'README.stock-dll.ko.txt',out/'README.ko.txt')
    inventory = {str(p.relative_to(out)).replace('\\','/'):sha(p) for p in out.rglob('*') if p.is_file()}
    pins = dict(schema=1,releaseId=RELEASE+('-stock-native' if stock_native_voices else ''),manifestSha256=sha(out/'manifest.json'),legacyManifestSha256=source_manifest,
                runtimeVersion='3.15.2',runtimeArchiveSha256=RUNTIME,files=inventory,
                hostGuardAlternates={'appxmanifest.xml':[REPAIRED_APPX]})
    if stock_native_voices:
        pins.update(stockNativeMode=True,allowedProfiles=['k0-w0-d0-off','k1-w0-d1-off'])
    (out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf-8')
    bootstrap = ['@echo off','title Crimson Skies BAT Installer','setlocal EnableExtensions DisableDelayedExpansion','chcp 65001 >nul',
                 'set "CSBAT_BASE=%~dp0"',
                 'set CSBAT_BASE | "%SystemRoot%\\System32\\findstr.exe" /l /c:"%%" /c:"!" /c:"&" /c:"^" /c:"(" /c:")" /c:"|" /c:"<" /c:">" >nul',
                 'if not errorlevel 1 goto UnsafePath']
    for name, expected in {**inventory,'pins.json':sha(out/'pins.json')}.items():
        if name.startswith(('runtime/','installer/')) or name in ('pins.json','manifest.json','tools/xdelta3.exe'):
            bootstrap += ['call :Hash "'+name.replace('/','\\')+'" '+expected,'if errorlevel 1 goto BadPackage']
    bootstrap += ['if "%~1"=="" goto Interactive',
                  '"%CSBAT_BASE%runtime\\python.exe" -I -B -X utf8 "%CSBAT_BASE%installer\\main.py" %*',
                  'exit /b %errorlevel%',':Interactive',
                  '"%CSBAT_BASE%runtime\\python.exe" -I -B -X utf8 "%CSBAT_BASE%installer\\main.py"',
                  'set "CSBAT_EXIT=%errorlevel%"','pause','exit /b %CSBAT_EXIT%',
                  ':UnsafePath','echo Extract to a path without percent, exclamation or shell metacharacters.','pause','exit /b 2',
                  ':BadPackage','echo Package verification failed. Extract the complete original ZIP.','exit /b 1',
                  ':Hash','"%SystemRoot%\\System32\\certutil.exe" -hashfile "%CSBAT_BASE%%~1" SHA256 2>nul | "%SystemRoot%\\System32\\findstr.exe" /l /i /x /c:"%~2" >nul','exit /b %errorlevel%']
    (out/'CrimsonSkies-Install.cmd').write_bytes(('\r\n'.join(bootstrap)+'\r\n').encode('ascii'))
    hashes = {str(p.relative_to(out)).replace('\\','/'):sha(p) for p in out.rglob('*') if p.is_file()}
    (out/'FILE-HASHES.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
    archive = out.parent/(out.name+'.zip'); assert not archive.exists()
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as target:
        for p in sorted(out.rglob('*')):
            if p.is_file(): target.write(p,str(Path(out.name)/p.relative_to(out)))
    report = dict(releaseId=pins['releaseId'],bytes=archive.stat().st_size,sha256=sha(archive),zip=str(archive),
                  manifestSha256=pins['manifestSha256'],ownInstallerExe=False,upstreamPython=RUNTIME,
                  originalGameFilesIncluded=False,SACCompatibility='Pending final runtime and download tests')
    archive.with_suffix('.zip.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)
    return pins

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('bundle','runtime','out'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--stock-native-voices',action='store_true')
    a=p.parse_args(); build(a.bundle.resolve(),a.runtime.resolve(),a.out.resolve(),stock_native_voices=a.stock_native_voices)
