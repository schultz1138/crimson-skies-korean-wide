// SPDX-License-Identifier: MIT
// Selected-profile backup only. Never edits a WGS index or calls a provider.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;
using System.Xml;

namespace CrimsonSkiesMultilingual {
 public sealed class ProfileBackupFile {
  public string Kind,ArchivePath,LogicalName,PhysicalFileName,Sha256;
  public long Bytes;
 }
 public sealed class VerifiedProfileBackup {
  public string FilePath,Sha256,ProfileId,ProfileName,ContextToken,LogicalContainerName;
  public string StorageFolderGuid,MetadataFileName,RawIndexRecordSha256,AccountIdHex,StorageSpaceId;
  public string IndexDisplayName;
  public ProfileBackupFile[] Files;
 }
 public static class ProfileBackup {
  public const long MaximumArchiveBytes=67108864,MaximumExpandedBytes=67108864;
  const int MaximumManifestBytes=65536;
  static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
  static readonly Regex GuidLeaf=new Regex("^[0-9a-fA-F]{32}$",RegexOptions.CultureInvariant);
  static readonly Regex ProfileLogical=new Regex("^U4d530021/[0-9a-fA-F]{12}$",RegexOptions.CultureInvariant|RegexOptions.IgnoreCase);
  static readonly Regex Hex16=new Regex("^[0-9A-F]{16}$",RegexOptions.CultureInvariant);
  static readonly Regex Sha=new Regex("^[0-9a-f]{64}$",RegexOptions.CultureInvariant);
  static readonly string[] Entries={"manifest.json","selected-profile.xml","metadata.bin","blobs/000.bin","blobs/001.bin"};
  sealed class Manifest {
   public int schema=1;
   public string format="CrimsonSkiesSelectedProfileBackup/v1",packageFamilyName,applicationId,accountIdHex,storageSpaceId;
   public string sourceWgsRoot,sourceUserRoot,sourceUserStoreName,contextToken,storeRevisionToken;
   public string profileId,profileName,logicalContainerName,storageFolderGuid,indexDisplayName;
   public string metadataFileName,rawIndexRecordBase64,rawIndexRecordSha256;
   public ProfileBackupFile[] files;
  }
  sealed class Bundle { public Manifest Manifest;public VerifiedProfileBackup Verified;public Dictionary<string,byte[]> Data; }
  static bool Same(string a,string b){return String.Equals(a,b,StringComparison.OrdinalIgnoreCase);}
  static string Full(string path){if(String.IsNullOrWhiteSpace(path))throw new IOException("A local path is required.");string p=Path.GetFullPath(path);return p.Length>Path.GetPathRoot(p).Length?p.TrimEnd('\\','/'):p;}
  static bool Inside(string p,string root){return Same(p,root)||p.StartsWith(root.TrimEnd('\\','/')+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase);}
  static void NoReparse(string path){if((File.GetAttributes(path)&FileAttributes.ReparsePoint)!=0)throw new IOException("Linked/reparse backup paths are not supported.");}
  static void GuardAncestors(string path){
   string p=Full(path),volume=Path.GetPathRoot(p);if(String.IsNullOrEmpty(volume)||volume.StartsWith("\\\\",StringComparison.Ordinal))throw new IOException("A local backup path is required.");
   string current=volume;NoReparse(current);foreach(string part in p.Substring(volume.Length).Split(new[]{'\\','/'},StringSplitOptions.RemoveEmptyEntries)){current=Path.Combine(current,part);if(File.Exists(current)||Directory.Exists(current))NoReparse(current);else break;}
  }
  // Resolve existing 8.3 aliases before testing the WGS exclusion boundary.
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern uint GetLongPathName(string path,StringBuilder result,uint size);
  [DllImport("kernel32.dll",EntryPoint="CreateDirectoryW",CharSet=CharSet.Unicode,SetLastError=true)]static extern bool CreateDirectoryNew(string path,IntPtr securityAttributes);
  static string Expanded(string path){string p=Full(path);if(Path.DirectorySeparatorChar!='\\')return p;var missing=new Stack<string>();string ancestor=p;while(!File.Exists(ancestor)&&!Directory.Exists(ancestor)){missing.Push(Path.GetFileName(ancestor));ancestor=Path.GetDirectoryName(ancestor);if(String.IsNullOrEmpty(ancestor))throw new IOException("Invalid backup ancestor.");}var b=new StringBuilder(32768);uint n=GetLongPathName(ancestor,b,(uint)b.Capacity);if(n==0||n>=b.Capacity)throw new IOException("Cannot resolve the backup ancestor.");string result=Full(b.ToString());while(missing.Count!=0)result=Path.Combine(result,missing.Pop());return Full(result);}
  static void OutsideWgs(string path,string sourceWgs,string sourceUser){
   string p=Expanded(path);GuardAncestors(path);foreach(string excluded in new[]{ProfileStore.DefaultWgsRoot(),sourceWgs,sourceUser})if(!String.IsNullOrEmpty(excluded)&&Inside(p,Expanded(excluded)))throw new IOException("Backups and materialized files must be outside WGS.");
  }
  static string Child(string root,string leaf){if(String.IsNullOrEmpty(leaf)||Path.IsPathRooted(leaf)||leaf.IndexOfAny(new[]{'\\','/',':','\0'})>=0||leaf=="."||leaf=="..")throw new InvalidDataException("Invalid backup leaf.");string p=Full(Path.Combine(root,leaf));if(!Inside(p,Full(root))||Same(p,Full(root)))throw new InvalidDataException("Backup leaf escapes its directory.");return p;}
  static byte[] Read(string path,int maximum){GuardAncestors(path);if(!File.Exists(path))throw new FileNotFoundException("A backup source is missing.",path);using(var f=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete)){byte[] b=ReadStream(f,f.Length,maximum);if(f.Length!=b.LongLength)throw new IOException("Source changed while reading.");GuardAncestors(path);return b;}}
  static byte[] ReadStream(Stream stream,long length,long maximum){if(length<0||length>maximum||length>Int32.MaxValue)throw new InvalidDataException("Backup data exceeds its finite bound.");byte[] b=new byte[(int)length];int at=0;while(at<b.Length){int n=stream.Read(b,at,b.Length-at);if(n==0)throw new InvalidDataException("Truncated backup data.");at+=n;}if(stream.ReadByte()!=-1)throw new InvalidDataException("Backup data exceeds its declared length.");return b;}
  static string StreamHash(Stream s){s.Position=0;using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(s)).Replace("-","").ToLowerInvariant();}
  static void WriteNew(string path,byte[] bytes){GuardAncestors(path);using(var f=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.None)){f.Write(bytes,0,bytes.Length);f.Flush(true);}GuardAncestors(path);}
  static string Token(params string[] values){var s=new StringBuilder();foreach(string v in values){string x=v??"";s.Append(x.Length.ToString(CultureInfo.InvariantCulture)).Append(':').Append(x);}return ProfileStore.Hash(Utf8.GetBytes(s.ToString()));}
  static byte[] Serialize(object value){return Utf8.GetBytes(new JavaScriptSerializer{MaxJsonLength=MaximumManifestBytes,RecursionLimit=16}.Serialize(value));}
  static ProfileBackupFile Describe(string kind,string archive,string logical,string physical,byte[] bytes){return new ProfileBackupFile{Kind=kind,ArchivePath=archive,LogicalName=logical,PhysicalFileName=physical,Bytes=bytes.LongLength,Sha256=ProfileStore.Hash(bytes)};}

  public static VerifiedProfileBackup Create(StoreSnapshot snapshot,ProfileEntry selected,string backupBase){
   if(snapshot==null||selected==null)throw new ArgumentNullException("selected");var fresh=ProfileStore.Revalidate(snapshot);var p=fresh.Profiles.SingleOrDefault(x=>x.StableId==selected.StableId);
   if(p==null||p.ContextToken!=selected.ContextToken||p.StoreRevisionToken!=selected.StoreRevisionToken||p.RevisionToken!=selected.RevisionToken||p.LogicalContainerName!=selected.LogicalContainerName||!Same(p.StorageFolderGuid,selected.StorageFolderGuid))throw new InvalidDataException("The selection no longer identifies the captured profile.");
   string output=Full(backupBase);OutsideWgs(output,fresh.WgsRoot,fresh.UserRoot);if(File.Exists(output))throw new IOException("The backup directory is a file.");
   var container=fresh.Containers.Single(x=>x.LogicalContainerName==p.LogicalContainerName&&Same(x.StorageFolderGuid,p.StorageFolderGuid)&&!x.IsDeleted);var record=container.IndexRecord;
   byte[] raw=new byte[record.RecordBytes];Buffer.BlockCopy(fresh.Index.RawIndexBytes,record.FileOffset,raw,0,raw.Length);if(ProfileStore.Hash(raw)!=record.RecordSha256)throw new InvalidDataException("The captured index record changed.");
   var data=new Dictionary<string,byte[]>(StringComparer.Ordinal);var files=new List<ProfileBackupFile>();
   byte[] metadata=Read(Child(Child(fresh.UserRoot,p.StorageFolderName),p.MetadataFileName),8+160*ProfileStore.MaximumBlobsPerContainer);
   if(metadata.LongLength!=p.MetadataBytes||ProfileStore.Hash(metadata)!=p.MetadataSha256)throw new IOException("The selected metadata changed.");ProfileStore.ParseContainerMetadata(metadata,record.OpaqueFlags);data.Add("metadata.bin",metadata);files.Add(Describe("metadata","metadata.bin",null,p.MetadataFileName,metadata));
   var blobs=p.Blobs.OrderBy(x=>x.LogicalName,StringComparer.Ordinal).ToArray();if(blobs.Length!=2)throw new InvalidDataException("Only the exact two-blob profile schema can be backed up.");
   for(int i=0;i<blobs.Length;i++){byte[] bytes=ProfileStore.ReadValidatedBlob(p,blobs[i]);string archive="blobs/"+i.ToString("D3",CultureInfo.InvariantCulture)+".bin";data.Add(archive,bytes);files.Add(Describe("blob",archive,blobs[i].LogicalName,blobs[i].StorageFileName,bytes));}
   var m=new Manifest{packageFamilyName=ProfileStore.PackageFamilyName,applicationId=fresh.ApplicationId,accountIdHex=fresh.AccountIdHex,storageSpaceId=fresh.StorageSpaceId,sourceWgsRoot=Full(fresh.WgsRoot),sourceUserRoot=Full(fresh.UserRoot),sourceUserStoreName=fresh.UserStoreName,contextToken=fresh.ContextToken,storeRevisionToken=fresh.SnapshotDigest,profileId=p.StableId,profileName=p.DisplayName,logicalContainerName=p.LogicalContainerName,storageFolderGuid=p.StorageFolderGuid,indexDisplayName=record.IndexDisplayName,metadataFileName=p.MetadataFileName,rawIndexRecordBase64=Convert.ToBase64String(raw),rawIndexRecordSha256=record.RecordSha256,files=files.ToArray()};
   data.Add("selected-profile.xml",BuildXml(m,data));data.Add("manifest.json",Serialize(m));ValidateBundle(m,data);ProfileStore.Revalidate(fresh);
   Directory.CreateDirectory(output);GuardAncestors(output);string stem=Guid.NewGuid().ToString("N"),temporary=Child(output,stem+".tmp"),final=Child(output,stem+".zip");bool ownTemp=false,ownFinal=false;
   try {
    using(var fs=new FileStream(temporary,FileMode.CreateNew,FileAccess.ReadWrite,FileShare.None)){ownTemp=true;using(var zip=new ZipArchive(fs,ZipArchiveMode.Create,true)){foreach(string name in Entries){var entry=zip.CreateEntry(name,CompressionLevel.Optimal);using(var s=entry.Open()){byte[] b=data[name];s.Write(b,0,b.Length);}}}fs.Flush(true);if(fs.Length>MaximumArchiveBytes)throw new InvalidDataException("Backup ZIP exceeds 64 MiB.");}
    Verify(temporary);ProfileStore.Revalidate(fresh);GuardAncestors(output);File.Move(temporary,final);ownTemp=false;ownFinal=true;var verified=Verify(final);ProfileStore.Revalidate(fresh);return verified;
   }catch{if(ownTemp)DeleteOwned(temporary);if(ownFinal)DeleteOwned(final);throw;}
  }
  static void DeleteOwned(string path){try{GuardAncestors(path);if(File.Exists(path))File.Delete(path);}catch{/* Preserve a suspicious path for inspection rather than following a link. */}}
  public static VerifiedProfileBackup Verify(string path){return Load(path).Verified;}
  static Bundle Load(string path){
   string full=Full(path);GuardAncestors(full);if(!File.Exists(full))throw new FileNotFoundException("The profile backup is missing.",full);
   using(var fs=new FileStream(full,FileMode.Open,FileAccess.Read,FileShare.Read)){
    if(fs.Length<=0||fs.Length>MaximumArchiveBytes)throw new InvalidDataException("Invalid backup ZIP size.");long length=fs.Length;string hash=StreamHash(fs);fs.Position=0;var data=new Dictionary<string,byte[]>(StringComparer.Ordinal);
    using(var zip=new ZipArchive(fs,ZipArchiveMode.Read,true)){
     if(zip.Entries.Count!=Entries.Length)throw new InvalidDataException("A selected-profile backup must contain exactly five entries.");long total=0;
     foreach(var e in zip.Entries){if(!Entries.Contains(e.FullName,StringComparer.Ordinal)||data.ContainsKey(e.FullName)||e.Length<0||e.CompressedLength<0||e.CompressedLength>MaximumArchiveBytes)throw new InvalidDataException("Unknown, duplicate or invalid backup entry.");checked{total+=e.Length;}if(total>MaximumExpandedBytes)throw new InvalidDataException("Expanded backup exceeds 64 MiB.");long limit=e.FullName=="manifest.json"?MaximumManifestBytes:e.FullName=="metadata.bin"?328:e.FullName.StartsWith("blobs/",StringComparison.Ordinal)?ProfileStore.MaximumBlobBytes:MaximumExpandedBytes;using(var s=e.Open())data.Add(e.FullName,ReadStream(s,e.Length,limit));}
    }
    var manifest=ParseManifest(data["manifest.json"]);ValidateBundle(manifest,data);if(fs.Length!=length||StreamHash(fs)!=hash)throw new IOException("Backup changed during verification.");GuardAncestors(full);
    return new Bundle{Manifest=manifest,Data=data,Verified=new VerifiedProfileBackup{FilePath=full,Sha256=hash,ProfileId=manifest.profileId,ProfileName=manifest.profileName,ContextToken=manifest.contextToken,LogicalContainerName=manifest.logicalContainerName,StorageFolderGuid=manifest.storageFolderGuid,MetadataFileName=manifest.metadataFileName,IndexDisplayName=manifest.indexDisplayName,RawIndexRecordSha256=manifest.rawIndexRecordSha256,AccountIdHex=manifest.accountIdHex,StorageSpaceId=manifest.storageSpaceId,Files=manifest.files}};
   }
  }
  public static void Materialize(VerifiedProfileBackup backup,string newEmptyDestination){
   if(backup==null)throw new ArgumentNullException("backup");var bundle=Load(backup.FilePath);var v=bundle.Verified;
   if(v.Sha256!=backup.Sha256||v.ProfileId!=backup.ProfileId||v.ContextToken!=backup.ContextToken||v.RawIndexRecordSha256!=backup.RawIndexRecordSha256||!Same(v.StorageFolderGuid,backup.StorageFolderGuid))throw new InvalidDataException("The verified backup identity changed.");
   string dest=Full(newEmptyDestination);OutsideWgs(dest,bundle.Manifest.sourceWgsRoot,bundle.Manifest.sourceUserRoot);if(File.Exists(dest)||Directory.Exists(dest))throw new IOException("Materialization requires a new, absent destination.");string parent=Path.GetDirectoryName(dest);if(String.IsNullOrEmpty(parent)||!Directory.Exists(parent))throw new DirectoryNotFoundException("The materialization parent must already exist.");GuardAncestors(parent);bool created=false;var written=new List<string>();
   try{
    // No preexisting directory, files, links or junctions are overwritten.
    if(!CreateDirectoryNew(dest,IntPtr.Zero))throw new IOException("The materialization directory could not be created exclusively (error "+Marshal.GetLastWin32Error().ToString(CultureInfo.InvariantCulture)+").");created=true;GuardAncestors(dest);foreach(var f in bundle.Manifest.files){string p=Child(dest,f.PhysicalFileName);WriteNew(p,bundle.Data[f.ArchivePath]);written.Add(p);}
    GuardAncestors(dest);string[] names=Directory.GetFileSystemEntries(dest).Select(Path.GetFileName).ToArray();if(names.Length!=3||names.Any(x=>!bundle.Manifest.files.Any(f=>f.PhysicalFileName==x)))throw new IOException("Materialized directory membership changed.");foreach(var f in bundle.Manifest.files){byte[] b=Read(Child(dest,f.PhysicalFileName),(int)f.Bytes);if(b.LongLength!=f.Bytes||ProfileStore.Hash(b)!=f.Sha256)throw new IOException("Materialized file verification failed.");}
   }catch{foreach(string p in written)DeleteOwned(p);if(created)try{GuardAncestors(dest);if(Directory.Exists(dest)&&!Directory.EnumerateFileSystemEntries(dest).Any())Directory.Delete(dest,false);}catch{}throw;}
  }
  static byte[] BuildXml(Manifest m,Dictionary<string,byte[]> data){
   using(var stream=new MemoryStream()){var settings=new XmlWriterSettings{Encoding=Utf8,Indent=true,NewLineChars="\r\n",NewLineHandling=NewLineHandling.None,CloseOutput=false};using(var w=XmlWriter.Create(stream,settings)){w.WriteStartDocument();w.WriteStartElement("XbConnectedStorageSpace");w.WriteStartElement("ContextDescription");w.WriteStartElement("PackageFamilyName");w.WriteAttributeString("pfn",m.packageFamilyName);w.WriteEndElement();w.WriteStartElement("Title");w.WriteAttributeString("scid",new Guid(m.storageSpaceId).ToString("D"));w.WriteEndElement();w.WriteEndElement();w.WriteStartElement("Data");w.WriteStartElement("Containers");w.WriteStartElement("Container");w.WriteAttributeString("name",m.logicalContainerName);w.WriteAttributeString("displayName",m.indexDisplayName);w.WriteStartElement("Blobs");foreach(var f in m.files.Where(x=>x.Kind=="blob")){w.WriteStartElement("Blob");w.WriteAttributeString("name",f.LogicalName);w.WriteCData(Convert.ToBase64String(data[f.ArchivePath]));w.WriteEndElement();}w.WriteEndElement();w.WriteEndElement();w.WriteEndElement();w.WriteEndElement();w.WriteEndElement();w.WriteEndDocument();}return stream.ToArray();}
  }
  static void ValidateBundle(Manifest m,Dictionary<string,byte[]> data){
   if(m.schema!=1||m.format!="CrimsonSkiesSelectedProfileBackup/v1"||m.packageFamilyName!=ProfileStore.PackageFamilyName||m.applicationId!=ProfileStore.ApplicationId||!Hex16.IsMatch(m.accountIdHex??"")||!GuidLeaf.IsMatch(m.storageSpaceId??"")||m.storageSpaceId!=m.storageSpaceId.ToUpperInvariant())throw new InvalidDataException("Unsupported backup identity.");
   if(!Sha.IsMatch(m.contextToken??"")||!Sha.IsMatch(m.storeRevisionToken??"")||!Sha.IsMatch(m.profileId??"")||!Sha.IsMatch(m.rawIndexRecordSha256??"")||!ProfileLogical.IsMatch(m.logicalContainerName??"")||!GuidLeaf.IsMatch(m.storageFolderGuid??"")||m.storageFolderGuid!=m.storageFolderGuid.ToUpperInvariant())throw new InvalidDataException("Invalid selected-profile identity.");
   string user=Full(m.sourceUserRoot),wgs=Full(m.sourceWgsRoot);if(user!=m.sourceUserRoot||wgs!=m.sourceWgsRoot||!Same(Path.GetDirectoryName(user),wgs)||Path.GetFileName(user)!=m.sourceUserStoreName||!Same(m.sourceUserStoreName,m.accountIdHex+"_"+m.storageSpaceId))throw new InvalidDataException("Invalid source account-store binding.");
   if(Token("CrimsonSkiesProfileStore/v1",user.ToUpperInvariant(),m.sourceUserStoreName.ToUpperInvariant(),m.applicationId)!=m.contextToken||Token("profile-v1",m.contextToken,m.logicalContainerName,m.storageFolderGuid)!=m.profileId)throw new InvalidDataException("Backup context/stable identity mismatch.");
   byte[] raw;try{raw=Convert.FromBase64String(m.rawIndexRecordBase64??"");}catch(FormatException e){throw new InvalidDataException("Invalid raw index record.",e);}if(raw.Length==0||raw.Length>8192||ProfileStore.Hash(raw)!=m.rawIndexRecordSha256)throw new InvalidDataException("Raw record size/hash mismatch.");
   StoreIndexRecord record=ParseSingleRecord(raw);if(!record.IsActive||record.LogicalContainerName!=m.logicalContainerName||record.IndexDisplayName!=m.indexDisplayName||record.StorageFolderGuid!=m.storageFolderGuid||m.metadataFileName!="container."+record.MetadataRevision.ToString(CultureInfo.InvariantCulture))throw new InvalidDataException("Raw record does not bind the selected profile.");
   if(m.files==null||m.files.Length!=3||m.files.Select(x=>x.PhysicalFileName).Distinct(StringComparer.OrdinalIgnoreCase).Count()!=3||m.files.Select(x=>x.ArchivePath).Distinct(StringComparer.Ordinal).Count()!=3)throw new InvalidDataException("The physical file list must have exactly three unique leaves.");
   string[] logical={"CrimsonData.txt00","SaveMeta.xbx00"};for(int i=0;i<m.files.Length;i++){var f=m.files[i];if(f==null||!Sha.IsMatch(f.Sha256??"")||f.Bytes<0||f.Bytes>ProfileStore.MaximumBlobBytes)throw new InvalidDataException("Invalid backup file descriptor.");if(i==0){if(f.Kind!="metadata"||f.ArchivePath!="metadata.bin"||f.LogicalName!=null||f.PhysicalFileName!=m.metadataFileName||f.Bytes!=328)throw new InvalidDataException("Invalid metadata descriptor.");}else if(f.Kind!="blob"||f.ArchivePath!="blobs/"+(i-1).ToString("D3",CultureInfo.InvariantCulture)+".bin"||f.LogicalName!=logical[i-1]||!GuidLeaf.IsMatch(f.PhysicalFileName??"")||i==1&&f.Bytes==0)throw new InvalidDataException("Invalid selected blob descriptor.");byte[] b;if(!data.TryGetValue(f.ArchivePath,out b)||b.LongLength!=f.Bytes||ProfileStore.Hash(b)!=f.Sha256)throw new InvalidDataException("Backup file size/hash mismatch.");}
   var metadata=ProfileStore.ParseContainerMetadata(data["metadata.bin"],record.OpaqueFlags);if(metadata.Length!=2)throw new InvalidDataException("Backup is not an exact two-blob profile.");foreach(var b in metadata){var f=m.files.SingleOrDefault(x=>x.Kind=="blob"&&x.LogicalName==b.LogicalName);if(f==null||!Same(f.PhysicalFileName,b.StorageGuid))throw new InvalidDataException("Metadata GUID/blob binding mismatch.");}
   if((ulong)m.files.Where(x=>x.Kind=="blob").Sum(x=>x.Bytes)!=record.TotalBlobBytes||ProfileStore.ParseProfileName(data["blobs/001.bin"])!=m.profileName)throw new InvalidDataException("Selected profile name/record total mismatch.");
   long expanded=data.Values.Sum(b=>b.LongLength);if(expanded>MaximumExpandedBytes||data["manifest.json"].Length>MaximumManifestBytes)throw new InvalidDataException("Expanded backup exceeds its finite bound.");
   // Compare our one-container grammar instead of parsing untrusted XML. This
   // also proves the base64 payload is CDATA, as required by the SDK reader.
   if(!BuildXml(m,data).SequenceEqual(data["selected-profile.xml"]))throw new InvalidDataException("Selected export XML differs from the verified single-container content.");
  }
  static StoreIndexRecord ParseSingleRecord(byte[] raw){using(var s=new MemoryStream()){using(var w=new BinaryWriter(s,Encoding.Unicode,true)){w.Write((uint)14);w.Write((uint)1);w.Write((uint)0);w.Write((uint)ProfileStore.ApplicationId.Length);w.Write(Encoding.Unicode.GetBytes(ProfileStore.ApplicationId));w.Write((ulong)0);w.Write((uint)0);string guid="11111111-1111-1111-1111-111111111111";w.Write((uint)guid.Length);w.Write(Encoding.Unicode.GetBytes(guid));w.Write((ulong)0);w.Write(raw);}return ProfileStore.ParseIndex(s.ToArray()).Records.Single();}}
  static Manifest ParseManifest(byte[] bytes){
   if(bytes==null||bytes.Length>MaximumManifestBytes)throw new InvalidDataException("Invalid backup manifest size.");var d=Obj(new StrictJson(Utf8.GetString(bytes)).Parse());Keys(d,"schema","format","packageFamilyName","applicationId","accountIdHex","storageSpaceId","sourceWgsRoot","sourceUserRoot","sourceUserStoreName","contextToken","storeRevisionToken","profileId","profileName","logicalContainerName","storageFolderGuid","indexDisplayName","metadataFileName","rawIndexRecordBase64","rawIndexRecordSha256","files");
   var m=new Manifest{schema=checked((int)Num(d["schema"])),format=Str(d["format"]),packageFamilyName=Str(d["packageFamilyName"]),applicationId=Str(d["applicationId"]),accountIdHex=Str(d["accountIdHex"]),storageSpaceId=Str(d["storageSpaceId"]),sourceWgsRoot=Str(d["sourceWgsRoot"]),sourceUserRoot=Str(d["sourceUserRoot"]),sourceUserStoreName=Str(d["sourceUserStoreName"]),contextToken=Str(d["contextToken"]),storeRevisionToken=Str(d["storeRevisionToken"]),profileId=Str(d["profileId"]),profileName=Str(d["profileName"]),logicalContainerName=Str(d["logicalContainerName"]),storageFolderGuid=Str(d["storageFolderGuid"]),indexDisplayName=Str(d["indexDisplayName"]),metadataFileName=Str(d["metadataFileName"]),rawIndexRecordBase64=Str(d["rawIndexRecordBase64"]),rawIndexRecordSha256=Str(d["rawIndexRecordSha256"])};
   var a=d["files"] as List<object>;if(a==null||a.Count!=3)throw new InvalidDataException("Invalid backup file array.");m.files=a.Select(x=>{var f=Obj(x);Keys(f,"Kind","ArchivePath","LogicalName","PhysicalFileName","Sha256","Bytes");return new ProfileBackupFile{Kind=Str(f["Kind"]),ArchivePath=Str(f["ArchivePath"]),LogicalName=f["LogicalName"]==null?null:Str(f["LogicalName"]),PhysicalFileName=Str(f["PhysicalFileName"]),Sha256=Str(f["Sha256"]),Bytes=Num(f["Bytes"])};}).ToArray();return m;
  }
  static Dictionary<string,object> Obj(object x){var d=x as Dictionary<string,object>;if(d==null)throw new InvalidDataException("Expected a JSON object.");return d;}
  static string Str(object x){string s=x as string;if(s==null||s.IndexOf('\0')>=0)throw new InvalidDataException("Expected a bounded JSON string.");return s;}
  static long Num(object x){if(!(x is long))throw new InvalidDataException("Expected a JSON integer.");return (long)x;}
  static void Keys(Dictionary<string,object> d,params string[] keys){if(d.Count!=keys.Length||keys.Any(k=>!d.ContainsKey(k)))throw new InvalidDataException("Unknown or missing backup manifest field.");}
  // Small strict parser: duplicate keys, noninteger numbers and invalid UTF16
  // are rejected rather than silently normalized by JavaScriptSerializer.
  sealed class StrictJson {
   readonly string s;int p,depth;public StrictJson(string text){s=text;}
   void White(){while(p<s.Length&&(s[p]==' '||s[p]=='\r'||s[p]=='\n'||s[p]=='\t'))p++;}
   char Take(){if(p>=s.Length)throw new InvalidDataException("Truncated JSON.");return s[p++];}
   void Need(char c){White();if(Take()!=c)throw new InvalidDataException("Invalid JSON token.");}
   public object Parse(){object x=Value();White();if(p!=s.Length)throw new InvalidDataException("Trailing JSON.");return x;}
   object Value(){White();if(++depth>12)throw new InvalidDataException("JSON is too deep.");object x;char c=p<s.Length?s[p]:'\0';if(c=='{'){p++;var d=new Dictionary<string,object>(StringComparer.Ordinal);White();if(p<s.Length&&s[p]=='}'){p++;x=d;}else{while(true){White();string k=String();Need(':');object v=Value();if(d.ContainsKey(k))throw new InvalidDataException("Duplicate JSON key.");d.Add(k,v);White();char next=Take();if(next=='}')break;if(next!=',')throw new InvalidDataException("Invalid JSON object.");}x=d;}}else if(c=='['){p++;var a=new List<object>();White();if(p<s.Length&&s[p]==']')p++;else while(true){if(a.Count>=32)throw new InvalidDataException("JSON array exceeds bound.");a.Add(Value());White();char next=Take();if(next==']')break;if(next!=',')throw new InvalidDataException("Invalid JSON array.");}x=a;}else if(c=='"')x=String();else if(p+4<=s.Length&&s.Substring(p,4)=="null"){p+=4;x=null;}else{int start=p;if(c=='-')p++;if(p>=s.Length||s[p]<'0'||s[p]>'9')throw new InvalidDataException("Invalid JSON number.");if(s[p]=='0')p++;else while(p<s.Length&&s[p]>='0'&&s[p]<='9')p++;long n;if(!Int64.TryParse(s.Substring(start,p-start),NumberStyles.AllowLeadingSign,CultureInfo.InvariantCulture,out n))throw new InvalidDataException("Invalid JSON integer.");x=n;}depth--;return x;}
   string String(){if(Take()!='"')throw new InvalidDataException("Expected JSON string.");var b=new StringBuilder();while(true){char c=Take();if(c=='"')break;if(c<' ')throw new InvalidDataException("Control character in JSON string.");if(c=='\\'){c=Take();switch(c){case '"':case '\\':case '/':b.Append(c);break;case 'b':b.Append('\b');break;case 'f':b.Append('\f');break;case 'n':b.Append('\n');break;case 'r':b.Append('\r');break;case 't':b.Append('\t');break;case 'u':if(p>s.Length-4)throw new InvalidDataException("Truncated JSON escape.");ushort u;if(!UInt16.TryParse(s.Substring(p,4),NumberStyles.HexNumber,CultureInfo.InvariantCulture,out u))throw new InvalidDataException("Invalid JSON escape.");p+=4;b.Append((char)u);break;default:throw new InvalidDataException("Invalid JSON escape.");}}else b.Append(c);if(b.Length>32768)throw new InvalidDataException("JSON string exceeds bound.");}string result=b.ToString();Utf8.GetByteCount(result);return result;}
  }
 }
}
