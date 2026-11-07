# Profile Manager — 0.12.2 alpha

[한국어](PROFILE_MANAGER.ko.md) | **English** · [Language packs](MULTILINGUAL.en.md)

The owned launcher now includes **Profiles**: list the local profiles, back up one
selected profile, back it up and delete its local profile/progress, or restore a
selected backup ZIP. Selecting or double-clicking a row never changes save data.
Existing profiles cannot be overwritten. The displayed **Save size** is
storage size, not a decoded campaign-completion percentage.

This is an experimental, version-specific WGS implementation for the packaged
Windows x64 game **2608.3123.1.0**, package family
`Xbox360BackwardCompatibil.PrimaryCrimsonSkiesHighR_ksqcvrsvwz2jp`, and the validated
version-14 local index format. Unknown metadata, multiple/changed account-store
identities, stale selections and unsupported states are rejected. It is not a
general Xbox cloud-save editor. The installed 0.11 foundation is still required
for subtitle-language switching; the game/native/font/catalog payloads are
unchanged by this profile-management update.

## Use

1. Save your game and close both the game and the original Play window.
2. Run the complete new `CrimsonSkies-Multilingual-0.12.2-alpha.1` bundle's
   `MultilingualLauncher.exe`, select the supported game folder, then **Profiles**.
3. Choose **Refresh**, inspect the store/profile identity and select one row.
4. **Back up selected** creates and verifies a selected-profile ZIP without
   deleting it. The operation log shows the archive path.
5. **Backup + delete** asks for confirmation naming that profile, its displayed
   save size and stable save identity. The warning explicitly includes loss of
   that profile's game progress. A fresh verified backup is mandatory before any
   deletion. Unselected local profiles/shared-title data are revalidated.
6. To restore a missing profile, choose **Restore ZIP** without selecting a row.
   Select a backup ZIP made by this manager. Inspection is read-only. Review its
   profile name, source identity, destination store, ZIP size and SHA-256, then
   confirm **Yes** to restore. The default response is **No**. If the same profile
   exists or another identity/name conflict is detected, restoration stops;
   there is no overwrite option. The ZIP and destination are checked again
   immediately before writing. Other profiles and shared-title data are checked
   for preservation, and the list is refreshed after the operation.

Deletion is first committed locally. Pending cloud synchronization is reported;
the next ordinary game/save-provider boot consumes the supported tombstone and
synchronizes it. The manager itself does not call a cloud provider. If the index
is between supported committed states, let the ordinary game/provider finish
synchronizing, close it, then refresh—unless the manager reports an interrupted
owned operation, in which case use **Recover** first. Disabled actions display a
reason instead of guessing how to modify an unknown store.

Normal use needs **no Microsoft GDK/SDK or xgamesaveutil installation**. The build
and release do not redistribute SDK tools, exports, private account identifiers,
profile data or the disposable provider-test container.

## Backups and recovery

Selected-profile archives are kept outside WGS under
`%LOCALAPPDATA%\CrimsonSkiesProfileManager\Backups`. They contain checked hashes,
account/store/profile binding metadata, original selected files and a
single-container `selected-profile.xml` export with the required CDATA payload.
Keep these archives private: they contain your save data and account metadata.
They are not whole-store replacement archives.

**Restore ZIP** restores a selected missing profile from this manager's verified
backup, including a backup kept after an intentional deletion. It does not
replace the whole store. This version requires the original account and exact
save-store context recorded in the archive; it does not migrate profiles to
another account or relocated WGS store. The ZIP file itself may be moved. The
restored profile can receive a new local storage identity, while the receipt
continues to identify the archive's original profile. A verified private copy of
the selected ZIP is retained and its location is logged. Synchronization, when
pending, happens on the next ordinary game/save-provider launch.

**Recover** is different: it handles only this manager's interrupted transaction.
It is not the button for importing a completed backup. Keep the verified ZIP if
you may need the profile later. No SDK import or whole-store `/replace` is used
by the Restore ZIP workflow.

If an operation is interrupted, close the game and Play window, reopen this
manager, and explicitly choose **Recover**. Listing/selecting never silently
recovers or writes. Backup/delete/restore stay disabled while recovery is pending. The
new launcher's **Apply & open** and CLI `--open` also reject an unresolved owned
transaction. Do not bypass this check with another/older game launcher while
recovery is pending. Recovery data are kept under
`%LOCALAPPDATA%\CrimsonSkiesProfileManager\Transactions`; do not manually erase
an active transaction pointer, index images or its verified backup.
The transaction-authentication key is protected with Windows DPAPI CurrentUser.
Interrupted **Recover must run under the same Windows user/profile** that started
the operation. Its recovery journal is not a portable restore mechanism; moving
it to another user or reinstalling Windows does not establish that identity.

The old language-pack backup identity remains
`CrimsonSkies-Multilingual-0.12.0-alpha.1` with the same catalog bytes/digest.
The new distribution folder/version is separate, so existing subtitle receipts
remain compatible. Old bundle folders, shortcuts and the 0.11 installer's stock
backups are not removed. **Restore 0.11** still concerns subtitle/content files;
it does not restore an intentionally deleted profile.

## Build

Use the same pinned Python/dependency environment described in
[REPRODUCING.en.md](REPRODUCING.en.md). The full source path remains:

```powershell
.\.venv\Scripts\python.exe multilingual\build.py `
  --input-content D:\CrimsonSkies-original\Content `
  --dependencies .deps `
  --out D:\CrimsonSkies-profile-build-001
```

For launcher/profile-source-only edits, a retained **private full source build**
can be reused:

```powershell
.\.venv\Scripts\python.exe multilingual\build.py `
  --package-from D:\prior-private-full-build `
  --repo-root . --out D:\CrimsonSkies-profile-package-001
```

The latter path rechecks the retained canonical/locale targets and decodes all
forward deltas. It cannot author new translations or use a published ZIP alone.
The build compiles all eleven C# sources using Windows' .NET Framework compiler and
Compression/FileSystem and System.Security framework references. No SDK is needed. Publish only the
named `0.12.2-alpha.1.zip`, not private `work/`, save archives or SDK-test evidence.
