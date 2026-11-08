// SPDX-License-Identifier: MIT
using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

namespace CrimsonSkiesMultilingual {
 internal sealed class ProfileRestoreOutcome {public string ProfileId,RestoredProfileId,BackupPath;public bool PendingCloudSync;}
 internal sealed partial class ProfileOperations {
  internal static void ValidateRestoreCandidate(StoreSnapshot snapshot,VerifiedProfileBackup backup) {
   if(snapshot==null||!snapshot.Available||backup==null||snapshot.ContextToken!=backup.ContextToken||snapshot.AccountIdHex!=backup.AccountIdHex||!Same(snapshot.StorageSpaceId,backup.StorageSpaceId))throw new IOException("원래 계정과 저장소에서만 복원할 수 있습니다. / Restore requires the original account and save-store context.");
   var existing=snapshot.Index.Records.SingleOrDefault(r=>Same(r.LogicalContainerName,backup.LogicalContainerName));
   if(existing!=null&&!existing.IsDeleted||snapshot.Profiles.Any(p=>Same(p.DisplayName,backup.ProfileName)))throw new IOException("같은 프로필이 이미 있습니다. 덮어쓰지 않습니다. / This profile already exists; overwrite is not supported.");
   if(snapshot.Index.Records.Any(r=>Same(r.StorageFolderGuid,backup.StorageFolderGuid)&&r!=existing))throw new IOException("The backup storage identity belongs to another container.");
   if(existing!=null&&Directory.Exists(PackEngine.Child(snapshot.UserRoot,existing.StorageFolderGuid)))throw new IOException("삭제 동기화를 마친 뒤 다시 시도하세요. / Synchronize the pending deletion before restoring its remaining directory.");
   // Read-only preflight includes framing/order/revision/size gates.
   string folder=existing==null?Guid.NewGuid().ToString("N").ToUpperInvariant():existing.StorageFolderGuid;
   ProfileRestoreImage.Build(snapshot.Index.RawIndexBytes,backup,folder,Guid.NewGuid().ToString("N"),Guid.NewGuid().ToString("N"),(ulong)DateTime.UtcNow.ToFileTimeUtc());
  }
  VerifiedProfileBackup KeepImportedBackup(VerifiedProfileBackup selected) {
   byte[] bytes=Read(selected.FilePath,(int)ProfileBackup.MaximumArchiveBytes);if(ProfileStore.Hash(bytes)!=selected.Sha256)throw new IOException("The selected ZIP changed after inspection.");
   MakeDirectory(BackupBase);string path=Path.Combine(BackupBase,Guid.NewGuid().ToString("N")+".zip");SaveNew(path,bytes);var owned=ProfileBackup.Verify(path);
   if(owned.Sha256!=selected.Sha256||owned.ProfileId!=selected.ProfileId||owned.ContextToken!=selected.ContextToken)throw new IOException("The retained restore backup did not match the selected ZIP.");return owned;
  }
  static void VerifyRestoreDirectory(string directory,ProfileRestorePlan plan) {
   Guard(directory,true);string[] actual=Directory.GetFileSystemEntries(directory).Select(Path.GetFileName).OrderBy(x=>x,StringComparer.Ordinal).ToArray();
   if(!actual.SequenceEqual(plan.Files.Select(f=>f.PhysicalFileName).OrderBy(x=>x,StringComparer.Ordinal),StringComparer.Ordinal))throw new IOException("Restored profile directory membership changed.");
   foreach(var f in plan.Files){string p=PackEngine.Child(directory,f.PhysicalFileName);Guard(p,false);if(new FileInfo(p).Length!=f.Bytes||HashFile(p,ProfileStore.MaximumBlobBytes)!=f.Sha256)throw new IOException("Restored profile data changed.");}
  }
  ProfileRestorePlan RestorePlan(ProfileTransaction tx,VerifiedProfileBackup backup) {return ProfileRestoreImage.Build(Read(Path.Combine(TransactionFolder(tx.Id),"before.index"),ProfileStore.MaximumIndexBytes),backup,tx.StorageGuid,tx.RestoreDataGuid,tx.RestoreNameGuid,tx.RestoreFileTime);}
  void PrepareRestoredDirectory(string dir,VerifiedProfileBackup backup,ProfileRestorePlan plan) {
   string materialized=Path.Combine(dir,"import-source"),prepared=Path.Combine(dir,"prepared");ProfileBackup.Materialize(backup,materialized);
   if(Directory.Exists(prepared)||File.Exists(prepared))throw new IOException("Restore staging already exists.");Directory.CreateDirectory(prepared);Guard(prepared,true);
   foreach(var f in plan.Files) {
    byte[] data=f.SourceFileName==null?plan.Metadata:Read(PackEngine.Child(materialized,f.SourceFileName),ProfileStore.MaximumBlobBytes);
    if(data.LongLength!=f.Bytes||ProfileStore.Hash(data)!=f.Sha256)throw new IOException("Restore staging differs from the verified backup.");SaveNew(PackEngine.Child(prepared,f.PhysicalFileName),data);
   }
   VerifyRestoreDirectory(prepared,plan);
  }
  public ProfileRestoreOutcome RestoreFromBackup(VerifiedProfileBackup selected,StoreSnapshot expected,IProgress<string> progress) {return Locked(delegate {
   requireStopped();if(HasPending)throw new IOException("Recover the interrupted profile operation first.");
   var external=ProfileBackup.Verify(selected.FilePath);if(external.Sha256!=selected.Sha256||external.ProfileId!=selected.ProfileId||external.ContextToken!=selected.ContextToken)throw new IOException("The selected backup changed after preview.");
   var before=ProfileStore.Scan(wgsRoot);if(expected==null||before.ContextToken!=expected.ContextToken||before.SnapshotDigest!=expected.SnapshotDigest)throw new IOException("The save store changed after preview. Inspect the ZIP again.");ValidateRestoreCandidate(before,external);
   var backup=KeepImportedBackup(external);fault("restore-after-backup");requireStopped();ProfileStore.Revalidate(before);
   var old=before.Index.Records.SingleOrDefault(r=>Same(r.LogicalContainerName,backup.LogicalContainerName));string folder=old==null?Guid.NewGuid().ToString("N").ToUpperInvariant():old.StorageFolderGuid;
   if(Directory.Exists(PackEngine.Child(before.UserRoot,folder))||File.Exists(PackEngine.Child(before.UserRoot,folder)))throw new IOException("The restore destination is not absent.");
   string id=Guid.NewGuid().ToString("N");MakeDirectory(scopeRoot);string dir=TransactionFolder(id);Directory.CreateDirectory(dir);Guard(dir,true);
   var tx=new ProfileTransaction{Schema=1,Kind="restore",Id=id,WgsRoot=wgsRoot,UserRoot=before.UserRoot,ContextToken=before.ContextToken,ProfileId=backup.ProfileId,LogicalName=backup.LogicalContainerName,StorageGuid=folder,BackupPath=backup.FilePath,BackupSha256=backup.Sha256,BeforeHash=before.IndexSha256,OtherContainers=OtherTokens(before,backup.LogicalContainerName),RestoreDataGuid=Guid.NewGuid().ToString("N").ToUpperInvariant(),RestoreNameGuid=Guid.NewGuid().ToString("N").ToUpperInvariant(),RestoreFileTime=(ulong)DateTime.UtcNow.ToFileTimeUtc()};
   var plan=ProfileRestoreImage.Build(before.Index.RawIndexBytes,backup,tx.StorageGuid,tx.RestoreDataGuid,tx.RestoreNameGuid,tx.RestoreFileTime);tx.AfterHash=ProfileStore.Hash(plan.IndexImage);
   PrepareRestoredDirectory(dir,backup,plan);fault("restore-after-staging");requireStopped();ProfileStore.Revalidate(before);
   byte[] key=new byte[32];using(var rng=RandomNumberGenerator.Create())rng.GetBytes(key);SaveNew(Path.Combine(dir,"atomic-key.bin"),ProtectedData.Protect(key,AtomicEntropy(tx),DataProtectionScope.CurrentUser));Array.Clear(key,0,key.Length);
   SaveNew(Path.Combine(dir,"before.index"),before.Index.RawIndexBytes);SaveNew(Path.Combine(dir,"after.index"),plan.IndexImage);SaveNew(Path.Combine(dir,"transaction.json"),Utf8.GetBytes(json.Serialize(tx)));SaveNew(ActivePath,Utf8.GetBytes(json.Serialize(new ProfileActiveTransaction{Schema=1,Id=id})));fault("restore-after-journal");
   try {
    requireStopped();ProfileStore.Revalidate(before);VerifyRestoreDirectory(Path.Combine(dir,"prepared"),plan);fault("restore-before-index");
    ReplaceIndex(tx,plan.IndexImage,tx.BeforeHash,Path.Combine(dir,"actual-before.index"));fault("restore-after-index");
    requireStopped();if(HashFile(Path.Combine(tx.UserRoot,"containers.index"),ProfileStore.MaximumIndexBytes)!=tx.AfterHash)throw new IOException("The save index changed before restoring the directory.");
    fault("restore-before-directory-move");MoveBound(Path.Combine(dir,"prepared"),Source(tx),dir,tx.UserRoot);fault("restore-after-directory-move");
    var after=VerifyRestoredState(tx,plan,backup);fault("restore-before-finish");requireStopped();VerifyRestoredState(tx,plan,backup);ClearActive(tx);
    if(progress!=null)progress.Report("선택한 프로필 복원과 다른 프로필 보존을 확인했습니다. / Selected profile restored; other profiles verified.");
    return new ProfileRestoreOutcome{ProfileId=backup.ProfileId,RestoredProfileId=after.Profiles.Single(p=>Same(p.LogicalContainerName,tx.LogicalName)).StableId,BackupPath=backup.FilePath,PendingCloudSync=true};
   } catch(Exception original) {
    if(HasPending)try{RecoverCore(tx);if(progress!=null)progress.Report("중단된 복원 작업을 일관된 상태로 복구했습니다. / Interrupted restore recovered.");}
    catch(Exception recovery){throw new IOException("Restore needs explicit recovery. The selected ZIP and owned backup are retained.\r\nOriginal: "+original.Message+"\r\nRecovery: "+recovery.Message,original);}
    throw;
   }
  });}
  StoreSnapshot VerifyRestoredState(ProfileTransaction tx,ProfileRestorePlan plan,VerifiedProfileBackup backup) {
   VerifyRestoreDirectory(Source(tx),plan);var s=ProfileStore.Scan(wgsRoot);var selected=s.Profiles.SingleOrDefault(p=>Same(p.LogicalContainerName,tx.LogicalName));
   if(s.ContextToken!=tx.ContextToken||s.IndexSha256!=tx.AfterHash||!OtherTokens(s,tx.LogicalName).SequenceEqual(tx.OtherContainers,StringComparer.Ordinal)||selected==null||!Same(selected.StorageFolderGuid,tx.StorageGuid)||selected.DisplayName!=backup.ProfileName)throw new IOException("Restored profile or other profiles did not match the verified plan.");return s;
  }
  void MoveRestoredOut(ProfileTransaction tx,ProfileRestorePlan plan) {
   string source=Source(tx),dir=TransactionFolder(tx.Id),removed=Path.Combine(dir,"restore-removed");
   if(Directory.Exists(source)){VerifyRestoreDirectory(source,plan);MoveBound(source,removed,tx.UserRoot,dir);}
   else if(File.Exists(source))throw new IOException("The selected restore directory became a file.");
   if(Directory.Exists(removed))VerifyRestoreDirectory(removed,plan);
  }
  void ResolveRestoreConcurrent(ProfileTransaction tx,ProfileRestorePlan plan) {
   requireStopped();string indexPath=Path.Combine(tx.UserRoot,"containers.index");byte[] latest=Read(indexPath,ProfileStore.MaximumIndexBytes);var index=ProfileStore.ParseIndex(latest);
   var reference=index.Records.SingleOrDefault(r=>Same(r.StorageFolderGuid,tx.StorageGuid));
   if(reference!=null&&reference.IsActive) {
    var planned=ProfileStore.ParseIndex(plan.IndexImage).Records.Single(r=>Same(r.LogicalContainerName,tx.LogicalName));
    if(reference.LogicalContainerName!=planned.LogicalContainerName||reference.RecordSha256!=planned.RecordSha256)throw new IOException("The provider now owns changed restored-profile data. Recovery will not overwrite it.");
    if(!Directory.Exists(Source(tx))) {
     string dir=TransactionFolder(tx.Id),removed=Path.Combine(dir,"restore-removed"),prepared=Path.Combine(dir,"prepared");string ready=Directory.Exists(removed)?removed:prepared;
     VerifyRestoreDirectory(ready,plan);MoveBound(ready,Source(tx),dir,tx.UserRoot);
    } else VerifyRestoreDirectory(Source(tx),plan);
   } else MoveRestoredOut(tx,plan);
   var verified=ProfileStore.Scan(wgsRoot);if(verified.ContextToken!=tx.ContextToken||verified.IndexSha256!=ProfileStore.Hash(latest))throw new IOException("The provider changed during restore recovery.");ClearActive(tx);
  }
  void RecoverRestore(ProfileTransaction tx) {
   var backup=ProfileBackup.Verify(tx.BackupPath);var plan=RestorePlan(tx,backup);if(RecoverAtomic(tx,true)){ResolveRestoreConcurrent(tx,plan);return;}
   string index=Path.Combine(tx.UserRoot,"containers.index"),dir=TransactionFolder(tx.Id);string actual=HashFile(index,ProfileStore.MaximumIndexBytes);
   if(actual!=tx.BeforeHash&&actual!=tx.AfterHash)throw new IOException("The provider changed the index outside this restore. Recovery will not overwrite it.");
   MoveRestoredOut(tx,plan);fault("restore-recovery-after-directory");requireStopped();
   if(actual==tx.AfterHash) {
    try{ReplaceIndex(tx,Read(Path.Combine(dir,"before.index"),ProfileStore.MaximumIndexBytes),tx.AfterHash,Path.Combine(dir,"rollback-capture-"+Guid.NewGuid().ToString("N")+".index"));}
    catch(ReplacedConcurrentIndexException){if(!RecoverAtomic(tx,true))throw;ResolveRestoreConcurrent(tx,plan);return;}
   }
   var restored=ProfileStore.Scan(wgsRoot);if(restored.ContextToken!=tx.ContextToken||restored.IndexSha256!=tx.BeforeHash||!OtherTokens(restored,tx.LogicalName).SequenceEqual(tx.OtherContainers,StringComparer.Ordinal)||Directory.Exists(Source(tx)))throw new IOException("Restore rollback verification failed.");ClearActive(tx);
  }
 }
}
