// SPDX-License-Identifier: MIT
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using System.Xml;

namespace CrimsonSkiesMultilingual {
 public sealed class ProfileManagerBackend : IProfileManagerBackend {
  // Enabled only after the disposable-container/provider test is recorded.
  internal const bool DeletionProtocolVerified=true;
  internal const bool RestoreProtocolVerified=true;
  readonly string gameFolder;
  readonly object sync=new object();
  Dictionary<string,ProfileEntry> listed=new Dictionary<string,ProfileEntry>(StringComparer.Ordinal);
  VerifiedProfileBackup restoreBackup;
  StoreSnapshot restoreSnapshot;
  bool restoreAllowed;
  public ProfileManagerBackend(string selectedGameFolder) {gameFolder=selectedGameFolder;}
  internal static string StateRoot() {return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"CrimsonSkiesProfileManager");}
  internal static ProfileOperations Operations() {return new ProfileOperations(ProfileStore.DefaultWgsRoot(),StateRoot(),PackEngine.RequireStopped);}
  static bool Stopped() {return !PackEngine.ProcessPresent("Emu")&&!PackEngine.ProcessPresent("EmuMenu");}
  string CheckHost() {
   var engine=new PackEngine(AppDomain.CurrentDomain.BaseDirectory,null);string content=engine.ResolveContent(gameFolder);
   string manifest=PackEngine.Child(content,"appxmanifest.xml");PackEngine.NoReparse(manifest,false);if(new FileInfo(manifest).Length>131072)throw new InvalidDataException("Invalid game identity document.");
   const string ns="http://schemas.microsoft.com/appx/manifest/foundation/windows10";int identities=0;bool root=false;
   var settings=new XmlReaderSettings{DtdProcessing=DtdProcessing.Prohibit,XmlResolver=null,MaxCharactersInDocument=131072,IgnoreComments=true,IgnoreWhitespace=true};
   using(var r=XmlReader.Create(manifest,settings))while(r.Read())if(r.NodeType==XmlNodeType.Element) {
    if(!root){if(r.LocalName!="Package"||r.NamespaceURI!=ns)throw new InvalidDataException("Unsupported game manifest.");root=true;}
    if(r.LocalName=="Identity"){identities++;if(identities!=1||r.Depth!=1||r.NamespaceURI!=ns||r.GetAttribute("Name")!="Xbox360BackwardCompatibil.PrimaryCrimsonSkiesHighR"||r.GetAttribute("Version")!="2608.3123.1.0"||r.GetAttribute("ProcessorArchitecture")!="x64"||r.GetAttribute("Publisher")!="CN=92ADE8CC-2A9A-4DF3-9BAF-18AF498CAA12")throw new InvalidDataException("Unsupported game package identity.");}
   }
   if(!root||identities!=1)throw new InvalidDataException("Missing game package identity.");string config=PackEngine.Child(content,"MicrosoftGame.config");PackEngine.NoReparse(config,false);
   if(new FileInfo(config).Length!=4255||PackEngine.HashFile(config)!="c73fd0bcdd473ec8293b0fbd6ea0b8f01b2a062b24a6bccb8ac6346641475e0d")throw new InvalidDataException("The game-save title configuration differs from the supported build.");return content;
  }
  T WithPatchMutex<T>(Func<T> action) {
   string content=CheckHost();using(var m=new Mutex(false,"Local\\CrimsonSkies-KoreanPatch-"+PackEngine.RootIdentity(content))) {
    bool held=false;try{try{held=m.WaitOne(0);}catch(AbandonedMutexException){held=true;}if(!held)throw new IOException("Another patch operation is using this game.");PackEngine.RequireStopped();return action();}finally{if(held)m.ReleaseMutex();}
   }
  }
  ProfileEntry Selection(ManagedProfileEntry selected) {
   if(selected==null)throw new InvalidDataException("Select one profile.");lock(sync){ProfileEntry p;if(!listed.TryGetValue(selected.Id??"",out p)||selected.ContextToken!=p.ContextToken||selected.RevisionToken!=p.RevisionToken)throw new IOException("The profile selection is stale. Refresh profiles.");return p;}
  }
  public Task<ProfileListResult> ListAsync() {return Task.Run(delegate {
   CheckHost();var ops=Operations();if(ops.HasPending)return new ProfileListResult{Entries=new ManagedProfileEntry[0],RecoveryRequired=true,RecoveryMessage="이전 프로필 작업을 복구한 뒤 계속하세요. / Recover the interrupted profile operation first.",CanBackup=false,CanDelete=false,DeleteBlockedReason="복구 필요 / Recovery required"};
   var s=ProfileStore.Scan(ProfileStore.DefaultWgsRoot());lock(sync)listed=s.Profiles.ToDictionary(p=>p.StableId,p=>p,StringComparer.Ordinal);
   bool stopped=Stopped();string reason=!stopped?"게임과 기존 플레이 창을 닫고 새로고침하세요. / Close the game and original Play window, then refresh.":!DeletionProtocolVerified?"삭제 경로 검증 중입니다. / Deletion protocol verification is pending.":null;
   return new ProfileListResult{ScopeLabel="이 PC에 동기화된 Crimson Skies 프로필 / Crimson Skies profiles synchronized to this PC",Entries=s.Profiles.Select(p=>new ManagedProfileEntry{Id=p.StableId,DisplayName=p.DisplayName,ContextToken=p.ContextToken,RevisionToken=p.RevisionToken,ProgressSummary=(p.Blobs.Sum(b=>b.Bytes)/1024.0).ToString("0.0",CultureInfo.InvariantCulture)+" KB"}).ToArray(),CanBackup=stopped&&s.Available,CanDelete=stopped&&s.Available&&DeletionProtocolVerified,CanRestore=stopped&&s.Available&&RestoreProtocolVerified,DeleteBlockedReason=reason};
  });}
  public Task<ProfileBackupResult> BackupAsync(ManagedProfileEntry selected,IProgress<string> log) {return Task.Run(delegate {
   var p=Selection(selected);return WithPatchMutex(delegate {var result=Operations().Backup(p,log);return new ProfileBackupResult{ProfileId=p.StableId,BackupPath=result.FilePath,BackupVerified=true};});
  });}
  public Task<ProfileDeleteResult> BackupAndDeleteAsync(ManagedProfileEntry selected,IProgress<string> log) {return Task.Run(delegate {
   if(!DeletionProtocolVerified)throw new IOException("Deletion protocol verification is pending.");var p=Selection(selected);return WithPatchMutex(delegate {var result=Operations().BackupAndDelete(p,log);return new ProfileDeleteResult{DeletedProfileId=result.ProfileId,BackupPath=result.BackupPath,BackupVerified=true,OtherProfilesPreserved=true,PendingCloudSync=result.PendingCloudSync};});
  });}
  public Task<ProfileRecoveryResult> RecoverAsync(IProgress<string> log) {return Task.Run(delegate {
   return WithPatchMutex(delegate {Operations().Recover(log);lock(sync){listed.Clear();restoreBackup=null;restoreSnapshot=null;restoreAllowed=false;}return new ProfileRecoveryResult{Recovered=true,OtherProfilesPreserved=true,Message="일관된 프로필 저장 상태로 복구했습니다. / A consistent profile save state was recovered."};});
  });}
  public Task<ProfileRestorePreview> InspectBackupAsync(string path) {return Task.Run(delegate {
   CheckHost();if(Operations().HasPending)throw new IOException("중단 작업을 먼저 복구하세요. / Recover the interrupted operation first.");
   var backup=ProfileBackup.Verify(path);var snapshot=ProfileStore.Scan(ProfileStore.DefaultWgsRoot());
   bool exists=snapshot.Profiles.Any(p=>String.Equals(p.DisplayName,backup.ProfileName,StringComparison.OrdinalIgnoreCase))||snapshot.Index!=null&&snapshot.Index.Records.Any(r=>String.Equals(r.LogicalContainerName,backup.LogicalContainerName,StringComparison.OrdinalIgnoreCase)&&r.IsActive);
   string blocked=null;try{ProfileOperations.ValidateRestoreCandidate(snapshot,backup);}catch(Exception error){blocked=error.Message;}
   if(blocked==null&&!Stopped())blocked="게임과 기존 플레이 창을 먼저 닫으세요. / Close the game and original Play window first.";
   if(blocked==null&&!RestoreProtocolVerified)blocked="복원 경로 검증 중입니다. / Restore protocol verification is pending.";
   bool allowed=blocked==null;lock(sync){restoreBackup=backup;restoreSnapshot=snapshot;restoreAllowed=allowed;}
   return new ProfileRestorePreview{ProfileId=backup.ProfileId,ProfileName=backup.ProfileName,ContextLabel="원래 Windows 계정의 Crimson Skies 저장소 / Original Windows account and Crimson Skies save store",ContextToken=snapshot.ContextToken,RevisionToken=snapshot.SnapshotDigest,BackupPath=backup.FilePath,BackupSha256=backup.Sha256,BackupBytes=new FileInfo(backup.FilePath).Length,SameProfileExists=exists,CanRestore=allowed,BlockedReason=blocked};
  });}
  public Task<ProfileRestoreResult> RestoreAsync(ProfileRestorePreview selected,IProgress<string> log) {return Task.Run(delegate {
   if(!RestoreProtocolVerified)throw new IOException("Restore protocol verification is pending.");VerifiedProfileBackup backup;StoreSnapshot snapshot;
   lock(sync) {backup=restoreBackup;snapshot=restoreSnapshot;
    if(!restoreAllowed||backup==null||snapshot==null||selected==null||!selected.CanRestore||selected.SameProfileExists||selected.ProfileId!=backup.ProfileId||selected.ContextToken!=snapshot.ContextToken||selected.RevisionToken!=snapshot.SnapshotDigest||selected.BackupSha256!=backup.Sha256||!String.Equals(selected.BackupPath,backup.FilePath,StringComparison.OrdinalIgnoreCase))throw new IOException("복원 미리보기가 오래됐습니다. ZIP을 다시 선택하세요. / The restore preview is stale; inspect the ZIP again.");
   }
   try{return WithPatchMutex(delegate {var result=Operations().RestoreFromBackup(backup,snapshot,log);return new ProfileRestoreResult{ProfileId=result.ProfileId,RestoredProfileId=result.RestoredProfileId,BackupPath=result.BackupPath,OtherProfilesPreserved=true,PendingCloudSync=result.PendingCloudSync};});}
   finally{lock(sync){restoreBackup=null;restoreSnapshot=null;restoreAllowed=false;}}
  });}
  public static Task EnsureNoPendingTransaction(string ignoredGameFolder) {return Task.Run(delegate {if(Operations().HasPending)throw new IOException("프로필 관리에서 중단 작업을 먼저 복구하세요. / Recover the interrupted operation in Profile Manager before opening the game.");});}
 }
 public static class ProfileManagerServices {
  public static void Configure() {ProfileManagerUi.BackendFactory=folder=>new ProfileManagerBackend(folder);ProfileManagerUi.BeforeGameLaunch=ProfileManagerBackend.EnsureNoPendingTransaction;}
 }
}
