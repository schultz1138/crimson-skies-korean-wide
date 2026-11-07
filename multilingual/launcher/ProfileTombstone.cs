// SPDX-License-Identifier: MIT
using System;
using System.IO;
using System.Linq;

namespace CrimsonSkiesMultilingual {
 // Pure format transformation. The production caller additionally requires a
 // selected, revalidated two-blob Crimson Skies profile and a verified backup.
 public static class ProfileTombstone {
  public static byte[] BuildIndexImage(byte[] before,string logicalName,string storageGuid) {
   StoreIndex index=ProfileStore.ParseIndex(before);
   var target=index.Records.SingleOrDefault(r=>r.LogicalContainerName==logicalName&&String.Equals(r.StorageFolderGuid,storageGuid,StringComparison.OrdinalIgnoreCase));
   if(target==null||(target.OpaqueFlags!=1&&target.OpaqueFlags!=2&&target.OpaqueFlags!=5))throw new InvalidDataException("Only a committed active container can be selected.");
   if(index.HeaderFlags>3)throw new InvalidDataException("Unsupported store header flags.");
   bool dirty=index.Records.Any(r=>r.OpaqueFlags==2||r.OpaqueFlags==3||r.OpaqueFlags==5);
   if(((index.HeaderFlags&1)==0)!=dirty)throw new InvalidDataException("The store is not at a coherent committed boundary.");
   byte[] after=(byte[])before.Clone();
   Put(after,target.StateU32Offset,BitConverter.GetBytes((uint)3));
   Put(after,target.TotalBlobBytesOffset,BitConverter.GetBytes((ulong)0));
   Put(after,index.HeaderFlagsU32Offset,BitConverter.GetBytes(index.HeaderFlags&~1u));
   for(int i=0;i<before.Length;i++)if(before[i]!=after[i]&&!Within(i,target.StateU32Offset,4)&&!Within(i,target.TotalBlobBytesOffset,8)&&!Within(i,index.HeaderFlagsU32Offset,4))throw new InvalidDataException("The profile plan changed an unrelated byte.");
   StoreIndex check=ProfileStore.ParseIndex(after);
   if(check.Records.Length!=index.Records.Length||check.FileTime!=index.FileTime||check.HeaderFlags!=(index.HeaderFlags&~1u))throw new InvalidDataException("Invalid tombstone header.");
   foreach(var old in index.Records) {
    var current=check.Records.Single(r=>r.LogicalContainerName==old.LogicalContainerName);
    if(old==target) {if(current.OpaqueFlags!=3||current.TotalBlobBytes!=0||current.StorageFolderGuid!=old.StorageFolderGuid||current.FileTime!=old.FileTime)throw new InvalidDataException("Invalid selected tombstone.");}
    else if(current.RecordSha256!=old.RecordSha256)throw new InvalidDataException("An unselected container changed.");
   }
   return after;
  }
  static bool Within(int p,int start,int length) {return p>=start&&p<start+length;}
  static void Put(byte[] bytes,int at,byte[] value) {if(at<0||at>bytes.Length-value.Length)throw new InvalidDataException("Invalid index field boundary.");Buffer.BlockCopy(value,0,bytes,at,value.Length);}
 }
}
