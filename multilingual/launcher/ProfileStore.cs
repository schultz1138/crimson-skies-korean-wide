// SPDX-License-Identifier: MIT
// Read-only, bounded snapshot parser. This file never writes, deletes, launches,
// edits a WGS index, or calls a cloud/game-save provider.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;

namespace CrimsonSkiesMultilingual {
 public sealed class StoreSnapshot {
  public bool Available;
  public string WgsRoot,UserRoot,UserStoreName,AccountIdHex,StorageSpaceId,ApplicationId;
  public string ContextToken,SnapshotDigest,IndexPath,IndexSha256,CapturedUtc;
  public long IndexBytes;
  public StoreIndex Index;
  public StoreContainerEntry[] Containers;
  public ProfileEntry[] Profiles;
 }
 public sealed class StoreIndex {
  public uint Version,HeaderReserved,HeaderFlags,OpaqueState;
  public string ApplicationId,OpaqueIdentityGuid;
  public ulong FileTime,OpaqueLimit;
  public byte[] RawIndexBytes;
  public int HeaderRecordCountOffset,HeaderFlagsU32Offset,HeaderFileTimeOffset,HeaderOpaqueStateOffset;
  public StoreIndexRecord[] Records;
 }
 public sealed class StoreIndexRecord {
  public string LogicalContainerName,IndexDisplayName,OpaqueEtag,StorageFolderGuid,RecordSha256;
  public byte MetadataRevision;
  public uint OpaqueFlags;
  public bool IsDeleted,IsActive;
  public ulong FileTime,Reserved,TotalBlobBytes;
  public int FileOffset,RecordEnd,RecordBytes,MetadataRevisionByteOffset,StateU32Offset,StorageGuidOffset,ModifiedFileTimeOffset,ReservedOffset,TotalBlobBytesOffset;
 }
 public sealed class StoreBlobMetadata {
  public string LogicalName,StorageGuid,SecondGuid;
 }
 public sealed class StoreContainerEntry {
  public string LogicalContainerName,StorageFolderGuid,StorageFolderName,MetadataFileName,MetadataSha256,RecordSha256,RevisionToken,ModifiedUtc;
  public bool IsDeleted,StorageFolderPresent;
  public long MetadataBytes;
  public StoreIndexRecord IndexRecord;
  public ProfileBlob[] Blobs;
 }
 public sealed class ProfileBlob {
  public string ProfileStableId,LogicalName,StorageGuid,StorageFileName,Sha256;
  public long Bytes;
 }
 public sealed class ProfileEntry {
  public string StableId,LogicalContainerName,StorageFolderGuid,StorageFolderName,DisplayName,ModifiedUtc;
  public string ContextToken,RevisionToken,StoreRevisionToken,UserRoot;
  public string MetadataFileName,MetadataSha256;
  public long MetadataBytes;
  public ProfileBlob[] Blobs;
 }

 public static class ProfileStore {
  public const string PackageFamilyName="Xbox360BackwardCompatibil.PrimaryCrimsonSkiesHighR_ksqcvrsvwz2jp";
  public const string ApplicationId=PackageFamilyName+"!App";
  public const string TitleContainer="U4d530021";
  public const int MaximumIndexBytes=1048576,MaximumContainers=256,MaximumBlobsPerContainer=128;
  public const int MaximumBlobBytes=16777216,MaximumSaveMetaBytes=65536;
  public const long MaximumStoreBlobBytes=268435456;
  static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
  static readonly UnicodeEncoding Wide=new UnicodeEncoding(false,false,true);
  static readonly Regex UserName=new Regex("^[0-9a-fA-F]{16}_[0-9a-fA-F]{32}$",RegexOptions.CultureInvariant);
  static readonly Regex GuidName=new Regex("^[0-9a-fA-F]{32}$",RegexOptions.CultureInvariant);
  static readonly Regex ProfileName=new Regex("^U4d530021/[0-9a-fA-F]{12}$",RegexOptions.CultureInvariant|RegexOptions.IgnoreCase);
  sealed class Fingerprint { public string Path,Hash; public int Limit; public long Bytes; }
  sealed class DirectoryFingerprint { public string Path; public string[] Names; }

  public static string DefaultWgsRoot() {return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Packages",PackageFamilyName,"SystemAppData","wgs");}
  public static string Hash(byte[] bytes) {using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
  static bool Same(string a,string b) {return String.Equals(a,b,StringComparison.OrdinalIgnoreCase);}
  static string Full(string path) {string p=Path.GetFullPath(path);return p.Length>Path.GetPathRoot(p).Length?p.TrimEnd('\\','/'):p;}
  static string Child(string root,string leaf) {
   if(String.IsNullOrEmpty(leaf)||Path.IsPathRooted(leaf)||leaf.IndexOfAny(new[]{'\\','/',':','\0'})>=0||leaf=="."||leaf=="..")throw new InvalidDataException("Invalid store leaf name.");
   string prefix=Full(root).TrimEnd('\\','/')+Path.DirectorySeparatorChar,p=Path.GetFullPath(Path.Combine(root,leaf));if(!p.StartsWith(prefix,StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("Store path escapes its root.");return p;
  }
  static void Attr(string path) {if((File.GetAttributes(path)&FileAttributes.ReparsePoint)!=0)throw new IOException("Linked/reparse store paths are not supported: "+path);}
  static void Guard(string path,bool directory) {
   string p=Full(path),volume=Path.GetPathRoot(p);if(String.IsNullOrEmpty(volume)||volume.StartsWith("\\\\",StringComparison.Ordinal))throw new IOException("A local WGS store is required.");
   string current=volume;Attr(current);foreach(string part in p.Substring(volume.Length).Split(new[]{'\\','/'},StringSplitOptions.RemoveEmptyEntries)){current=Path.Combine(current,part);Attr(current);}
   if(directory?!Directory.Exists(p):!File.Exists(p))throw new FileNotFoundException("Required store path is missing: "+p);
  }
  static void GuardExistingAncestor(string path) {
   string p=Full(path);while(!Directory.Exists(p)){if(File.Exists(p))throw new IOException("A store ancestor is a file.");p=Path.GetDirectoryName(p);if(String.IsNullOrEmpty(p))throw new IOException("Invalid store path.");}Guard(p,true);
  }
  static byte[] ReadBounded(string path,int maximum) {
   Guard(path,false);
   // Do not block GamingServices. Concurrent changes are rejected by the
   // complete second snapshot pass instead of locking the provider's files.
   using(var f=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete)) {
    long length=f.Length;if(length<0||length>maximum)throw new InvalidDataException("Store file exceeds its read bound: "+path);
    byte[] data=new byte[(int)length];int used=0;while(used<data.Length){int n=f.Read(data,used,data.Length-used);if(n==0)throw new IOException("Store file changed during reading.");used+=n;}
    if(f.ReadByte()!=-1||f.Length!=length)throw new IOException("Store file changed during reading.");Guard(path,false);return data;
   }
  }
  static byte[] Track(string path,int maximum,List<Fingerprint> files) {byte[] b=ReadBounded(path,maximum);files.Add(new Fingerprint{Path=path,Limit=maximum,Bytes=b.LongLength,Hash=Hash(b)});return b;}
  static string[] Names(string directory) {
   Guard(directory,true);string[] names=Directory.EnumerateFileSystemEntries(directory).Take(513).Select(Path.GetFileName).OrderBy(x=>x,StringComparer.OrdinalIgnoreCase).ThenBy(x=>x,StringComparer.Ordinal).ToArray();
   if(names.Length>512)throw new InvalidDataException("Store directory exceeds its finite membership bound.");
   if(names.Distinct(StringComparer.OrdinalIgnoreCase).Count()!=names.Length)throw new InvalidDataException("Case-ambiguous store names.");
   foreach(string n in names)Attr(Child(directory,n));return names;
  }
  static string[] TrackDirectory(string path,List<DirectoryFingerprint> dirs) {string[] n=Names(path);dirs.Add(new DirectoryFingerprint{Path=path,Names=n});return n;}
  static string GuidText(byte[] bytes,int offset) {byte[] g=new byte[16];Buffer.BlockCopy(bytes,offset,g,0,16);var id=new Guid(g);if(id==Guid.Empty)throw new InvalidDataException("An empty storage GUID is not a committed binding.");return id.ToString("N").ToUpperInvariant();}
  static string Date(ulong value) {if(value==0)return null;if(value>Int64.MaxValue)throw new InvalidDataException("Invalid store FILETIME.");try{return DateTime.FromFileTimeUtc((long)value).ToString("o",CultureInfo.InvariantCulture);}catch(ArgumentOutOfRangeException e){throw new InvalidDataException("Invalid store FILETIME.",e);}}
  sealed class Reader {
   readonly byte[] data;public int At;
   public Reader(byte[] input){data=input;}
   void Need(int count){if(count<0||At>data.Length-count)throw new InvalidDataException("Truncated containers.index.");}
   public uint U32(){Need(4);uint v=BitConverter.ToUInt32(data,At);At+=4;return v;}
   public ulong U64(){Need(8);ulong v=BitConverter.ToUInt64(data,At);At+=8;return v;}
   public byte U8(){Need(1);return data[At++];}
   public byte[] Bytes(int n){Need(n);var b=new byte[n];Buffer.BlockCopy(data,At,b,0,n);At+=n;return b;}
   public string Text(int max,bool empty){uint chars=U32();if(chars>max||!empty&&chars==0)throw new InvalidDataException("Invalid index string length.");string s=Wide.GetString(Bytes(checked((int)chars*2)));if(s.IndexOf('\0')>=0||s.Any(c=>Char.IsControl(c)))throw new InvalidDataException("Invalid index string.");return s;}
   public bool End{get{return At==data.Length;}}
  }
  public static StoreIndex ParseIndex(byte[] bytes) {
   if(bytes==null||bytes.Length<16||bytes.Length>MaximumIndexBytes)throw new InvalidDataException("Invalid containers.index size.");var r=new Reader(bytes);
   // The third DWORD is the length of an HSTRING prefix, not a flag word.
   // Only the captured empty-prefix framing is supported; do not guess how
   // a nonempty prefix changes the supported account-store interpretation.
   uint version=r.U32(),count=r.U32(),reserved=r.U32();if(version!=14||count>MaximumContainers||reserved!=0)throw new InvalidDataException("Unsupported WGS index framing/prefix.");
   string app=r.Text(256,false);if(app!=ApplicationId)throw new InvalidDataException("The index belongs to another application.");int headerTime=r.At;ulong time=r.U64();Date(time);int headerState=r.At;uint state=r.U32();string identity=r.Text(128,false);Guid parsed;
   if(!Guid.TryParseExact(identity,"D",out parsed)||parsed==Guid.Empty)throw new InvalidDataException("Invalid index identity GUID.");ulong limit=r.U64();var records=new List<StoreIndexRecord>();var logical=new HashSet<string>(StringComparer.OrdinalIgnoreCase);var storage=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
   for(uint i=0;i<count;i++) {
    int start=r.At;string name=r.Text(256,false),display=r.Text(1024,true),etag=r.Text(1024,true);int revisionAt=r.At;byte revision=r.U8();int flagsAt=r.At;uint flags=r.U32();int guidAt=r.At;string folder=GuidText(r.Bytes(16),0);int modifiedAt=r.At;ulong modified=r.U64();int reservedAt=r.At;ulong zero=r.U64();int totalAt=r.At;ulong total=r.U64();Date(modified);
    if(revision==0||(flags!=1&&flags!=2&&flags!=3&&flags!=5)||zero!=0||total>MaximumStoreBlobBytes||flags==3&&total!=0)throw new InvalidDataException("Unsupported/uncommitted index record state.");
    if(name.StartsWith("/",StringComparison.Ordinal)||name.EndsWith("/",StringComparison.Ordinal)||name.IndexOfAny(new[]{'\\',':'})>=0||name.Split('/').Any(s=>s.Length==0||s=="."||s==".."))throw new InvalidDataException("Malformed logical container name.");
    if(!logical.Add(name)||!storage.Add(folder))throw new InvalidDataException("Duplicate logical/container GUID binding.");
    byte[] raw=new byte[r.At-start];Buffer.BlockCopy(bytes,start,raw,0,raw.Length);records.Add(new StoreIndexRecord{LogicalContainerName=name,IndexDisplayName=display,OpaqueEtag=etag,StorageFolderGuid=folder,MetadataRevision=revision,OpaqueFlags=flags,IsDeleted=flags==3,IsActive=flags==1||flags==2||flags==5,FileTime=modified,Reserved=zero,TotalBlobBytes=total,FileOffset=start,RecordEnd=r.At,RecordBytes=raw.Length,MetadataRevisionByteOffset=revisionAt,StateU32Offset=flagsAt,StorageGuidOffset=guidAt,ModifiedFileTimeOffset=modifiedAt,ReservedOffset=reservedAt,TotalBlobBytesOffset=totalAt,RecordSha256=Hash(raw)});
   }
   if(!r.End)throw new InvalidDataException("Trailing bytes or index record-count mismatch.");return new StoreIndex{Version=version,HeaderReserved=reserved,HeaderFlags=state,OpaqueState=state,ApplicationId=app,OpaqueIdentityGuid=identity,FileTime=time,OpaqueLimit=limit,RawIndexBytes=(byte[])bytes.Clone(),HeaderRecordCountOffset=4,HeaderFlagsU32Offset=headerState,HeaderFileTimeOffset=headerTime,HeaderOpaqueStateOffset=headerState,Records=records.ToArray()};
  }
  public static StoreBlobMetadata[] ParseContainerMetadata(byte[] bytes) {
   return ParseContainerMetadata(bytes,1);
  }
  public static StoreBlobMetadata[] ParseContainerMetadata(byte[] bytes,uint recordState) {
   if(recordState!=1&&recordState!=2&&recordState!=5)throw new InvalidDataException("Unsupported metadata record state.");
   if(bytes==null||bytes.Length<8||bytes.Length>8+160*MaximumBlobsPerContainer)throw new InvalidDataException("Invalid container metadata size.");uint version=BitConverter.ToUInt32(bytes,0),count=BitConverter.ToUInt32(bytes,4);
   if(version!=4||count>MaximumBlobsPerContainer||bytes.Length!=8+160*(long)count)throw new InvalidDataException("Unsupported/truncated container metadata.");var result=new List<StoreBlobMetadata>();var names=new HashSet<string>(StringComparer.OrdinalIgnoreCase);var ids=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
   for(int i=0;i<count;i++) {
    int at=8+160*i,end=128;for(int p=0;p<128;p+=2)if(bytes[at+p]==0&&bytes[at+p+1]==0){end=p;break;}
    for(int p=end;p<128;p++)if(bytes[at+p]!=0)throw new InvalidDataException("Nonzero padding after a blob name.");string name=Wide.GetString(bytes,at,end);
    if(String.IsNullOrEmpty(name)||name.IndexOfAny(new[]{'\\','/',':','\0'})>=0||name.Any(c=>Char.IsControl(c)))throw new InvalidDataException("Invalid logical blob name.");
    bool emptyFirst=true;for(int p=0;p<16;p++)if(bytes[at+128+p]!=0)emptyFirst=false;
    string first=emptyFirst?null:GuidText(bytes,at+128),second=GuidText(bytes,at+144);
    // Proven pending-new-blob form: state2/5, remote slot zero, local slot
    // nonzero. Other differing nonzero pairs remain unsupported.
    if((emptyFirst?recordState==1:!Same(first,second))||!names.Add(name)||!ids.Add(second))throw new InvalidDataException("Ambiguous/duplicate blob GUID binding.");
    result.Add(new StoreBlobMetadata{LogicalName=name,StorageGuid=second,SecondGuid=second});
   }
   return result.ToArray();
  }
  public static string ParseProfileName(byte[] bytes) {
   if(bytes==null||bytes.Length<16||bytes.Length>MaximumSaveMetaBytes||(bytes.Length&1)!=0||bytes[0]!=0xff||bytes[1]!=0xfe)throw new InvalidDataException("Invalid SaveMeta UTF16LE BOM/framing.");string s=Wide.GetString(bytes,2,bytes.Length-2);
   if(!s.StartsWith("Name=",StringComparison.Ordinal)||!s.EndsWith("\r\n",StringComparison.Ordinal))throw new InvalidDataException("Invalid SaveMeta name record.");string name=s.Substring(5,s.Length-7);
   if(name.Length==0||name.Length>64||name.Any(c=>Char.IsControl(c)||c=='\ufeff'))throw new InvalidDataException("Invalid profile display name.");return name;
  }
  static string Token(params string[] values) {var s=new StringBuilder();foreach(string v in values){string x=v??"";s.Append(x.Length.ToString(CultureInfo.InvariantCulture)).Append(':').Append(x);}return Hash(Utf8.GetBytes(s.ToString()));}
  static string ContainerToken(StoreContainerEntry e) {if(e.IsDeleted)return Token("deleted-record-v14",e.LogicalContainerName,e.StorageFolderGuid,e.RecordSha256);var values=new List<string>{e.LogicalContainerName,e.StorageFolderGuid,e.RecordSha256,e.MetadataFileName,e.MetadataSha256,e.MetadataBytes.ToString(CultureInfo.InvariantCulture)};foreach(var b in e.Blobs.OrderBy(x=>x.LogicalName,StringComparer.Ordinal)){values.Add(b.LogicalName);values.Add(b.StorageGuid);values.Add(b.Bytes.ToString(CultureInfo.InvariantCulture));values.Add(b.Sha256);}return Token(values.ToArray());}
  static string FindUserRoot(string root,out string wgs) {
   string path=Full(root);GuardExistingAncestor(path);wgs=path;if(!Directory.Exists(path))return null;Guard(path,true);
   if(UserName.IsMatch(Path.GetFileName(path))&&File.Exists(Child(path,"containers.index"))){wgs=Path.GetDirectoryName(path);return path;}
   var users=new List<string>();foreach(string name in Names(path)) {string child=Child(path,name);if(!Directory.Exists(child))throw new InvalidDataException("Unexpected file in the WGS root.");if(name=="t")continue;if(!UserName.IsMatch(name))throw new InvalidDataException("Unrecognized WGS account-store directory.");if(!File.Exists(Child(child,"containers.index")))throw new InvalidDataException("Account store has no committed index.");users.Add(child);}
   if(users.Count==0)return null;if(users.Count!=1)throw new InvalidDataException("Multiple account stores are present; select one explicit store before a profile operation.");return users[0];
  }
  public static StoreSnapshot Scan(string root) {
   if(String.IsNullOrWhiteSpace(root))throw new ArgumentException("A WGS root is required.");string wgs,user=FindUserRoot(root,out wgs);
   if(user==null)return new StoreSnapshot{Available=false,WgsRoot=wgs,ContextToken=Token("empty-store-v1",wgs.ToUpperInvariant()),Containers=new StoreContainerEntry[0],Profiles=new ProfileEntry[0],CapturedUtc=DateTime.UtcNow.ToString("o")};
   string userName=Path.GetFileName(user),indexPath=Child(user,"containers.index");var files=new List<Fingerprint>();var dirs=new List<DirectoryFingerprint>();string[] userNames=TrackDirectory(user,dirs);byte[] indexBytes=Track(indexPath,MaximumIndexBytes,files);StoreIndex index=ParseIndex(indexBytes);
   string context=Token("CrimsonSkiesProfileStore/v1",user.ToUpperInvariant(),userName.ToUpperInvariant(),index.ApplicationId),indexHash=Hash(indexBytes);var containers=new List<StoreContainerEntry>();var profiles=new List<ProfileEntry>();var expectedDirs=new HashSet<string>(StringComparer.OrdinalIgnoreCase);long sum=0;
   foreach(var record in index.Records) {
    string folderName=userNames.SingleOrDefault(n=>Same(n,record.StorageFolderGuid));
    if(record.IsDeleted) {
     if(folderName!=null) {if(!GuidName.IsMatch(folderName)||!Directory.Exists(Child(user,folderName)))throw new InvalidDataException("Deleted storage GUID is not a guarded directory.");expectedDirs.Add(folderName);string deleted=Child(user,folderName);string[] remaining=TrackDirectory(deleted,dirs);if(remaining.Any(n=>Directory.Exists(Child(deleted,n))))throw new InvalidDataException("Nested directories in a deleted container are not supported.");}
     var tombstone=new StoreContainerEntry{LogicalContainerName=record.LogicalContainerName,StorageFolderGuid=record.StorageFolderGuid,StorageFolderName=folderName,StorageFolderPresent=folderName!=null,IsDeleted=true,IndexRecord=record,RecordSha256=record.RecordSha256,Blobs=new ProfileBlob[0],ModifiedUtc=Date(record.FileTime)};tombstone.RevisionToken=ContainerToken(tombstone);containers.Add(tombstone);continue;
    }
    if(folderName==null||!GuidName.IsMatch(folderName)||!Directory.Exists(Child(user,folderName)))throw new InvalidDataException("Index storage GUID has no matching folder.");expectedDirs.Add(folderName);string folder=Child(user,folderName),metadataName="container."+record.MetadataRevision.ToString(CultureInfo.InvariantCulture);string[] leafNames=TrackDirectory(folder,dirs);
    if(!leafNames.Contains(metadataName,StringComparer.Ordinal)||leafNames.Count(n=>n.StartsWith("container.",StringComparison.OrdinalIgnoreCase))!=1)throw new InvalidDataException("Missing, duplicate or stale container metadata revision.");
    byte[] metadata=Track(Child(folder,metadataName),8+160*MaximumBlobsPerContainer,files);var blobs=ParseContainerMetadata(metadata,record.OpaqueFlags);var expectedFiles=new HashSet<string>(StringComparer.OrdinalIgnoreCase){metadataName};var entries=new List<ProfileBlob>();byte[] saveMeta=null;long containerTotal=0;
    foreach(var blob in blobs) {
     string physical=leafNames.SingleOrDefault(n=>Same(n,blob.StorageGuid));if(physical==null||!GuidName.IsMatch(physical)||!File.Exists(Child(folder,physical)))throw new InvalidDataException("Blob storage GUID is missing or ambiguous.");expectedFiles.Add(physical);byte[] data=Track(Child(folder,physical),MaximumBlobBytes,files);checked{containerTotal+=data.LongLength;sum+=data.LongLength;}if(sum>MaximumStoreBlobBytes)throw new InvalidDataException("Store exceeds the complete snapshot bound.");
     entries.Add(new ProfileBlob{LogicalName=blob.LogicalName,StorageGuid=blob.StorageGuid,StorageFileName=physical,Bytes=data.LongLength,Sha256=Hash(data)});if(blob.LogicalName=="SaveMeta.xbx00")saveMeta=data;
    }
    if(leafNames.Length!=expectedFiles.Count||leafNames.Any(n=>!expectedFiles.Contains(n))||leafNames.Any(n=>Directory.Exists(Child(folder,n))))throw new InvalidDataException("Unindexed/stale files remain in a container.");if((ulong)containerTotal!=record.TotalBlobBytes)throw new InvalidDataException("Index byte total does not match the bound blobs.");
    var entry=new StoreContainerEntry{LogicalContainerName=record.LogicalContainerName,StorageFolderGuid=record.StorageFolderGuid,StorageFolderName=folderName,StorageFolderPresent=true,IsDeleted=false,MetadataFileName=metadataName,MetadataSha256=Hash(metadata),MetadataBytes=metadata.LongLength,RecordSha256=record.RecordSha256,IndexRecord=record,Blobs=entries.ToArray(),ModifiedUtc=Date(record.FileTime)};entry.RevisionToken=ContainerToken(entry);containers.Add(entry);
    if(ProfileName.IsMatch(record.LogicalContainerName)) {
     if(entries.Count!=2||!entries.Any(x=>x.LogicalName=="CrimsonData.txt00"&&x.Bytes>0)||!entries.Any(x=>x.LogicalName=="SaveMeta.xbx00")||saveMeta==null)throw new InvalidDataException("Profile container does not have its exact two-blob schema.");string display=ParseProfileName(saveMeta),stable=Token("profile-v1",context,entry.LogicalContainerName,entry.StorageFolderGuid);
     foreach(var blob in entry.Blobs)blob.ProfileStableId=stable;
     profiles.Add(new ProfileEntry{StableId=stable,LogicalContainerName=entry.LogicalContainerName,StorageFolderGuid=entry.StorageFolderGuid,StorageFolderName=folderName,DisplayName=display,ModifiedUtc=entry.ModifiedUtc,ContextToken=context,RevisionToken=entry.RevisionToken,UserRoot=user,MetadataFileName=entry.MetadataFileName,MetadataSha256=entry.MetadataSha256,MetadataBytes=entry.MetadataBytes,Blobs=entry.Blobs});
    }
   }
   if(userNames.Any(n=>n!="containers.index"&&!expectedDirs.Contains(n))||userNames.Length!=expectedDirs.Count+1)throw new InvalidDataException("Unindexed/stale container directories remain in the account store.");
   if(profiles.Select(p=>p.DisplayName).Distinct(StringComparer.OrdinalIgnoreCase).Count()!=profiles.Count)throw new InvalidDataException("Duplicate display names require explicit disambiguation before profile operations.");
   // Optimistic coherent snapshot: every directory membership and every byte
   // hash must be unchanged in a second pass. This is not a cloud lock.
   foreach(var d in dirs)if(!Names(d.Path).SequenceEqual(d.Names,StringComparer.Ordinal))throw new IOException("Store membership changed while listing.");
   foreach(var f in files){byte[] now=ReadBounded(f.Path,f.Limit);if(now.LongLength!=f.Bytes||Hash(now)!=f.Hash)throw new IOException("Store bytes changed while listing.");}
   string digest=Token(new[]{"store-snapshot-v1",context,indexHash}.Concat(containers.OrderBy(c=>c.LogicalContainerName,StringComparer.Ordinal).Select(c=>c.RevisionToken)).ToArray());foreach(var p in profiles)p.StoreRevisionToken=digest;
   return new StoreSnapshot{Available=true,WgsRoot=wgs,UserRoot=user,UserStoreName=userName,AccountIdHex=userName.Substring(0,16).ToUpperInvariant(),StorageSpaceId=userName.Substring(17).ToUpperInvariant(),ApplicationId=index.ApplicationId,ContextToken=context,SnapshotDigest=digest,IndexPath=indexPath,IndexSha256=indexHash,IndexBytes=indexBytes.LongLength,Index=index,Containers=containers.ToArray(),Profiles=profiles.OrderBy(p=>p.DisplayName,StringComparer.OrdinalIgnoreCase).ThenBy(p=>p.StableId,StringComparer.Ordinal).ToArray(),CapturedUtc=DateTime.UtcNow.ToString("o")};
  }
  public static StoreSnapshot Revalidate(StoreSnapshot expected) {
   if(expected==null||!expected.Available||expected.UserRoot==null)throw new InvalidDataException("There is no selected committed store to revalidate.");var current=Scan(expected.UserRoot);if(!current.Available||current.ContextToken!=expected.ContextToken||current.SnapshotDigest!=expected.SnapshotDigest)throw new IOException("The selected store changed. Refresh profiles before continuing.");return current;
  }
  public static byte[] ReadValidatedBlob(ProfileEntry entry,ProfileBlob requested) {
   if(entry==null||requested==null||entry.UserRoot==null||requested.ProfileStableId!=entry.StableId)throw new InvalidDataException("The blob does not belong to the selected profile.");var snapshot=Scan(entry.UserRoot);
   if(snapshot.ContextToken!=entry.ContextToken||snapshot.SnapshotDigest!=entry.StoreRevisionToken)throw new IOException("The selected store changed. Refresh profiles before backup.");var profile=snapshot.Profiles.SingleOrDefault(p=>p.StableId==entry.StableId);
   if(profile==null||profile.RevisionToken!=entry.RevisionToken||profile.LogicalContainerName!=entry.LogicalContainerName||!Same(profile.StorageFolderGuid,entry.StorageFolderGuid))throw new InvalidDataException("The selected profile identity no longer matches.");
   var blob=profile.Blobs.SingleOrDefault(b=>b.LogicalName==requested.LogicalName);
   if(blob==null||!Same(blob.StorageGuid,requested.StorageGuid)||!Same(blob.StorageFileName,requested.StorageFileName)||blob.Bytes!=requested.Bytes||blob.Sha256!=requested.Sha256)throw new InvalidDataException("The requested blob descriptor was not captured for this profile.");
   string path=Child(Child(snapshot.UserRoot,profile.StorageFolderName),blob.StorageFileName);byte[] bytes=ReadBounded(path,MaximumBlobBytes);if(bytes.LongLength!=blob.Bytes||Hash(bytes)!=blob.Sha256)throw new IOException("The selected blob changed during reading.");Revalidate(snapshot);return bytes;
  }
 }
}
