// SPDX-License-Identifier: MIT
// Refresh only the two dubbed cinematic WAVs' existing English ZIP cache.
// Build2608's title-local XTAF cache uses 64KiB clusters and a BE16 FAT.
// Cache replacement is atomic at the host-file level; every unowned byte is
// preserved, including checkpoints, marker/index files and all FAT metadata.
using System;using System.Collections.Generic;using System.IO;using System.Linq;using System.Security.Cryptography;using System.Text;using System.Runtime.InteropServices;using Microsoft.Win32;
namespace CrimsonSkiesKoreanPatch {
 public sealed partial class PatchEngine {
#if AUDIO_TRANSACTION_FIXTURE
  internal static string VoiceCacheFixturePath;
  internal static string VoiceCacheFixtureBackupBase;
  internal void FixtureVoiceCacheRollback(string content){var c=new VoiceCacheTransaction(this,content);c.Preflight();c.Commit(true);c.Rollback();}
#endif
  internal void RefreshVoiceCache(bool apply,string content){var c=new VoiceCacheTransaction(this,content);c.Preflight();try{c.Commit(apply);}catch{c.Rollback();throw;}}
  internal void InspectVoiceCacheOnly(string content){new VoiceCacheTransaction(this,content).Preflight();}
  sealed class VoiceCacheTransaction {
   const int Cluster=65536,FatOffset=4096,DataOffset=0x12000,ArchiveBytes=2301230;
   const long ArchiveLogical=822077440,MaxRaw=4294967296;
   const string Name="cinematics_dialog_sound.zip",Original="529874729e341e61d688fa1bca6acc609c6760324e18c84ceed8df7ff9925ee3",Dub="97bcf1f5092e6988c8f582cadc75b00dff6b73a510e601244dddc1c581604620";
   readonly PatchEngine owner;readonly string content,raw;
   string beforeHash,afterHash,backup;bool committed;
   sealed class Part {public long offset;public int bytes;}
   sealed class Entry {public string name;public byte flags;public int cluster,size;public long record;}
   sealed class Cached {public List<Part> parts;public string hash;public long record;}
   public VoiceCacheTransaction(PatchEngine owner,string content){this.owner=owner;this.content=content;raw=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),@"Packages\Xbox360BackwardCompatibil.PrimaryCrimsonSkiesHighR_ksqcvrsvwz2jp\LocalCache\Local\VirtualDrive\Harddisk\Cache1\RawPartition");
#if AUDIO_TRANSACTION_FIXTURE
    if(VoiceCacheFixturePath!=null){raw=Path.GetFullPath(VoiceCacheFixturePath);return;}
#endif
    if(!RegisteredTree(content)){raw=null;owner.log("Copied/unregistered game tree: shared title cache is left untouched.");}
   }
   [StructLayout(LayoutKind.Sequential)]struct Identity {public uint attrs,c0,c1,a0,a1,w0,w1,volume,sizeHigh,sizeLow,links,indexHigh,indexLow;}
   [DllImport("kernel32.dll",SetLastError=true)]static extern bool GetFileInformationByHandle(IntPtr h,out Identity info);
   [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern IntPtr CreateFile(string p,uint access,uint share,IntPtr security,uint disposition,uint flags,IntPtr template);
   [DllImport("kernel32.dll")]static extern bool CloseHandle(IntPtr h);
   static bool SameFile(string a,string b){if(!File.Exists(a)||!File.Exists(b))return false;IntPtr x=CreateFile(a,0,7,IntPtr.Zero,3,0,IntPtr.Zero),y=CreateFile(b,0,7,IntPtr.Zero,3,0,IntPtr.Zero);try{Need(x!=new IntPtr(-1)&&y!=new IntPtr(-1),"cannot open registered file metadata");Identity i=new Identity(),j=new Identity();Need(GetFileInformationByHandle(x,out i)&&GetFileInformationByHandle(y,out j),"cannot establish registered title identity");return i.volume==j.volume&&i.indexHigh==j.indexHigh&&i.indexLow==j.indexLow;}finally{if(x!=new IntPtr(-1))CloseHandle(x);if(y!=new IntPtr(-1))CloseHandle(y);}}

   internal static bool RegisteredTree(string content){const string path=@"Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\Repository\Packages\Xbox360BackwardCompatibil.PrimaryCrimsonSkiesHighR_2608.3123.1.0_x64__ksqcvrsvwz2jp";using(var key=Registry.CurrentUser.OpenSubKey(path)){if(key==null)return false;string root=key.GetValue("PackageRootFolder")as string;return root!=null&&SameFile(Path.Combine(content,"Emu.exe"),Path.Combine(root,"Emu.exe"))&&SameFile(Path.Combine(content,"appxmanifest.xml"),Path.Combine(root,"appxmanifest.xml"));}}
   static void Need(bool ok,string why){if(!ok)throw new InvalidDataException("Voice cache: "+why);}
   static int Be16(byte[] b,int i){return b[i]*256+b[i+1];}
   static int Be32(byte[] b,int i){long n=((long)b[i]<<24)|((long)b[i+1]<<16)|((long)b[i+2]<<8)|b[i+3];Need(n<=Int32.MaxValue,"oversized cache field");return(int)n;}
   static byte[] Read(FileStream f,long offset,int count){Need(offset>=0&&count>=0&&offset+count<=f.Length,"bounded read escaped partition");byte[] b=new byte[count];f.Position=offset;int at=0;while(at<count){int n=f.Read(b,at,count-at);Need(n>0,"short read");at+=n;}return b;}
   static string HashOpen(FileStream f){f.Position=0;using(var h=SHA256.Create())return Hex(h.ComputeHash(f));}
   static byte[] Gather(FileStream f,List<Part> parts){using(var s=new MemoryStream()){foreach(var p in parts){byte[] b=Read(f,p.offset,p.bytes);s.Write(b,0,b.Length);}return s.ToArray();}}
   List<Cached> Inspect(FileStream f){
    var found=new List<Cached>();if(f.Length==0)return found;Need(f.Length>=DataOffset+Cluster&&f.Length<=MaxRaw,"unsupported nonempty partition size");
    byte[] head=Read(f,0,16);Need(head[0]==0x58&&head[1]==0x54&&head[2]==0x41&&head[3]==0x46&&Be32(head,8)==128&&Be32(head,12)==1,"unsupported XTAF layout");byte[] fat=Read(f,FatOffset,DataOffset-FatOffset);Need(Be16(fat,0)==0xfff8&&Be16(fat,2)>=0xfff8,"unsupported FAT16 header");
    var allocated=new Dictionary<int,string>();
    Func<int,List<int>> chain=delegate(int first){var result=new List<int>();var seen=new HashSet<int>();int c=first;while(true){Need(c>0&&c<fat.Length/2&&seen.Add(c),"invalid/cyclic cluster chain");result.Add(c);Need(result.Count<=fat.Length/2,"unbounded cluster chain");int next=Be16(fat,c*2);if(next>=0xfff8)break;Need(next!=0&&next<0xfff0,"free/reserved cluster in chain");c=next;}return result;};
    Action<List<int>,string> claim=delegate(List<int> cs,string who){foreach(int c in cs){Need(!allocated.ContainsKey(c),"cross-linked cache allocation");allocated[c]=who;}};
    Func<int,string,List<Entry>> directory=delegate(int first,string who){var cs=chain(first);Need(cs.Count<=8,"directory exceeds bound");claim(cs,who);var entries=new List<Entry>();foreach(int c in cs){long at=DataOffset+(long)(c-1)*Cluster;byte[] data=Read(f,at,Cluster);for(int i=0;i<Cluster;i+=64){int n=data[i];if(n==0||n==255)return entries;if(n==229)continue;Need(n<=42,"invalid directory name length");string name=Encoding.ASCII.GetString(data,i+2,n);Need(name.All(ch=>ch>=32&&ch<=126)&&name.IndexOfAny(new[]{'\\','/',':'})<0,"invalid cache name");entries.Add(new Entry{name=name,flags=data[i+1],cluster=Be32(data,i+44),size=Be32(data,i+48),record=at+i});}}return entries;};
    var roots=directory(1,"root");Need(roots.Count<=3,"unexpected root entries");
    foreach(var slot in roots){Need((slot.flags&16)!=0&&new[]{"Xbox0","Xbox1","Xbox2"}.Contains(slot.name,StringComparer.OrdinalIgnoreCase),"unexpected cache root");foreach(var e in directory(slot.cluster,slot.name)){
      Need((e.flags&16)==0,"nested cache directory unsupported");if(e.cluster==0){Need(e.size==0,"nonempty cache file has no cluster");continue;}var cs=chain(e.cluster);claim(cs,slot.name+"/"+e.name);Need(e.size<=(long)cs.Count*Cluster,"cache file exceeds allocation");if(!String.Equals(e.name,Name,StringComparison.OrdinalIgnoreCase))continue;
      Need(e.size==ArchiveBytes&&cs.Count==(ArchiveBytes+Cluster-1)/Cluster,"unsupported cinematic cache extent");var parts=new List<Part>();int left=e.size;foreach(int c in cs){int n=Math.Min(Cluster,left);parts.Add(new Part{offset=DataOffset+(long)(c-1)*Cluster,bytes=n});left-=n;}string h=Hash(Gather(f,parts));Need(h==Original||h==Dub,"unknown cinematic ZIP cache; no game/cache files were overwritten");found.Add(new Cached{parts=parts,hash=h,record=e.record});Need(found.Count<=3,"too many cinematic caches");
    }}return found;
   }
   public void Preflight(bool readOnly=false){if(readOnly&&(ProcessPresent("Emu")||ProcessPresent("EmuMenu"))){owner.log("Close the game to include the voice-cache preflight; no cache was written.");return;}if(!File.Exists(raw))return;NoReparse(raw,false);using(var f=new FileStream(raw,FileMode.Open,FileAccess.Read,FileShare.Read)){Inspect(f);}}
   byte[] Desired(bool apply){var output=new byte[ArchiveBytes];int at=0;while(at<output.Length){long logical=ArchiveLogical+at,page=logical/4096;int within=(int)(logical%4096),volume=(int)(page/41412),local=(int)(page%41412),group=local/204,slot=local%204;long physical=(2L+group*205+slot)*4096+within;int take=Math.Min(output.Length-at,(204-slot)*4096-within);string file=Child(content,"Game/DefaultPackage.data/Data"+volume.ToString("D4"));NoReparse(file,false);using(var f=new FileStream(file,FileMode.Open,FileAccess.Read,FileShare.Read)){byte[] b=Read(f,physical,take);Buffer.BlockCopy(b,0,output,at,take);}at+=take;}Need(Hash(output)==(apply?Dub:Original),"desired source archive differs from finalized audio");return output;}
   public void Commit(bool apply){
    if(!File.Exists(raw))return;RequireStopped();NoReparse(raw,false);string temp=Path.Combine(Path.GetDirectoryName(raw),".csdub-"+Guid.NewGuid().ToString("N")+".tmp");string desired=apply?Dub:Original;var parts=new List<Part>();
    try{
     using(var source=new FileStream(raw,FileMode.Open,FileAccess.Read,FileShare.Read)){
      var entries=Inspect(source);if(entries.Count==0||entries.All(e=>e.hash==desired)){owner.log("Cinematic voice cache: no stale owned ZIP to refresh.");return;}byte[] zip=Desired(apply);beforeHash=HashOpen(source);source.Position=0;
      using(var stage=new FileStream(temp,FileMode.CreateNew,FileAccess.ReadWrite,FileShare.None)){source.CopyTo(stage,1048576);foreach(var e in entries){int at=0;foreach(var p in e.parts){stage.Position=p.offset;stage.Write(zip,at,p.bytes);at+=p.bytes;parts.Add(p);}}stage.Flush(true);afterHash=HashOpen(stage);Need(Inspect(stage).All(e=>e.hash==desired),"staged cache ZIP verification failed");
       // Compare every unowned byte against the still-locked source, including
       // the allocation table, directory records, checkpoints and cache marker.
       var owned=parts.OrderBy(p=>p.offset).ToArray();long cursor=0;byte[] a=new byte[1048576],b=new byte[1048576];source.Position=0;stage.Position=0;int n;while((n=source.Read(a,0,a.Length))>0){int used=0;while(used<n){int got=stage.Read(b,used,n-used);Need(got>0,"short staged cache");used+=got;}int start=0;foreach(var p in owned){long lo=Math.Max(cursor,p.offset),hi=Math.Min(cursor+n,p.offset+p.bytes);if(lo>=hi)continue;int l=(int)(lo-cursor),r=(int)(hi-cursor);for(int k=start;k<l;k++)Need(a[k]==b[k],"unowned cache byte changed");start=r;}for(int k=start;k<n;k++)Need(a[k]==b[k],"unowned cache tail changed");cursor+=n;}
      }Need(HashOpen(source)==beforeHash,"cache changed while staging");
     }
     string backupRoot=owner.ReleaseBackupDirectory(content);
#if AUDIO_TRANSACTION_FIXTURE
     if(VoiceCacheFixtureBackupBase!=null)backupRoot=Path.GetFullPath(VoiceCacheFixtureBackupBase);
#endif
     string folder=Child(backupRoot,"voice-cache-"+Guid.NewGuid().ToString("N"));CreateSafeDirectory(folder);backup=Child(folder,"before.raw");RequireStopped();NoReparse(raw,false);Need(HashFile(raw)==beforeHash,"cache changed before atomic replacement");File.Replace(temp,raw,backup);committed=true;Need(HashFile(raw)==afterHash&&HashFile(backup)==beforeHash,"atomic cache readback failed");
     var meta=new{schema=1,manifestSha256=ManifestDigest,root=content,cachePath=raw,beforeSha256=beforeHash,afterSha256=afterHash,cinematicsZipSha256=desired,ownedZipCount=parts.Count/((ArchiveBytes+Cluster-1)/Cluster),allOtherCacheBytesExact=true};File.WriteAllText(Child(folder,"cache-backup.json"),owner.serializer.Serialize(meta),Utf8);owner.log("Refreshed only existing English cinematic ZIP cache; all other cache bytes preserved. Backup: "+folder);
    }finally{if(File.Exists(temp)){NoReparse(temp,false);File.Delete(temp);}}
   }
   public void Rollback(){if(!committed)return;RequireStopped();NoReparse(raw,false);string current=HashFile(raw);if(current==beforeHash)return;Need(current==afterHash&&HashFile(backup)==beforeHash,"cache rollback refused unknown concurrent bytes");string temp=Path.Combine(Path.GetDirectoryName(raw),".csdub-rollback-"+Guid.NewGuid().ToString("N")+".tmp");try{File.Copy(backup,temp,false);Need(HashFile(temp)==beforeHash,"cache rollback snapshot differs");RequireStopped();Need(HashFile(raw)==afterHash,"cache changed before rollback");File.Replace(temp,raw,null);Need(HashFile(raw)==beforeHash,"cache rollback verification failed");}finally{if(File.Exists(temp)){NoReparse(temp,false);File.Delete(temp);}}}
  }
 }
}
