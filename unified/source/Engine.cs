// SPDX-License-Identifier: MIT
// One coherent transaction for every selected component. Original files are
// retained per installation; no profile/save files are opened by this engine.
using System;using System.Collections.Generic;using System.Diagnostics;using System.IO;using System.Linq;using System.Security.Cryptography;using System.Text;using System.Text.RegularExpressions;using System.Threading;using System.Threading.Tasks;using System.Web.Script.Serialization;using System.Xml;
namespace CrimsonSkiesUnified {
 public sealed class Tool {public string path,sha256;}
 public sealed class Node {public string sha256;public long bytes;}
 public sealed class Edge {public string source,target,path,sha256;public long bytes;}
 public sealed class FileDef {public string path;public Node[] nodes;public Edge[] edges;}
 public sealed class Profile {public string id,captions;public bool korean,wide,dub;public string[] hashes;}
 public sealed class Input {public string id;public string[] hashes;}
 public sealed class Guard {public string path,sha256;public long bytes;}
 public sealed class Identity {public string name,version,architecture,publisher;}
 public sealed class Manifest {public int schema;public string releaseId;public Identity supportedPackage;public Tool tool;public FileDef[] files;public Profile[] profiles;public Input[] inputs,knownExternal;public Guard[] guards;public CacheFile[] cacheFiles;}
 public sealed class Pending {public string stage,from,to,settingsBefore,settingsAfter;public int[] changed;}
 public sealed class Receipt {public int schema;public string releaseId,root,manifestSha256,original,current;public SettingOrigin settings;public Pending pending;}
 public sealed partial class PatchEngine {
  public const string ReleaseId=Pins.ReleaseId;
  public const string ManifestDigest=Pins.Manifest;
  public const string NativeName="xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll";
  static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
  readonly JavaScriptSerializer serializer=new JavaScriptSerializer{MaxJsonLength=4194304};
  readonly string package;readonly Action<string> log;readonly Manifest manifest;
#if UNIFIED_TEST
  internal static string BackupOverride,SettingsOverride;internal static Action<string> Fault;
#endif
  public PatchEngine(string directory,Action<string> logger){package=Path.GetFullPath(directory);NoReparse(package,true);log=logger??delegate{};string p=Child(package,"manifest.json");NoReparse(p,false);Need(new FileInfo(p).Length<=4194304&&HashFile(p)==ManifestDigest,"설치 파일 목록 검증 실패 / Invalid manifest");manifest=serializer.Deserialize<Manifest>(File.ReadAllText(p,Utf8));Validate();}
  void Validate(){
   Need(manifest!=null&&manifest.schema==1&&manifest.releaseId==ReleaseId&&manifest.files!=null&&manifest.files.Length==29&&manifest.profiles!=null&&manifest.profiles.Length<=64&&manifest.profiles.Length>=4,"Unsupported package");
   Need(manifest.cacheFiles!=null&&manifest.cacheFiles.Length>0&&manifest.cacheFiles.Length<=128,"Missing asset cache fingerprints");
   var cacheNames=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
   var cacheStates=new HashSet<string>(manifest.inputs.Select(v=>v.id).Concat(manifest.profiles.Select(v=>v.id)).Concat(manifest.knownExternal.Select(v=>v.id)));
   foreach(var cache in manifest.cacheFiles){Need(cache!=null&&Regex.IsMatch(cache.name??"","^[A-Za-z0-9_ .-]{1,42}$")&&cacheNames.Add(cache.name)&&cache.nodes!=null&&cache.nodes.Length>0&&cache.nodes.Length<=16&&cache.nodes.All(n=>n!=null&&IsHash(n.sha256)&&n.bytes>0&&n.bytes<=268435456)&&cache.hashes!=null&&cache.hashes.Count==cacheStates.Count&&cache.hashes.All(kv=>cacheStates.Contains(kv.Key)&&cache.nodes.Any(n=>n.sha256==kv.Value)),"Invalid asset cache metadata");}
   Need(manifest.tool!=null&&manifest.tool.path=="tools/xdelta3.exe"&&IsHash(manifest.tool.sha256),"Invalid tool");var paths=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
   for(int i=0;i<29;i++){var f=manifest.files[i];string expected=i==0?NativeName:i==1?"VGPUDX12.dll":i==2?"EmuMenu/Assets/TitleMenuData.json":"Game/DefaultPackage.data/Data"+(i-3).ToString("D4");Need(f!=null&&f.path==expected&&paths.Add(f.path)&&f.nodes!=null&&f.nodes.Length>0&&f.nodes.Length<=32&&f.edges!=null&&f.edges.Length<=128,"Invalid file nodes");Need(f.nodes.All(n=>n!=null&&IsHash(n.sha256)&&n.bytes>0&&n.bytes<=8589934592L)&&f.nodes.Select(n=>n.sha256).Distinct().Count()==f.nodes.Length,"Invalid node identity");foreach(var e in f.edges)Need(e!=null&&f.nodes.Any(n=>n.sha256==e.source)&&f.nodes.Any(n=>n.sha256==e.target)&&e.source!=e.target&&Regex.IsMatch(e.path??"","^patches/[0-9]{3}[.]vcdiff$")&&IsHash(e.sha256)&&e.bytes>0&&e.bytes<8589934592L,"Invalid delta edge");}
   Need(manifest.inputs!=null&&manifest.inputs.Length==2&&manifest.inputs[0].id=="stock"&&manifest.inputs[1].id=="foundation"&&manifest.knownExternal!=null,"Invalid baselines");var ids=new HashSet<string>();foreach(var v in manifest.inputs.Concat(manifest.knownExternal)){Need(v!=null&&ids.Add(v.id),"Duplicate input");Vector(v.hashes);}
   foreach(var p in manifest.profiles){Need(p!=null&&Regex.IsMatch(p.id??"","^k[01]-w[01]-d[01]-(off|original|dub)$")&&ids.Add(p.id),"Invalid profile");Need(p.id=="k"+(p.korean?1:0)+"-w"+(p.wide?1:0)+"-d"+(p.dub?1:0)+"-"+p.captions,"Profile option mismatch");Need((p.korean||!p.dub&&p.captions=="off")&&(p.captions!="dub"||p.dub),"Invalid dependencies");Vector(p.hashes);}
   Need(manifest.guards!=null&&manifest.guards.Length>=3&&manifest.guards.Length<=16,"Missing guards");foreach(var g in manifest.guards)Need(g!=null&&!paths.Contains(g.path)&&IsHash(g.sha256)&&g.bytes>0&&g.bytes<67108864,"Invalid guard");
  }
  void Vector(string[] v){Need(v!=null&&v.Length==29,"Invalid profile vector");for(int i=0;i<29;i++)Need(manifest.files[i].nodes.Any(n=>n.sha256==v[i]),"Profile node missing");}
  static void Need(bool ok,string s){if(!ok)throw new InvalidDataException(s);}
  static bool IsHash(string s){return s!=null&&Regex.IsMatch(s,"^[0-9a-f]{64}$");}
  static string Hex(byte[] b){return BitConverter.ToString(b).Replace("-","").ToLowerInvariant();}
  public static string Hash(byte[] b){using(var h=SHA256.Create())return Hex(h.ComputeHash(b));}
  public static string HashFile(string p){using(var h=SHA256.Create())using(var f=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.Read))return Hex(h.ComputeHash(f));}
  public static void NoReparse(string p,bool directory){p=Path.GetFullPath(p);string volume=Path.GetPathRoot(p);Need(!String.IsNullOrEmpty(volume)&&!volume.StartsWith("\\\\"),"Local disk required");string at=volume;foreach(string s in p.Substring(volume.Length).Split(new[]{'\\','/'},StringSplitOptions.RemoveEmptyEntries)){at=Path.Combine(at,s);Need((File.GetAttributes(at)&FileAttributes.ReparsePoint)==0,"Linked paths are not supported: "+at);}Need(directory?Directory.Exists(p):File.Exists(p),"Missing path: "+p);}
  public static string Child(string root,string rel){Need(!String.IsNullOrEmpty(rel)&&!Path.IsPathRooted(rel)&&rel.IndexOf(':')<0&&rel.Split(new[]{'\\','/'}).All(s=>s!=""&&s!="."&&s!=".."),"Invalid relative path");string basePath=Path.GetFullPath(root).TrimEnd('\\','/')+Path.DirectorySeparatorChar,p=Path.GetFullPath(Path.Combine(basePath,rel.Replace('/',Path.DirectorySeparatorChar)));Need(p.StartsWith(basePath,StringComparison.OrdinalIgnoreCase),"Path escaped owner");return p;}
  static void GuardAncestor(string p){p=Path.GetFullPath(p);while(!Directory.Exists(p)){Need(!File.Exists(p),"Ancestor is a file");p=Path.GetDirectoryName(p);Need(p!=null,"No local ancestor");}NoReparse(p,true);}
  static void CreateSafeDirectory(string p){GuardAncestor(p);Directory.CreateDirectory(p);NoReparse(p,true);}
  static void Verify(string p,string hash,long? size){NoReparse(p,false);Need((!size.HasValue||new FileInfo(p).Length==size)&&HashFile(p)==hash,"파일 검증 실패 / Hash mismatch: "+p);}
  public static string RootIdentity(string content){return Hash(Utf8.GetBytes(Path.GetFullPath(content).TrimEnd('\\','/').ToUpperInvariant()));}
  public string ReleaseBackupDirectory(string content){
   string basePath=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"CrimsonSkiesUnified","Backups");
#if UNIFIED_TEST
   if(BackupOverride!=null)basePath=BackupOverride;
#endif
   return Child(Child(basePath,RootIdentity(content)),ReleaseId);
  }
  public static string SettingsPath(){
#if UNIFIED_TEST
   if(SettingsOverride!=null)return SettingsOverride;
#endif
   return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),@"Packages\Xbox360BackwardCompatibil.PrimaryCrimsonSkiesHighR_ksqcvrsvwz2jp\LocalCache\Local\Settings.ini");
  }
  public static bool ProcessPresent(string name){var a=Process.GetProcessesByName(name);try{return a.Length>0;}finally{foreach(var p in a)p.Dispose();}}
  public static void RequireStopped(){
#if !UNIFIED_TEST
   if(ProcessPresent("Emu")||ProcessPresent("EmuMenu"))throw new IOException("게임과 플레이 창을 모두 종료하세요. / Close the game and Play window first.");
#endif
  }
  static void Point(string s){
#if UNIFIED_TEST
   if(Fault!=null)Fault(s);
#endif
  }
  public string Resolve(string selected){Need(!String.IsNullOrWhiteSpace(selected),"게임 폴더를 선택하세요.");string p=Path.GetFullPath(selected);NoReparse(p,true);if(!File.Exists(Path.Combine(p,NativeName)))p=Path.Combine(p,"Content");NoReparse(p,true);return p.TrimEnd('\\','/');}
  void VerifyHost(string content){foreach(var g in manifest.guards)Verify(Child(content,g.path),g.sha256,g.bytes);var h=manifest.supportedPackage;Need(h!=null&&h.name=="Xbox360BackwardCompatibil.PrimaryCrimsonSkiesHighR"&&h.version=="2608.3123.1.0"&&h.architecture=="x64"&&h.publisher=="CN=92ADE8CC-2A9A-4DF3-9BAF-18AF498CAA12","Unsupported host");var settings=new XmlReaderSettings{DtdProcessing=DtdProcessing.Prohibit,XmlResolver=null,MaxCharactersInDocument=131072};int count=0;using(var r=XmlReader.Create(Child(content,"appxmanifest.xml"),settings))while(r.Read())if(r.NodeType==XmlNodeType.Element&&r.LocalName=="Identity"){count++;Need(r.Depth==1&&r.NamespaceURI=="http://schemas.microsoft.com/appx/manifest/foundation/windows10"&&r.GetAttribute("Name")==h.name&&r.GetAttribute("Version")==h.version&&r.GetAttribute("ProcessorArchitecture")==h.architecture&&r.GetAttribute("Publisher")==h.publisher,"Unsupported identity");}Need(count==1,"Invalid host identity");}
  string[] Inspect(string content){var v=new string[29];for(int i=0;i<29;i++){string p=Child(content,manifest.files[i].path);NoReparse(p,false);long n=new FileInfo(p).Length;Need(manifest.files[i].nodes.Any(x=>x.bytes==n),"Unsupported file size: "+manifest.files[i].path);v[i]=HashFile(p);Need(manifest.files[i].nodes.Any(x=>x.sha256==v[i]&&x.bytes==n),"알 수 없는 파일이 있어 중단했습니다. / Unknown modified file: "+manifest.files[i].path);log("검사 / Checked "+(i+1)+"/29: "+manifest.files[i].path);}return v;}
  string[] V(string id){var p=manifest.profiles.SingleOrDefault(x=>x.id==id);if(p!=null)return p.hashes;var s=manifest.inputs.SingleOrDefault(x=>x.id==id);Need(s!=null,"Unknown owned state");return s.hashes;}
  Profile Choice(string id){var p=manifest.profiles.SingleOrDefault(x=>x.id==id);Need(p!=null,"Unknown component selection");return p;}
  bool Dub(string id){var p=manifest.profiles.SingleOrDefault(x=>x.id==id);return p!=null&&p.dub;}
  bool Wide(string id){var p=manifest.profiles.SingleOrDefault(x=>x.id==id);return p!=null?p.wide:id=="foundation";}
  bool Korean(string id){var p=manifest.profiles.SingleOrDefault(x=>x.id==id);return p!=null?p.korean:id=="foundation";}
  Node N(int i,string hash){return manifest.files[i].nodes.Single(n=>n.sha256==hash);}
  string Original(string dir,int i){return Child(dir,"original-"+i.ToString("D2")+".bin");}
  void WriteReceipt(string dir,Receipt r){string dest=Child(dir,"receipt.json"),temp=Child(dir,".receipt-"+Guid.NewGuid().ToString("N")+".tmp");try{byte[] b=Utf8.GetBytes(serializer.Serialize(r));using(var f=new FileStream(temp,FileMode.CreateNew,FileAccess.Write,FileShare.None)){f.Write(b,0,b.Length);f.Flush(true);}RequireStopped();NoReparse(dir,true);if(File.Exists(dest)){NoReparse(dest,false);File.Replace(temp,dest,null);}else File.Move(temp,dest);}finally{if(File.Exists(temp)){NoReparse(temp,false);File.Delete(temp);}}}
  Receipt ReadReceipt(string content,string dir){GuardAncestor(dir);string p=Child(dir,"receipt.json");if(!File.Exists(p))return null;NoReparse(p,false);Need(new FileInfo(p).Length<=524288,"Oversize receipt");var r=serializer.Deserialize<Receipt>(File.ReadAllText(p,Utf8));Need(r!=null&&r.schema==1&&r.releaseId==ReleaseId&&r.root==content&&r.manifestSha256==ManifestDigest&&manifest.inputs.Any(x=>x.id==r.original),"백업 기록이 이 설치기·게임과 일치하지 않습니다. / Receipt binding mismatch");V(r.current);Settings.ValidateOrigin(r.settings);if(r.pending!=null){var j=r.pending;Need(Regex.IsMatch(j.stage??"","^[.]csunified-[0-9a-f]{32}$")&&j.changed!=null&&j.changed.Length<=29&&j.changed.Distinct().Count()==j.changed.Length&&j.changed.All(i=>i>=0&&i<29),"Invalid transaction journal");V(j.from);V(j.to);Settings.Bytes(j.settingsBefore);Settings.Bytes(j.settingsAfter);}return r;}
  void VerifyBackups(string dir,Receipt r){for(int i=0;i<29;i++){string p=Original(dir,i);if(File.Exists(p))Verify(p,V(r.original)[i],N(i,V(r.original)[i]).bytes);}}
  List<Edge> Route(int i,string from,string to){var todo=new Queue<string>();var seen=new HashSet<string>{from};var back=new Dictionary<string,Edge>();todo.Enqueue(from);while(todo.Count>0){string at=todo.Dequeue();if(at==to){var result=new List<Edge>();while(at!=from){var e=back[at];result.Add(e);at=e.source;}result.Reverse();return result;}foreach(var e in manifest.files[i].edges.Where(x=>x.source==at))if(seen.Add(e.target)){back[e.target]=e;todo.Enqueue(e.target);}}return null;}
  void Decode(string source,Edge e,string dest){Verify(Child(package,manifest.tool.path),manifest.tool.sha256,null);Verify(Child(package,e.path),e.sha256,e.bytes);var start=new ProcessStartInfo(Child(package,manifest.tool.path),"-d -D -R -s "+Quote(source)+" "+Quote(Child(package,e.path))+" "+Quote(dest)){UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden,RedirectStandardError=true,RedirectStandardOutput=true};start.EnvironmentVariables.Remove("XDELTA");using(var p=Process.Start(start)){var a=p.StandardOutput.ReadToEndAsync();var b=p.StandardError.ReadToEndAsync();if(!p.WaitForExit(300000)){try{p.Kill();}catch{}throw new IOException("Delta timed out");}Task.WaitAll(a,b);Need(p.ExitCode==0,"Delta failed: "+a.Result+b.Result);}}
  static string Quote(string s){Need(s.IndexOfAny(new[]{'"','\r','\n'})<0,"Invalid process path");return "\""+s.TrimEnd('\\')+"\"";}
  void Materialize(int i,string content,string dir,Receipt r,string current,string desired,string dest,string stage){
   string path=Child(content,manifest.files[i].path);var route=Route(i,current,desired);string source=path,backup=Original(dir,i);if(File.Exists(backup)){var other=Route(i,V(r.original)[i],desired);if(other!=null&&(route==null||other.Count<route.Count)){route=other;source=backup;}}
   Need(route!=null,"복구용 원본이 없습니다. 이전 설치기의 복구를 먼저 실행하세요. / No verified route from owned inputs.");Verify(source,source==path?current:V(r.original)[i],null);string prev=source;
   try{for(int k=0;k<route.Count;k++){string next=Child(stage,"decode-"+i+"-"+k+".bin");Decode(prev,route[k],next);Verify(next,route[k].target,N(i,route[k].target).bytes);if(prev!=source){NoReparse(prev,false);File.Delete(prev);}prev=next;}if(prev==source)File.Copy(source,dest,false);else{File.Move(prev,dest);prev=source;}Verify(dest,desired,N(i,desired).bytes);}finally{if(prev!=source&&File.Exists(prev)){NoReparse(prev,false);File.Delete(prev);}}
  }
  void CheckSpace(string content,string dir,int[] changed,Receipt r){var totals=new Dictionary<string,long>(StringComparer.OrdinalIgnoreCase);Action<string,long> add=(p,n)=>{string root=Path.GetPathRoot(p);if(!totals.ContainsKey(root))totals[root]=0;totals[root]=checked(totals[root]+n);};long sum=changed.Sum(i=>manifest.files[i].nodes.Max(n=>n.bytes)),largest=changed.Length==0?0:changed.Max(i=>manifest.files[i].nodes.Max(n=>n.bytes));add(content,sum*2+largest*2+268435456);foreach(int i in changed)if(!File.Exists(Original(dir,i)))add(dir,N(i,V(r.original)[i]).bytes);string cache=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),@"Packages\Xbox360BackwardCompatibil.PrimaryCrimsonSkiesHighR_ksqcvrsvwz2jp\LocalCache\Local\VirtualDrive\Harddisk\Cache1\RawPartition");if(File.Exists(cache)){long n=new FileInfo(cache).Length;add(cache,n);add(dir,n);}foreach(var kv in totals)Need(new DriveInfo(kv.Key).AvailableFreeSpace>=kv.Value,"공간이 부족합니다 / Insufficient space on "+kv.Key+": "+Math.Ceiling(kv.Value/1073741824.0)+" GiB required");}
  void Cleanup(string content,Pending j){string stage=Child(content,j.stage);if(!Directory.Exists(stage))return;NoReparse(stage,true);foreach(string p in Directory.GetFiles(stage)){Need(Regex.IsMatch(Path.GetFileName(p),"^(ready|undo)-[0-9]+[.]bin$|^decode-[0-9]+-[0-9]+[.]bin$"),"Unowned stage member");NoReparse(p,false);File.Delete(p);}Directory.Delete(stage,false);}
  void Recover(string content,string dir,Receipt r){var j=r.pending;Need(j!=null,"중단된 작업이 없습니다. / No interrupted transaction");string stage=Child(content,j.stage);NoReparse(stage,true);var now=Inspect(content);string[] before=V(j.from),after=V(j.to);for(int i=0;i<29;i++){Need(now[i]==before[i]||j.changed.Contains(i)&&now[i]==after[i],"Recovery refused unknown concurrent file");if(j.changed.Contains(i))Verify(Child(stage,"undo-"+i+".bin"),before[i],N(i,before[i]).bytes);}
   RequireStopped();foreach(int i in j.changed.Reverse()){string p=Child(content,manifest.files[i].path);if(now[i]==before[i])continue;string undo=Child(stage,"undo-"+i+".bin"),temp=Child(stage,"ready-"+i+".bin");if(File.Exists(temp)){NoReparse(temp,false);File.Delete(temp);}File.Copy(undo,temp,false);RequireStopped();Verify(p,now[i],null);File.Replace(temp,p,null);Verify(p,before[i],N(i,before[i]).bytes);}
   RefreshGameCache(j.from,content);Settings.Rollback(SettingsPath(),Settings.Bytes(j.settingsBefore),Settings.Bytes(j.settingsAfter));Need(Inspect(content).SequenceEqual(before),"Recovery verification failed");r.current=j.from;r.pending=null;WriteReceipt(dir,r);Cleanup(content,j);log("중단 전 상태로 복구했습니다. 다시 선택해서 설치할 수 있습니다. / Interrupted transaction rolled back.");
  }
  public void Run(string mode,string selected,string profileId){Need(new[]{"--check","--apply","--restore","--recover"}.Contains(mode),"Invalid mode");string content=Resolve(selected);using(var mutex=new Mutex(false,"Local\\CrimsonSkies-KoreanPatch-"+RootIdentity(content))){bool held=false;try{try{held=mutex.WaitOne(0);}catch(AbandonedMutexException){held=true;}Need(held,"다른 설치기가 사용 중입니다. / Another installer owns this game.");RunLocked(mode,content,profileId);}finally{if(held)mutex.ReleaseMutex();}}}
  void RunLocked(string mode,string content,string profileId){
   VerifyHost(content);string dir=ReleaseBackupDirectory(content);var receipt=ReadReceipt(content,dir);bool newOwner=receipt==null;if(mode!="--check")RequireStopped();
   if(mode=="--recover"){Need(receipt!=null,"No owned recovery record");Recover(content,dir,receipt);return;}
   if(receipt!=null&&receipt.pending!=null)throw new IOException("중단된 작업이 있습니다. ‘중단 작업 복구’를 먼저 누르세요. / Recover the interrupted transaction first.");
   string[] current=Inspect(content);string input=null;
   if(receipt!=null){VerifyBackups(dir,receipt);Need(current.SequenceEqual(V(receipt.current)),"현재 파일이 통합 설치 기록과 다릅니다. 이전 도구로 변경한 상태를 먼저 복구하세요. / Current files differ from the owned receipt.");input=receipt.current;}
   else{var initial=manifest.inputs.FirstOrDefault(p=>p.hashes.SequenceEqual(current));if(initial!=null)input=initial.id;}
   if(input==null){var ext=manifest.knownExternal.FirstOrDefault(x=>x.hashes.SequenceEqual(current));throw new IOException(ext!=null?"기존 Alpha 2 더빙/자막은 이전 도구에서 자막 → 음성 순서로 복구한 뒤 통합 설치기를 사용하세요. / Restore captions then audio with the previous tools first.":"이 설치기가 소유하지 않은 조합입니다. 원본 또는 0.11 기반 상태가 필요합니다. / Unsupported/unowned component mixture.");}
   Verify(Child(package,manifest.tool.path),manifest.tool.sha256,null);
   if(mode=="--check"){foreach(var f in manifest.files)foreach(var e in f.edges)Verify(Child(package,e.path),e.sha256,e.bytes);new GameCacheTransaction(this,content,null).Preflight(true);log("지원 상태 / Supported state: "+input+"\r\n게임 파일 변경 없음 / No game files changed.");return;}
   bool restoring=mode=="--restore";Need(!restoring||receipt!=null,"이 설치기가 만든 백업이 없습니다. / No owned restore history.");Profile choice=restoring?null:Choice(profileId);string targetId=restoring?receipt.original:choice.id;string[] target=V(targetId);byte[] settingsBefore=Settings.Read(SettingsPath());
   if(receipt==null)receipt=new Receipt{schema=1,releaseId=ReleaseId,root=content,manifestSha256=ManifestDigest,original=input,current=input,settings=Settings.Capture(settingsBefore)};
   byte[] settingsAfter=Settings.Plan(settingsBefore,receipt.settings,Korean(targetId),Wide(targetId),restoring);
   int[] changed=Enumerable.Range(0,29).Where(i=>current[i]!=target[i]).ToArray();CheckSpace(content,dir,changed,receipt);var cache=new GameCacheTransaction(this,content,targetId);cache.Preflight();
   // Check every chosen route and payload before making a stage or backup.
   foreach(int i in changed){var route=Route(i,current[i],target[i]);if(File.Exists(Original(dir,i))){var other=Route(i,V(receipt.original)[i],target[i]);if(other!=null&&(route==null||other.Count<route.Count))route=other;}Need(route!=null,"Required original backup is unavailable");foreach(var e in route)Verify(Child(package,e.path),e.sha256,e.bytes);}
   string stageName=".csunified-"+Guid.NewGuid().ToString("N"),stage=Child(content,stageName);CreateSafeDirectory(stage);CreateSafeDirectory(dir);
   var journal=new Pending{stage=stageName,from=input,to=targetId,changed=changed,settingsBefore=Settings.Encode(settingsBefore),settingsAfter=Settings.Encode(settingsAfter)};bool pendingSaved=false;
   try{
    // Bind partial backups even if decoding is interrupted before the first
    // game-file write. Such a receipt still describes the verified input.
    if(newOwner)WriteReceipt(dir,receipt);
    foreach(int i in changed){string source=Child(content,manifest.files[i].path),undo=Child(stage,"undo-"+i+".bin"),ready=Child(stage,"ready-"+i+".bin");File.Copy(source,undo,false);Verify(undo,current[i],N(i,current[i]).bytes);Materialize(i,content,dir,receipt,current[i],target[i],ready,stage);string backup=Original(dir,i);if(!File.Exists(backup)){Need(current[i]==V(receipt.original)[i],"Missing original backup for previously changed file");string temp=Child(dir,".backup-"+Guid.NewGuid().ToString("N")+".tmp");try{File.Copy(source,temp,false);Verify(temp,current[i],N(i,current[i]).bytes);using(var f=new FileStream(temp,FileMode.Open,FileAccess.ReadWrite,FileShare.None))f.Flush(true);File.Move(temp,backup);}finally{if(File.Exists(temp)){NoReparse(temp,false);File.Delete(temp);}}}Verify(backup,V(receipt.original)[i],N(i,V(receipt.original)[i]).bytes);log("준비 / Staged: "+manifest.files[i].path);}
    RequireStopped();Need(Inspect(content).SequenceEqual(current),"Game files changed while staging");Settings.Ensure(SettingsPath(),settingsBefore);receipt.pending=journal;WriteReceipt(dir,receipt);pendingSaved=true;Point("prepared");
    foreach(int i in changed){RequireStopped();string p=Child(content,manifest.files[i].path);Verify(p,current[i],N(i,current[i]).bytes);string ready=Child(stage,"ready-"+i+".bin");Verify(ready,target[i],N(i,target[i]).bytes);File.Replace(ready,p,null);Verify(p,target[i],N(i,target[i]).bytes);log("적용 / Applied: "+manifest.files[i].path);Point("file-"+i);}
    Need(Inspect(content).SequenceEqual(target),"Final game verification failed");cache.Commit();Point("cache");Settings.Commit(SettingsPath(),settingsBefore,settingsAfter);Point("settings");receipt.current=targetId;receipt.pending=null;WriteReceipt(dir,receipt);pendingSaved=false;log(restoring?"설치 전 상태로 복구했습니다. / Restored the installation-before state.":"선택한 구성요소 설치와 전체 검증을 마쳤습니다. / Selected components installed and verified.");
   }catch(Exception failure){
    if(pendingSaved){try{cache.Rollback();receipt.pending=journal;Recover(content,dir,receipt);pendingSaved=false;}catch(Exception rollback){log("중단 작업 복구가 필요합니다 / Recovery required: "+rollback.Message);throw new IOException("작업이 중단됐습니다. 게임을 닫고 ‘중단 작업 복구’를 실행하세요. 백업 / Backup: "+dir+"\r\n"+failure.Message,failure);}}
    throw;
   }finally{if(!pendingSaved)try{Cleanup(content,journal);}catch(Exception e){log("임시 파일 정리 보류 / Temporary cleanup deferred: "+e.Message);}}
  }
  public void Open(string selected){string content=Resolve(selected);RequireStopped();VerifyHost(content);string exe=Child(content,"EmuMenu/EmuMenu.exe");NoReparse(exe,false);Process.Start(new ProcessStartInfo(exe){UseShellExecute=true,WorkingDirectory=Path.GetDirectoryName(exe)});}
 }
}
