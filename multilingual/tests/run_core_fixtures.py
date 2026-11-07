"""Portable, destructive-error-boundary QA for the multilingual transaction core.

Requires Windows/.NET csc + official pinned xdelta3. Inputs are production C#
sources only; every Content file is synthetic, created in a new workspace.
The runner never opens a game, launcher or real user settings. Source clamps
are explicit and recorded; transaction/validation/recovery bodies are intact.
"""
from pathlib import Path
import argparse,base64,hashlib,json,os,re,shutil,subprocess,sys
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def blob_sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-dir',type=Path,required=True);ap.add_argument('--xdelta',type=Path,required=True);ap.add_argument('--work',type=Path,required=True);ap.add_argument('--csc',type=Path,default=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe'));a=ap.parse_args()
 source=a.source_dir.resolve(strict=True);work=a.work.resolve();assert not work.exists(),'Fresh workspace required';assert not work.is_relative_to(source)and not source.is_relative_to(work),'Sources and fixture outputs must be disjoint'
 assert sha(a.xdelta)=='732980d52f9220dc81817ccdd0c295eadce8a0048a24c2a771a73f791ac824e9','Use official pinned xdelta3 3.2.2'
 work.mkdir(parents=True);src=work/'src';src.mkdir();case_root=work/'f';case_root.mkdir();package=work/'package';(package/'tools').mkdir(parents=True);shutil.copyfile(a.xdelta,package/'tools/xdelta3.exe')
 runner=Path(__file__).resolve().with_name('CoreFixtureRunner.cs');assert runner.is_file()
 menu={'Categories':[{'Id':'language','Label':'Language','Items':[{'Id':'game-language','Label':'Game Language','Type':'dropdown','Options':['System','English','한국어'],'ArgValues':['','-locale en-US','-locale ko-KR'],'Default':'System','LaunchOnly':True,'IsLaunchArgument':True}]},{'Id':'graphics','Label':'Graphics','Items':[{'Id':'scaling','Options':['1280x960','1920x1080'],'ArgValues':['-scaling 2@cs2','-scaling 3@cs9'],'Default':'1280x960','IsLaunchArgument':True}]}]}
 menu_bytes=(json.dumps(menu,ensure_ascii=False,indent=2)+'\n').encode()
 base=[b'QA Native foundation\n'+bytes(range(64)),b'QA Data0000 foundation\n'+bytes(range(96)),b'QA Data0005 foundation\n'+bytes(range(128)),menu_bytes]
 variants={'ko-KR':base[:3],'en-US':[base[0]+b'\nEnglish data-only variant',base[1],base[2]+b'\nEnglish Unicode/font variant'],'es-ES':[base[0]+b'\nSpanish data-only variant',base[1],base[2]+b'\nSpanish Unicode/font variant']}
 files=['xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll','Game/DefaultPackage.data/Data0000','Game/DefaultPackage.data/Data0005','EmuMenu/Assets/TitleMenuData.json']
 foundation=work/'foundation';foundation.mkdir()
 for i,b in enumerate(base):(foundation/str(i)).write_bytes(b)
 catalog={'schema':1,'releaseId':'Fixture-0.12','tool':{'path':'tools/xdelta3.exe','sha256':sha(a.xdelta)},'packs':[]}
 for locale,contents in variants.items():
  p={'id':locale,'displayName':locale,'englishName':locale,'status':'baseline'if locale=='ko-KR'else'partial','fallback':None if locale=='ko-KR'else'ko-KR','coverage':'Synthetic transaction fixture, never a translation claim.','files':[]}
  for i,b in enumerate(contents):
   row={'path':files[i],'sha256':blob_sha(b),'bytes':len(b),'delta':None,'deltaSha256':None,'deltaBytes':0}
   if b!=base[i]:
    target=foundation/(locale+'-'+str(i));target.write_bytes(b);rel='patches/'+locale+'-'+str(i)+'.vcdiff';delta=package/rel;delta.parent.mkdir(exist_ok=True)
    subprocess.run([str(a.xdelta.resolve()),'-e','-9','-A','-D','-s',str(foundation/str(i)),str(target),str(delta)],check=True,capture_output=True)
    row.update(delta=rel,deltaSha256=sha(delta),deltaBytes=delta.stat().st_size)
   p['files'].append(row)
  catalog['packs'].append(p)
 dump(package/'catalog.json',catalog);catalog_hash=sha(package/'catalog.json')
 gpu=b'QA GPU untouched\n';menu_dll=b'QA original managed launcher sentinel\n';default_prefix=b'exe=..\\Emu.exe\r\n';defaults=default_prefix+b';'*(107-len(default_prefix));assert len(defaults)==107
 source_pins={p.name:sha(p)for p in[source/'MultilingualCore.cs',source/'MenuAndSettings.cs']}
 core=(source/'MultilingualCore.cs').read_text('utf8');helper=(source/'MenuAndSettings.cs').read_text('utf8');clamps=[]
 def replace(text,old,new,label):
  assert text.count(old)==1,(label,text.count(old));clamps.append({'label':label,'oldSha256':blob_sha(old.encode()),'newSha256':blob_sha(new.encode())});return text.replace(old,new)
 core=re.sub(r'public static readonly string\[\] FoundationHashes=\{.*?\};','public static readonly string[] FoundationHashes={'+','.join('"'+blob_sha(b)+'"'for b in base)+'};',core,count=1,flags=re.S)
 core=re.sub(r'public static readonly long\[\] FoundationBytes=\{.*?\};','public static readonly long[] FoundationBytes={'+','.join(str(len(b))+'L'for b in base)+'};',core,count=1,flags=re.S);clamps.append({'label':'Four synthetic foundation hashes/sizes'})
 for name,b,length in[('GpuHash',gpu,6393856),('MenuDllHash',menu_dll,634880),('LaunchDefaultsHash',defaults,107)]:
  core,count=re.subn(r'(public const string '+name+r'=)"[0-9a-f]{64}";',lambda m:m[1]+'"'+blob_sha(b)+'";',core,count=1);assert count==1
  core=replace(core,str(length)+'L',str(len(b))+'L','synthetic '+name+' size')
  clamps.append({'label':'Synthetic '+name+' hash'})
 patterns=[
  (r'public static string BackupBase\(\) \{[^\r\n]+\}', 'public static string BackupBase() {return QAHooks.Backups();}', 'backup path'),
  (r'public static string SettingsPath\(\) \{[^\r\n]+\}', 'public static string SettingsPath() {return QAHooks.Settings();}', 'settings path'),
  (r'public static bool ProcessPresent\(string name\) \{[^\r\n]+\}', 'public static bool ProcessPresent(string name) {return QAHooks.Running(name);}', 'process inventory'),
  (r'static void Fault\(string phase\) \{ \}', 'static void Fault(string phase) {QAHooks.Fault(phase);}', 'fault injection'),
  (r'public string ReleaseBackupDirectory\(string content\) \{[^\r\n]+\}', 'public string ReleaseBackupDirectory(string content) {return Child(Child(Child(BackupBase(),RootIdentity(content).Substring(0,12)),CatalogPin.ReleaseId),CatalogPin.Digest.ToLowerInvariant().Substring(0,12));}', 'short private backup path (root/release/catalog separation retained)'),
  (r'public void LaunchOriginal\(string content\) \{.*?\n  \}', 'public void LaunchOriginal(string content) {RequireStopped();VerifyLauncher(content);string exe=Child(content,"EmuMenu/EmuMenu.exe");NoReparse(exe,false);QAHooks.Launch(content,exe);}', 'launch sink')]
 for pat,new,label in patterns:
  core,count=re.subn(pat,lambda m:new,core,count=1,flags=re.S if label=='launch sink'else 0);assert count==1,label;clamps.append({'label':label})
 helper,count=re.subn(r'(public const string FoundationSha256 = )"[0-9a-f]{64}";',lambda m:m[1]+'"'+blob_sha(menu_bytes)+'";',helper,count=1);assert count==1;clamps.append({'label':'Synthetic menu foundation SHA only; menu/settings methods unmodified'})
 (src/'MultilingualCore.cs').write_text(core,'utf8');(src/'MenuAndSettings.cs').write_text(helper,'utf8');shutil.copyfile(runner,src/runner.name)
 exe=work/'CoreFixtureRunner.exe';cmd=[str(a.csc.resolve()),'/nologo','/target:exe','/optimize+','/r:System.Web.Extensions.dll','/r:System.Xml.dll','/out:'+str(exe),str(src/'MultilingualCore.cs'),str(src/'MenuAndSettings.cs'),str(src/runner.name)]
 c=subprocess.run(cmd,capture_output=True);(work/'compile.log').write_bytes(c.stdout+c.stderr);assert c.returncode==0,c.stdout+c.stderr
 initial='; original\r\nAA=4x\r\ngame-language=English\r\naudio=on\r\nscaling=1920×1080 (1080p, 16:9)\r\n'.encode()
 xml='<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"><Identity Name="Xbox360BackwardCompatibil.PrimaryCrimsonSkiesHighR" Version="2608.3123.1.0" ProcessorArchitecture="x64" Publisher="CN=92ADE8CC-2A9A-4DF3-9BAF-18AF498CAA12" /></Package>'
 rows=[];case_no=0
 def fresh(name):
  nonlocal case_no
  case_no+=1;root=case_root/str(case_no);content=root/'Content';content.mkdir(parents=True)
  for rel,b in zip(files,base):p=content/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  for rel,b in[('VGPUDX12.dll',gpu),('EmuMenu/EmuMenu.dll',menu_dll),('EmuMenu/EmuMenuLaunchArguments.txt',defaults),('EmuMenu/EmuMenu.exe',b'QA never executed'),('appxmanifest.xml',xml.encode())]:p=content/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  settings=root/'Settings.ini';settings.write_bytes(initial)
  return {'name':name,'root':root,'content':content,'settings':settings,'backups':root/'b'}
 def invoke(case,mode,pack=None,**kw):
  cfg={'package':str(package),'content':str(case['content']),'settings':str(case['settings']),'backups':str(case['backups']),'mode':mode,'pack':pack,'catalogHash':catalog_hash,**kw}
  idx=len(list(case['root'].glob('run-*.json')));cp=case['root']/('run-'+str(idx)+'.json');rp=case['root']/('result-'+str(idx)+'.json');dump(cp,cfg)
  p=subprocess.run([str(exe),str(cp),str(rp)],capture_output=True);assert rp.exists(),p.stderr+p.stdout;return json.loads(rp.read_text('utf8'))
 def state(case):return [sha(case['content']/p)for p in files],case['settings'].read_bytes()if case['settings'].exists()else None
 def receipt_dir(case,digest=catalog_hash):
  identity=blob_sha(str(case['content'].resolve()).upper().encode())[:12]
  return case['backups']/identity/'Fixture-0.12'/digest[:12]
 def add(name,ok,detail=None):rows.append({'name':name,'status':'PASS'if ok else'FAIL','detail':detail});print(json.dumps({'case':name,'status':rows[-1]['status']}),flush=True)
 # Complete install/switch/restore, immutable baseline and proper launch ordering.
 c=fresh('roundtrip');s0=state(c);r=invoke(c,'--check');add('check-is-readonly',r['success']and state(c)==s0 and not c['backups'].exists())
 r=invoke(c,'--restore');add('unowned-foundation-restore-refused',not r['success']and state(c)==s0)
 for locale in['ko-KR','en-US','es-ES','en-US']:
  r=invoke(c,'--activate',locale);expected=[blob_sha(b)for b in variants[locale]];add('roundtrip-activate-'+locale+str(len(rows)),r['success']and state(c)[0][:3]==expected and('game-language='+locale).encode()in state(c)[1],r.get('error'))
  if locale=='ko-KR':saved=[sha(receipt_dir(c)/('base-'+str(i)+'.bin'))for i in range(4)]
  add('immutable-foundation-'+locale+str(len(rows)),saved==[sha(receipt_dir(c)/('base-'+str(i)+'.bin'))for i in range(4)])
 c['settings'].write_bytes(c['settings'].read_bytes().replace(b'AA=4x',b'AA=2x'))
 r=invoke(c,'--restore');add('restore-foundation-preserve-current-aa',r['success']and state(c)[0]==s0[0]and state(c)[1]==initial.replace(b'AA=4x',b'AA=2x'),r.get('error'))
 for locale in['ko-KR','en-US','es-ES']:
  c=fresh('launch-'+locale);r=invoke(c,'--activate',locale,open=True,launchSetsMenu=True);add('launch-after-success-'+locale,r['success']and r['launches']==1 and not(receipt_dir(c)/'journal.json').exists(),r.get('error'))
 c=fresh('launchfail');s0=state(c);r=invoke(c,'--activate','en-US',open=True,launchFail=True);add('launch-start-failure-rolls-back',not r['success']and r['launches']==1 and state(c)==s0 and not(receipt_dir(c)/'journal.json').exists(),r.get('error'))
 c=fresh('switch-launchfail');assert invoke(c,'--activate','en-US')['success'];s0=state(c);old_receipt=(receipt_dir(c)/'receipt.json').read_bytes();r=invoke(c,'--activate','es-ES',open=True,launchFail=True);add('switch-launch-failure-restores-active-pack-and-receipt',not r['success']and state(c)==s0 and(receipt_dir(c)/'receipt.json').read_bytes()==old_receipt,r.get('error'))
 for process in['emu','menu']:
  c=fresh('running-'+process);s0=state(c);r=invoke(c,'--activate','en-US',**{process:True});add('running-'+process+'-refused',not r['success']and state(c)==s0 and not c['backups'].exists())
  r=invoke(c,'--check',**{process:True});add('running-'+process+'-check-readonly',r['success']and state(c)==s0 and not c['backups'].exists())
 c=fresh('mutex');s0=state(c);r=invoke(c,'--activate','en-US',mutexRoot=str(c['content']));add('same-root-mutex-contention-refused',not r['success']and state(c)==s0)
 other=fresh('other-root');r=invoke(c,'--activate','en-US',mutexRoot=str(other['content']));add('different-root-mutex-does-not-block',r['success'])
 c=fresh('held-target');s0=state(c);r=invoke(c,'--activate','en-US',lockFile=str(c['content']/files[2]));add('held-file-refused-beforewrites',not r['success']and state(c)==s0)
 for phase in['before-journal','after-journal','after-commit-0','after-commit-1','after-commit-2','after-commit-3','after-settings','after-receipt','before-launch']:
  c=fresh('fault-'+phase);s0=state(c);r=invoke(c,'--activate','en-US',faultPhase=phase,open=phase=='before-launch');add('late-fault-rollback-'+phase,not r['success']and state(c)==s0 and(r['launches']==0),r.get('error'))
 def prepared(name):
  c=fresh(name);r=invoke(c,'--activate','en-US',faultPhase='after-journal',blockRecovery=True);assert not r['success'];directory=receipt_dir(c);jp=directory/'journal.json';assert jp.exists();j=json.loads(jp.read_text('utf8'));return c,jp,j
 c,jp,j=prepared('check-owned-pending');s0=state(c);journal_hash=sha(jp);r=invoke(c,'--check',emu=True);add('owned-pending-check-running-is-readonly',r['success']and state(c)==s0 and sha(jp)==journal_hash)
 for phase in['before-journal','after-settings']:
  c=fresh('concurrent-'+phase);r=invoke(c,'--activate','en-US',faultPhase=phase,concurrentAA='8x');add('rollback-preserves-concurrent-aa-'+phase,not r['success']and state(c)[0]==[blob_sha(b)for b in base]and state(c)[1]==initial.replace(b'AA=4x',b'AA=8x'),r.get('error'))
 # 8 distinct changed-file vectors x settings-before/after x receipt-before/after.
 # Data0000 is identical and is deliberately not counted as another mask bit.
 for mode in['--activate','--restore']:
  for mask in range(8):
   for settings_after in[False,True]:
    for receipt_after in[False,True]:
     name='partial-'+mode[2:]+'-'+str(mask)+'-'+str(int(settings_after))+'-'+str(int(receipt_after));c,jp,j=prepared(name);stage=c['content']/j['stage']
     for bit,index in enumerate([0,2,3]):
      if mask&(1<<bit):shutil.copyfile(stage/('ready-'+str(index)+'.bin'),c['content']/files[index])
     if settings_after:c['settings'].write_bytes(base64.b64decode(j['afterSettings']))
     if receipt_after:(jp.parent/'receipt.json').write_bytes(base64.b64decode(j['afterReceipt']))
     r=invoke(c,mode,'en-US'if mode=='--activate'else None);expected=[blob_sha(b)for b in(variants['en-US']if mode=='--activate'else base[:3])]
     ok=r['success']and state(c)[0][:3]==expected and not jp.exists()
     if mode=='--restore':ok=ok and state(c)[0][3]==blob_sha(base[3])and state(c)[1]==initial and not(jp.parent/'receipt.json').exists()
     add(name,ok,r.get('error'))
 # Tampered recovery snapshots/identity/file paths must refuse before recovery.
 for field,value in[('root','C:/not-this-root'),('stage','../escape'),('settingsPath','C:/not-fixture/Settings.ini'),('targetPackId','unknown')]:
  c,jp,j=prepared('journal-'+field);j[field]=value;dump(jp,j);s0=state(c);r=invoke(c,'--activate','en-US');add('tampered-journal-'+field,not r['success']and state(c)==s0)
 c,jp,j=prepared('journal-aa');j['beforeSettings']=base64.b64encode(initial.replace(b'AA=4x',b'AA=off')).decode();c['settings'].write_bytes(base64.b64decode(j['afterSettings']));dump(jp,j);s0=state(c);r=invoke(c,'--activate','en-US');add('tampered-before-aa-snapshot-refused',not r['success']and state(c)==s0)
 c,jp,j=prepared('journal-selection');j['selectionBefore']['OriginalLine']='game-language=Deutsch';dump(jp,j);s0=state(c);r=invoke(c,'--activate','en-US');add('tampered-journal-selector-refused',not r['success']and state(c)==s0)
 c,jp,j=prepared('unknownpartial');(c['content']/files[0]).write_bytes(b'unknown content');s0=state(c);r=invoke(c,'--restore');add('unknown-owned-partial-refused',not r['success']and state(c)==s0)
 c=fresh('unownedmixed');(c['content']/files[0]).write_bytes(variants['en-US'][0]);s0=state(c);r=invoke(c,'--activate','en-US');add('unowned-mixed-profile-refused',not r['success']and state(c)==s0)
 c=fresh('receipt-otherroot');assert invoke(c,'--activate','en-US')['success'];rp=receipt_dir(c)/'receipt.json';rj=json.loads(rp.read_text('utf8'));rj['root']='C:/wrong';dump(rp,rj);s0=state(c);r=invoke(c,'--restore');add('wrong-root-receipt-refused',not r['success']and state(c)==s0)
 c=fresh('backup-tamper');assert invoke(c,'--activate','en-US')['success'];(receipt_dir(c)/'base-0.bin').write_bytes(b'tampered');s0=state(c);r=invoke(c,'--activate','es-ES');add('tampered-immutable-base-refused',not r['success']and state(c)==s0)
 # Catalog, delta/tool and host identity mutations are restored after each case.
 for name,path in[('catalog',package/'catalog.json'),('delta',next((package/'patches').glob('*.vcdiff'))),('tool',package/'tools/xdelta3.exe')]:
  original_bytes=path.read_bytes();path.write_bytes(original_bytes+b'X');c=fresh('tamper-'+name);s0=state(c);r=invoke(c,'--activate','en-US');add('tampered-'+name+'-refused',not r['success']and state(c)==s0);path.write_bytes(original_bytes)
 for name,relative in[('gpu','VGPUDX12.dll'),('managed-launcher','EmuMenu/EmuMenu.dll'),('launch-defaults','EmuMenu/EmuMenuLaunchArguments.txt')]:
  c=fresh('host-'+name);(c['content']/relative).write_bytes(b'not the expected host');s0=state(c);r=invoke(c,'--activate','en-US');add('unknown-'+name+'-refused',not r['success']and state(c)==s0)
 for name,bad in[('version',xml.replace('2608.3123.1.0','1.0.0.0')),('nested',xml.replace('<Identity','<Properties><Identity').replace(' /></Package>',' /></Properties></Package>')),('duplicate',xml.replace(' /></Package>',' /><Identity Name="second" /></Package>')),('dtd','<!DOCTYPE Package [<!ENTITY x "x">]>'+xml)]:
  c=fresh('host-xml-'+name);(c['content']/'appxmanifest.xml').write_text(bad,'utf8');s0=state(c);r=invoke(c,'--activate','en-US');add('host-xml-'+name+'-refused',not r['success']and state(c)==s0)
 # Catalog changes have separate immutable backup namespaces. An active old
 # profile must first be restored by its owning old tool, not adopted silently.
 alt_package=work/'packageB';shutil.copytree(package,alt_package);alternate=json.loads((alt_package/'catalog.json').read_text('utf8'));alternate['packs'][1]['coverage']+=' Alternate catalog.';dump(alt_package/'catalog.json',alternate);alt_hash=sha(alt_package/'catalog.json')
 c=fresh('catalog-upgrade');assert invoke(c,'--activate','en-US')['success'];s0=state(c);r=invoke(c,'--activate','es-ES',package=str(alt_package),catalogHash=alt_hash);add('new-catalog-refuses-old-active-pack',not r['success']and state(c)==s0 and not receipt_dir(c,alt_hash).exists())
 assert invoke(c,'--restore')['success'];old_backup={p.name:sha(p)for p in receipt_dir(c).iterdir()if p.is_file()};r=invoke(c,'--activate','es-ES',package=str(alt_package),catalogHash=alt_hash);add('new-catalog-after-old-restore-activates',r['success']and state(c)[0][:3]==[blob_sha(b)for b in variants['es-ES']]and receipt_dir(c,alt_hash).exists(),r.get('error'))
 add('catalog-upgrade-keeps-old-backups-immutable',old_backup=={p.name:sha(p)for p in receipt_dir(c).iterdir()if p.is_file()})
 r=invoke(c,'--restore',package=str(alt_package),catalogHash=alt_hash);add('new-catalog-restore-returns-foundation',r['success']and state(c)[0]==[blob_sha(b)for b in base]and state(c)[1]==initial,r.get('error'))
 source_unchanged=source_pins=={p.name:sha(p)for p in[source/'MultilingualCore.cs',source/'MenuAndSettings.cs']};add('production-source-unchanged-during-bound-run',source_unchanged)
 result={'schema':'multilingual-core-portable-synthetic-transaction-qa-v1','status':'PASS'if all(r['status']=='PASS'for r in rows)else'FAIL','uniqueOutcomes':len(rows),'passed':sum(r['status']=='PASS'for r in rows),'cases':rows,'productionSourcePins':source_pins,'productionSourceUnchangedDuringRun':source_unchanged,'clamps':clamps,'clampedSourcePins':{p.name:sha(p)for p in src.glob('*.cs')},'runnerSha256':sha(exe),'testScriptSha256':sha(__file__),'sourceBeforeAfterChanges':'No source edits; copied/clamped fixture source only','originalLaunchDefaultsUnchanged':True,'nativeGpuTargetCodeExecuted':False,'actualGameSettingsProcessesAccessed':False,'scope':'Real xdelta decode and unmodified core catalog/host/ownership/transaction/recovery logic with synthetic Content files. Explicit fixture clamps replace constants, process/launch callbacks and all user paths. No physical launcher/gameplay test.'}
 dump(work/'results.json',result);print(json.dumps({'status':result['status'],'uniqueOutcomes':len(rows),'passed':result['passed'],'failures':[r for r in rows if r['status']=='FAIL']},ensure_ascii=False,indent=2));raise SystemExit(0 if result['status']=='PASS'else 1)
if __name__=='__main__':main()
