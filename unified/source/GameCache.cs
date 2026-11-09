// SPDX-License-Identifier: MIT
// Refresh known cached game assets, preserving checkpoints and all other bytes.
using System;using System.Collections.Generic;using System.IO;using System.Linq;using System.Security.Cryptography;using System.Text;
namespace CrimsonSkiesUnified {
 public sealed class CacheFile {public string name;public Node[] nodes;public Dictionary<string,string> hashes;}
 public sealed partial class PatchEngine {
#if UNIFIED_TEST
  internal static string GameCacheFixturePath,GameCacheFixturePayload;
  internal void FixtureGameCache(string content,string target,bool rollback){var cache=new GameCacheTransaction(this,content,target);cache.Preflight();cache.Commit();if(rollback)cache.Rollback();}
#endif
  void RefreshGameCache(string target,string content){var cache=new GameCacheTransaction(this,content,target);cache.Preflight();try{cache.Commit();}catch{cache.Rollback();throw;}}
  sealed class GameCacheTransaction {
   const int Cluster=65536,FatOffset=4096,DataOffset=0x12000,MaxAsset=268435456;
   readonly PatchEngine owner;readonly string content,raw,targetId;
   string beforeHash,afterHash,backup;bool committed;
   sealed class Part {public long offset;public int bytes;}
   sealed class Cached {public CacheFile definition;public string hash;public int size;public long record;public List<int> clusters;}
   sealed class Entry {public string name;public byte flags;public int cluster,size;public long record;}
   public GameCacheTransaction(PatchEngine owner,string content,string target){this.owner=owner;this.content=content;targetId=target;
    if(owner.manifest.cacheFiles==null||owner.manifest.cacheFiles.Length==0)return;
#if UNIFIED_TEST
    if(GameCacheFixturePath!=null){raw=GameCacheFixturePath;return;}
#endif
    if(!VoiceCacheTransaction.RegisteredTree(content)){owner.log("Copied/unregistered game tree: title asset cache left untouched.");return;}
    raw=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),@"Packages\Xbox360BackwardCompatibil.PrimaryCrimsonSkiesHighR_ksqcvrsvwz2jp\LocalCache\Local\VirtualDrive\Harddisk\Cache1\RawPartition");
   }
   static void Check(bool ok,string message){if(!ok)throw new InvalidDataException("Asset cache: "+message);}
   static int Be16(byte[] bytes,int at){return bytes[at]*256+bytes[at+1];}
   static int Be32(byte[] bytes,int at){long value=((long)bytes[at]<<24)|((long)bytes[at+1]<<16)|((long)bytes[at+2]<<8)|bytes[at+3];Check(value<=Int32.MaxValue,"oversized field");return(int)value;}
   static byte[] Read(FileStream stream,long offset,int count){Check(offset>=0&&count>=0&&offset+count<=stream.Length,"read escaped file");byte[] bytes=new byte[count];stream.Position=offset;int used=0;while(used<count){int got=stream.Read(bytes,used,count-used);Check(got>0,"short read");used+=got;}return bytes;}
   static string Hash(byte[] bytes){using(var digest=SHA256.Create())return Hex(digest.ComputeHash(bytes));}
   static string HashOpen(FileStream stream){stream.Position=0;using(var digest=SHA256.Create())return Hex(digest.ComputeHash(stream));}
   static byte[] Gather(FileStream stream,List<int> clusters,int count){using(var buffer=new MemoryStream()){foreach(int cluster in clusters){int take=Math.Min(Cluster,count-(int)buffer.Length);if(take==0)break;byte[] bytes=Read(stream,DataOffset+(long)(cluster-1)*Cluster,take);buffer.Write(bytes,0,bytes.Length);}Check(buffer.Length==count,"short cached asset");return buffer.ToArray();}}
   List<Cached> Inspect(FileStream stream){
    var result=new List<Cached>();if(stream.Length==0)return result;
    Check(stream.Length>=DataOffset+Cluster&&stream.Length<=4294967296L,"unsupported partition size");
    byte[] head=Read(stream,0,16),fat=Read(stream,FatOffset,DataOffset-FatOffset);
    Check(head[0]==88&&head[1]==84&&head[2]==65&&head[3]==70&&Be32(head,8)==128&&Be32(head,12)==1,"unsupported XTAF layout");
    Check(Be16(fat,0)==0xfff8&&Be16(fat,2)>=0xfff8,"unsupported FAT header");
    var allocated=new HashSet<int>();
    Func<int,List<int>> chain=delegate(int first){var list=new List<int>();var seen=new HashSet<int>();int current=first;while(true){Check(current>0&&current<fat.Length/2&&seen.Add(current),"invalid cluster chain");list.Add(current);int next=Be16(fat,current*2);if(next>=0xfff8)break;Check(next>0&&next<0xfff0,"free/reserved cluster");current=next;}return list;};
    Action<List<int>> claim=delegate(List<int> clusters){foreach(int cluster in clusters)Check(allocated.Add(cluster),"cross-linked allocation");};
    Func<int,List<Entry>> directory=delegate(int first){var clusters=chain(first);Check(clusters.Count<=8,"oversized directory");claim(clusters);var entries=new List<Entry>();foreach(int cluster in clusters){long at=DataOffset+(long)(cluster-1)*Cluster;byte[] bytes=Read(stream,at,Cluster);for(int i=0;i<Cluster;i+=64){int length=bytes[i];if(length==0||length==255)return entries;if(length==229)continue;Check(length<=42,"invalid name length");string name=Encoding.ASCII.GetString(bytes,i+2,length);Check(name.All(c=>c>=32&&c<=126)&&name.IndexOfAny(new[]{'\\','/',':'})<0,"invalid name");entries.Add(new Entry{name=name,flags=bytes[i+1],cluster=Be32(bytes,i+44),size=Be32(bytes,i+48),record=at+i});}}return entries;};
    var roots=directory(1);Check(roots.Count<=3,"unexpected root entries");
    foreach(var root in roots){Check((root.flags&16)!=0&&new[]{"Xbox0","Xbox1","Xbox2"}.Contains(root.name,StringComparer.OrdinalIgnoreCase),"unexpected cache root");foreach(var entry in directory(root.cluster)){
     Check((entry.flags&16)==0,"nested directory unsupported");if(entry.cluster==0){Check(entry.size==0,"missing file cluster");continue;}
     var clusters=chain(entry.cluster);claim(clusters);Check(entry.size<=(long)clusters.Count*Cluster,"asset exceeds allocation");
     var definition=owner.manifest.cacheFiles.SingleOrDefault(file=>String.Equals(file.name,entry.name,StringComparison.OrdinalIgnoreCase));if(definition==null)continue;
     Check(entry.size<=MaxAsset,"oversized cached asset");string hash=Hash(Gather(stream,clusters,entry.size));
     Check(definition.nodes.Any(node=>node.sha256==hash&&node.bytes==entry.size),"unknown bytes in "+entry.name+"; no game/cache files were overwritten");
     result.Add(new Cached{definition=definition,hash=hash,size=entry.size,record=entry.record,clusters=clusters});
    }}return result;
   }
   static byte[] GameRead(string content,long logical,int count){Check(logical>=0&&count>=0&&count<=MaxAsset,"invalid source range");byte[] result=new byte[count];int at=0;while(at<count){long offset=logical+at,page=offset/4096;int within=(int)(offset%4096),volume=(int)(page/41412),local=(int)(page%41412),group=local/204,slot=local%204;Check(volume>=0&&volume<26,"source volume escaped package");int take=Math.Min(count-at,(204-slot)*4096-within);string path=Child(content,"Game/DefaultPackage.data/Data"+volume.ToString("D4"));NoReparse(path,false);using(var stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read)){byte[] bytes=Read(stream,(2L+group*205+slot)*4096+within,take);Buffer.BlockCopy(bytes,0,result,at,take);}at+=take;}return result;}
   byte[] Desired(CacheFile definition){
#if UNIFIED_TEST
    if(GameCacheFixturePayload!=null)return File.ReadAllBytes(GameCacheFixturePayload);
#endif
    byte[] volume=GameRead(content,0,2048);Check(Encoding.ASCII.GetString(volume,0,20)=="MICROSOFT*XBOX*MEDIA","unknown game volume");
    long root=((long)BitConverter.ToUInt32(volume,20)-32)*2048;uint size=BitConverter.ToUInt32(volume,24);Check(size>0&&size<=1048576,"invalid root table");byte[] table=GameRead(content,root,(int)size);
    var pending=new Stack<int>();var visited=new HashSet<int>();pending.Push(0);byte[] found=null;
    while(pending.Count>0){int at=pending.Pop();Check(at>=0&&at+14<=table.Length&&visited.Add(at),"invalid root tree");int left=BitConverter.ToUInt16(table,at),right=BitConverter.ToUInt16(table,at+2),length=table[at+13];Check(length>0&&at+14+length<=table.Length,"invalid root name");if(left!=0)pending.Push(left*4);if(right!=0)pending.Push(right*4);
     string name=Encoding.ASCII.GetString(table,at+14,length);if((table[at+12]&16)==0&&String.Equals(name,definition.name,StringComparison.OrdinalIgnoreCase)){Check(found==null,"duplicate root asset");uint bytes=BitConverter.ToUInt32(table,at+8);Check(bytes>0&&bytes<=MaxAsset,"oversized game asset");found=GameRead(content,((long)BitConverter.ToUInt32(table,at+4)-32)*2048,(int)bytes);}}
    Check(found!=null,"root asset missing: "+definition.name);return found;
   }
   public void Preflight(bool readOnly=false){if(raw==null||!File.Exists(raw))return;if(readOnly&&(ProcessPresent("Emu")||ProcessPresent("EmuMenu"))){owner.log("Close game to include asset-cache preflight; no cache was written.");return;}NoReparse(raw,false);using(var stream=new FileStream(raw,FileMode.Open,FileAccess.Read,FileShare.Read))Inspect(stream);}
   public void Commit(){
    if(raw==null||!File.Exists(raw))return;RequireStopped();NoReparse(raw,false);
    string temp=Path.Combine(Path.GetDirectoryName(raw),".csassets-"+Guid.NewGuid().ToString("N")+".tmp");var parts=new List<Part>();int changed=0;
    try{
     using(var source=new FileStream(raw,FileMode.Open,FileAccess.Read,FileShare.Read)){
      var entries=Inspect(source);beforeHash=HashOpen(source);source.Position=0;
      using(var stage=new FileStream(temp,FileMode.CreateNew,FileAccess.ReadWrite,FileShare.None)){
       source.CopyTo(stage,1048576);
       foreach(var entry in entries){string desired;Check(entry.definition.hashes.TryGetValue(targetId,out desired),"missing target fingerprint");
        if(entry.hash==desired)continue;
        byte[] payload=Desired(entry.definition);Check(Hash(payload)==desired&&entry.definition.nodes.Any(node=>node.sha256==desired&&node.bytes==payload.Length),"desired asset differs from selected profile: "+entry.definition.name);
        Check(payload.Length<=(long)entry.clusters.Count*Cluster,"existing asset cache allocation too small");int at=0;
        foreach(int cluster in entry.clusters){int take=Math.Min(Cluster,payload.Length-at);if(take==0)break;long offset=DataOffset+(long)(cluster-1)*Cluster;stage.Position=offset;stage.Write(payload,at,take);parts.Add(new Part{offset=offset,bytes=take});at+=take;}
        Check(at==payload.Length,"short cache write");if(entry.size!=payload.Length){byte[] bytes=BitConverter.GetBytes(payload.Length);if(BitConverter.IsLittleEndian)Array.Reverse(bytes);stage.Position=entry.record+48;stage.Write(bytes,0,4);parts.Add(new Part{offset=entry.record+48,bytes=4});}
        changed++;owner.log("준비한 자산 캐시 / Staged cached asset: "+entry.definition.name);
       }
       if(changed==0){owner.log("Game asset cache already matches selected profile.");return;}
       stage.Flush(true);Check(Inspect(stage).All(entry=>entry.hash==entry.definition.hashes[targetId]),"staged asset cache verification failed");afterHash=HashOpen(stage);
       var owned=parts.OrderBy(part=>part.offset).ToArray();long cursor=0;byte[] a=new byte[1048576],b=new byte[1048576];source.Position=0;stage.Position=0;int count;
       while((count=source.Read(a,0,a.Length))>0){int used=0;while(used<count){int got=stage.Read(b,used,count-used);Check(got>0,"short staged partition");used+=got;}int start=0;foreach(var part in owned){long lo=Math.Max(cursor,part.offset),hi=Math.Min(cursor+count,part.offset+part.bytes);if(lo>=hi)continue;int left=(int)(lo-cursor),right=(int)(hi-cursor);for(int i=start;i<left;i++)Check(a[i]==b[i],"unowned cache bytes changed");start=right;}for(int i=start;i<count;i++)Check(a[i]==b[i],"unowned cache tail changed");cursor+=count;}
      }Check(HashOpen(source)==beforeHash,"cache changed while staging");
     }
     string folder=Child(owner.ReleaseBackupDirectory(content),"asset-cache-"+Guid.NewGuid().ToString("N"));CreateSafeDirectory(folder);backup=Child(folder,"before.raw");RequireStopped();Check(HashFile(raw)==beforeHash,"cache changed before replacement");File.Replace(temp,raw,backup);committed=true;Check(HashFile(raw)==afterHash&&HashFile(backup)==beforeHash,"atomic cache readback failed");
     File.WriteAllText(Child(folder,"cache-backup.json"),owner.serializer.Serialize(new{schema=1,manifestSha256=ManifestDigest,root=content,target=targetId,beforeSha256=beforeHash,afterSha256=afterHash,changedAssets=changed,checkpointsAndUnownedBytesExact=true}),Utf8);
     owner.log("게임 자산 캐시 갱신 완료; 체크포인트와 나머지 바이트 보존 / Asset cache refreshed; checkpoints and all other bytes preserved.");
    }finally{if(File.Exists(temp)){NoReparse(temp,false);File.Delete(temp);}}
   }
   public void Rollback(){if(!committed)return;RequireStopped();string current=HashFile(raw);if(current==beforeHash)return;Check(current==afterHash&&HashFile(backup)==beforeHash,"rollback refused concurrent cache changes");string temp=Path.Combine(Path.GetDirectoryName(raw),".csassets-rollback-"+Guid.NewGuid().ToString("N")+".tmp");try{File.Copy(backup,temp,false);Check(HashFile(temp)==beforeHash,"rollback snapshot mismatch");RequireStopped();Check(HashFile(raw)==afterHash,"cache changed before rollback");File.Replace(temp,raw,null);Check(HashFile(raw)==beforeHash,"cache rollback failed");}finally{if(File.Exists(temp))File.Delete(temp);}}
  }
 }
}
