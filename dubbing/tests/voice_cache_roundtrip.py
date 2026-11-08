"""Owned synthetic XTAF cache round trips; installed cache is READ ONLY probed."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys
import argparse
REPO=Path(__file__).resolve().parents[2]
a=argparse.ArgumentParser(description="Synthetic voice-cache install/restore/rollback tests; no installed-cache writes")
a.add_argument('--bundle',required=True,type=Path);a.add_argument('--source-content',required=True,type=Path);a.add_argument('--dubbed-content',required=True,type=Path);a.add_argument('--out',required=True,type=Path)
args=a.parse_args();BUNDLE=args.bundle.resolve();BASE=args.source_content.resolve();TARGET=args.dubbed_content.resolve();WORK=args.out.resolve();SRC=REPO/'dubbing/audio'
assert not WORK.exists() and all(not WORK.is_relative_to(p)and not p.is_relative_to(WORK)for p in [REPO,BASE,TARGET,BUNDLE])
def locate(logical):
 page,within=divmod(logical,4096);volume,local=divmod(page,41412);group,slot=divmod(local,204);return volume,(2+group*205+slot)*4096+within,within,group,slot

def archive(content):
 out=bytearray();start=822077440;size=2301230
 while len(out)<size:
  v,physical,w,g,s=locate(start+len(out));n=min(size-len(out),(204-s)*4096-w)
  with(content/f'Game/DefaultPackage.data/Data{v:04d}').open('rb')as f:f.seek(physical);out+=f.read(n)
 return bytes(out)
def create(zipdata,path):
 cluster=65536;data=0x12000;n=(len(zipdata)+cluster-1)//cluster;end=5+n;raw=bytearray([0xa5])*(data+(end+2)*cluster);raw[:4096]=b'\xff'*4096;struct.pack_into('>4I',raw,0,0x58544146,0x11223344,128,1);raw[4096:data]=bytes(data-4096)
 def fat(c,nxt):struct.pack_into('>H',raw,4096+c*2,nxt)
 fat(0,0xfff8)
 for c in [1,2,3,4]:fat(c,0xffff)
 for c in range(5,end):fat(c,c+1 if c+1<end else 0xffff)
 fat(end,end+1);fat(end+1,0xffff)
 def record(at,name,flags,c,size):
  raw[at:at+64]=b'\xff'*64;b=name.encode('ascii');raw[at]=len(b);raw[at+1]=flags;raw[at+2:at+2+len(b)]=b;struct.pack_into('>II',raw,at+44,c,size)
 for c in [1,2,3,4]:raw[data+(c-1)*cluster:data+c*cluster]=b'\xff'*cluster
 for i in range(3):record(data+i*64,'Xbox'+str(i),16,i+2,0)
 folder=data+3*cluster;record(folder,'cinematics_dialog_sound.zip',0,5,len(zipdata));record(folder+64,'checkpoint.dat',0,end,100000);record(folder+128,'cache_good.txt',0,0,0)
 pos=data+4*cluster;raw[pos:pos+len(zipdata)]=zipdata;path.write_bytes(raw);return bytes(raw),pos
def main():
 WORK.mkdir(parents=True,exist_ok=False);h=WORK/'Harness.cs';h.write_text('''using System;using System.Text;using CrimsonSkiesKoreanPatch;class CacheFixtureMain {static int Main(string[] a){Console.OutputEncoding=new UTF8Encoding(false);try{var e=new PatchEngine(a[0],Console.WriteLine);if(a[3]=="probe"){PatchEngine.VoiceCacheFixturePath=null;e.InspectVoiceCacheOnly(a[1]);}else{PatchEngine.VoiceCacheFixturePath=a[2];PatchEngine.VoiceCacheFixtureBackupBase=System.IO.Path.Combine(System.IO.Path.GetDirectoryName(a[2]),"backups");if(a[3]=="rollback")e.FixtureVoiceCacheRollback(a[1]);else e.RefreshVoiceCache(a[3]=="apply",a[1]);}return 0;}catch(Exception x){Console.WriteLine(x.Message);return 1;}}}''',encoding='utf-8')
 exe=WORK/'CacheFixture.exe';csc=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe';args=[str(csc),'/nologo','/codepage:65001','/target:exe','/optimize+','/define:AUDIO_TRANSACTION_FIXTURE','/main:CacheFixtureMain','/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Web.Extensions.dll','/r:System.Xml.dll','/r:System.Core.dll','/out:'+str(exe),*[str(SRC/n)for n in ['InstallerEngine.cs','NoSettings.cs','VoiceCache.cs','InstallerUi.cs','ReleasePins.cs']],str(h)]
 r=subprocess.run(args,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=90);assert r.returncode==0,r.stdout.decode('cp949','replace')
 logs=[]
 def run(mode,content,raw,ok=True):
  r=subprocess.run([str(exe),str(BUNDLE),str(content),str(raw),mode],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=90);s=(r.stdout+r.stderr).decode('utf-8-sig','replace');print(mode,r.returncode,s[-220:].strip(),flush=True);assert(r.returncode==0)==ok,s;logs.append(dict(mode=mode,exit=r.returncode,tail=s[-220:]));return s
 original,dub=archive(BASE),archive(TARGET);assert len(original)==len(dub)==2301230
 raw=WORK/'RawPartition';before,pos=create(original,raw)
 run('apply',TARGET,raw);after=raw.read_bytes();assert after[pos:pos+len(dub)]==dub and before[:pos]==after[:pos]and before[pos+len(dub):]==after[pos+len(dub):]
 run('restore',BASE,raw);assert raw.read_bytes()==before
 run('rollback',TARGET,raw);assert raw.read_bytes()==before
 run('apply',BASE,raw,False);assert raw.read_bytes()==before
 corrupt=bytearray(before);corrupt[pos+20]^=1;raw.write_bytes(corrupt);run('apply',TARGET,raw,False);assert raw.read_bytes()==corrupt
 corrupt=bytearray(before);struct.pack_into('>H',corrupt,4096+5*2,5);raw.write_bytes(corrupt);run('apply',TARGET,raw,False);assert raw.read_bytes()==corrupt
 corrupt=bytearray(before);corrupt[0]^=1;raw.write_bytes(corrupt);run('apply',TARGET,raw,False);assert raw.read_bytes()==corrupt
 raw.write_bytes(before);run('apply',TARGET,raw);once=raw.read_bytes();run('apply',TARGET,raw);assert raw.read_bytes()==once
 # Restoring audio after unrelated checkpoint/cache edits preserves those edits.
 checkpoint=0x12000+(4+(len(original)+65535)//65536)*65536+123;changed=bytearray(once);changed[checkpoint]^=1;raw.write_bytes(changed);run('restore',BASE,raw);restored=raw.read_bytes();expected=bytearray(before);expected[checkpoint]^=1;assert restored==expected
 out=dict(schema=1,status='PASS_TARGETED_VOICE_CACHE_ATOMIC_ROUNDTRIPS',checks=logs,actualRegisteredTreeProbed=False,installedCacheWrites=0,syntheticCacheOnly=True,allUnownedBytesAndCheckpointPreserved=True,unknownZipCycleAndFormatRefused=True,atomicRollbackExact=True,concurrentUnrelatedCacheChangesPreserved=True)
 (WORK/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(out['status'])
if __name__=='__main__':main()
