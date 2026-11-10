# Beta 2 installation and restore guide

**[Download Beta 2](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.14.0-beta.2)** · [한국어](README.md)

This guide covers **CrimsonSkiesSetup.exe** in `CrimsonSkies-Unified-0.14.0-beta.2.zip`.
You need an owned installation of **Crimson Skies: High Road to Revenge**, **Windows x64 build 2608.3123.1.0**.

[First installation](#first-installation) · [Existing patches](#if-you-already-use-a-patch) · [Options](#which-options-do-i-choose) · [Restore](#change-options-or-restore) · [Troubleshooting](#troubleshooting)

## Before starting

- Launch the original game once and confirm it works, including its required controller connection.
- Save your progress and **close both the game and the launcher containing the Play button**.
- Allow about **14GB extra space** for the complete dub. Check both the game drive and the drive containing your Windows user folder.
- If you used an older patch, follow the table below first.

> **Execution blocking:** This package is unsigned. Smart App Control (SAC) can block the installer or patched game. Disabling SAC reduces app-execution protection for the whole PC. Re-enabling availability depends on the PC/Windows configuration, and re-enabling it can block the game again. The installer does not change security settings. To keep SAC enabled, postpone installation. [Details](#smart-app-control-sac)

## If you already use a patch

Keep the previous installers and backups. Supported stock files can go directly to Beta 2.

| Current state | Before installing Beta 2 |
| --- | --- |
| Unmodified original game | Continue with First installation below |
| Public **0.11 foundation patch** | Can be used directly; confirm with Check |
| **0.12 language pack** | Restore the pack with its previous launcher to return to the 0.11 foundation. [Older guide](https://github.com/schultz1138/crimson-skies-korean-wide/blob/main/docs/MULTILINGUAL.en.md) |
| **0.13 Alpha 2 voices/captions** | Use the previous tools to **restore captions, then restore audio**. [Older tools](https://github.com/schultz1138/crimson-skies-korean-wide/blob/main/docs/DUBBING.en.md) |
| **Older 0.14 Alpha/Beta 1** | Open **that version's CrimsonSkiesSetup.exe and use Restore first** |
| **Beta 2** already installed | Use the same Beta 2 to [change options](#change-options-or-restore) |
| Unknown version or failed previous restore | Stop additional installation and [report](https://github.com/schultz1138/crimson-skies-korean-wide/issues) the version/error |

Backup/restore ownership is not carried between versions.

## First installation

### 1. Download the installer ZIP

Open the [Beta 2 release](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.14.0-beta.2), expand **Assets**, and download **`CrimsonSkies-Unified-0.14.0-beta.2.zip`**.
`Source code (zip)` and `Source code (tar.gz)` are developer source archives. `SHA256SUMS.txt` lists checksums for users who want to verify download integrity.

### 2. Extract the whole ZIP

Right-click the ZIP, choose **Extract All**, and extract into a new folder. Run `CrimsonSkiesSetup.exe` inside the extracted folder.
Keep the installer, `manifest.json`, `patches` and `tools` folders together. Extracting the entire ZIP prepares these files.

Starting from stock does not require an earlier 0.11 installation, Python installation, API key or voice generation.

### 3. Select the installed game folder

Click **폴더 선택 / Browse** and select **the installed game folder or its Content subfolder**. A typical path is shown below; your drive/folder name may differ.

```text
C:\XboxGames\Crimson Skies- High Road to Revenge\Content
```

If you do not know its location, check the game's installation location in the Xbox app's management screen.

### 4. Select voices/captions and widescreen

Use the [options table](#which-options-do-i-choose) below.
The initial defaults are **Korean voices + matched captions** and **widescreen enabled**. Check both selections before installing.

### 5. Check, then install

Click **상태 검사 / Check**. When the output shows **`지원 상태 / Supported state:`**, click **선택 항목 설치 / Install selected**. Check does not install files.

If it reports an error or stops, use [Troubleshooting](#troubleshooting). Keep the game and other installers closed until this completion message appears:

> **선택한 구성요소 설치와 전체 검증을 마쳤습니다. / Selected components installed and verified.**

Changed files are backed up automatically. Save profiles are not modified.

### 6. Launch and confirm

Click **플레이 창 열기 / Open game** to open the game launcher.
For widescreen, open **Settings → Graphics → Resolution**, choose a **16:9 resolution such as 1920×1080**, then select **Play**. Resolution changes apply on the next game launch.

Check your selected voices/captions and aspect ratio in the game. If a Korean preset still shows English menus, also check the launcher's language setting. If the game asks for a controller, connect the controller used for the original game.

## Which options do I choose?

Select **one** voice/caption preset and set widescreen **separately**.

| What you want | Voice/caption preset | Widescreen |
| --- | --- | --- |
| English voices + Korean captions | **English voices + Korean captions** | Your choice |
| Korean voices without added dialogue captions | **Korean voices only (no added captions)** | Your choice |
| Korean voices + matching dialogue captions | **Korean voices + matched captions** | Your choice |
| Original English with widescreen only | **Original voices and captions** | **On** |
| Original voices/captions and 4:3 | **Original voices and captions** | **Off** |

- **Voices only** disables added radio/in-engine cutscene captions. **Built-in movie captions and required Korean menu/fonts remain.**
- **Widescreen** adds 4:3/16:9 resolution selection, HUD fixes and high-resolution options. Up to 4K refers to internal rendering; output follows the window/display size.
- Changing the preset leaves the widescreen checkbox unchanged. Confirm both before installation.
- The dub contains pre-generated **AI voices**. Installation does not require an account, API key or voice generation.

## Change options or restore

### Switch an installed configuration

Close the game and Play window → open **the same Beta 2 installer** → select the same game folder → choose the preset/widescreen → **Check → Install selected**.

### Return to the installation-before state

Close the game and Play window → select the same folder in **Beta 2** → click **설치 전 복구 / Restore**.
Wait for **`설치 전 상태로 복구했습니다. / Restored the installation-before state.`**

Restore returns to the state **before the first Beta 2 installation**: stock if you started from stock, or 0.11 if you started from that foundation. It is not an undo button for the last preset switch.

### If installation/restore was interrupted

When the installer reports an interrupted operation, use **중단 작업 복구 / Recover** first. It rolls that interrupted operation back to its starting state. After completion, select installation or Restore again as needed.

Backups belong to the same Windows user and are stored here. Paste this into File Explorer's address bar to open it:

```text
%LOCALAPPDATA%\CrimsonSkiesUnified\Backups
```

Keep previous installers and backups. Restore can be refused if its backup is missing or another tool changed the game files.

## Troubleshooting

| Symptom/message | Next step |
| --- | --- |
| Installer blocked | Check whether the alert names **Smart App Control**, then read the [SAC section](#smart-app-control-sac). SmartScreen is separate. Check the alert text, official download source and file hash. |
| `Invalid manifest`, missing tool/delta | Extract the entire installer ZIP into a new folder and check its contents. Also check Windows Security's Protection History for blocked files. |
| Game/Play window still running | Close both the game and launcher, then retry. |
| `Hash mismatch`, `Unknown modified file`, unsupported state | Confirm the game folder and previous patch version. Follow the upgrade table's restore order. If it still fails, stop installation and report the error. |
| Not enough space | Free space on the game drive and Windows-user-folder drive. Preserve patch backups. |
| Interrupted operation recorded | Use **Recover** with the same version/game folder first. |
| `No owned restore history` | Confirm the original Windows user, game folder and installer version. Use the originating installer for an older installation. |
| Current files differ from receipt | Another installer or Xbox repair may have changed files. Stop additional changes and report the error and tools used. |
| Patched game blocked after installation | Allowing the installer and allowing modified game files are separate. Read the [SAC section](#smart-app-control-sac), including after re-enabling SAC. |
| Voices/captions do not match your selection | Confirm preset/widescreen, close the game, then Check/change the configuration with the same Beta 2. Do not manually delete caches or backups. |

In [GitHub Issues](https://github.com/schultz1138/crimson-skies-korean-wide/issues), include **installer version, previous patch version, selected options, the failing step and the last error message**. Original game files and saves are not needed for an error report.

## Smart App Control (SAC)

From Start, open **Windows Security → App & browser control → Smart App Control** to check its current state and the notice for that PC.

The installer and bundled tool are unsigned. Modified game DLLs were blocked with SAC on; **Beta 2's installation-check fix does not resolve SAC blocking**.

Microsoft describes recent updates that allow re-enabling SAC without a clean installation, but availability depends on the device, updates and configuration. **Do not assume you can re-enable it; read the notice shown by Windows Security on that PC.** Re-enabling it can block the patched game again. [Official Microsoft FAQ](https://support.microsoft.com/en-us/windows/security/threat-malware-protection/smart-app-control-frequently-asked-questions)

SAC has no per-app exception. Disabling it reduces app-execution protection for the whole PC. To keep it enabled, postpone installation. The installer does not automatically change Windows security settings.

The separate original-DLL/BAT experiment is a different package. Its results do not establish SAC compatibility for the complete Beta 2 package. [Packaging, signing and experiment record](SIGNING.md)

## Beta 2 changes and testing scope

Beta 2 fixes supported installations rejected after Xbox **Verify/Repair** changed metadata for the same build. Only two known original variants are accepted; different builds and unknown changes remain refused.

Payloads match the earlier eight Beta 1 configurations. Beta 2's full preset was checked again through actual install → 1080p first-mission gameplay → restore. Full-campaign playthrough, 4K gameplay and final listening review of all dialogue remain pending. [Beta 2 verification](https://github.com/schultz1138/crimson-skies-korean-wide/blob/main/unified/verification-beta2.json)

---

The sections below are **for developers building the patch or installer**. Users installing the release ZIP can follow the steps above.

## For developers: source builds

Use `pipeline/build.py --game-only`, `dubbing/build_audio.py`, and
`dubbing/build_captions.py` with owned files to prepare exact targets.
See the existing public source guides for prerequisites. This packages
finalized voices; it does not synthesize them or require API credentials.

```powershell
python unified/build.py --stock D:\owned-stock\Content --foundation D:\source-011\generated-content --full-dub D:\full-dub\Content --dub-captions D:\caption-build\Content --native-work D:\source-011\native-work --xdelta D:\deps\xdelta3.exe --out D:\unified-014-build
```

Stock/foundation/full-dub must contain all26 game volumes plus package/launcher
identity files. If a source build emits changed files only, overlay its outputs
on a **separate owned stock copy** to prepare the respective tree. Never use
the installed game as build output. The dub-caption tree needs only its three
modified files. Output must be new and separate from all inputs/source.

The ZIP contains only VCDIFFs, managed tools, metadata and notices. Source
builds create the Beta 2 bundle, `preparation.json`, and a normal unsigned
ZIP/checksum/report in the `release` subdirectory. `--prepare-only` skips ZIP
creation. Existing prepared bundles can use `release.py finalize` directly;
only the optional signed path uses `--require-signatures`. See [SIGNING.md](SIGNING.md).

Native composition restores only the source caption compiler's declared
hooks/dispatch ranges. Disabling wide uses the public pre-wide caption stage,
stock GPU and stock resolution menu. Default full installation preserves
Alpha2 Native/volume outputs. See the release verification record for the scope
of actual installation/gameplay checks. A complete campaign playthrough and
4K gameplay have not been verified. Installer MIT;
font SIL OFL; see bundled notices.

## Installer tests

`tests/transactions.py` uses small synthetic file identities with the actual
component graph and engine. It covers all selections, rollback, forced-process
exit/recovery, tampered inputs/deltas/backups and unrelated settings preservation.
The `UNIFIED_TEST` executable is never shipped.

```powershell
python unified/tests/transactions.py --package D:\unified-014-build\CrimsonSkies-Unified-0.14.0-beta.2 --out D:\unified-synthetic-001
python unified/tests/owned_roundtrip.py --package D:\unified-014-build\CrimsonSkies-Unified-0.14.0-beta.2 --stock D:\owned-stock\Content --out D:\unified-owned-test-001
```

Both require a fresh scratch directory. The full-size test copies owned stock
inputs and uses isolated settings/backups without changing the installed game.
These checks do not certify gameplay. Profile management remains available in
the older separate launcher; it is not included in this setup preview's UI.
