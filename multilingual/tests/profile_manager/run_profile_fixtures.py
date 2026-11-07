# SPDX-License-Identifier: MIT
"""Windows-only synthetic profile-manager QA. No installed game is required."""
import argparse, hashlib, json, os, pathlib, shutil, subprocess, sys
sys.dont_write_bytecode = True
P = pathlib.Path
HERE = P(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def replace_once(text, before, after):
    if text.count(before) != 1: raise RuntimeError('Named fixture seam changed: '+before[:70])
    return text.replace(before, after)
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-dir',type=P,required=True,help='Folder containing the nine production C# launcher files')
    ap.add_argument('--work',type=P,required=True,help='Fresh absent private workspace; a short local NTFS path is recommended')
    ap.add_argument('--csc',type=P,default=P(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe')
    a=ap.parse_args(); src=a.source_dir.resolve(); work=a.work.resolve()
    if os.name!='nt': raise RuntimeError('Windows/.NET Framework/NTFS are required')
    if work.exists() or work==P(work.anchor): raise RuntimeError('Workspace must be fresh and absent')
    if work==src or src in work.parents or work in src.parents: raise RuntimeError('Workspace and production sources must be separate')
    for ancestor in (work,*work.parents):
        if ancestor.name.lower()=='wgs' or (ancestor/'containers.index').exists() or (ancestor/'appxmanifest.xml').exists() or (ancestor/'Content/appxmanifest.xml').exists():
            raise RuntimeError('Refusing a game or save-store workspace')
    names=['ProfileStore.cs','ProfileBackup.cs','ProfileTombstone.cs','ProfileOperations.cs','ProfileRestoreImage.cs','ProfileRestoreOperations.cs','ProfileManagerBackend.cs','ProfileManagerUi.cs','MultilingualUi.cs','MultilingualCore.cs','MenuAndSettings.cs']
    sources={n:src/n for n in names}
    if any(not p.is_file() for p in sources.values()): raise RuntimeError('Production source file missing')
    inputs={n:sha(p) for n,p in sources.items()}
    fixtures=['ProfileStoreFixture.cs','ProfileBackupFixture.cs','ProfileOperationsFixture.cs','ProfileOperationsAdversarialFixture.cs','ProfileUiFixture.cs','ProfileLaunchGuardFixture.cs','ProfilePathProbe.cs','ProfileRestoreFixture.cs','ProfileRestoreRecoveryFixture.cs','ProfileCrossVersionFixture.cs','ProfileRestoreUiFixture.cs','LegacyProfileOperations_v0121.cs']
    if any(not(HERE/n).is_file() for n in fixtures): raise RuntimeError('Fixture source file missing')
    work.mkdir(parents=True); code=work/'code'; code.mkdir(); temp=work/'tmp'; temp.mkdir()
    env=dict(os.environ,TEMP=str(temp),TMP=str(temp),PYTHONDONTWRITEBYTECODE='1')
    def write(n,s):
        p=code/n;p.write_text(s,encoding='utf-8');return p
    for n,p in sources.items(): shutil.copyfile(p,code/n)
    for n in fixtures: shutil.copyfile(HERE/n,code/n)
    store=write('Store.clamped.cs',replace_once(sources['ProfileStore.cs'].read_text(encoding='utf-8'),
        'public static string DefaultWgsRoot() {return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Packages",PackageFamilyName,"SystemAppData","wgs");}',
        'public static string DefaultWgsRoot() {return ProfileBackupFixture.DefaultWgs;}'))
    ops=write('Operations.clamped.cs',replace_once(sources['ProfileOperations.cs'].read_text(encoding='utf-8'),
        'scopeRoot=Path.Combine(stateRoot,"Transactions",ProfileStore.Hash(Utf8.GetBytes(wgsRoot.ToUpperInvariant())).Substring(0,16));','scopeRoot=stateRoot;'))
    legacy_ops=write('LegacyOperations.clamped.cs',replace_once((HERE/'LegacyProfileOperations_v0121.cs').read_text(encoding='utf-8'),
        'scopeRoot=Path.Combine(stateRoot,"Transactions",ProfileStore.Hash(Utf8.GetBytes(wgsRoot.ToUpperInvariant())).Substring(0,16));','scopeRoot=stateRoot;'))
    ui=write('LanguageUi.clamped.cs',replace_once(sources['MultilingualUi.cs'].read_text(encoding='utf-8'),
        'return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "CrimsonSkiesLanguagePacks", "ui.json");','return FixtureState.PreferencePath;'))
    refs=['System.Core','System.Web.Extensions','System.IO.Compression','System.IO.Compression.FileSystem','System.Xml','System.Security','System.Windows.Forms','System.Drawing']
    def run(args):
        r=subprocess.run([str(x) for x in args],cwd=work,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        if r.returncode: raise RuntimeError(r.stdout.decode('utf-8',errors='replace'))
        return r.stdout.decode('utf-8',errors='replace')
    def compile_exe(main,files):
        out=work/(main+'.exe');run([a.csc,'/nologo','/target:exe','/main:'+main,'/out:'+str(out),*['/r:'+r+'.dll' for r in refs],*[code/f if isinstance(f,str) else f for f in files]])
        return out
    cohorts=[]
    def cohort(label,main,files,args):
        report=work/(label+'.json');exe=compile_exe(main,files);run([exe,*args,report]);result=json.loads(report.read_text(encoding='utf-8-sig'))
        if result.get('status')!='PASS':raise RuntimeError('Fixture failed: '+label)
        cohorts.append({'name':label,'cases':result['cases'],'sha256':sha(report),'report':report.name})
    cohort('store','ProfileStoreFixture',['ProfileStoreFixture.cs','ProfileStore.cs'],[work/'a'])
    backup_files=['ProfileStoreFixture.cs','ProfileBackupFixture.cs',store,'ProfileBackup.cs']
    cohort('backup','ProfileBackupFixture',backup_files,[work/'b'])
    operation_files=backup_files+['ProfileOperationsFixture.cs','ProfileOperationsAdversarialFixture.cs',ops,'ProfileTombstone.cs','ProfileRestoreImage.cs','ProfileRestoreOperations.cs','ProfileManagerUi.cs','ProfileManagerBackend.cs','MultilingualCore.cs','MenuAndSettings.cs']
    cohort('operations','ProfileOperationsFixture',operation_files,[work/'c'])
    cohort('adversarial','ProfileOperationsAdversarialFixture',operation_files,[work/'d'])
    cohort('restore','ProfileRestoreFixture',operation_files+['ProfileRestoreFixture.cs'],[work/'e'])
    cohort('restore-recovery','ProfileRestoreRecoveryFixture',operation_files+['ProfileRestoreFixture.cs','ProfileRestoreRecoveryFixture.cs'],[work/'f'])
    legacy_files=backup_files+['ProfileOperationsFixture.cs','ProfileCrossVersionFixture.cs',legacy_ops,'ProfileTombstone.cs','MultilingualCore.cs','MenuAndSettings.cs']
    legacy=compile_exe('LegacyPendingDeleteFixture',legacy_files)
    run([legacy,work/'g'])
    cohort('cross-version','NewRecoverLegacyFixture',operation_files+['ProfileCrossVersionFixture.cs'],[work/'g'])
    cohort('ui','ProfileUiFixture',['ProfileUiFixture.cs','ProfileManagerUi.cs'],[])
    cohort('restore-ui','ProfileRestoreUiFixture',['ProfileRestoreUiFixture.cs','ProfileManagerUi.cs'],[])
    cohort('launch-guard','ProfileLaunchGuardFixture',['ProfileLaunchGuardFixture.cs','ProfileManagerUi.cs',ui],[work])
    probe=compile_exe('ProfilePathProbe',['ProfilePathProbe.cs','ProfileStore.cs'])
    ps=write('junction.ps1','param([string]$Link,[string]$Target)\nNew-Item -ItemType Junction -Path $Link -Target $Target -ErrorAction Stop | Out-Null\n')
    store_target=work/'a/s0';user=store_target/'0123456789ABCDEF_0123456789ABCDEF0123456789ABCDEF'
    for n,target in enumerate((store_target,user)):
        link=work/('j'+str(n));run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',ps,'-Link',link,'-Target',target]);run([probe,work,link])
    if inputs!={n:sha(p) for n,p in sources.items()}: raise RuntimeError('Source changed during QA')
    result={'schema':1,'status':'PASS','sourceSha256':inputs,'fixtureSha256':{n:sha(HERE/n) for n in fixtures},'cohorts':cohorts,'ntfsJunctionCases':2,'assertions':sum(c['cases'] for c in cohorts)+2,
        'clamps':['DefaultWgsRoot returns fixture path','ProfileOperations scopeRoot resolver shortened inside workspace','GUI PreferencePath returns fixture path'],
        'dependenciesStubbed':['Process state injected through production callback','GUI/CLI PackEngine and ProfileManagerServices dependency boundary stubbed'],
        'limits':['No real game/WGS/cloud operations','No SDK tool or proprietary binary is required or distributed','Host-package adapter and cloud protocol need separate validation','DPAPI/HMAC checks do not protect against the same Windows principal rewriting/decrypting everything']}
    (work/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'status':'PASS','assertions':result['assertions'],'report':'verification.json'}))
if __name__=='__main__':main()
