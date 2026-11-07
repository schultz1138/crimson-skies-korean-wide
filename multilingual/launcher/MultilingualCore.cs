// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Crimson Skies patch contributors.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Xml;

namespace CrimsonSkiesMultilingual {
 public sealed class ToolDefinition { public string path,sha256; }
 public sealed class PackFileDefinition { public string path,sha256,delta,deltaSha256; public long bytes,deltaBytes; }
 public sealed class PackDefinition { public string id,displayName,englishName,status,fallback,coverage; public PackFileDefinition[] files; }
 public sealed class CatalogDefinition { public int schema; public string releaseId; public ToolDefinition tool; public PackDefinition[] packs; }
 public sealed class PackReceipt {
  public int schema; public string releaseId,root,catalogSha256,state,activePackId,createdUtc;
  public SelectionBefore originalGameLanguage;
 }
 public sealed class BaseMetadata { public int schema; public string releaseId,root,catalogSha256; public string[] hashes; }
 public sealed class SwitchJournal {
  public int schema; public string releaseId,root,catalogSha256,stage,targetPackId,mode,settingsPath;
  public string beforeReceipt,afterReceipt,beforeSettings,afterSettings;
  public string[] beforeHashes,targetHashes; public long[] beforeBytes,targetBytes;
  public SelectionBefore selectionBefore;
 }
 sealed class Snapshot { public string path,hash; public long bytes; }

 public sealed class PackEngine {
  public const string NativeName="xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll";
  public static readonly string[] Files={NativeName,"Game/DefaultPackage.data/Data0000","Game/DefaultPackage.data/Data0005","EmuMenu/Assets/TitleMenuData.json"};
  public static readonly string[] FoundationHashes={
   "45c2c716da6c01f0937ce922dbfe2de89a3a9dfb163578757cfc5c5cc7e65f44",
   "91f96697337e6717dcdfaa99eb321196c3521da33295e77e54fb6777c92ed487",
   "68317f440ba24f74a832346f9ddf400f6a3076a743cd8e80b67be62aa5484e31",
   "200b609e7b279c25814fb42ed1dd1cdcd6f3203b670dc3b05749a6ee26686265"};
  public static readonly long[] FoundationBytes={42328576L,170459136L,170459136L,2200L};
  public const string GpuHash="f4d7784a007919a1e397405340855ac539c76f4abccfc6ecf8edebb2ed9835aa";
  public const string MenuDllHash="40e78379367b74c6dc7ccffce9215abae7400a069cebb9f8d50360f7a46fdc11";
  public const string LaunchDefaultsHash="da7174421ed8ec03bbdbe9d9b8e094a937786c82b445d05906911335eb25a4f0";
  const string FoundationNamespace="http://schemas.microsoft.com/appx/manifest/foundation/windows10";
  const long MaxBytes=8589934592L;
  static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
  static readonly Regex HashPattern=new Regex("^[0-9a-fA-F]{64}$",RegexOptions.CultureInvariant);
  readonly string packageRoot; readonly Action<string> log;
  readonly JavaScriptSerializer json=new JavaScriptSerializer{MaxJsonLength=2097152,RecursionLimit=32};
  readonly CatalogDefinition catalog;
  public CatalogDefinition Catalog { get { return catalog; } }

  public PackEngine(string packageDir,Action<string> logger) {
   log=logger??delegate{};packageRoot=Path.GetFullPath(packageDir);NoReparse(packageRoot,true);
   string path=Child(packageRoot,"catalog.json");NoReparse(path,false);if(new FileInfo(path).Length<1||new FileInfo(path).Length>1048576)throw new InvalidDataException("Invalid catalog size.");
   byte[] raw=File.ReadAllBytes(path);if(!IsHash(CatalogPin.Digest)||!Same(Hash(raw),CatalogPin.Digest))throw new InvalidDataException("The catalog does not match this launcher.");
   ValidateSchema(json.DeserializeObject(Utf8.GetString(raw)));catalog=json.Deserialize<CatalogDefinition>(Utf8.GetString(raw));ValidateCatalog();
  }
  static IDictionary<string,object> Object(object v,string label) {var d=v as IDictionary<string,object>;if(d==null)throw new InvalidDataException("Invalid "+label+" object.");return d;}
  static void Keys(IDictionary<string,object> d,string[] keys) {if(d.Count!=keys.Length||d.Keys.Any(k=>!keys.Contains(k,StringComparer.Ordinal)))throw new InvalidDataException("Unknown or missing catalog fields.");}
  static IEnumerable<object> Array(object v) {var a=v as object[];if(a!=null)return a;var b=v as ArrayList;if(b!=null)return b.Cast<object>();throw new InvalidDataException("Invalid catalog array.");}
  static void Text(object value,bool nullable) {if(!(value is string)&&!(nullable&&value==null))throw new InvalidDataException("Catalog text has the wrong JSON type.");}
  static void Integer(object value) {if(!(value is int)&&!(value is long))throw new InvalidDataException("Catalog sizes/schema must be integer JSON values.");}
  void ValidateSchema(object value) {
   var root=Object(value,"catalog");Keys(root,new[]{"schema","releaseId","tool","packs"});Integer(root["schema"]);Text(root["releaseId"],false);var tool=Object(root["tool"],"tool");Keys(tool,new[]{"path","sha256"});Text(tool["path"],false);Text(tool["sha256"],false);
   foreach(object p in Array(root["packs"])) {var pack=Object(p,"pack");Keys(pack,new[]{"id","displayName","englishName","status","fallback","coverage","files"});foreach(string k in new[]{"id","displayName","englishName","status","coverage"})Text(pack[k],false);Text(pack["fallback"],true);foreach(object f in Array(pack["files"])) {var file=Object(f,"file");Keys(file,new[]{"path","sha256","bytes","delta","deltaSha256","deltaBytes"});Text(file["path"],false);Text(file["sha256"],false);Text(file["delta"],true);Text(file["deltaSha256"],true);Integer(file["bytes"]);Integer(file["deltaBytes"]);}}
  }
  static bool Plain(string value,int max) {return !String.IsNullOrWhiteSpace(value)&&value.Length<=max&&!value.Any(c=>Char.IsControl(c));}
  void ValidateCatalog() {
   if(catalog==null||catalog.schema!=1||catalog.releaseId!=CatalogPin.ReleaseId||!Plain(catalog.releaseId,80)||!Regex.IsMatch(catalog.releaseId,"^[A-Za-z0-9._-]{1,80}$",RegexOptions.CultureInvariant)||catalog.tool==null||catalog.tool.path!="tools/xdelta3.exe"||!IsHash(catalog.tool.sha256)||catalog.packs==null||catalog.packs.Length<1||catalog.packs.Length>64)throw new InvalidDataException("Unsupported subtitle catalog.");
   var ids=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
   foreach(var p in catalog.packs) {
    if(p==null||!MenuPolicy.IsPackId(p.id)||!ids.Add(p.id)||!Plain(p.displayName,128)||!Plain(p.englishName,128)||!Plain(p.status,80)||!Plain(p.coverage,2048)||p.files==null||p.files.Length!=3)throw new InvalidDataException("Invalid subtitle pack metadata.");
    for(int i=0;i<3;i++) {
     var f=p.files[i];if(f==null||f.path!=Files[i]||!IsHash(f.sha256)||f.bytes<1||f.bytes>MaxBytes)throw new InvalidDataException("Invalid pack file.");
     if(Same(f.sha256,FoundationHashes[i])) {if(f.bytes!=FoundationBytes[i]||f.delta!=null||f.deltaSha256!=null||f.deltaBytes!=0)throw new InvalidDataException("Identity files cannot carry deltas.");}
     else if(f.delta==null||!Regex.IsMatch(f.delta,"^patches/[A-Za-z0-9._-]+[.]vcdiff$",RegexOptions.CultureInvariant)||!IsHash(f.deltaSha256)||f.deltaBytes<1||f.deltaBytes>MaxBytes)throw new InvalidDataException("Invalid forward delta.");
    }
   }
   foreach(var p in catalog.packs)if(p.fallback!=null&&(!catalog.packs.Any(x=>x.id==p.fallback)||p.fallback==p.id))throw new InvalidDataException("Unknown fallback pack.");
  }
  public static string Hash(byte[] b) {using(var h=SHA256.Create())return Hex(h.ComputeHash(b));}
  public static string HashFile(string p) {using(var h=SHA256.Create())using(var f=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.Read))return Hex(h.ComputeHash(f));}
  static string Hex(byte[] b) {return BitConverter.ToString(b).Replace("-","").ToLowerInvariant();}
  static bool Same(string a,string b) {return String.Equals(a,b,StringComparison.OrdinalIgnoreCase);}
  static bool Equal(byte[] a,byte[] b) {return a==null?b==null:b!=null&&a.SequenceEqual(b);}
  static bool EqualSelection(SelectionBefore a,SelectionBefore b) {return a!=null&&b!=null&&a.HadKey==b.HadKey&&String.Equals(a.OriginalLine,b.OriginalLine,StringComparison.Ordinal);}
  static bool IsHash(string s) {return s!=null&&HashPattern.IsMatch(s);}
  static string B64(byte[] b) {return b==null?null:Convert.ToBase64String(b);}
  static byte[] Un64(string s,int max) {if(s==null)return null;byte[] b=Convert.FromBase64String(s);if(b.Length>max)throw new InvalidDataException("Journal snapshot exceeds its bound.");return b;}
  static void Attr(string p) {if((File.GetAttributes(p)&FileAttributes.ReparsePoint)!=0)throw new IOException("Linked/reparse paths are not supported: "+p);}
  public static void NoReparse(string path,bool directory) {
   string p=Path.GetFullPath(path),volume=Path.GetPathRoot(p);if(String.IsNullOrEmpty(volume)||volume.StartsWith("\\\\",StringComparison.Ordinal))throw new IOException("Use a local drive.");
   string current=volume;Attr(current);foreach(string part in p.Substring(volume.Length).Split(new[]{'\\','/'},StringSplitOptions.RemoveEmptyEntries)){current=Path.Combine(current,part);Attr(current);}
   if(directory?!Directory.Exists(p):!File.Exists(p))throw new FileNotFoundException("Required path is missing: "+p);
  }
  public static string Child(string root,string relative) {
   if(String.IsNullOrEmpty(relative)||Path.IsPathRooted(relative)||relative.IndexOf(':')>=0||relative.Split(new[]{'\\','/'}).Any(x=>x==".."||x=="."||x.Length==0))throw new InvalidDataException("Invalid relative path.");
   string prefix=Path.GetFullPath(root).TrimEnd('\\','/')+Path.DirectorySeparatorChar,p=Path.GetFullPath(Path.Combine(prefix,relative.Replace('/',Path.DirectorySeparatorChar)));
   if(!p.StartsWith(prefix,StringComparison.OrdinalIgnoreCase))throw new IOException("Path escapes its owner.");return p;
  }
  static void GuardAncestor(string path) {string p=Path.GetFullPath(path);while(!Directory.Exists(p)){if(File.Exists(p))throw new IOException("A parent path is a file.");p=Path.GetDirectoryName(p);if(String.IsNullOrEmpty(p))throw new IOException("Invalid parent path.");}NoReparse(p,true);}
  static void MakeDirectory(string path) {if(Directory.Exists(path)){NoReparse(path,true);return;}string parent=Path.GetDirectoryName(path);if(String.IsNullOrEmpty(parent))throw new IOException("Invalid directory.");MakeDirectory(parent);Directory.CreateDirectory(path);NoReparse(path,true);}
  public string ResolveContent(string selected) {if(String.IsNullOrWhiteSpace(selected))throw new ArgumentException("Select the game folder.");string p=Path.GetFullPath(selected);if(p.Length>Path.GetPathRoot(p).Length)p=p.TrimEnd('\\','/');NoReparse(p,true);if(!File.Exists(Path.Combine(p,NativeName)))p=Path.Combine(p,"Content");NoReparse(p,true);return p.Length>Path.GetPathRoot(p).Length?p.TrimEnd('\\','/'):p;}
  public static string RootIdentity(string content) {return Hash(Utf8.GetBytes(Path.GetFullPath(content).TrimEnd('\\','/').ToUpperInvariant()));}
  // Small named seams are replaced only in QA copies; production has no test flags.
  public static string BackupBase() {return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"CrimsonSkiesSubtitlePacks","Backups");}
  public static string SettingsPath() {return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),@"Packages\Xbox360BackwardCompatibil.PrimaryCrimsonSkiesHighR_ksqcvrsvwz2jp\LocalCache\Local\Settings.ini");}
  public static bool ProcessPresent(string name) {Process[] ps=Process.GetProcessesByName(name);try{return ps.Length!=0;}finally{foreach(var p in ps)p.Dispose();}}
  public static void RequireStopped() {if(ProcessPresent("Emu")||ProcessPresent("EmuMenu"))throw new IOException("Close the game and its original launcher first. This tool never closes them.");}
  static void Fault(string phase) { }
  public string ReleaseBackupDirectory(string content) {return Child(Child(Child(BackupBase(),RootIdentity(content)),CatalogPin.ReleaseId),CatalogPin.Digest.ToLowerInvariant());}
  public void LaunchOriginal(string content) {
   RequireStopped();VerifyLauncher(content);string exe=Child(content,"EmuMenu/EmuMenu.exe");NoReparse(exe,false);
   using(Process p=Process.Start(new ProcessStartInfo(exe){UseShellExecute=true,WorkingDirectory=Path.GetDirectoryName(exe)})) {if(p==null)throw new IOException("The original launcher did not start.");}
  }
  void VerifyHost(string content) {
   string path=Child(content,"appxmanifest.xml");NoReparse(path,false);if(new FileInfo(path).Length<1||new FileInfo(path).Length>131072)throw new InvalidDataException("Invalid host identity document.");
   var s=new XmlReaderSettings{DtdProcessing=DtdProcessing.Prohibit,XmlResolver=null,MaxCharactersInDocument=131072,IgnoreComments=true,IgnoreWhitespace=true};bool root=false;int count=0;
   using(var r=XmlReader.Create(path,s))while(r.Read())if(r.NodeType==XmlNodeType.Element) {
    if(!root){if(r.LocalName!="Package"||r.NamespaceURI!=FoundationNamespace)throw new InvalidDataException("Unsupported host manifest.");root=true;}
    if(r.LocalName=="Identity") {count++;if(count!=1||r.Depth!=1||r.NamespaceURI!=FoundationNamespace||r.GetAttribute("Name")!="Xbox360BackwardCompatibil.PrimaryCrimsonSkiesHighR"||r.GetAttribute("Version")!="2608.3123.1.0"||r.GetAttribute("ProcessorArchitecture")!="x64"||r.GetAttribute("Publisher")!="CN=92ADE8CC-2A9A-4DF3-9BAF-18AF498CAA12")throw new InvalidDataException("Unsupported game host build.");}
   }
   if(!root||count!=1)throw new InvalidDataException("Missing host identity.");VerifyHash(Child(content,"VGPUDX12.dll"),GpuHash,6393856L);VerifyLauncher(content);
  }
  void VerifyLauncher(string content) {VerifyHash(Child(content,"EmuMenu/EmuMenu.dll"),MenuDllHash,634880L);VerifyHash(Child(content,"EmuMenu/EmuMenuLaunchArguments.txt"),LaunchDefaultsHash,107L);}
  static void VerifyHash(string path,string hash,long? bytes) {NoReparse(path,false);if((bytes.HasValue&&new FileInfo(path).Length!=bytes.Value)||!Same(HashFile(path),hash))throw new InvalidDataException("File verification failed: "+path);}
  PackDefinition Pack(string id) {var p=catalog.packs.SingleOrDefault(x=>x.id==id);if(p==null)throw new InvalidDataException("Unknown subtitle pack.");return p;}
  void VerifyPayloads() {string tool=Child(packageRoot,catalog.tool.path);NoReparse(tool,false);if(new FileInfo(tool).Length>67108864)throw new InvalidDataException("Invalid delta tool size.");VerifyHash(tool,catalog.tool.sha256,null);foreach(var p in catalog.packs)foreach(var f in p.files)if(f.delta!=null)VerifyHash(Child(packageRoot,f.delta),f.deltaSha256,f.deltaBytes);}
  Snapshot[] Inspect(string content) {return Files.Select(x=>{string p=Child(content,x);NoReparse(p,false);return new Snapshot{path=p,bytes=new FileInfo(p).Length,hash=HashFile(p)};}).ToArray();}
  static bool Matches(Snapshot[] s,string[] hashes,long[] lengths) {return Enumerable.Range(0,4).All(i=>Same(s[i].hash,hashes[i])&&s[i].bytes==lengths[i]);}
  string Original(string folder,int i) {return Child(folder,"base-"+i.ToString(CultureInfo.InvariantCulture)+".bin");}
  byte[] BaseMenu(string content) {string f=Original(ReleaseBackupDirectory(content),3);VerifyHash(f,FoundationHashes[3],FoundationBytes[3]);return File.ReadAllBytes(f);}
  static byte[] ReadMaybe(string path,int max) {GuardAncestor(Path.GetDirectoryName(path));if(Directory.Exists(path))throw new IOException("A file path is a directory.");if(!File.Exists(path))return null;NoReparse(path,false);if(new FileInfo(path).Length>max)throw new InvalidDataException("Snapshot exceeds its size bound.");return File.ReadAllBytes(path);}
  byte[] JsonBytes(object value) {return Utf8.GetBytes(json.Serialize(value));}
  T ReadJson<T>(string path,int max) {byte[] raw=ReadMaybe(path,max);return raw==null?default(T):json.Deserialize<T>(Utf8.GetString(raw));}
  static string Temp(string folder,string prefix) {return Child(folder,prefix+Guid.NewGuid().ToString("N").Substring(0,8)+".tmp");}
  static void DeleteOwned(string path,string owner) {string p=Child(owner,Path.GetFileName(path));if(!Same(p,path))throw new IOException("Cleanup path escapes its owner.");if(File.Exists(p)){NoReparse(p,false);File.Delete(p);}}
  static void VerifyCurrent(string path,byte[] expected,int max) {if(!Equal(ReadMaybe(path,max),expected))throw new IOException("A file changed concurrently: "+path);}
  void AtomicBytes(string path,byte[] expected,byte[] desired,int max) {
   string parent=Path.GetDirectoryName(path);NoReparse(parent,true);VerifyCurrent(path,expected,max);RequireStopped();
   if(desired==null){if(expected!=null){NoReparse(path,false);File.Delete(path);}return;}
   if(desired.Length>max)throw new InvalidDataException("Atomic file exceeds its bound.");string temp=Temp(parent,"w-");
   try {using(var f=new FileStream(temp,FileMode.CreateNew,FileAccess.Write,FileShare.None)){f.Write(desired,0,desired.Length);f.Flush(true);}RequireStopped();VerifyCurrent(path,expected,max);if(expected==null)File.Move(temp,path);else File.Replace(temp,path,null);VerifyCurrent(path,desired,max);}finally{DeleteOwned(temp,parent);}
  }
  void Bound(string root,string release,string digest,string content) {if(!Same(root,content)||release!=CatalogPin.ReleaseId||!Same(digest,CatalogPin.Digest))throw new InvalidDataException("The recovery record belongs to another game/catalog.");}
  void ValidateSelection(SelectionBefore s) {if(s==null||s.HadKey&&(s.OriginalLine==null||s.OriginalLine.Length>65536||s.OriginalLine.IndexOfAny(new[]{'\r','\n','\0','\uFEFF'})>=0)||!s.HadKey&&s.OriginalLine!=null)throw new InvalidDataException("Invalid original language preference.");if(s.HadKey&&!LanguageSettings.Capture(Utf8.GetBytes(s.OriginalLine)).HadKey)throw new InvalidDataException("Original preference is not a language setting.");}
  PackReceipt ReadReceipt(string content,byte[] raw) {
   if(raw==null)return null;var r=json.Deserialize<PackReceipt>(Utf8.GetString(raw));if(r==null||r.schema!=1||(r.state!="active"&&r.state!="restored"))throw new InvalidDataException("Invalid subtitle receipt.");Bound(r.root,r.releaseId,r.catalogSha256,content);ValidateSelection(r.originalGameLanguage);if(r.state=="active")Pack(r.activePackId);else if(r.activePackId!=null)throw new InvalidDataException("Restored receipt names an active pack.");return r;
  }
  void Expected(string content,PackReceipt r,out string[] hashes,out long[] lengths) {
   hashes=FoundationHashes.ToArray();lengths=FoundationBytes.ToArray();if(r==null||r.state=="restored")return;var p=Pack(r.activePackId);
   for(int i=0;i<3;i++){hashes[i]=p.files[i].sha256;lengths[i]=p.files[i].bytes;}byte[] menu=MenuPolicy.BuildMenu(BaseMenu(content),catalog,p.id);hashes[3]=Hash(menu);lengths[3]=menu.Length;
  }
  void ValidateBase(string content,bool required) {
   string dir=ReleaseBackupDirectory(content);GuardAncestor(dir);if(!Directory.Exists(dir)){if(required)throw new IOException("Subtitle base backup is missing.");return;}NoReparse(dir,true);
   var m=ReadJson<BaseMetadata>(Child(dir,"base.json"),65536);if(m!=null){Bound(m.root,m.releaseId,m.catalogSha256,content);if(m.schema!=1||m.hashes==null||!m.hashes.SequenceEqual(FoundationHashes,StringComparer.OrdinalIgnoreCase))throw new InvalidDataException("Invalid base backup metadata.");}else if(required)throw new IOException("Base backup identity is missing.");
   for(int i=0;i<4;i++){string p=Original(dir,i);if(File.Exists(p))VerifyHash(p,FoundationHashes[i],FoundationBytes[i]);else if(required)throw new IOException("A base backup is missing.");}
  }
  void PrepareBase(string content,Snapshot[] current) {
   if(!Matches(current,FoundationHashes,FoundationBytes))throw new InvalidDataException("Install the canonical 0.11 Korean/widescreen patch before adding subtitle packs.");ValidateBase(content,false);string dir=ReleaseBackupDirectory(content);MakeDirectory(dir);
   for(int i=0;i<4;i++){string p=Original(dir,i);if(File.Exists(p))continue;string temp=Temp(dir,"b-");try{File.Copy(current[i].path,temp,false);VerifyHash(temp,FoundationHashes[i],FoundationBytes[i]);RequireStopped();VerifyHash(current[i].path,current[i].hash,current[i].bytes);File.Move(temp,p);}finally{DeleteOwned(temp,dir);}}
   string meta=Child(dir,"base.json");if(!File.Exists(meta))AtomicBytes(meta,null,JsonBytes(new BaseMetadata{schema=1,releaseId=CatalogPin.ReleaseId,root=content,catalogSha256=CatalogPin.Digest,hashes=FoundationHashes.ToArray()}),65536);ValidateBase(content,true);
  }
  void Decode(string source,PackFileDefinition file,string output) {
   string tool=Child(packageRoot,catalog.tool.path),delta=Child(packageRoot,file.delta);VerifyHash(tool,catalog.tool.sha256,null);VerifyHash(delta,file.deltaSha256,file.deltaBytes);
   var s=new ProcessStartInfo(tool,"-d -D -R -s "+Quote(source)+" "+Quote(delta)+" "+Quote(output)){UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden,RedirectStandardOutput=true,RedirectStandardError=true,WorkingDirectory=packageRoot};s.EnvironmentVariables.Remove("XDELTA");
   using(Process p=Process.Start(s)){Task<string> o=p.StandardOutput.ReadToEndAsync(),e=p.StandardError.ReadToEndAsync();if(!p.WaitForExit(180000)){try{p.Kill();}catch{}throw new IOException("Delta decoding timed out before the game files were changed.");}Task.WaitAll(o,e);if(p.ExitCode!=0)throw new InvalidDataException("Delta decoding failed: "+e.Result+o.Result);}
  }
  static string Quote(string s) {if(s.IndexOfAny(new[]{'"','\r','\n'})>=0)throw new ArgumentException("Invalid command path.");return "\""+s.TrimEnd('\\')+"\"";}
  void CleanupStage(string content,string stageName) {
   if(stageName==null||!Regex.IsMatch(stageName,"^[.]csmulti-[0-9a-f]{8}$",RegexOptions.CultureInvariant))throw new InvalidDataException("Invalid owned staging name.");string stage=Child(content,stageName);if(!Directory.Exists(stage))return;NoReparse(stage,true);
   for(int i=0;i<4;i++)foreach(string prefix in new[]{"ready-","undo-","back-"})DeleteOwned(Child(stage,prefix+i+".bin"),stage);
   try{Directory.Delete(stage,false);}catch(IOException){log("Staging cleanup left unrelated files untouched: "+stage);}
  }
  void TryCleanupStage(string content,string stageName) {try{CleanupStage(content,stageName);}catch(Exception e){log("Staging cleanup deferred: "+e.Message);}}
  SwitchJournal ValidateJournal(string content,byte[] raw) {
   if(raw==null)return null;var j=json.Deserialize<SwitchJournal>(Utf8.GetString(raw));if(j==null||j.schema!=1||(j.mode!="--activate"&&j.mode!="--restore"))throw new InvalidDataException("Invalid write-ahead journal.");Bound(j.root,j.releaseId,j.catalogSha256,content);
   if(j.stage==null||!Regex.IsMatch(j.stage,"^[.]csmulti-[0-9a-f]{8}$",RegexOptions.CultureInvariant)||j.settingsPath!=SettingsPath())throw new InvalidDataException("Journal path mismatch.");ValidateSelection(j.selectionBefore);
   var before=ReadReceipt(content,Un64(j.beforeReceipt,262144));var after=ReadReceipt(content,Un64(j.afterReceipt,262144));if(after==null)throw new InvalidDataException("Missing target receipt.");
   if((j.mode=="--activate"&&(after.state!="active"||after.activePackId!=j.targetPackId))||(j.mode=="--restore"&&(after.state!="restored"||j.targetPackId!=null)))throw new InvalidDataException("Journal target mismatch.");
   string[] bh,th;long[] bl,tl;Expected(content,before,out bh,out bl);Expected(content,after,out th,out tl);
   if(j.beforeHashes==null||j.targetHashes==null||j.beforeBytes==null||j.targetBytes==null||!j.beforeHashes.SequenceEqual(bh,StringComparer.OrdinalIgnoreCase)||!j.targetHashes.SequenceEqual(th,StringComparer.OrdinalIgnoreCase)||!j.beforeBytes.SequenceEqual(bl)||!j.targetBytes.SequenceEqual(tl))throw new InvalidDataException("Journal file profiles are not owned catalog profiles.");
   byte[] settingsBefore=Un64(j.beforeSettings,65536),settingsAfter=Un64(j.afterSettings,65536);
   SelectionBefore captured=LanguageSettings.Capture(settingsBefore);
   if(!EqualSelection(captured,j.selectionBefore))throw new InvalidDataException("Journal original selector does not match its before snapshot.");
   if(j.mode=="--restore"&&before==null)throw new InvalidDataException("A restore journal has no owned previous receipt.");
   SettingsPlan plan=j.mode=="--activate"?LanguageSettings.Prepare(settingsBefore,j.targetPackId):LanguageSettings.PrepareRestore(settingsBefore,before.originalGameLanguage,catalog.packs.Select(x=>x.id));
   if(!Equal(plan.AfterBytes,settingsAfter)||!EqualSelection(plan.OriginalGameLanguage,j.selectionBefore))throw new InvalidDataException("Journal changes settings outside the allowed language transition.");
   SelectionBefore expectedOriginal=j.mode=="--activate"&&(before==null||before.state=="restored")?captured:before.originalGameLanguage;
   if(!EqualSelection(after.originalGameLanguage,expectedOriginal))throw new InvalidDataException("Journal changes the saved original language preference.");
   return j;
  }
  void ValidateRecoveryFiles(string content,SwitchJournal j) {
   ValidateBase(content,true);Snapshot[] states=Inspect(content);string stage=Child(content,j.stage);NoReparse(stage,true);
   for(int i=0;i<4;i++){if(!((Same(states[i].hash,j.beforeHashes[i])&&states[i].bytes==j.beforeBytes[i])||(Same(states[i].hash,j.targetHashes[i])&&states[i].bytes==j.targetBytes[i])))throw new InvalidDataException("An interrupted switch contains an unknown game file. Nothing was overwritten.");VerifyHash(Child(stage,"undo-"+i+".bin"),j.beforeHashes[i],j.beforeBytes[i]);}
   byte[] receipt=ReadMaybe(Child(ReleaseBackupDirectory(content),"receipt.json"),262144);if(!Equal(receipt,Un64(j.beforeReceipt,262144))&&!Equal(receipt,Un64(j.afterReceipt,262144)))throw new InvalidDataException("The active receipt changed outside this transaction.");
  }
  void RollbackSettings(SwitchJournal j) {
   byte[] before=Un64(j.beforeSettings,65536),after=Un64(j.afterSettings,65536);if(Equal(before,after))return;
   byte[] current=ReadMaybe(j.settingsPath,65536);var plan=new SettingsPlan{Path=j.settingsPath,BeforeBytes=before,AfterBytes=after,OriginalGameLanguage=j.selectionBefore};
   byte[] back=LanguageSettings.RollbackBytes(current,plan,j.targetPackId);if(!Equal(current,back))AtomicBytes(j.settingsPath,current,back,65536);
  }
  void Recover(string content,SwitchJournal j,byte[] journalRaw) {
   ValidateRecoveryFiles(content,j);RequireStopped();string dir=ReleaseBackupDirectory(content),stage=Child(content,j.stage);
   for(int i=3;i>=0;i--){var s=Inspect(content);if(Same(s[i].hash,j.beforeHashes[i])&&s[i].bytes==j.beforeBytes[i])continue;RequireStopped();string back=Child(stage,"back-"+i+".bin");DeleteOwned(back,stage);File.Copy(Child(stage,"undo-"+i+".bin"),back,false);VerifyHash(back,j.beforeHashes[i],j.beforeBytes[i]);VerifyHash(s[i].path,j.targetHashes[i],j.targetBytes[i]);File.Replace(back,s[i].path,null);VerifyHash(s[i].path,j.beforeHashes[i],j.beforeBytes[i]);}
   RollbackSettings(j);string receiptPath=Child(dir,"receipt.json");byte[] current=ReadMaybe(receiptPath,262144),before=Un64(j.beforeReceipt,262144);if(!Equal(current,before))AtomicBytes(receiptPath,current,before,262144);
   if(!Matches(Inspect(content),j.beforeHashes,j.beforeBytes))throw new IOException("Recovery verification did not complete.");AtomicBytes(Child(dir,"journal.json"),journalRaw,null,2097152);TryCleanupStage(content,j.stage);log("Recovered the interrupted switch to its previous coherent selection.");
  }
  public void Run(string mode,string selected,string packId,bool openOriginal=false) {
   if(mode!="--check"&&mode!="--activate"&&mode!="--restore")throw new ArgumentException("Unsupported mode.");if(mode=="--activate")Pack(packId);else if(openOriginal)throw new ArgumentException("Only explicit activation may open the original launcher.");string content=ResolveContent(selected);
   if(mode=="--check"){RunCore(mode,content,packId,false);return;}
   using(var mutex=new Mutex(false,"Local\\CrimsonSkies-KoreanPatch-"+RootIdentity(content))) {bool held=false;try{try{held=mutex.WaitOne(0);}catch(AbandonedMutexException){held=true;}if(!held)throw new IOException("Another patch transaction is using this game folder.");RunCore(mode,content,packId,openOriginal);}finally{if(held)mutex.ReleaseMutex();}}
  }
  void RunCore(string mode,string content,string packId,bool openOriginal) {
   VerifyHost(content);VerifyPayloads();if(mode!="--check")RequireStopped();string dir=ReleaseBackupDirectory(content);GuardAncestor(dir);
   byte[] journalRaw=ReadMaybe(Child(dir,"journal.json"),2097152);SwitchJournal pending=ValidateJournal(content,journalRaw);
   if(pending!=null) {ValidateRecoveryFiles(content,pending);if(mode=="--check"){log("An owned interrupted switch is recoverable. Check made no changes.");return;}Recover(content,pending,journalRaw);if(mode=="--restore"&&pending.beforeReceipt==null){log("Restored the canonical 0.11 foundation from the interrupted first activation.");return;}}
   Snapshot[] current=Inspect(content);byte[] receiptRaw=ReadMaybe(Child(dir,"receipt.json"),262144);PackReceipt receipt=ReadReceipt(content,receiptRaw);if(receipt!=null)ValidateBase(content,true);
   string[] expected;long[] expectedBytes;Expected(content,receipt,out expected,out expectedBytes);if(!Matches(current,expected,expectedBytes))throw new InvalidDataException("The game is not the canonical 0.11 foundation or this launcher's coherent active pack. No unknown files were overwritten.");
   if(mode=="--check"){if(receipt==null)ValidateBase(content,false);log(receipt!=null&&receipt.state=="active"?"Active subtitle pack: "+receipt.activePackId:"Canonical 0.11 foundation is ready.");if(ProcessPresent("Emu")||ProcessPresent("EmuMenu"))log("The game or launcher is running; this was a read-only check.");return;}
   if(mode=="--restore"&&receipt==null)throw new InvalidDataException("This launcher has no owned subtitle-switch receipt to restore.");
   string settings=SettingsPath();byte[] settingsBefore=ReadMaybe(settings,65536);SettingsPlan plan=mode=="--activate"?LanguageSettings.Prepare(settingsBefore,packId):LanguageSettings.PrepareRestore(settingsBefore,receipt.originalGameLanguage,catalog.packs.Select(x=>x.id));plan.Path=settings;
   SelectionBefore original=mode=="--activate"&&(receipt==null||receipt.state=="restored")?LanguageSettings.Capture(settingsBefore):receipt.originalGameLanguage;ValidateSelection(original);
   if(mode=="--activate"&&receipt!=null&&receipt.state=="active"&&receipt.activePackId==packId&&!plan.Changed) {RequireStopped();VerifyCurrent(settings,settingsBefore,65536);if(openOriginal)LaunchOriginal(content);log("Subtitle pack is already active: "+packId);return;}
   if(receipt==null)PrepareBase(content,current);else ValidateBase(content,true);
   var afterReceipt=new PackReceipt{schema=1,releaseId=CatalogPin.ReleaseId,root=content,catalogSha256=CatalogPin.Digest,state=mode=="--activate"?"active":"restored",activePackId=mode=="--activate"?packId:null,createdUtc=receipt==null?DateTime.UtcNow.ToString("o"):receipt.createdUtc,originalGameLanguage=original};
   string[] target;long[] targetBytes;Expected(content,afterReceipt,out target,out targetBytes);
   string stageName=".csmulti-"+Guid.NewGuid().ToString("N").Substring(0,8),stage=Child(content,stageName);if(Directory.Exists(stage)||File.Exists(stage))throw new IOException("Staging folder already exists.");Directory.CreateDirectory(stage);NoReparse(stage,true);
   SwitchJournal j=null;bool journalWritten=false;
   try {
    for(int i=0;i<4;i++) {
     RequireStopped();string ready=Child(stage,"ready-"+i+".bin");
     if(i==3)File.WriteAllBytes(ready,mode=="--activate"?MenuPolicy.BuildMenu(BaseMenu(content),catalog,packId):BaseMenu(content));
     else {var f=mode=="--activate"?Pack(packId).files[i]:null;if(f==null||f.delta==null)File.Copy(Original(dir,i),ready,false);else Decode(Original(dir,i),f,ready);}
     VerifyHash(ready,target[i],targetBytes[i]);string undo=Child(stage,"undo-"+i+".bin");File.Copy(current[i].path,undo,false);VerifyHash(undo,current[i].hash,current[i].bytes);
    }
    RequireStopped();foreach(var s in current)VerifyHash(s.path,s.hash,s.bytes);VerifyCurrent(settings,settingsBefore,65536);VerifyCurrent(Child(dir,"receipt.json"),receiptRaw,262144);Fault("before-journal");
    j=new SwitchJournal{schema=1,releaseId=CatalogPin.ReleaseId,root=content,catalogSha256=CatalogPin.Digest,stage=stageName,targetPackId=mode=="--activate"?packId:null,mode=mode,settingsPath=settings,beforeReceipt=B64(receiptRaw),afterReceipt=B64(JsonBytes(afterReceipt)),beforeSettings=B64(settingsBefore),afterSettings=B64(plan.AfterBytes),selectionBefore=plan.OriginalGameLanguage,beforeHashes=current.Select(x=>x.hash).ToArray(),beforeBytes=current.Select(x=>x.bytes).ToArray(),targetHashes=target,targetBytes=targetBytes};
    journalRaw=JsonBytes(j);AtomicBytes(Child(dir,"journal.json"),null,journalRaw,2097152);journalWritten=true;Fault("after-journal");
    for(int i=0;i<4;i++) {RequireStopped();VerifyHash(current[i].path,current[i].hash,current[i].bytes);if(!Same(current[i].hash,target[i])||current[i].bytes!=targetBytes[i])File.Replace(Child(stage,"ready-"+i+".bin"),current[i].path,null);VerifyHash(current[i].path,target[i],targetBytes[i]);Fault("after-commit-"+i);}
    if(plan.Changed)AtomicBytes(settings,settingsBefore,plan.AfterBytes,65536);Fault("after-settings");
    if(!Matches(Inspect(content),target,targetBytes))throw new IOException("Coherent target verification failed.");AtomicBytes(Child(dir,"receipt.json"),receiptRaw,Un64(j.afterReceipt,262144),262144);Fault("after-receipt");
    if(openOriginal){Fault("before-launch");LaunchOriginal(content);}
    // A successful launch starts only after the coherent commit; cleanup touches
    // our local journal/staging, never running game files or Settings.ini.
    if(openOriginal){string journal=Child(dir,"journal.json");VerifyCurrent(journal,journalRaw,2097152);NoReparse(journal,false);File.Delete(journal);}else AtomicBytes(Child(dir,"journal.json"),journalRaw,null,2097152);
    journalWritten=false;TryCleanupStage(content,stageName);log(mode=="--activate"?"Subtitle pack activated: "+packId:"Restored the canonical 0.11 foundation.");
   } catch(Exception error) {
    if(journalWritten)try{RequireStopped();Recover(content,j,journalRaw);journalWritten=false;}catch(Exception recovery){throw new IOException("The switch could not be fully rolled back. Close the game/launcher and run this tool again. Owned recovery journal: "+Child(dir,"journal.json")+"\r\nOriginal: "+error.Message+"\r\nRecovery: "+recovery.Message,error);}
    throw;
   } finally {if(!journalWritten)TryCleanupStage(content,stageName);}
  }
 }
}
