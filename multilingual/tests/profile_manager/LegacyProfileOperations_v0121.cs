// SPDX-License-Identifier: MIT
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Security.Cryptography;
using System.Threading;
using System.Web.Script.Serialization;

namespace CrimsonSkiesMultilingual {
 internal sealed class ProfileTransaction {
  public int Schema;
  public string Id,WgsRoot,UserRoot,ContextToken,ProfileId,LogicalName,StorageGuid;
  public string BackupPath,BackupSha256,BeforeHash,AfterHash;
  public string[] OtherContainers;
 }
 internal sealed class ProfileActiveTransaction { public int Schema; public string Id; }
 internal sealed class ProfileAtomicIntent { public int Schema; public string ExpectedHash,DesiredHash,CaptureLeaf,ImageLeaf,Mac; public bool PreserveConcurrent; }
 internal sealed class ProfileDeleteOutcome { public string ProfileId,BackupPath; public bool PendingCloudSync; }
 internal sealed class ReplacedConcurrentIndexException : IOException {
  public ReplacedConcurrentIndexException():base("The save index changed concurrently; its actual previous version was preserved. Refresh profiles."){}
 }

 // Owns only one selected native profile directory and its three committed
 // index fields. It never issues whole-store delete/import/replace commands.
 internal sealed class ProfileOperations {
  readonly string wgsRoot,stateRoot,scopeRoot;
  readonly Action requireStopped;
  readonly Action<string> fault;
  readonly JavaScriptSerializer json=new JavaScriptSerializer{MaxJsonLength=2097152,RecursionLimit=32};
  static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
  static readonly Regex IdPattern=new Regex("^[0-9a-f]{32}$",RegexOptions.CultureInvariant);
  static readonly Regex ProfilePattern=new Regex("^U4d530021/[0-9a-fA-F]{12}$",RegexOptions.CultureInvariant);
  public ProfileOperations(string wgs,string state,Action stopped,Action<string> faultHook=null) {
   wgsRoot=Full(wgs);stateRoot=Full(state);requireStopped=stopped??delegate{};fault=faultHook??delegate{};
   scopeRoot=Path.Combine(stateRoot,"Transactions",ProfileStore.Hash(Utf8.GetBytes(wgsRoot.ToUpperInvariant())).Substring(0,16));
   GuardAncestor(wgsRoot);GuardAncestor(stateRoot);
  }
  public string BackupBase { get {return Path.Combine(stateRoot,"Backups");} }
  string ActivePath {get{return Path.Combine(scopeRoot,"active.json");}}
  public bool HasPending {get{GuardAncestor(scopeRoot);if(!Directory.Exists(scopeRoot))return false;Guard(scopeRoot,true);if(Directory.Exists(ActivePath))throw new IOException("Invalid recovery pointer.");if(File.Exists(ActivePath)){Guard(ActivePath,false);return true;}return false;}}
  static string Full(string p) {return Path.GetFullPath(p).TrimEnd('\\','/');}
  static void Guard(string p,bool directory) {PackEngine.NoReparse(p,directory);}
  static void GuardAncestor(string p) {p=Path.GetFullPath(p);while(!Directory.Exists(p)){if(File.Exists(p))throw new IOException("A required directory is a file.");p=Path.GetDirectoryName(p);if(String.IsNullOrEmpty(p))throw new IOException("Invalid directory.");}Guard(p,true);}
  static void MakeDirectory(string p) {if(Directory.Exists(p)){Guard(p,true);return;}GuardAncestor(p);Directory.CreateDirectory(p);Guard(p,true);}
  static byte[] Read(string p,int max) {Guard(p,false);if(new FileInfo(p).Length>max)throw new IOException("Recovery file exceeds its bound.");return File.ReadAllBytes(p);}
  static string HashFile(string p,int max) {return ProfileStore.Hash(Read(p,max));}
  static bool Same(string a,string b) {return String.Equals(a,b,StringComparison.OrdinalIgnoreCase);}
  static string ContextFor(string user,string application) {var b=new StringBuilder();foreach(string value in new[]{"CrimsonSkiesProfileStore/v1",user.ToUpperInvariant(),Path.GetFileName(user).ToUpperInvariant(),application})b.Append(value.Length.ToString(CultureInfo.InvariantCulture)).Append(':').Append(value);return ProfileStore.Hash(Utf8.GetBytes(b.ToString()));}
  static void SaveNew(string p,byte[] bytes) {Guard(Path.GetDirectoryName(p),true);using(var f=new FileStream(p,FileMode.CreateNew,FileAccess.Write,FileShare.None)){f.Write(bytes,0,bytes.Length);f.Flush(true);}Guard(p,false);}
  string TransactionFolder(string id) {if(!IdPattern.IsMatch(id??""))throw new InvalidDataException("Invalid recovery operation ID.");return PackEngine.Child(scopeRoot,id);}
  static string[] OtherTokens(StoreSnapshot s,string selected) {return s.Containers.Where(c=>c.LogicalContainerName!=selected).Select(c=>c.LogicalContainerName+":"+c.RevisionToken).OrderBy(x=>x,StringComparer.Ordinal).ToArray();}
  static ProfileEntry Selected(StoreSnapshot s,ProfileEntry expected) {
   if(expected==null||!s.Available||s.ContextToken!=expected.ContextToken||s.SnapshotDigest!=expected.StoreRevisionToken)throw new IOException("The selected store changed. Refresh profiles.");
   var p=s.Profiles.SingleOrDefault(x=>x.StableId==expected.StableId);
   if(p==null||p.RevisionToken!=expected.RevisionToken||p.LogicalContainerName!=expected.LogicalContainerName||!Same(p.StorageFolderGuid,expected.StorageFolderGuid))throw new IOException("The selected profile changed. Refresh profiles.");return p;
  }
  T Locked<T>(Func<T> action) {
   using(var mutex=new Mutex(false,"Local\\CrimsonSkiesProfileManager-"+ProfileStore.Hash(Utf8.GetBytes(wgsRoot.ToUpperInvariant())))) {
    bool held=false;try{try{held=mutex.WaitOne(0);}catch(AbandonedMutexException){held=true;}if(!held)throw new IOException("Another profile operation is in progress.");return action();}finally{if(held)mutex.ReleaseMutex();}
   }
  }
  public VerifiedProfileBackup Backup(ProfileEntry selected,IProgress<string> progress) {return Locked(delegate {
   requireStopped();if(HasPending)throw new IOException("Recover the interrupted profile operation first.");var snapshot=ProfileStore.Scan(wgsRoot);var current=Selected(snapshot,selected);
   var result=ProfileBackup.Create(snapshot,current,BackupBase);requireStopped();ProfileStore.Revalidate(snapshot);if(progress!=null)progress.Report("선택한 프로필 백업 검증 완료 / Selected backup verified.");return result;
  });}
  public ProfileDeleteOutcome BackupAndDelete(ProfileEntry selected,IProgress<string> progress) {return Locked(delegate {
   requireStopped();if(HasPending)throw new IOException("Recover the interrupted profile operation first.");var before=ProfileStore.Scan(wgsRoot);var current=Selected(before,selected);
   var backup=ProfileBackup.Create(before,current,BackupBase);CheckBackup(backup,before,current);fault("after-backup");
   requireStopped();ProfileStore.Revalidate(before);
   byte[] original=before.Index.RawIndexBytes,desired=ProfileTombstone.BuildIndexImage(original,current.LogicalContainerName,current.StorageFolderGuid);
   if(ProfileStore.Hash(original)!=before.IndexSha256)throw new InvalidDataException("The index snapshot was altered.");
   string id=Guid.NewGuid().ToString("N");MakeDirectory(scopeRoot);string dir=TransactionFolder(id);Directory.CreateDirectory(dir);Guard(dir,true);
   var tx=new ProfileTransaction{Schema=1,Id=id,WgsRoot=wgsRoot,UserRoot=before.UserRoot,ContextToken=before.ContextToken,ProfileId=current.StableId,LogicalName=current.LogicalContainerName,StorageGuid=current.StorageFolderGuid,BackupPath=backup.FilePath,BackupSha256=backup.Sha256,BeforeHash=ProfileStore.Hash(original),AfterHash=ProfileStore.Hash(desired),OtherContainers=OtherTokens(before,current.LogicalContainerName)};
   byte[] atomicKey=new byte[32];using(var rng=RandomNumberGenerator.Create())rng.GetBytes(atomicKey);
   SaveNew(Path.Combine(dir,"atomic-key.bin"),ProtectedData.Protect(atomicKey,AtomicEntropy(tx),DataProtectionScope.CurrentUser));Array.Clear(atomicKey,0,atomicKey.Length);
   SaveNew(Path.Combine(dir,"before.index"),original);SaveNew(Path.Combine(dir,"after.index"),desired);
   SaveNew(Path.Combine(dir,"transaction.json"),Utf8.GetBytes(json.Serialize(tx)));SaveNew(ActivePath,Utf8.GetBytes(json.Serialize(new ProfileActiveTransaction{Schema=1,Id=id})));fault("after-journal");
   try {
    requireStopped();ProfileStore.Revalidate(before);VerifyDirectory(Source(tx),backup);fault("before-index");
    ReplaceIndex(tx,desired,tx.BeforeHash,Path.Combine(dir,"actual-before.index"));fault("after-index");
    requireStopped();VerifyOtherContainers(tx);VerifyDirectory(Source(tx),backup);fault("before-directory-move");
    MoveBound(Source(tx),Removed(tx),tx.UserRoot,dir);fault("after-directory-move");
    VerifyOtherContainers(tx);if(Directory.Exists(Source(tx)))throw new IOException("Selected profile directory still exists.");
    fault("before-cleanup");RemoveKnownDirectory(Removed(tx),backup,dir);fault("after-cleanup");
    VerifyOtherContainers(tx);ClearActive(tx);
    if(progress!=null)progress.Report("선택한 프로필만 삭제했습니다. 다른 프로필 검증 완료 / Selected profile removed; other profiles verified.");
    return new ProfileDeleteOutcome{ProfileId=current.StableId,BackupPath=backup.FilePath,PendingCloudSync=true};
   } catch(ReplacedConcurrentIndexException) {ClearActive(tx);throw;}
   catch(Exception originalError) {
    if(HasPending)try {RecoverCore(tx);if(progress!=null)progress.Report("중단된 삭제를 백업으로 복구했습니다 / Interrupted deletion rolled back.");}
    catch(Exception recovery) {throw new IOException("The operation needs explicit recovery. The verified profile backup is retained.\r\nOriginal: "+originalError.Message+"\r\nRecovery: "+recovery.Message,originalError);}
    throw;
   }
  });}
  string Source(ProfileTransaction tx) {return PackEngine.Child(tx.UserRoot,tx.StorageGuid);}
  string Removed(ProfileTransaction tx) {return Path.Combine(TransactionFolder(tx.Id),"removed");}
  static void CheckBackup(VerifiedProfileBackup b,StoreSnapshot s,ProfileEntry p) {
   var r=s.Index.Records.Single(x=>x.LogicalContainerName==p.LogicalContainerName);
   if(b.ProfileId!=p.StableId||b.ContextToken!=s.ContextToken||b.LogicalContainerName!=p.LogicalContainerName||!Same(b.StorageFolderGuid,p.StorageFolderGuid)||b.RawIndexRecordSha256!=r.RecordSha256||b.AccountIdHex!=s.AccountIdHex||!Same(b.StorageSpaceId,s.StorageSpaceId))throw new InvalidDataException("The backup is not bound to this selected profile.");
  }
  static void VerifyDirectory(string directory,VerifiedProfileBackup backup) {
   Guard(directory,true);var names=Directory.GetFileSystemEntries(directory).Select(Path.GetFileName).OrderBy(x=>x,StringComparer.Ordinal).ToArray();
   if(names.Length!=backup.Files.Length||!names.SequenceEqual(backup.Files.Select(f=>f.PhysicalFileName).OrderBy(x=>x,StringComparer.Ordinal),StringComparer.Ordinal))throw new IOException("Selected profile files changed.");
   foreach(var item in backup.Files){string p=PackEngine.Child(directory,item.PhysicalFileName);Guard(p,false);if(new FileInfo(p).Length!=item.Bytes||HashFile(p,ProfileStore.MaximumBlobBytes)!=item.Sha256)throw new IOException("Selected profile contents changed.");}
  }
  static void MoveBound(string source,string destination,string sourceParent,string destinationParent) {
   Guard(source,true);Guard(sourceParent,true);Guard(destinationParent,true);
   if(!Same(Full(Path.GetDirectoryName(source)),Full(sourceParent))||!Same(Full(Path.GetDirectoryName(destination)),Full(destinationParent))||!Same(Path.GetPathRoot(source),Path.GetPathRoot(destination))||Directory.Exists(destination)||File.Exists(destination))throw new IOException("Invalid owned profile-directory move.");
   Directory.Move(source,destination);Guard(destination,true);
  }
  void RemoveKnownDirectory(string directory,VerifiedProfileBackup backup,string owner) {
   if(!Same(Full(Path.GetDirectoryName(directory)),Full(owner)))throw new IOException("Cleanup escapes its owned transaction.");VerifyDirectory(directory,backup);
   int n=0;foreach(var f in backup.Files){string p=PackEngine.Child(directory,f.PhysicalFileName);Guard(p,false);if(HashFile(p,ProfileStore.MaximumBlobBytes)!=f.Sha256)throw new IOException("Cleanup file changed.");File.Delete(p);fault("after-cleanup-file-"+(n++).ToString(CultureInfo.InvariantCulture));}Directory.Delete(directory,false);
  }
  static void VerifyRemainingSubset(string directory,VerifiedProfileBackup backup) {
   Guard(directory,true);foreach(string path in Directory.GetFileSystemEntries(directory)) {
    Guard(path,false);string name=Path.GetFileName(path);var expected=backup.Files.SingleOrDefault(f=>f.PhysicalFileName==name);
    if(expected==null||new FileInfo(path).Length!=expected.Bytes||HashFile(path,ProfileStore.MaximumBlobBytes)!=expected.Sha256)throw new IOException("Unknown or changed recovery staging content.");
   }
  }
  static void CompleteStagedCopy(string directory,VerifiedProfileBackup backup,string owner) {
   if(!Same(Full(Path.GetDirectoryName(directory)),Full(owner)))throw new IOException("Recovery staging escapes its owner.");
   VerifyRemainingSubset(directory,backup);string ready=Path.Combine(owner,"rebuild-"+Guid.NewGuid().ToString("N"));ProfileBackup.Materialize(backup,ready);VerifyDirectory(ready,backup);
   // Only the verified remaining subset of this selected profile is removed.
   foreach(string p in Directory.GetFiles(directory)){Guard(p,false);File.Delete(p);}Directory.Delete(directory,false);MoveBound(ready,directory,owner,owner);
  }
  static byte[] AtomicEntropy(ProfileTransaction tx) {return Utf8.GetBytes("CrimsonSkiesAtomicIntent/v1:"+tx.Id+":"+tx.ContextToken);}
  string AtomicMac(ProfileTransaction tx,ProfileAtomicIntent intent) {
   byte[] key=ProtectedData.Unprotect(Read(Path.Combine(TransactionFolder(tx.Id),"atomic-key.bin"),4096),AtomicEntropy(tx),DataProtectionScope.CurrentUser);
   try {if(key.Length!=32)throw new InvalidDataException("Invalid atomic recovery key.");using(var hmac=new HMACSHA256(key))return BitConverter.ToString(hmac.ComputeHash(Utf8.GetBytes(String.Join("|",new[]{"CrimsonSkiesAtomicIntent/v1",tx.Id,tx.ContextToken,intent.Schema.ToString(CultureInfo.InvariantCulture),intent.ExpectedHash,intent.DesiredHash,intent.CaptureLeaf,intent.ImageLeaf,intent.PreserveConcurrent?"1":"0"})))).Replace("-","").ToLowerInvariant();}
   finally{Array.Clear(key,0,key.Length);}
  }
  static bool MacMatches(string left,string right) {if(left==null||right==null||left.Length!=64||right.Length!=64)return false;int difference=0;for(int i=0;i<64;i++)difference|=left[i]^right[i];return difference==0;}
  void ReplaceIndex(ProfileTransaction tx,byte[] desired,string expectedHash,string captured,bool preserveConcurrent=false,int depth=0) {
   string index=Path.Combine(tx.UserRoot,"containers.index"),dir=TransactionFolder(tx.Id);Guard(index,false);requireStopped();
   if(depth>4)throw new IOException("Repeated concurrent index changes; recovery records are retained.");
   if(!Same(Full(Path.GetDirectoryName(captured)),Full(dir)))throw new IOException("Atomic capture escapes its transaction.");
   if(HashFile(index,ProfileStore.MaximumIndexBytes)!=expectedHash)throw new IOException("The save index changed before commit.");
   string imageLeaf="atomic-image-"+Guid.NewGuid().ToString("N")+".index";SaveNew(Path.Combine(dir,imageLeaf),desired);
   var intent=new ProfileAtomicIntent{Schema=1,ExpectedHash=expectedHash,DesiredHash=ProfileStore.Hash(desired),CaptureLeaf=Path.GetFileName(captured),ImageLeaf=imageLeaf,PreserveConcurrent=preserveConcurrent};
   intent.Mac=AtomicMac(tx,intent);
   string pointer=Path.Combine(dir,"atomic.json"),pointerReady=Path.Combine(dir,"atomic-pointer-"+Guid.NewGuid().ToString("N")+".json");SaveNew(pointerReady,Utf8.GetBytes(json.Serialize(intent)));
   if(File.Exists(pointer)){Guard(pointer,false);File.Replace(pointerReady,pointer,null);}else File.Move(pointerReady,pointer);
   string ready=Path.Combine(dir,"commit-"+Guid.NewGuid().ToString("N")+".index");SaveNew(ready,desired);requireStopped();
   if(HashFile(index,ProfileStore.MaximumIndexBytes)!=expectedHash)throw new IOException("The save index changed before replacement.");
   if(File.Exists(captured)||Directory.Exists(captured))throw new IOException("An atomic capture path already exists.");fault("before-atomic-replace");File.Replace(ready,index,captured);fault("after-atomic-replace");
   if(HashFile(captured,ProfileStore.MaximumIndexBytes)!=expectedHash) {
    // File.Replace captured the actual replaced version atomically. Restore it
    // instead of overwriting a concurrent provider update with our old snapshot.
    if(HashFile(index,ProfileStore.MaximumIndexBytes)!=ProfileStore.Hash(desired))throw new IOException("The save index changed after concurrent replacement; atomic capture retained.");
    byte[] actualPrevious=Read(captured,ProfileStore.MaximumIndexBytes);ProfileStore.ParseIndex(actualPrevious);
    ReplaceIndex(tx,actualPrevious,ProfileStore.Hash(desired),Path.Combine(dir,"concurrent-recovery-"+Guid.NewGuid().ToString("N")+".index"),true,depth+1);throw new ReplacedConcurrentIndexException();
   }
   if(HashFile(index,ProfileStore.MaximumIndexBytes)!=ProfileStore.Hash(desired))throw new IOException("Index replacement verification failed.");
  }
  StoreSnapshot VerifyOtherContainers(ProfileTransaction tx) {
   var s=ProfileStore.Scan(wgsRoot);var deleted=s.Index.Records.SingleOrDefault(c=>c.LogicalContainerName==tx.LogicalName);
   if(s.ContextToken!=tx.ContextToken||s.IndexSha256!=tx.AfterHash||!OtherTokens(s,tx.LogicalName).SequenceEqual(tx.OtherContainers,StringComparer.Ordinal)||deleted==null||!deleted.IsDeleted||deleted.TotalBlobBytes!=0||s.Profiles.Any(c=>c.LogicalContainerName==tx.LogicalName))throw new IOException("The selected deletion or unselected profiles did not match the transaction.");return s;
  }
  ProfileTransaction LoadTransaction() {
   Guard(scopeRoot,true);var pointer=json.Deserialize<ProfileActiveTransaction>(Utf8.GetString(Read(ActivePath,4096)));if(pointer==null||pointer.Schema!=1||!IdPattern.IsMatch(pointer.Id??""))throw new InvalidDataException("Invalid profile recovery pointer.");
   string dir=TransactionFolder(pointer.Id);Guard(dir,true);var tx=json.Deserialize<ProfileTransaction>(Utf8.GetString(Read(Path.Combine(dir,"transaction.json"),65536)));
   if(tx==null||tx.Schema!=1||tx.Id!=pointer.Id||!Same(tx.WgsRoot,wgsRoot)||tx.OtherContainers==null||!ProfilePattern.IsMatch(tx.LogicalName??""))throw new InvalidDataException("Invalid profile recovery ownership.");
   string user=Full(tx.UserRoot);if(!Same(Path.GetDirectoryName(user),wgsRoot)||!Regex.IsMatch(Path.GetFileName(user),"^[0-9a-fA-F]{16}_[0-9a-fA-F]{32}$"))throw new InvalidDataException("Recovery account path escapes this game store.");Guard(user,true);
   byte[] before=Read(Path.Combine(dir,"before.index"),ProfileStore.MaximumIndexBytes),after=Read(Path.Combine(dir,"after.index"),ProfileStore.MaximumIndexBytes);
   if(ProfileStore.Hash(before)!=tx.BeforeHash||ProfileStore.Hash(after)!=tx.AfterHash||!ProfileTombstone.BuildIndexImage(before,tx.LogicalName,tx.StorageGuid).SequenceEqual(after))throw new InvalidDataException("Recovery index images are not a selected-only plan.");
   var record=ProfileStore.ParseIndex(before).Records.Single(x=>x.LogicalContainerName==tx.LogicalName&&Same(x.StorageFolderGuid,tx.StorageGuid));
   string backup=Full(tx.BackupPath),prefix=Full(BackupBase)+Path.DirectorySeparatorChar;if(!backup.StartsWith(prefix,StringComparison.OrdinalIgnoreCase)||!IdPattern.IsMatch(Path.GetFileNameWithoutExtension(backup))||Path.GetExtension(backup)!=".zip")throw new InvalidDataException("Recovery backup path escapes the profile backup folder.");
   var verified=ProfileBackup.Verify(backup);if(verified.Sha256!=tx.BackupSha256||verified.ProfileId!=tx.ProfileId||verified.ContextToken!=tx.ContextToken||verified.LogicalContainerName!=tx.LogicalName||!Same(verified.StorageFolderGuid,tx.StorageGuid)||verified.RawIndexRecordSha256!=record.RecordSha256||!Same(Path.GetFileName(user),verified.AccountIdHex+"_"+verified.StorageSpaceId)||ContextFor(user,ProfileStore.ParseIndex(before).ApplicationId)!=tx.ContextToken)throw new InvalidDataException("Recovery backup identity mismatch.");return tx;
  }
  public void Recover(IProgress<string> progress) {Locked(delegate {requireStopped();if(!HasPending)throw new IOException("There is no interrupted profile operation.");var tx=LoadTransaction();RecoverCore(tx);if(progress!=null)progress.Report("프로필 삭제 작업을 이전 상태로 복구했습니다 / Previous profile state recovered.");return true;});}
  bool RecoverAtomic(ProfileTransaction tx) {
   string dir=TransactionFolder(tx.Id),pointer=Path.Combine(dir,"atomic.json");if(!File.Exists(pointer)){if(HashFile(Path.Combine(tx.UserRoot,"containers.index"),ProfileStore.MaximumIndexBytes)!=tx.BeforeHash)throw new IOException("The atomic recovery intent is missing and the index changed.");return false;}
   var intent=json.Deserialize<ProfileAtomicIntent>(Utf8.GetString(Read(pointer,4096)));
   if(intent==null||intent.Schema!=1||!Regex.IsMatch(intent.ExpectedHash??"","^[0-9a-f]{64}$")||!Regex.IsMatch(intent.DesiredHash??"","^[0-9a-f]{64}$")||!Regex.IsMatch(intent.CaptureLeaf??"","^[a-z0-9-]+[.]index$")||!Regex.IsMatch(intent.ImageLeaf??"","^atomic-image-[0-9a-f]{32}[.]index$"))throw new InvalidDataException("Invalid atomic recovery intent.");
   if(!MacMatches(intent.Mac,AtomicMac(tx,intent)))throw new InvalidDataException("Atomic recovery intent integrity check failed.");
   byte[] image=Read(PackEngine.Child(dir,intent.ImageLeaf),ProfileStore.MaximumIndexBytes);if(ProfileStore.Hash(image)!=intent.DesiredHash)throw new InvalidDataException("Atomic recovery image changed.");ProfileStore.ParseIndex(image);
   if(!intent.PreserveConcurrent&&!(intent.ExpectedHash==tx.BeforeHash&&intent.DesiredHash==tx.AfterHash)&&!(intent.ExpectedHash==tx.AfterHash&&intent.DesiredHash==tx.BeforeHash))throw new InvalidDataException("Atomic recovery plan is not this selected deletion or rollback.");
   string index=Path.Combine(tx.UserRoot,"containers.index"),capture=PackEngine.Child(dir,intent.CaptureLeaf);string actual=HashFile(index,ProfileStore.MaximumIndexBytes);
   if(File.Exists(capture)) {
    byte[] previous=Read(capture,ProfileStore.MaximumIndexBytes);string previousHash=ProfileStore.Hash(previous);ProfileStore.ParseIndex(previous);
    if(previousHash!=intent.ExpectedHash) {
     if(actual==intent.DesiredHash) {try{ReplaceIndex(tx,previous,intent.DesiredHash,Path.Combine(dir,"concurrent-recovery-"+Guid.NewGuid().ToString("N")+".index"),true);}catch(ReplacedConcurrentIndexException){} }
     else if(actual!=previousHash)throw new IOException("The provider changed the index after the atomic capture. Recovery will not overwrite it.");
     ClearActive(tx);return true;
    }
    if(actual!=intent.DesiredHash)throw new IOException("The index differs from the recorded atomic replacement. Recovery will not overwrite it.");
    if(intent.PreserveConcurrent){ClearActive(tx);return true;}
   } else {
    if(actual!=intent.ExpectedHash)throw new IOException("The atomic capture is missing and the index changed. Recovery will not overwrite it.");
    if(intent.PreserveConcurrent){try{ReplaceIndex(tx,image,intent.ExpectedHash,Path.Combine(dir,"concurrent-recovery-"+Guid.NewGuid().ToString("N")+".index"),true);}catch(ReplacedConcurrentIndexException){}ClearActive(tx);return true;}
   }
   return false;
  }
  void RecoverCore(ProfileTransaction tx) {
   requireStopped();tx=LoadTransaction();if(RecoverAtomic(tx))return;string dir=TransactionFolder(tx.Id),index=Path.Combine(tx.UserRoot,"containers.index");string actual=HashFile(index,ProfileStore.MaximumIndexBytes);
   if(actual!=tx.BeforeHash&&actual!=tx.AfterHash)throw new IOException("The provider changed the save index outside this transaction. Recovery will not overwrite it.");
   var backup=ProfileBackup.Verify(tx.BackupPath);string source=Source(tx),removed=Removed(tx);
   if(Directory.Exists(source)) {if(Directory.Exists(removed))throw new IOException("Both original and removed profile directories exist.");VerifyDirectory(source,backup);}
   else {
    if(Directory.Exists(removed)) {VerifyRemainingSubset(removed,backup);try{VerifyDirectory(removed,backup);}catch{CompleteStagedCopy(removed,backup,dir);}}
    else {ProfileBackup.Materialize(backup,removed);VerifyDirectory(removed,backup);}
    requireStopped();MoveBound(removed,source,dir,tx.UserRoot);
   }
   if(actual==tx.AfterHash) {byte[] before=Read(Path.Combine(dir,"before.index"),ProfileStore.MaximumIndexBytes);ReplaceIndex(tx,before,tx.AfterHash,Path.Combine(dir,"rollback-capture-"+Guid.NewGuid().ToString("N")+".index"));}
   var restored=ProfileStore.Scan(wgsRoot);if(restored.ContextToken!=tx.ContextToken||restored.IndexSha256!=tx.BeforeHash||!OtherTokens(restored,tx.LogicalName).SequenceEqual(tx.OtherContainers,StringComparer.Ordinal)||!restored.Profiles.Any(p=>p.StableId==tx.ProfileId))throw new IOException("Profile recovery verification failed.");
   ClearActive(tx);
  }
  void ClearActive(ProfileTransaction tx) {
   if(!File.Exists(ActivePath))return;var p=json.Deserialize<ProfileActiveTransaction>(Utf8.GetString(Read(ActivePath,4096)));if(p==null||p.Schema!=1||p.Id!=tx.Id)throw new InvalidDataException("The recovery pointer changed.");Guard(ActivePath,false);File.Delete(ActivePath);
  }
 }
}
