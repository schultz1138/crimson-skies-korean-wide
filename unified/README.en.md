# Crimson Skies Selective Unified Setup

Offline component installer for an owned Windows x64 **2608.3123.1.0** game.
Extract the entire ZIP, close the game and original Play window, then run
`CrimsonSkiesSetup.exe`. Select the game folder or Content, check, install,
and open the original launcher. No earlier patch installation or API key is
needed when starting from exact stock files.

[Download on GitHub](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.14.0-beta.1) · [한국어](README.md)
The installer ZIP is `CrimsonSkies-Unified-0.14.0-beta.1.zip`; the source ZIP is separate.

## In development: Beta 2 installation metadata compatibility

The public download remains Beta 1. The next source build targets a **0.14.0-beta.2 candidate**.
Xbox Verify/Repair was observed to leave a different `appxmanifest.xml` for the same supported game
build, causing Beta 1's host check to stop. The fix accepts only the two observed complete
SHA-256/size pairs while retaining the game name, version, architecture, Publisher, and every
other file check. Unknown XML changes and different game builds still fail. It does not rewrite
game metadata, bypass checks, or change SAC compatibility.

Stop installation if Beta 1 reports this metadata error and check for the corrected version.
Published ZIPs are not replaced. The next version uses its own backup/restore receipt; restore
an installed Beta 1 with **Beta 1's own Restore button first**.

Developer check: `python unified/tests/host_metadata.py --package PACKAGE --out NEW_OUTPUT`.
Repeated `--owned-manifest PATH` arguments additionally verify owned XML snapshots read-only.
The tests and distributed artifacts do not include the game's XML contents.
See the [Beta 2 candidate verification record](verification-beta2.json) for the live install,
first-mission, restore results, and testing limits.

## Code signing policy

The Beta 1 installer and bundled xdelta are unsigned. A previous installer
launch was blocked on a PC with Smart App Control enabled. See
[packaging and optional signing](SIGNING.md). Normal fan-patch ZIP packaging
does not require SignPath or certificates. Checksums do not grant Windows
execution permission.

> [!WARNING]
> **SAC affects both installation and launching the patched game.** The public Beta 1 installer and bundled xdelta are unsigned.
> **Modified DLLs used for widescreen and added captions were blocked with SAC on. Re-enabling SAC after installation may block the patched game again.** Temporarily disabling it only for installation does not establish gameplay compatibility.
> Recent Windows 11 updates allow SAC to be re-enabled without reinstalling Windows. Availability still depends on the device, updates and configuration; check that PC's Windows Security guidance.
> Disabling SAC reduces app-execution protection for the entire PC. SAC has no per-app exception. Changing that setting is the user's decision; to keep SAC on, postpone installing configurations that modify game DLLs.
> The installer does not change security settings automatically. Signing only the installer does not resolve trust for modified game DLLs. The free-signing application remains an unsubmitted, unapproved draft on hold.
>
> [Microsoft SAC FAQ](https://support.microsoft.com/en-us/windows/security/threat-malware-protection/smart-app-control-frequently-asked-questions) · [Signing status](SIGNING.md)

## Smart App Control (SAC)

Installation and game launch were tested separately on 2026-11-09.

| Configuration | Result on this PC |
| --- | --- |
| Modified DLLs for public Beta 1 widescreen/added captions | SAC blocked the modified GPU during actual game launch. Modified widescreen/caption Native DLLs were also blocked in a separate image-load diagnostic |
| Separate BAT experiment: Korean voices, 4:3, original Native/GPU file objects | Browser-downloaded installation, first-mission gameplay, restore and reinstall passed with SAC on |
| Original game | Launched with SAC on after official Xbox Verify & Repair |

**The BAT candidate is an unpublished experiment, not the public Beta 1 “Korean voices only” preset.**
These observations do not establish SAC compatibility for public Beta 1 or every PC.
The original-DLL candidate retains built-in movie captions and required Korean menu assets.

Being able to re-enable SAC does not authorize modified DLLs. Re-enabling it after installation
can block the patched game again. Official file review and final-DLL signing/trust routes have
been investigated, but full-preset SAC compatibility has not been achieved.

## Beta 1 presets

Choose one of four voice/caption presets and select widescreen independently.

| Preset | Behavior |
| --- | --- |
| Original voices and captions | English voices and the game's built-in captions |
| English voices + Korean captions | Original voices, translated Korean captions/menu/fonts |
| Korean voices only | Korean voices; added radio/in-engine captions off |
| Korean voices + matched captions | Korean voices and captions matching the spoken dub |

Both dub presets include the required Korean menu/fonts. In “Voices only”,
built-in movie captions remain. This does not remove all text/movie captions or
preserve the original menu unchanged. The UI no longer offers Korean voices
with the older, unmatched translation captions.

Widescreen/high resolutions is a separate checkbox and stays unchanged when
switching voice presets. Choose Original + widescreen for a screen-only patch,
or Original without widescreen for stock composition. Switch presets later
by running this same tool again.

Exact public 0.11 is also a supported initial state. Restore old 0.12 packs
with their own launcher first. For pre-existing Alpha2, restore captions,
then audio with the old tools before migration. Old backup ownership is
not adopted. Restore returns to this installer's first installation-before
state, stock or 0.11; retain all older tools/backups as needed.
For an older **0.14 unified installer**, use that version's **Restore** before
installing Beta 1. Backup receipts are version-bound and are not adopted.

Allow about **14GB** extra for the complete dub. Only changing files are
backed up/staged. All chosen results are verified before atomic file swaps.
A journal supports rollback/recovery after interruption. Unknown files are
refused. Known game-asset caches are refreshed to match the selected profile;
checkpoints and every other cache byte are preserved. Unknown cached payloads
and insufficient existing allocations are refused. This fixes stale captions
after switching profiles and added tutorial captions in Voices only mode.
Resolution/language settings are migrated;
AA and other settings are preserved. Save profiles are not opened or modified.
Do not run other installers or the game during installation. Use this tool
for subsequent component changes rather than mixing older installers.

Backups: `%LOCALAPPDATA%\CrimsonSkiesUnified\Backups`.
Use **Restore** for the installation-before state, or **Recover** first if
an interrupted operation is recorded. Do not delete backups.

## Build

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
builds create the Beta 1 bundle, `preparation.json`, and a normal unsigned
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
python unified/tests/transactions.py --package D:\unified-014-build\CrimsonSkies-Unified-0.14.0-beta.1 --out D:\unified-synthetic-001
python unified/tests/owned_roundtrip.py --package D:\unified-014-build\CrimsonSkies-Unified-0.14.0-beta.1 --stock D:\owned-stock\Content --out D:\unified-owned-test-001
```

Both require a fresh scratch directory. The full-size test copies owned stock
inputs and uses isolated settings/backups without changing the installed game.
These checks do not certify gameplay. Profile management remains available in
the older separate launcher; it is not included in this setup preview's UI.
