// SPDX-License-Identifier: MIT
using System;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

namespace CrimsonSkiesMultilingual {
 internal sealed class ProfileRestoreFile {
  public string PhysicalFileName,SourceFileName,Sha256;
  public long Bytes;
 }
 internal sealed class ProfileRestorePlan {
  public string LogicalName,StorageGuid,MetadataFileName;
  public byte[] IndexImage,Metadata;
  public ProfileRestoreFile[] Files;
 }
 // Pure, bounded v14/v4 serialization. No filesystem or provider operations.
 internal static class ProfileRestoreImage {
  static bool Same(string a,string b){return String.Equals(a,b,StringComparison.OrdinalIgnoreCase);}
  static string GuidLeaf(string value){Guid g;if(!Guid.TryParseExact(value,"N",out g)||g==Guid.Empty)throw new InvalidDataException("Invalid restore GUID.");return g.ToString("N").ToUpperInvariant();}
  static void Text(BinaryWriter w,string value){if(value==null)throw new InvalidDataException("Missing restore text.");w.Write((uint)value.Length);w.Write(Encoding.Unicode.GetBytes(value));}
  internal static byte[] BuildContainerImage(byte[] before,string logicalName,string displayName,string folderGuid,ulong total,ulong fileTime) {
   var index=ProfileStore.ParseIndex(before);var current=index.Records.SingleOrDefault(r=>Same(r.LogicalContainerName,logicalName));folderGuid=GuidLeaf(folderGuid);
   for(int i=1;i<index.Records.Length;i++)if(StringComparer.Ordinal.Compare(index.Records[i-1].LogicalContainerName,index.Records[i].LogicalContainerName)>=0)throw new InvalidDataException("Synchronize the unsorted container index before restoring.");
   if(index.HeaderFlags>3||(((index.HeaderFlags&1)==0)!=index.Records.Any(r=>r.OpaqueFlags==2||r.OpaqueFlags==3||r.OpaqueFlags==5)))throw new InvalidDataException("The store is not at a coherent committed boundary.");
   if(current!=null&&(!current.IsDeleted||!Same(current.StorageFolderGuid,folderGuid)))throw new IOException("An existing active profile cannot be overwritten.");
   if(index.Records.Any(r=>Same(r.StorageFolderGuid,folderGuid)&&r!=current))throw new IOException("The restore storage GUID is already in use.");
   if(current==null&&index.Records.Length>=ProfileStore.MaximumContainers)throw new IOException("The store has reached its container limit.");
   byte revision=current==null?(byte)1:NextRevision(current.MetadataRevision);
   byte[] record;using(var m=new MemoryStream())using(var w=new BinaryWriter(m)) {
    Text(w,current==null?logicalName:current.LogicalContainerName);Text(w,current==null?displayName:current.IndexDisplayName);Text(w,current==null?"":current.OpaqueEtag);
    w.Write(revision);w.Write(current==null?(uint)5:(uint)2);w.Write(Guid.ParseExact(folderGuid,"N").ToByteArray());w.Write(fileTime);w.Write((ulong)0);w.Write(total);record=m.ToArray();
   }
   var following=current==null?index.Records.FirstOrDefault(r=>StringComparer.Ordinal.Compare(r.LogicalContainerName,logicalName)>0):null;
   int at=current==null?(following==null?before.Length:following.FileOffset):current.FileOffset,oldLength=current==null?0:current.RecordBytes;
   int length=checked(before.Length-oldLength+record.Length);if(length>ProfileStore.MaximumIndexBytes)throw new IOException("The restored index would exceed its bound.");
   var after=new byte[length];Buffer.BlockCopy(before,0,after,0,at);Buffer.BlockCopy(record,0,after,at,record.Length);Buffer.BlockCopy(before,at+oldLength,after,at+record.Length,before.Length-at-oldLength);
   if(current==null)Buffer.BlockCopy(BitConverter.GetBytes((uint)(index.Records.Length+1)),0,after,index.HeaderRecordCountOffset,4);
   Buffer.BlockCopy(BitConverter.GetBytes(index.HeaderFlags&~1u),0,after,index.HeaderFlagsU32Offset,4);
   var check=ProfileStore.ParseIndex(after);if(check.FileTime!=index.FileTime||check.Records.Length!=index.Records.Length+(current==null?1:0))throw new InvalidDataException("Invalid restore index header.");
   foreach(var original in index.Records.Where(r=>r!=current))if(check.Records.Single(r=>r.LogicalContainerName==original.LogicalContainerName).RecordSha256!=original.RecordSha256)throw new InvalidDataException("Restore changed an unselected index record.");
   return after;
  }
  static byte NextRevision(byte old){if(old==254)throw new IOException("Synchronize this deleted container before restoring its metadata revision.");return (byte)(((int)old+1)%255);}
  internal static byte[] BuildMetadata(string[] names,string[] localGuids) {
   if(names==null||localGuids==null||names.Length!=localGuids.Length||names.Length<1||names.Length>128||names.Distinct(StringComparer.OrdinalIgnoreCase).Count()!=names.Length||localGuids.Distinct(StringComparer.OrdinalIgnoreCase).Count()!=localGuids.Length)throw new InvalidDataException("Invalid restored blob set.");
   using(var m=new MemoryStream())using(var w=new BinaryWriter(m)) {
    w.Write((uint)4);w.Write((uint)names.Length);
    for(int i=0;i<names.Length;i++) {string name=names[i];if(String.IsNullOrEmpty(name)||name.Length>=64||name.Any(c=>Char.IsControl(c))||name.IndexOfAny(new[]{'\\','/',':'})>=0)throw new InvalidDataException("Invalid restored blob name.");var padded=new byte[128];byte[] text=Encoding.Unicode.GetBytes(name);Buffer.BlockCopy(text,0,padded,0,text.Length);w.Write(padded);w.Write(new byte[16]);w.Write(Guid.ParseExact(GuidLeaf(localGuids[i]),"N").ToByteArray());}
    return m.ToArray();
   }
  }
  internal static ProfileRestorePlan Build(byte[] before,VerifiedProfileBackup backup,string folderGuid,string dataGuid,string nameGuid,ulong fileTime) {
   if(backup==null||!Regex.IsMatch(backup.LogicalContainerName??"","^U4d530021/[0-9a-fA-F]{12}$"))throw new InvalidDataException("Only a verified native profile backup can be restored.");
   folderGuid=GuidLeaf(folderGuid);dataGuid=GuidLeaf(dataGuid);nameGuid=GuidLeaf(nameGuid);if(dataGuid==nameGuid)throw new InvalidDataException("Restored blob GUIDs must be distinct.");
   var blobs=backup.Files.Where(f=>f.Kind=="blob").OrderBy(f=>f.LogicalName,StringComparer.Ordinal).ToArray();if(blobs.Length!=2||blobs[0].LogicalName!="CrimsonData.txt00"||blobs[1].LogicalName!="SaveMeta.xbx00")throw new InvalidDataException("Unexpected selected backup blob schema.");
   var index=ProfileStore.ParseIndex(before);var current=index.Records.SingleOrDefault(r=>Same(r.LogicalContainerName,backup.LogicalContainerName));
   if(index.Records.Any(r=>Same(r.StorageFolderGuid,backup.StorageFolderGuid)&&r!=current))throw new IOException("The original backup storage identity is used by another container.");
   byte[] metadata=BuildMetadata(blobs.Select(f=>f.LogicalName).ToArray(),new[]{dataGuid,nameGuid});byte revision=current==null?(byte)1:NextRevision(current.MetadataRevision);
   var plan=new ProfileRestorePlan{LogicalName=backup.LogicalContainerName,StorageGuid=folderGuid,MetadataFileName="container."+revision.ToString(CultureInfo.InvariantCulture),Metadata=metadata};
   plan.IndexImage=BuildContainerImage(before,backup.LogicalContainerName,backup.IndexDisplayName,folderGuid,checked((ulong)blobs.Sum(f=>f.Bytes)),fileTime);
   plan.Files=new[]{new ProfileRestoreFile{PhysicalFileName=plan.MetadataFileName,Bytes=metadata.LongLength,Sha256=ProfileStore.Hash(metadata)},new ProfileRestoreFile{PhysicalFileName=dataGuid,SourceFileName=blobs[0].PhysicalFileName,Bytes=blobs[0].Bytes,Sha256=blobs[0].Sha256},new ProfileRestoreFile{PhysicalFileName=nameGuid,SourceFileName=blobs[1].PhysicalFileName,Bytes=blobs[1].Bytes,Sha256=blobs[1].Sha256}};
   return plan;
  }
 }
}
