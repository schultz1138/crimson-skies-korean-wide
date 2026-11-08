// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Crimson Skies Korean patch contributors.
using System;using System.Collections.Generic;using System.Diagnostics;using System.Globalization;using System.IO;using System.Linq;using System.Security.Cryptography;using System.Text;using System.Text.RegularExpressions;using System.Threading;using System.Threading.Tasks;using System.Web.Script.Serialization;using System.Xml;
namespace CrimsonSkiesKoreanPatch {
 public sealed class PatchGuard {public string path,sha256;public long bytes;}
 public sealed class PatchTool {public string path,sha256;}
 public sealed class PackageIdentity {public string name,version,architecture,publisher;}
 public sealed class PatchSource {public long sourceBytes,deltaBytes;public string sourceSha256,delta,deltaSha256;}
 public sealed class PatchFile {public string path,targetSha256;public long targetBytes;public PatchSource[] sources;}
 public sealed class SourceProfile {public string id,label;public string[] sha256;}
 public sealed class PatchManifest {public int schema;public string releaseId;public PatchTool tool;public PackageIdentity supportedPackage;public PatchFile[] files;public SourceProfile[] profiles;public PatchGuard[] guards;}
 public sealed class SelectionBefore {public string beforeKey,restoreKey;public int beforePresetId;}
 public sealed class BackupReceipt {public int schema;public string releaseId,root,manifestSha256,profileId,createdUtc,state;public string[] beforeSha256;public SelectionBefore selection;}
 public sealed class ProfileBackupMetadata {public int schema;public string releaseId,root,manifestSha256,profileId,createdUtc;public string[] beforeSha256;}
 public sealed class FileState {public int Index;public PatchFile Item;public string Path,Hash,Kind;public long Bytes;}
 public sealed partial class PatchEngine {
  public const string ManifestDigest=ReleasePins.ManifestSha256;
  public const string ReleaseId="CrimsonSkies-Korean-Dub-0.13.0-alpha.2";
  public const string NativeName="xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll";
  public static readonly string[] Allowed=ReleasePins.Allowed;
  public const string FoundationNamespace="http://schemas.microsoft.com/appx/manifest/foundation/windows10";
  const long MaxFileBytes=8589934592L;
  static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
  static readonly Regex DigestPattern=new Regex("^[0-9a-fA-F]{64}$",RegexOptions.CultureInvariant);
  readonly string packageRoot;readonly PatchManifest manifest;readonly Action<string> log;
  readonly JavaScriptSerializer serializer=new JavaScriptSerializer{MaxJsonLength=262144};
  public PatchEngine(string directory,Action<string> logger) {
   log=logger??delegate{};packageRoot=Path.GetFullPath(directory);NoReparse(packageRoot,true);string path=Child(packageRoot,"manifest.json");NoReparse(path,false);
   if(new FileInfo(path).Length>262144)throw new InvalidDataException("배포 파일 목록이 너무 큽니다.");byte[] bytes=File.ReadAllBytes(path);
   if(!IsHash(ManifestDigest)||!Same(Hash(bytes),ManifestDigest))throw new InvalidDataException("배포 파일 목록이 이 설치기와 일치하지 않습니다. 압축 파일을 다시 받아 주세요.");
   manifest=serializer.Deserialize<PatchManifest>(Utf8.GetString(bytes));ValidateManifest();
  }
  void ValidateManifest() {
   if(manifest==null||manifest.schema!=2||manifest.releaseId!=ReleaseId||manifest.tool==null||manifest.tool.path!="tools/xdelta3.exe"||!IsHash(manifest.tool.sha256)||manifest.files==null||manifest.files.Length!=Allowed.Length||manifest.profiles==null||manifest.profiles.Length!=1)throw new InvalidDataException("지원하지 않는 패치 목록입니다.");
   PackageIdentity h=manifest.supportedPackage;
   if(h==null||h.name!="Xbox360BackwardCompatibil.PrimaryCrimsonSkiesHighR"||h.version!="2608.3123.1.0"||h.architecture!="x64"||h.publisher!="CN=92ADE8CC-2A9A-4DF3-9BAF-18AF498CAA12")throw new InvalidDataException("지원하는 게임 실행 환경 정보가 없습니다.");
   if(manifest.guards==null||manifest.guards.Length!=ReleasePins.Guards.Length)throw new InvalidDataException("Missing audio foundation guards.");
   for(int g=0;g<manifest.guards.Length;g++)if(manifest.guards[g].path!=ReleasePins.Guards[g]||manifest.guards[g].bytes<1||!IsHash(manifest.guards[g].sha256))throw new InvalidDataException("Invalid audio foundation guard.");
   var deltas=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
   for(int i=0;i<Allowed.Length;i++) {
    PatchFile f=manifest.files[i];if(f==null||f.path!=Allowed[i]||!IsHash(f.targetSha256)||f.targetBytes<1||f.targetBytes>MaxFileBytes||f.sources==null||f.sources.Length<1||f.sources.Length>4)throw new InvalidDataException("패치 대상 파일 정보가 올바르지 않습니다.");
    var hashes=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
    foreach(PatchSource s in f.sources)if(s==null||!IsHash(s.sourceSha256)||!hashes.Add(s.sourceSha256)||Same(s.sourceSha256,f.targetSha256)||s.sourceBytes<1||s.sourceBytes>MaxFileBytes||s.deltaBytes<1||s.deltaBytes>MaxFileBytes||!IsHash(s.deltaSha256)||s.delta==null||!Regex.IsMatch(s.delta,"^patches/[A-Za-z0-9_-]+[.]vcdiff$",RegexOptions.CultureInvariant)||!deltas.Add(s.delta))throw new InvalidDataException("차분 원본 정보가 올바르지 않습니다.");
   }
   var ids=new HashSet<string>(StringComparer.Ordinal);var vectors=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
   foreach(SourceProfile p in manifest.profiles) {
    if(p==null||p.id!="ko-wide-0.11.0-beta.1"||!ids.Add(p.id)||String.IsNullOrWhiteSpace(p.label)||p.label.Length>128||p.sha256==null||p.sha256.Length!=Allowed.Length||p.sha256.Any(x=>!IsHash(x))||!vectors.Add(String.Join("|",p.sha256))||p.sha256.Where((x,i)=>!Same(x,manifest.files[i].targetSha256)).Count()==0)throw new InvalidDataException("지원 원본 조합이 올바르지 않습니다.");
    for(int i=0;i<Allowed.Length;i++)BeforeBytes(p,i);
   }
  }
  public static string Hash(byte[] b){using(var h=SHA256.Create())return Hex(h.ComputeHash(b));}
  public static string HashFile(string p){using(var h=SHA256.Create())using(var f=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.Read))return Hex(h.ComputeHash(f));}
  static string Hex(byte[] b){return BitConverter.ToString(b).Replace("-","").ToLowerInvariant();}
  static bool Same(string a,string b){return String.Equals(a,b,StringComparison.OrdinalIgnoreCase);}
  static bool IsHash(string s){return s!=null&&DigestPattern.IsMatch(s);}
  public static void NoReparse(string path,bool directory) {
   string p=Path.GetFullPath(path),volume=Path.GetPathRoot(p);if(String.IsNullOrEmpty(volume)||volume.StartsWith("\\\\",StringComparison.Ordinal))throw new IOException("로컬 디스크의 폴더를 선택해 주세요.");
   string current=volume;CheckAttributes(current);foreach(string part in p.Substring(volume.Length).Split(new[]{'\\','/'},StringSplitOptions.RemoveEmptyEntries)){current=Path.Combine(current,part);CheckAttributes(current);}
   if(directory?!Directory.Exists(p):!File.Exists(p))throw new FileNotFoundException("필요한 파일 또는 폴더가 없습니다: "+p);
  }
  static void CheckAttributes(string p){if((File.GetAttributes(p)&FileAttributes.ReparsePoint)!=0)throw new IOException("연결 폴더·심볼릭 링크 경로는 지원하지 않습니다: "+p);}
  public static string Child(string root,string relative) {
   if(String.IsNullOrEmpty(relative)||Path.IsPathRooted(relative)||relative.IndexOf(':')>=0||relative.Split(new[]{'\\','/'}).Any(x=>x==".."||x=="."||x.Length==0))throw new InvalidDataException("잘못된 상대 경로입니다.");
   string parent=Path.GetFullPath(root).TrimEnd('\\','/')+Path.DirectorySeparatorChar,p=Path.GetFullPath(Path.Combine(parent,relative.Replace('/',Path.DirectorySeparatorChar)));if(!p.StartsWith(parent,StringComparison.OrdinalIgnoreCase))throw new IOException("폴더를 벗어나는 경로입니다.");return p;
  }
  static void CreateSafeDirectory(string p){if(Directory.Exists(p)){NoReparse(p,true);return;}string parent=Path.GetDirectoryName(p);if(String.IsNullOrEmpty(parent))throw new IOException("잘못된 폴더 경로입니다.");CreateSafeDirectory(parent);Directory.CreateDirectory(p);NoReparse(p,true);}
  static void GuardExistingAncestor(string p){string q=Path.GetFullPath(p);while(!Directory.Exists(q)){if(File.Exists(q))throw new IOException("백업 폴더 위치에 파일이 있습니다.");q=Path.GetDirectoryName(q);if(String.IsNullOrEmpty(q))throw new IOException("잘못된 백업 경로입니다.");}NoReparse(q,true);}
  public string ResolveContent(string selected) {
   if(String.IsNullOrWhiteSpace(selected))throw new ArgumentException("게임 폴더를 선택해 주세요.");string p=Path.GetFullPath(selected);if(p.Length>Path.GetPathRoot(p).Length)p=p.TrimEnd('\\','/');NoReparse(p,true);
   if(!File.Exists(Path.Combine(p,NativeName)))p=Path.Combine(p,"Content");NoReparse(p,true);return p.TrimEnd('\\','/');
  }
  public void VerifySupportedHost(string content) {
   string p=Child(content,"appxmanifest.xml");NoReparse(p,false);if(new FileInfo(p).Length<1||new FileInfo(p).Length>131072)throw new InvalidDataException("게임 실행 환경 정보의 크기가 올바르지 않습니다.");
   var settings=new XmlReaderSettings{DtdProcessing=DtdProcessing.Prohibit,XmlResolver=null,MaxCharactersInDocument=131072,IgnoreComments=true,IgnoreWhitespace=true};int identities=0;bool root=false;
   using(var reader=XmlReader.Create(p,settings))while(reader.Read())if(reader.NodeType==XmlNodeType.Element) {
    if(!root){if(reader.LocalName!="Package"||reader.NamespaceURI!=FoundationNamespace)throw new InvalidDataException("지원하는 게임 패키지 문서가 아닙니다.");root=true;}
    if(reader.LocalName=="Identity") {
     identities++;if(identities!=1||reader.Depth!=1||reader.NamespaceURI!=FoundationNamespace||reader.GetAttribute("Name")!=manifest.supportedPackage.name||reader.GetAttribute("Version")!=manifest.supportedPackage.version||reader.GetAttribute("ProcessorArchitecture")!=manifest.supportedPackage.architecture||reader.GetAttribute("Publisher")!=manifest.supportedPackage.publisher)throw new InvalidDataException("지원하는 게임 실행 환경 버전과 일치하지 않습니다.");
    }
   }
   if(!root||identities!=1)throw new InvalidDataException("게임 실행 환경의 식별 정보가 없습니다.");
   foreach(var g in manifest.guards)VerifyHash(Child(content,g.path),g.sha256,g.bytes);
  }
  public static string RootIdentity(string content){return Hash(Utf8.GetBytes(Path.GetFullPath(content).TrimEnd('\\','/').ToUpperInvariant()));}
  public static string BackupBase(){return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"CrimsonSkiesFullDubPublic","Backups");}
  public static string SettingsPath(){return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),@"Packages\Xbox360BackwardCompatibil.PrimaryCrimsonSkiesHighR_ksqcvrsvwz2jp\LocalCache\Local\Settings.ini");}
  public string ReleaseBackupDirectory(string content){return Child(Child(BackupBase(),RootIdentity(content)),ReleaseId);}
  public string ProfileBackupDirectory(string content,string profileId){Profile(profileId);return Child(ReleaseBackupDirectory(content),profileId);}
  string OriginalPath(string folder,int i){return Child(folder,"original-"+i.ToString(CultureInfo.InvariantCulture)+".bin");}
  public static bool ProcessPresent(string name){Process[] ps=Process.GetProcessesByName(name);try{return ps.Length!=0;}finally{foreach(var p in ps)p.Dispose();}}
  public static void RequireStopped(){
#if AUDIO_TRANSACTION_FIXTURE
return;
#else
if(ProcessPresent("Emu")||ProcessPresent("EmuMenu"))throw new IOException("게임과 원래 실행기를 모두 종료한 뒤 다시 실행해 주세요. 이 도구는 실행 중인 프로그램을 종료하지 않습니다.");
#endif
}
  SourceProfile Profile(string id){SourceProfile p=manifest.profiles.SingleOrDefault(x=>x.id==id);if(p==null)throw new InvalidDataException("지원 원본 종류를 확인할 수 없습니다.");return p;}
  long BeforeBytes(SourceProfile p,int i){PatchFile f=manifest.files[i];if(Same(p.sha256[i],f.targetSha256))return f.targetBytes;PatchSource s=f.sources.SingleOrDefault(x=>Same(x.sourceSha256,p.sha256[i]));if(s==null)throw new InvalidDataException("원본 조합과 차분 목록이 일치하지 않습니다.");return s.sourceBytes;}
  public List<FileState> Inspect(string content) {
   var states=new List<FileState>();for(int i=0;i<Allowed.Length;i++){PatchFile f=manifest.files[i];string p=Child(content,f.path);NoReparse(p,false);long length=new FileInfo(p).Length;string h=HashFile(p);string kind=length==f.targetBytes&&Same(h,f.targetSha256)?"target":f.sources.Any(s=>s.sourceBytes==length&&Same(s.sourceSha256,h))?"known-source":"unknown";states.Add(new FileState{Index=i,Item=f,Path=p,Bytes=length,Hash=h,Kind=kind});log(f.path+": "+(kind=="target"?"통합 패치 대상과 일치":kind=="known-source"?"지원 원본과 일치":"지원하지 않는 파일")+"\r\nSHA-256 "+h);}return states;
  }
  SourceProfile CoherentProfile(List<FileState> states){return manifest.profiles.SingleOrDefault(p=>Enumerable.Range(0,Allowed.Length).All(i=>states[i].Bytes==BeforeBytes(p,i)&&Same(states[i].Hash,p.sha256[i])));}
  bool AllTarget(List<FileState> s){return s.All(x=>x.Bytes==x.Item.targetBytes&&Same(x.Hash,x.Item.targetSha256));}
  bool OwnedState(List<FileState> s,SourceProfile p){return s.All(x=>(x.Bytes==x.Item.targetBytes&&Same(x.Hash,x.Item.targetSha256))||(x.Bytes==BeforeBytes(p,x.Index)&&Same(x.Hash,p.sha256[x.Index])));}
  static void VerifyHash(string p,string hash,long? bytes){NoReparse(p,false);if(bytes.HasValue&&new FileInfo(p).Length!=bytes.Value||!Same(HashFile(p),hash))throw new InvalidDataException("파일 검증 실패: "+p);}
  void VerifyPayloads(){VerifyHash(Child(packageRoot,manifest.tool.path),manifest.tool.sha256,null);foreach(var f in manifest.files)foreach(var s in f.sources)VerifyHash(Child(packageRoot,s.delta),s.deltaSha256,s.deltaBytes);}
  static void DeleteOwnedFile(string p,string parent){string prefix=Path.GetFullPath(parent).TrimEnd('\\','/')+Path.DirectorySeparatorChar;p=Path.GetFullPath(p);if(!p.StartsWith(prefix,StringComparison.OrdinalIgnoreCase))throw new IOException("임시 파일 경로 검증 실패");if(File.Exists(p)){NoReparse(p,false);File.Delete(p);}}
  static string ShortTemp(string folder,string prefix){return Child(folder,prefix+Guid.NewGuid().ToString("N").Substring(0,8)+".tmp");}
  void WriteJsonAtomic(string path,object value,string parent,bool replace) {
   string temp=ShortTemp(parent,"r-");try{byte[] bytes=Utf8.GetBytes(serializer.Serialize(value));using(var f=new FileStream(temp,FileMode.CreateNew,FileAccess.Write,FileShare.None)){f.Write(bytes,0,bytes.Length);f.Flush(true);}RequireStopped();NoReparse(parent,true);if(File.Exists(path)){if(!replace)throw new IOException("기존 백업 기록을 덮어쓸 수 없습니다.");NoReparse(path,false);File.Replace(temp,path,null);}else File.Move(temp,path);}finally{DeleteOwnedFile(temp,parent);}
  }
  T ReadJson<T>(string path,int max){NoReparse(path,false);if(new FileInfo(path).Length<1||new FileInfo(path).Length>max)throw new InvalidDataException("백업 기록 크기가 올바르지 않습니다.");return serializer.Deserialize<T>(File.ReadAllText(path,Utf8));}
  void ValidateBinding(int schema,string release,string root,string digest,string profileId,string[] hashes,string content,SourceProfile p){if(schema!=2||release!=ReleaseId||!Same(root,content)||!Same(digest,ManifestDigest)||profileId!=p.id||hashes==null||hashes.Length!=Allowed.Length||hashes.Where((h,i)=>!Same(h,p.sha256[i])).Any())throw new InvalidDataException("백업 기록이 선택한 게임·원본·패치와 일치하지 않습니다.");}
  void ValidateProfileBackups(string content,SourceProfile p,bool required) {
   string folder=ProfileBackupDirectory(content,p.id);GuardExistingAncestor(folder);if(!Directory.Exists(folder)){if(required)throw new IOException("설치 전 백업 폴더가 없습니다.");return;}NoReparse(folder,true);
   string meta=Child(folder,"profile.json");if(File.Exists(meta)){var d=ReadJson<ProfileBackupMetadata>(meta,65536);if(d==null)throw new InvalidDataException("백업 기록이 올바르지 않습니다.");ValidateBinding(d.schema,d.releaseId,d.root,d.manifestSha256,d.profileId,d.beforeSha256,content,p);}else if(required)throw new IOException("설치 전 백업 식별 정보가 없습니다.");
   for(int i=0;i<Allowed.Length;i++){string b=OriginalPath(folder,i);if(File.Exists(b))VerifyHash(b,p.sha256[i],BeforeBytes(p,i));else if(required)throw new IOException("설치 전 백업 파일이 없습니다: "+i);}
  }
  BackupReceipt ReadOwnedReceipt(string content) {
   string dir=ReleaseBackupDirectory(content);GuardExistingAncestor(dir);if(!Directory.Exists(dir))return null;NoReparse(dir,true);string path=Child(dir,"receipt.json");if(!File.Exists(path))return null;
   BackupReceipt r=ReadJson<BackupReceipt>(path,65536);if(r==null)throw new InvalidDataException("설치 기록이 올바르지 않습니다.");SourceProfile p=Profile(r.profileId);ValidateBinding(r.schema,r.releaseId,r.root,r.manifestSha256,r.profileId,r.beforeSha256,content,p);
   if(r.state!="prepared"&&r.state!="installed"&&r.state!="restored"&&r.state!="interrupted")throw new InvalidDataException("설치 기록 상태가 올바르지 않습니다.");ValidateSelectionBefore(r.selection);ValidateProfileBackups(content,p,true);return r;
  }
  void SaveReceipt(string content,SourceProfile p,SelectionBefore selection,string state,string created) {
   string dir=ReleaseBackupDirectory(content);NoReparse(dir,true);string path=Child(dir,"receipt.json");if(File.Exists(path))ReadOwnedReceipt(content);
   var data=new BackupReceipt{schema=2,releaseId=ReleaseId,root=content,manifestSha256=ManifestDigest,profileId=p.id,beforeSha256=p.sha256.ToArray(),createdUtc=created??DateTime.UtcNow.ToString("o"),state=state,selection=selection};
   WriteJsonAtomic(path,data,dir,true);var verify=ReadOwnedReceipt(content);if(verify==null||verify.profileId!=p.id||verify.state!=state)throw new IOException("설치 기록 저장 확인에 실패했습니다.");
  }
  void PrepareBackups(string content,SourceProfile p,List<FileState> states,bool fresh) {
   ValidateProfileBackups(content,p,!fresh);if(!fresh)return;string folder=ProfileBackupDirectory(content,p.id);CreateSafeDirectory(folder);
   for(int i=0;i<Allowed.Length;i++){string b=OriginalPath(folder,i);if(File.Exists(b)){VerifyHash(b,p.sha256[i],BeforeBytes(p,i));continue;}VerifyHash(states[i].Path,p.sha256[i],BeforeBytes(p,i));string temp=ShortTemp(folder,"b"+i+"-");try{File.Copy(states[i].Path,temp,false);VerifyHash(temp,p.sha256[i],BeforeBytes(p,i));using(var f=new FileStream(temp,FileMode.Open,FileAccess.ReadWrite,FileShare.None))f.Flush(true);RequireStopped();NoReparse(folder,true);File.Move(temp,b);VerifyHash(b,p.sha256[i],BeforeBytes(p,i));}finally{DeleteOwnedFile(temp,folder);}}
   string meta=Child(folder,"profile.json");if(!File.Exists(meta)){var d=new ProfileBackupMetadata{schema=2,releaseId=ReleaseId,root=content,manifestSha256=ManifestDigest,profileId=p.id,beforeSha256=p.sha256.ToArray(),createdUtc=DateTime.UtcNow.ToString("o")};WriteJsonAtomic(meta,d,folder,false);}ValidateProfileBackups(content,p,true);
  }
  void Decode(string source,PatchSource variant,string output) {
   string tool=Child(packageRoot,manifest.tool.path),delta=Child(packageRoot,variant.delta);VerifyHash(tool,manifest.tool.sha256,null);VerifyHash(delta,variant.deltaSha256,variant.deltaBytes);
   var start=new ProcessStartInfo(tool,"-d -D -R -s "+Quote(source)+" "+Quote(delta)+" "+Quote(output)){UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden,RedirectStandardError=true,RedirectStandardOutput=true,WorkingDirectory=packageRoot};start.EnvironmentVariables.Remove("XDELTA");
   using(Process p=Process.Start(start)){Task<string> error=p.StandardError.ReadToEndAsync(),normal=p.StandardOutput.ReadToEndAsync();if(!p.WaitForExit(180000)){try{p.Kill();}catch{}throw new IOException("차분 복원 시간이 초과됐습니다. 게임 파일은 아직 변경하지 않았습니다.");}Task.WaitAll(error,normal);if(p.ExitCode!=0)throw new InvalidDataException("차분 복원 실패: "+error.Result+normal.Result);}
  }
  static string Quote(string s){if(s.IndexOf('"')>=0||s.IndexOf('\r')>=0||s.IndexOf('\n')>=0)throw new ArgumentException("잘못된 파일 경로");return "\""+s.TrimEnd('\\')+"\"";}
  public void Run(string mode,string selected) {
   if(mode!="--check"&&mode!="--apply"&&mode!="--restore")throw new ArgumentException("지원하지 않는 실행 모드입니다.");string content=ResolveContent(selected);
   if(mode=="--check"){RunCore(mode,content);return;}using(var mutex=new Mutex(false,"Local\\CrimsonSkies-KoreanPatch-"+RootIdentity(content))){bool acquired=false;try{try{acquired=mutex.WaitOne(0);}catch(AbandonedMutexException){acquired=true;}if(!acquired)throw new IOException("같은 게임 폴더를 다른 설치·복구 작업이 사용 중입니다.");RunCore(mode,content);}finally{if(acquired)mutex.ReleaseMutex();}}
  }
  void RunCore(string mode,string content) {
   VerifySupportedHost(content);if(mode!="--check")RequireStopped();log("게임 Content: "+content);List<FileState> states=Inspect(content);BackupReceipt receipt=ReadOwnedReceipt(content);SourceProfile fresh=CoherentProfile(states);bool target=AllTarget(states);SourceProfile owner=receipt==null?null:Profile(receipt.profileId);bool owned=owner!=null&&OwnedState(states,owner);
   if(mode=="--check") {VerifyPayloads();new VoiceCacheTransaction(this,content).Preflight(true);if(!target&&fresh==null&&!owned)throw new InvalidDataException("지원하는 원본 조합 또는 이 설치기의 복구 가능한 상태가 아닙니다. 파일을 변경하지 않았습니다.");log(target?(receipt==null?"통합 패치 대상과 일치합니다. 이 설치기의 복구 기록은 없습니다.":"통합 패치가 설치되어 있으며 설치 전 상태로 복구할 수 있습니다."):fresh!=null?"지원 원본 조합: "+fresh.label:"이 설치기의 부분 적용 상태입니다. 설치 재개 또는 복구가 가능합니다.");if(ProcessPresent("Emu")||ProcessPresent("EmuMenu"))log("게임 또는 실행기가 실행 중입니다. 검사만 수행했습니다.");return;}
   bool apply=mode=="--apply";
   if(!apply&&receipt==null)throw new InvalidDataException(target?"통합 패치 대상과 일치하지만 이 설치기가 만든 백업이 없습니다. 이전에 적용한 패치의 복구 도구를 사용해 주세요.":"이 설치기가 만든 설치 기록이 없어 설치 전 상태를 확인할 수 없습니다. 파일을 변경하지 않았습니다.");
   if(!apply&&!owned)throw new InvalidDataException("현재 파일이 이 설치기의 설치 기록과 일치하지 않습니다. 복구하지 않았습니다.");
   if(apply&&fresh==null&&!target&&!owned)throw new InvalidDataException("원본과 다른 패치가 섞였거나 지원하지 않는 상태입니다. 설치하지 않았습니다.");
   if(apply)VerifyPayloads();
   var voiceCache=new VoiceCacheTransaction(this,content);voiceCache.Preflight();
   if(apply&&target){var plan=PrepareApplySelection();try{voiceCache.Commit(true);CommitSelection(plan);if(receipt!=null)SaveReceipt(content,owner,receipt.selection,"installed",receipt.createdUtc);}catch{voiceCache.Rollback();RollbackSelection(plan);throw;}log(receipt==null?"이미 통합 패치 대상과 일치합니다. 설정 이름만 확인했습니다. 복구 백업은 새로 만들지 않았습니다.":"이미 통합 패치가 설치되어 있습니다.");return;}
   SourceProfile selected=apply?(fresh??owner):owner;bool isFresh=apply&&fresh!=null;ValidateProfileBackups(content,selected,!isFresh);
   var selectionPlan=apply?PrepareApplySelection():PrepareRestoreSelection(receipt.selection.restoreKey);SelectionBefore before=isFresh?CaptureSelectionBefore(selectionPlan):receipt.selection;string created=receipt!=null&&receipt.profileId==selected.id?receipt.createdUtc:null;
   string stage=Child(content,".cskp-"+Guid.NewGuid().ToString("N").Substring(0,8));if(Directory.Exists(stage)||File.Exists(stage))throw new IOException("임시 작업 폴더가 이미 있습니다.");Directory.CreateDirectory(stage);NoReparse(stage,true);var ownedFiles=new List<string>();var committed=new List<int>();bool rollbackFailed=false;
   try {
    for(int i=0;i<Allowed.Length;i++) {
     FileState s=states[i];string ready=Child(stage,"ready-"+i+".bin");ownedFiles.Add(ready);
     if(apply){if(Same(s.Hash,s.Item.targetSha256)&&s.Bytes==s.Item.targetBytes)File.Copy(s.Path,ready,false);else{PatchSource variant=s.Item.sources.Single(x=>Same(x.sourceSha256,selected.sha256[i]));Decode(s.Path,variant,ready);}VerifyHash(ready,s.Item.targetSha256,s.Item.targetBytes);}
     else{File.Copy(OriginalPath(ProfileBackupDirectory(content,selected.id),i),ready,false);VerifyHash(ready,selected.sha256[i],BeforeBytes(selected,i));}
     string undo=Child(stage,"undo-"+i+".bin");ownedFiles.Add(undo);File.Copy(s.Path,undo,false);VerifyHash(undo,s.Hash,s.Bytes);
    }
    PrepareBackups(content,selected,states,isFresh);RequireStopped();foreach(FileState s in states)VerifyHash(s.Path,s.Hash,s.Bytes);EnsureSelectionUnchanged(selectionPlan);SaveReceipt(content,selected,before,"prepared",created);log("설치 전 백업: "+ProfileBackupDirectory(content,selected.id));
    if(!apply)CommitSelection(selectionPlan);
    for(int i=0;i<Allowed.Length;i++) {
     FileState s=states[i];string desired=apply?s.Item.targetSha256:selected.sha256[i];long bytes=apply?s.Item.targetBytes:BeforeBytes(selected,i);if(Same(s.Hash,desired)&&s.Bytes==bytes)continue;
     RequireStopped();NoReparse(stage,true);VerifyHash(s.Path,s.Hash,s.Bytes);string ready=Child(stage,"ready-"+i+".bin");VerifyHash(ready,desired,bytes);File.Replace(ready,s.Path,null);committed.Add(i);VerifyHash(s.Path,desired,bytes);log((apply?"설치 완료: ":"복구 완료: ")+s.Item.path);
    }
    for(int i=0;i<Allowed.Length;i++)VerifyHash(states[i].Path,apply?states[i].Item.targetSha256:selected.sha256[i],apply?states[i].Item.targetBytes:BeforeBytes(selected,i));
    if(apply)CommitSelection(selectionPlan);voiceCache.Commit(apply);SaveReceipt(content,selected,before,apply?"installed":"restored",created);log(apply?"통합 패치 설치와 전체 파일 검증을 마쳤습니다.":"설치 전 상태로 복구하고 전체 파일을 확인했습니다.");
   } catch(Exception original) {
    try{voiceCache.Rollback();}catch(Exception e){rollbackFailed=true;log("Voice cache rollback incomplete: "+e.Message);}
    try{RollbackSelection(selectionPlan);}catch(Exception e){rollbackFailed=true;log("설정 자동 되돌리기 미완료: "+e.Message);}
    foreach(int i in committed.AsEnumerable().Reverse())try{RequireStopped();FileState s=states[i];VerifyHash(s.Path,apply?s.Item.targetSha256:selected.sha256[i],null);string undo=Child(stage,"undo-"+i+".bin");VerifyHash(undo,s.Hash,s.Bytes);string back=Child(stage,"back-"+i+".bin");ownedFiles.Add(back);File.Copy(undo,back,false);File.Replace(back,s.Path,null);VerifyHash(s.Path,s.Hash,s.Bytes);}catch(Exception e){rollbackFailed=true;log("파일 자동 되돌리기 미완료: "+e.Message);}
    if(rollbackFailed)throw new IOException("작업이 중단되어 자동 되돌리기가 끝나지 않았습니다. 게임과 실행기를 종료하고 이 도구의 복구를 실행해 주세요. 백업: "+ProfileBackupDirectory(content,selected.id)+"\r\n원인: "+original.Message,original);throw;
   } finally {
    foreach(string p in ownedFiles)try{DeleteOwnedFile(p,stage);}catch(Exception e){log("임시 파일 정리 보류: "+e.Message);}try{NoReparse(stage,true);Directory.Delete(stage,false);}catch(Exception e){log("임시 폴더 정리 보류: "+e.Message);}
   }
  }
 }
}
