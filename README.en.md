# Crimson Skies Korean & Widescreen Patch

An unofficial fan patch for **Crimson Skies: High Road to Revenge**, with Korean captions, AI Korean voices and optional widescreen.
You need an owned installation of the **Windows x64 game build 2608.3123.1.0**.

**[Download Beta 2](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.14.0-beta.2)** · **[Step-by-step installation](unified/README.en.md)** · [한국어](README.md)

## First installation

**Read the SAC notice before starting.** This package is unsigned, and Windows Smart App Control (SAC) can block the installer or patched game. Disabling it reduces app-execution protection across the PC; re-enabling it can block the game again. Re-enabling availability depends on the PC and Windows configuration. The installer does not change security settings. Read the [blocking/SAC guidance](unified/README.en.md#smart-app-control-sac) before deciding to install.

1. Open **Download Beta 2**, expand **Assets**, and download `CrimsonSkies-Unified-0.14.0-beta.2.zip`. GitHub's `Source code` archives are for developers.
2. Confirm the original game runs, then close both the game and its **Play window**.
3. Extract the whole ZIP into a new folder and run `CrimsonSkiesSetup.exe` inside it.
4. **Choose the game folder → choose a voice/caption preset → select optional widescreen → Check → Install selected.**
5. Wait for the completion message, then choose **Open game**. For widescreen, select a **16:9 resolution such as 1920×1080** in the launcher.

Already using a patch? Start with the [upgrade table](unified/README.en.md#if-you-already-use-a-patch). Restore an older 0.14 installation with **that version's Restore button first**.

## Which options do I choose?

Choose one voice/caption preset, then turn widescreen on or off separately.

| What you want | Select in the installer |
| --- | --- |
| English voices with Korean captions | **English voices + Korean captions** |
| Korean voices without added dialogue captions | **Korean voices only (no added captions)** |
| Korean voices with matching captions | **Korean voices + matched captions** |
| Widescreen only | **Original voices and captions** + **Widescreen & high resolutions** checked |

Voices only retains built-in movie captions and required Korean menu/fonts. Allow about **14GB extra space** for the full dub. Voices are already generated; no API key is required. You can start directly from supported stock files.

## Install, change options, restore

- [Download through first launch](unified/README.en.md)
- [Upgrade from an existing patch](unified/README.en.md#if-you-already-use-a-patch)
- [Change options or restore](unified/README.en.md#change-options-or-restore)
- [Troubleshooting](unified/README.en.md#troubleshooting)

## Beta 2 and testing scope

Beta 2 fixes supported installations being rejected after Xbox **Verify/Repair**. Caption, voice and widescreen content is unchanged from Beta 1. **This update does not resolve SAC blocking.**

First-mission install/play/restore, file hashes and save preservation were checked. Full-campaign playthrough, 4K gameplay and final listening review of all dialogue remain pending; this is a **beta prerelease**. [Beta 2 verification](unified/verification-beta2.json) · [Earlier eight-configuration verification](unified/verification-beta1.json)

## Older versions and developer resources

Use the unified installer above for a first installation. These resources support older installations or development.

- [Older 0.13 dub/caption tools](docs/DUBBING.en.md)
- [0.12 language packs](docs/MULTILINGUAL.en.md) · [Older profile manager](docs/PROFILE_MANAGER.en.md)
- [0.11-specific installation (Korean)](읽어주세요.txt)
- [Unified source builds](unified/README.en.md#for-developers-source-builds) · [0.11 reproduction](docs/REPRODUCING.en.md)
- [Archived README](https://github.com/schultz1138/crimson-skies-korean-wide/blob/v0.14.0-beta.2/README.en.md)
- [Contributing](CONTRIBUTING.en.md) · [Packaging/signing status](unified/SIGNING.md)

Installer source is [MIT](LICENSE); fonts/tools retain their [bundled licenses](THIRD-PARTY-NOTICES.txt). Original game files are not included. This is not an official Microsoft/Xbox project. Original game assets, trademarks, voices and video retain their respective owners' rights.
