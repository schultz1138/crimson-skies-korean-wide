// SPDX-License-Identifier: MIT
// Caption-only sparse switching on the accepted FullDubBeta1 baseline.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Web.Script.Serialization;

namespace CrimsonSkiesMultilingual {
 public sealed class CaptionFile { public string path,baselineSha256; public long bytes; }
 public sealed class CaptionGuard { public string path,sha256; public long bytes; }
 public sealed class CaptionSpan { public int fileIndex,bytes; public long offset; }
 public sealed class CaptionPayload { public string path,sha256; public long bytes; }
 public sealed class CaptionStyle { public string id,displayName,coverage; public string[] hashes,spanHashes; public CaptionPayload payload; }
 public sealed class CaptionCatalog { public int schema; public string releaseId,baselineId,baselineStyleId; public CaptionFile[] files; public CaptionGuard[] guards; public CaptionSpan[] spans; public CaptionStyle[] styles; }
 sealed class CaptionReceipt { public int schema; public string root,catalogSha256,baselineId,styleId; }
 sealed class CaptionJournal { public int schema; public string root,catalogSha256,transaction,beforeStyle,targetStyle,beforeReceipt,undoSha256; }

 public sealed class CaptionSpanEngine {
  const int Chunk=1024*1024,MaxJson=8*1024*1024;
  const long MaxPayload=128L*1024*1024;
  static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
  static readonly string[] AllowedFiles={PackEngine.NativeName,"Game/DefaultPackage.data/Data0000","Game/DefaultPackage.data/Data0005"};
  readonly string packageRoot,stateBase,catalogHash; readonly Action<string> log,launch,fault; readonly Action stopped;
  readonly JavaScriptSerializer json=new JavaScriptSerializer{MaxJsonLength=MaxJson,RecursionLimit=32};
  readonly CaptionCatalog catalog; readonly long[] payloadAt;
  public CaptionCatalog Catalog {get{return catalog;}}
  public static string DefaultGameRoot {get{return @"C:\XboxGames\Crimson Skies- High Road to Revenge\Content";}}
  public static string DefaultStateBase {get{return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"CrimsonSkiesSubtitlePacks","Backups");}}
  public CaptionSpanEngine(string packageDir,Action<string> logger,Action<string> launchOriginal)
   :this(packageDir,CaptionCatalogPin.Digest,DefaultStateBase,logger,launchOriginal,PackEngine.RequireStopped,delegate{}){}
  // API-only fixture seam. The production UI/CLI supplies no override arguments.
  internal CaptionSpanEngine(string packageDir,string pinnedCatalog,string backupBase,Action<string> logger,Action<string> launchOriginal,Action requireStopped,Action<string> faultHook) {
   packageRoot=Path.GetFullPath(packageDir);PackEngine.NoReparse(packageRoot,true);catalogHash=pinnedCatalog;
   stateBase=Path.GetFullPath(backupBase);log=logger??delegate{};launch=launchOriginal??delegate{};stopped=requireStopped??PackEngine.RequireStopped;fault=faultHook??delegate{};
   string p=PackEngine.Child(packageRoot,"dub-caption-catalog.json");PackEngine.NoReparse(p,false);byte[] raw=ReadSmall(p,MaxJson);
   Need(IsHash(catalogHash)&&Hash(raw)==catalogHash,"The caption catalog does not match this launcher.");
   ValidateSchema(json.DeserializeObject(Utf8.GetString(raw)));catalog=json.Deserialize<CaptionCatalog>(Utf8.GetString(raw));
   Need(catalog.schema==1&&catalog.baselineId=="FullDubBeta1"&&catalog.baselineStyleId=="ko-KR"&&Plain(catalog.releaseId,80),"Unsupported caption baseline.");
   Need(catalog.files!=null&&catalog.files.Length==3&&catalog.guards!=null&&catalog.guards.Length>=2&&catalog.guards.Length<=64,"Invalid caption file/guard set.");
   for(int i=0;i<3;i++)Need(catalog.files[i]!=null&&catalog.files[i].path==AllowedFiles[i]&&catalog.files[i].bytes>0&&catalog.files[i].bytes<=8589934592L&&IsHash(catalog.files[i].baselineSha256),"Invalid caption source file.");
   var names=new HashSet<string>(AllowedFiles,StringComparer.OrdinalIgnoreCase);
   foreach(var g in catalog.guards)Need(g!=null&&names.Add(g.path)&&SafeRelative(g.path)&&g.bytes>0&&IsHash(g.sha256),"Invalid or overlapping read-only guard.");
   Need(catalog.guards.Any(g=>g.path=="Game/DefaultPackage")&&catalog.guards.Any(g=>g.path=="appxmanifest.xml"),"Header and package manifest guards are required.");
   Need(catalog.spans!=null&&catalog.spans.Length>0&&catalog.spans.Length<=32768,"Invalid owned span count.");
   payloadAt=new long[catalog.spans.Length];long total=0;int priorFile=-1;long priorEnd=0;
   for(int i=0;i<catalog.spans.Length;i++) {var s=catalog.spans[i];Need(s!=null&&s.fileIndex>=0&&s.fileIndex<3&&s.bytes>0&&s.bytes<=Chunk&&s.offset>=0&&s.offset<=catalog.files[s.fileIndex].bytes-s.bytes,"Owned caption span escapes its exact file extent.");Need(s.fileIndex>priorFile||s.fileIndex==priorFile&&s.offset>=priorEnd,"Owned caption spans overlap or are unsorted.");priorFile=s.fileIndex;priorEnd=s.offset+s.bytes;payloadAt[i]=total;total=checked(total+s.bytes);}
   Need(total<=MaxPayload,"Caption payload exceeds the bounded sparse size.");
   Need(catalog.styles!=null&&catalog.styles.Length>=2&&catalog.styles.Length<=64,"Invalid caption style count.");var ids=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
   foreach(var s in catalog.styles) {Need(s!=null&&MenuPolicy.IsPackId(s.id)&&ids.Add(s.id)&&Plain(s.displayName,128)&&Plain(s.coverage,4096)&&s.hashes!=null&&s.hashes.Length==3&&s.hashes.All(IsHash)&&s.spanHashes!=null&&s.spanHashes.Length==catalog.spans.Length&&s.spanHashes.All(IsHash)&&s.payload!=null&&SafeRelative(s.payload.path)&&s.payload.bytes==total&&IsHash(s.payload.sha256),"Invalid caption style payload metadata.");}
   Need(ids.Contains("ko-KR")&&ids.Contains("ko-KR-dub"),"Both original and spoken-dub Korean styles are required.");
   Need(catalog.styles.Select(s=>String.Join(":",s.hashes)).Distinct(StringComparer.Ordinal).Count()==catalog.styles.Length,"Caption styles must have distinct coherent whole-file states.");
   Need(Style("ko-KR").hashes.SequenceEqual(catalog.files.Select(f=>f.baselineSha256)),"Original Korean style must be the exact full-dub baseline.");
   for(int f=0;f<3;f++)if(!catalog.spans.Any(s=>s.fileIndex==f))Need(catalog.styles.All(s=>s.hashes[f]==catalog.files[f].baselineSha256),"A nonowned file cannot change between styles.");
  }
  static void Need(bool ok,string message){if(!ok)throw new InvalidDataException(message);}
  static bool IsHash(string s){return s!=null&&Regex.IsMatch(s,"^[0-9a-f]{64}$");}
  static bool Plain(string s,int max){return !String.IsNullOrWhiteSpace(s)&&s.Length<=max&&!s.Any(Char.IsControl);}
  static bool SafeRelative(string p){return !String.IsNullOrEmpty(p)&&!Path.IsPathRooted(p)&&p.IndexOf(':')<0&&p.Split(new[]{'\\','/'}).All(x=>x.Length>0&&x!="."&&x!="..");}
  static string Hash(byte[] raw){using(var h=SHA256.Create())return Hex(h.ComputeHash(raw));}
  static string Hex(byte[] b){return BitConverter.ToString(b).Replace("-","").ToLowerInvariant();}
  static string HashStream(Stream s){s.Position=0;using(var h=SHA256.Create()){byte[] b=new byte[Chunk];int n;while((n=s.Read(b,0,b.Length))>0)h.TransformBlock(b,0,n,b,0);h.TransformFinalBlock(new byte[0],0,0);return Hex(h.Hash);}}
  static byte[] ReadAt(Stream s,long at,int n){byte[] b=new byte[n];s.Position=at;int done=0;while(done<n){int got=s.Read(b,done,n-done);if(got==0)throw new EndOfStreamException("Short owned span read.");done+=got;}return b;}
  static byte[] ReadSmall(string path,int max){PackEngine.NoReparse(path,false);Need(new FileInfo(path).Length<=max,"Metadata exceeds its bound.");return File.ReadAllBytes(path);}
  static bool Equal(byte[] a,byte[] b){return a==null?b==null:b!=null&&a.SequenceEqual(b);}
  static IDictionary<string,object> Obj(object x){var d=x as IDictionary<string,object>;Need(d!=null,"Expected JSON object.");return d;}
  static IEnumerable<object> Arr(object x){var a=x as object[];if(a!=null)return a;var b=x as ArrayList;Need(b!=null,"Expected JSON array.");return b.Cast<object>();}
  static void Keys(object x,params string[] keys){var d=Obj(x);Need(d.Count==keys.Length&&d.Keys.All(k=>keys.Contains(k)),"Unknown/missing caption catalog or state fields.");}
  static void Integer(object x){Need(x is int||x is long,"Expected integer JSON field.");}
  static void Text(object x){Need(x is string,"Expected string JSON field.");}
  static void Typed(object x,string[] text,string[] integer){var d=Obj(x);foreach(var k in text)Text(d[k]);foreach(var k in integer)Integer(d[k]);}
  static void ValidateSchema(object x){
   Keys(x,"schema","releaseId","baselineId","baselineStyleId","files","guards","spans","styles");var d=Obj(x);Typed(x,new[]{"releaseId","baselineId","baselineStyleId"},new[]{"schema"});
   foreach(var f in Arr(d["files"])){Keys(f,"path","bytes","baselineSha256");Typed(f,new[]{"path","baselineSha256"},new[]{"bytes"});}
   foreach(var g in Arr(d["guards"])){Keys(g,"path","bytes","sha256");Typed(g,new[]{"path","sha256"},new[]{"bytes"});}
   foreach(var s in Arr(d["spans"])){Keys(s,"fileIndex","offset","bytes");Typed(s,new string[0],new[]{"fileIndex","offset","bytes"});}
   foreach(var s in Arr(d["styles"])){Keys(s,"id","displayName","coverage","hashes","payload","spanHashes");Typed(s,new[]{"id","displayName","coverage"},new string[0]);var sd=Obj(s);foreach(var v in Arr(sd["hashes"]))Text(v);foreach(var v in Arr(sd["spanHashes"]))Text(v);Keys(sd["payload"],"path","bytes","sha256");Typed(sd["payload"],new[]{"path","sha256"},new[]{"bytes"});}
  }
  public bool HasStyle(string id){return catalog.styles.Any(s=>s.id==id);}
  CaptionStyle Style(string id){var s=catalog.styles.SingleOrDefault(x=>x.id==id);Need(s!=null,"Unknown caption style.");return s;}
  string StateRoot(string content){return PackEngine.Child(PackEngine.Child(stateBase,PackEngine.RootIdentity(content)),catalogHash);}
  static void GuardParent(string path){string p=Path.GetFullPath(path);while(!Directory.Exists(p)){Need(!File.Exists(p),"A state parent is a file.");p=Path.GetDirectoryName(p);Need(p!=null,"Invalid state path.");}PackEngine.NoReparse(p,true);}
  static void Mkdir(string path){GuardParent(path);if(!Directory.Exists(path))Directory.CreateDirectory(path);PackEngine.NoReparse(path,true);}
  static byte[] Maybe(string path,int max){GuardParent(Path.GetDirectoryName(path));Need(!Directory.Exists(path),"Expected metadata file is a directory.");return File.Exists(path)?ReadSmall(path,max):null;}
  byte[] Encode(object value){return Utf8.GetBytes(json.Serialize(value)+"\n");}
  void Atomic(string path,byte[] before,byte[] after){Need(Equal(Maybe(path,MaxJson),before),"State metadata changed unexpectedly.");Mkdir(Path.GetDirectoryName(path));string temp=path+"."+Guid.NewGuid().ToString("N")+".tmp";using(var f=new FileStream(temp,FileMode.CreateNew,FileAccess.Write,FileShare.None)){f.Write(after,0,after.Length);f.Flush(true);}Need(Equal(ReadSmall(temp,MaxJson),after),"Durable metadata readback failed.");Need(Equal(Maybe(path,MaxJson),before),"State changed before atomic commit.");if(before==null)File.Move(temp,path);else File.Replace(temp,path,null);Need(Equal(ReadSmall(path,MaxJson),after),"Metadata commit verification failed.");}
  void DeleteExact(string path,byte[] expected){Need(Equal(Maybe(path,MaxJson),expected),"Unknown state cannot be removed.");PackEngine.NoReparse(path,false);File.Delete(path);}
  string Resolve(string selected){Need(!String.IsNullOrWhiteSpace(selected),"Select the game folder.");string p=Path.GetFullPath(selected);PackEngine.NoReparse(p,true);if(!File.Exists(Path.Combine(p,AllowedFiles[0])))p=Path.Combine(p,"Content");PackEngine.NoReparse(p,true);return p.TrimEnd('\\','/');}
  void StateOutsideContent(string content){string a=Path.GetFullPath(stateBase).TrimEnd('\\','/')+Path.DirectorySeparatorChar,b=Path.GetFullPath(content).TrimEnd('\\','/')+Path.DirectorySeparatorChar;Need(!a.StartsWith(b,StringComparison.OrdinalIgnoreCase)&&!b.StartsWith(a,StringComparison.OrdinalIgnoreCase),"Caption backups must be outside game Content.");Need(a.IndexOf(@"\Packages\",StringComparison.OrdinalIgnoreCase)<0,"Caption backups must remain outside the MSIX app cache.");GuardParent(stateBase);}
  FileStream Payload(CaptionStyle s){string p=PackEngine.Child(packageRoot,s.payload.path);PackEngine.NoReparse(p,false);var f=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.Read);try{Need(f.Length==s.payload.bytes&&HashStream(f)==s.payload.sha256,"Caption payload pin differs.");for(int i=0;i<catalog.spans.Length;i++)Need(Hash(ReadAt(f,payloadAt[i],catalog.spans[i].bytes))==s.spanHashes[i],"Caption span payload pin differs.");return f;}catch{f.Dispose();throw;}}
  CaptionReceipt Receipt(string root,byte[] raw){if(raw==null)return null;object value=json.DeserializeObject(Utf8.GetString(raw));Keys(value,"schema","root","catalogSha256","baselineId","styleId");Typed(value,new[]{"root","catalogSha256","baselineId","styleId"},new[]{"schema"});var r=json.Deserialize<CaptionReceipt>(Utf8.GetString(raw));Need(r.schema==1&&String.Equals(r.root,root,StringComparison.OrdinalIgnoreCase)&&r.catalogSha256==catalogHash&&r.baselineId==catalog.baselineId&&HasStyle(r.styleId),"Caption receipt ownership differs.");return r;}
  CaptionReceipt NewReceipt(string root,string style){return new CaptionReceipt{schema=1,root=root,catalogSha256=catalogHash,baselineId=catalog.baselineId,styleId=style};}
  string Detect(FileStream[] fs){var hashes=fs.Select(HashStream).ToArray();var matches=catalog.styles.Where(s=>s.hashes.SequenceEqual(hashes)).ToArray();Need(matches.Length>=1,"Unknown/noncoherent bytes: no caption or audio bytes were overwritten.");return matches[0].id;}
  void VerifyHashes(FileStream[] fs,string style){Need(fs.Select(HashStream).SequenceEqual(Style(style).hashes),"Whole-file caption/audio preservation verification failed.");}
  void OverlayHashes(FileStream[] fs,Stream payload,string style){
   for(int f=0;f<fs.Length;f++)using(var h=SHA256.Create()){long at=0;byte[] buffer=new byte[Chunk];while(at<fs[f].Length){int n=(int)Math.Min(Chunk,fs[f].Length-at);buffer=ReadAt(fs[f],at,n);for(int i=0;i<catalog.spans.Length;i++){var s=catalog.spans[i];if(s.fileIndex!=f)continue;long a=Math.Max(at,s.offset),b=Math.Min(at+n,s.offset+s.bytes);if(a<b){byte[] p=ReadAt(payload,payloadAt[i]+a-s.offset,(int)(b-a));Buffer.BlockCopy(p,0,buffer,(int)(a-at),p.Length);}}h.TransformBlock(buffer,0,n,buffer,0);at+=n;}h.TransformFinalBlock(new byte[0],0,0);Need(Hex(h.Hash)==Style(style).hashes[f],"Owned overlay cannot reproduce the known whole-file state; unknown nonowned bytes or an invalid ownership mask.");}
  }
  void WriteSpans(FileStream[] fs,Stream payload,bool hooks){for(int i=0;i<catalog.spans.Length;i++){var s=catalog.spans[i];byte[] b=ReadAt(payload,payloadAt[i],s.bytes);fs[s.fileIndex].Position=s.offset;fs[s.fileIndex].Write(b,0,b.Length);fs[s.fileIndex].Flush(true);if(hooks)fault("after-span-"+i);}}
  void Snapshot(FileStream[] fs,string path,CaptionStyle expected){using(var f=new FileStream(path,FileMode.CreateNew,FileAccess.ReadWrite,FileShare.None)){foreach(var s in catalog.spans){byte[] b=ReadAt(fs[s.fileIndex],s.offset,s.bytes);f.Write(b,0,b.Length);}f.Flush(true);Need(f.Length==expected.payload.bytes&&HashStream(f)==expected.payload.sha256,"Sparse backup does not match the coherent current caption state.");}using(var f=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read))Need(HashStream(f)==expected.payload.sha256,"Sparse backup durable readback failed.");}
  void ValidateBase(string content,bool required){string dir=StateRoot(content),p=PackEngine.Child(dir,"baseline.bin"),m=PackEngine.Child(dir,"base.json");byte[] metadata=Maybe(m,MaxJson);if(metadata==null){Need(!required&&!File.Exists(p),"Owned baseline metadata/backup is missing or incomplete.");return;}var r=Receipt(content,metadata);Need(r.styleId==catalog.baselineStyleId,"Invalid baseline backup identity.");PackEngine.NoReparse(p,false);using(var f=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.Read))Need(f.Length==Style(r.styleId).payload.bytes&&HashStream(f)==Style(r.styleId).payload.sha256,"Original caption backup changed.");}
  void PrepareBase(string content,FileStream[] fs){string dir=StateRoot(content);ValidateBase(content,false);if(File.Exists(PackEngine.Child(dir,"base.json")))return;Mkdir(dir);Snapshot(fs,PackEngine.Child(dir,"baseline.bin"),Style(catalog.baselineStyleId));Atomic(PackEngine.Child(dir,"base.json"),null,Encode(NewReceipt(content,catalog.baselineStyleId)));ValidateBase(content,true);}
  CaptionJournal Journal(string content,byte[] raw){if(raw==null)return null;object value=json.DeserializeObject(Utf8.GetString(raw));Keys(value,"schema","root","catalogSha256","transaction","beforeStyle","targetStyle","beforeReceipt","undoSha256");var d=Obj(value);foreach(var k in new[]{"root","catalogSha256","transaction","beforeStyle","targetStyle","undoSha256"})Text(d[k]);Need(d["beforeReceipt"]==null||d["beforeReceipt"] is string,"Invalid receipt snapshot.");Integer(d["schema"]);var j=json.Deserialize<CaptionJournal>(Utf8.GetString(raw));Need(j.schema==1&&String.Equals(j.root,content,StringComparison.OrdinalIgnoreCase)&&j.catalogSha256==catalogHash&&Regex.IsMatch(j.transaction??"","^[0-9a-f]{32}$")&&HasStyle(j.beforeStyle)&&HasStyle(j.targetStyle)&&j.undoSha256==Style(j.beforeStyle).payload.sha256,"Invalid caption recovery ownership.");byte[] before=j.beforeReceipt==null?null:Convert.FromBase64String(j.beforeReceipt);var r=Receipt(content,before);Need(r==null?j.beforeStyle==catalog.baselineStyleId:r.styleId==j.beforeStyle,"Prior receipt/style differs.");return j;}
  string Undo(string content,CaptionJournal j){return PackEngine.Child(PackEngine.Child(PackEngine.Child(StateRoot(content),"transactions"),j.transaction),"before.bin");}
  void ValidateRecovery(string content,FileStream[] fs,CaptionJournal j){ValidateBase(content,true);byte[] now=Maybe(PackEngine.Child(StateRoot(content),"receipt.json"),MaxJson),old=j.beforeReceipt==null?null:Convert.FromBase64String(j.beforeReceipt);if(!Equal(now,old)){var r=Receipt(content,now);Need(r!=null&&r.styleId==j.targetStyle,"Unknown receipt cannot be rolled back.");}string undo=Undo(content,j);PackEngine.NoReparse(undo,false);using(var before=new FileStream(undo,FileMode.Open,FileAccess.Read,FileShare.Read))using(var after=Payload(Style(j.targetStyle))){Need(before.Length==Style(j.beforeStyle).payload.bytes&&HashStream(before)==j.undoSha256,"Transaction undo snapshot pin differs.");for(int i=0;i<catalog.spans.Length;i++){var s=catalog.spans[i];byte[] actual=ReadAt(fs[s.fileIndex],s.offset,s.bytes),a=ReadAt(before,payloadAt[i],s.bytes),b=ReadAt(after,payloadAt[i],s.bytes);for(int k=0;k<actual.Length;k++)Need(actual[k]==a[k]||actual[k]==b[k],"Unknown third byte in an owned caption span; recovery refused.");}OverlayHashes(fs,before,j.beforeStyle);}}
  void Recover(string content,FileStream[] fs,CaptionJournal j,byte[] journalRaw){ValidateRecovery(content,fs,j);stopped();using(var b=new FileStream(Undo(content,j),FileMode.Open,FileAccess.Read,FileShare.Read))WriteSpans(fs,b,false);VerifyHashes(fs,j.beforeStyle);string rp=PackEngine.Child(StateRoot(content),"receipt.json");byte[] now=Maybe(rp,MaxJson),old=j.beforeReceipt==null?null:Convert.FromBase64String(j.beforeReceipt);if(!Equal(now,old)){var r=Receipt(content,now);Need(r!=null&&r.styleId==j.targetStyle,"Unknown receipt cannot be rolled back.");if(old==null)DeleteExact(rp,now);else Atomic(rp,now,old);}DeleteExact(PackEngine.Child(StateRoot(content),"journal.json"),journalRaw);log("Recovered the interrupted caption switch; full-dub audio remains byte-exact.");}
  public void Run(string mode,string selected,string id,bool openOriginal=false){
   Need(mode=="--check"||mode=="--activate"||mode=="--restore","Unknown caption operation.");if(mode=="--activate")Style(id);Need(!openOriginal||mode=="--activate","Only activation may open the original launcher.");string content=Resolve(selected);StateOutsideContent(content);
   bool mutate=mode!="--check";using(var mutex=new Mutex(false,"Local\\CrimsonSkies-KoreanPatch-"+PackEngine.RootIdentity(content))){bool held=false;try{if(mutate){try{held=mutex.WaitOne(0);}catch(AbandonedMutexException){held=true;}Need(held,"Another patch transaction owns this game folder.");stopped();}RunLocked(mode,content,id,mutate);}finally{if(held)mutex.ReleaseMutex();}}
   if(openOriginal)launch(content);
  }
  void RunLocked(string mode,string content,string id,bool mutate){
   foreach(var s in catalog.styles)using(Payload(s)){} // All restoration payloads must remain available and pinned.
   var handles=new List<FileStream>();try{
    for(int i=0;i<3;i++){string p=PackEngine.Child(content,catalog.files[i].path);PackEngine.NoReparse(p,false);var f=new FileStream(p,FileMode.Open,mutate?FileAccess.ReadWrite:FileAccess.Read,mutate?FileShare.None:FileShare.Read);handles.Add(f);Need(f.Length==catalog.files[i].bytes,"Caption file byte extent changed; native growth is not supported.");}
    FileStream[] fs=handles.ToArray();foreach(var g in catalog.guards){string p=PackEngine.Child(content,g.path);PackEngine.NoReparse(p,false);var f=new FileStream(p,FileMode.Open,FileAccess.Read,mutate?FileShare.None:FileShare.Read);handles.Add(f);Need(f.Length==g.bytes&&HashStream(f)==g.sha256,"Read-only game identity guard differs.");}
    string dir=StateRoot(content),jp=PackEngine.Child(dir,"journal.json"),rp=PackEngine.Child(dir,"receipt.json");byte[] journalRaw=Maybe(jp,MaxJson);var pending=Journal(content,journalRaw);
    if(pending!=null){ValidateRecovery(content,fs,pending);if(!mutate){log("An owned interrupted caption switch is recoverable. Check made no changes.");return;}Recover(content,fs,pending,journalRaw);}
    string current=Detect(fs);byte[] receiptRaw=Maybe(rp,MaxJson);var receipt=Receipt(content,receiptRaw);
    if(receipt==null)Need(current==catalog.baselineStyleId,"Known caption target has no owned backup/receipt; adoption refused.");else{Need(receipt.styleId==current,"Caption receipt and full-file state differ.");ValidateBase(content,true);}
    if(!mutate){ValidateBase(content,false);log("FullDubBeta1 caption style: "+current+". Read-only check; audio was not modified.");return;}
    string target=mode=="--restore"?catalog.baselineStyleId:id;
    if(target==current){log("Caption style already active: "+current);return;}
    if(receipt==null)PrepareBase(content,fs);else ValidateBase(content,true);
    using(var payload=Payload(Style(target)))OverlayHashes(fs,payload,target); // Prove ownership before any write.
    string transaction=Guid.NewGuid().ToString("N"),txdir=PackEngine.Child(PackEngine.Child(dir,"transactions"),transaction);Mkdir(txdir);
    Snapshot(fs,PackEngine.Child(txdir,"before.bin"),Style(current));
    var journal=new CaptionJournal{schema=1,root=content,catalogSha256=catalogHash,transaction=transaction,beforeStyle=current,targetStyle=target,beforeReceipt=receiptRaw==null?null:Convert.ToBase64String(receiptRaw),undoSha256=Style(current).payload.sha256};
    journalRaw=Encode(journal);Atomic(jp,null,journalRaw);bool journalOwned=true;
    try{stopped();VerifyHashes(fs,current);fault("after-journal");using(var payload=Payload(Style(target)))WriteSpans(fs,payload,true);VerifyHashes(fs,target);fault("before-receipt");Atomic(rp,receiptRaw,Encode(NewReceipt(content,target)));fault("after-receipt");DeleteExact(jp,journalRaw);journalOwned=false;log(mode=="--restore"?"Restored FullDubBeta1 original translation captions; Korean audio retained.":"Caption style activated: "+target+"; Korean audio retained.");}
    catch(Exception error){if(journalOwned)try{fault("before-rollback");Recover(content,fs,journal,journalRaw);}catch(Exception recovery){throw new IOException("Caption switch rollback is pending. Durable sparse backup/journal: "+jp+"\r\nOriginal: "+error.Message+"\r\nRecovery: "+recovery.Message,error);}throw;}
   }finally{foreach(var f in handles)f.Dispose();}
  }
 }
}
