# 0.14.1 Beta 1 installation and recovery — game build 2611

**[Download](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.14.1-beta.1)** · [한국어](https://github.com/schultz1138/crimson-skies-korean-wide/blob/main/unified/README.2611.ko.md)

For a locally installed **Crimson Skies: High Road to Revenge, Windows x64 2611.323.502.0** only. Own the game separately. Xbox consoles and cloud play are unsupported. For **2608.3123.1.0**, use [0.14.0 Beta 2](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.14.0-beta.2).

## Before installing

Confirm the build in Xbox game management. Run the original game once to check it and your controller, then close **both the game and Play launcher**. Allow approximately **14 GB extra space** for full dubbing on both the game and Windows profile drives.

Start from **stock 2611 files**. If still on patched 2608, restore with its own installer before the Xbox update. If already updated and Check fails, obtain stock 2611 files with Xbox **Verify and Repair**. **Never copy a 2608 backup over 2611.** Other preview versions must restore their own installation first. Keep each installer and its backups together; future game builds need another compatibility check.

## Install and play

1. Download **`CrimsonSkies-Unified-0.14.1-beta.1.zip`** from the release **Assets**, rather than the development `Source code` archives.
2. Extract the **entire ZIP to a new folder** and run `CrimsonSkiesSetup.exe`. Keep `manifest.json`, `patches` and `tools` with it. No Python, API key or voice generation is needed.
3. **Browse** to the actual game installation or its `Content`, for example `C:\XboxGames\Crimson Skies- High Road to Revenge\Content`. Find your location in Xbox game management.
4. Select one voice/caption preset and independently select widescreen.
5. Run **Check → Install selected**. Stop on errors; do not force unsupported files. Keep the game closed until successful installation and verification are reported.
6. Select **Open game**. With widescreen installed, select an explicit **16:9** graphics preset, such as **1920×1080 (1080p)** or **3840×2160 (4K)**, then Play. Resolution changes apply on the next start. 4K and MSAA increase GPU and memory requirements.

## Presets

| Desired result | Voice/caption preset | Widescreen |
| --- | --- | --- |
| English audio, Korean radio captions | English voices + Korean captions | Optional |
| Korean audio without added captions | Korean voices only (additional captions off) | Optional |
| Korean audio, matching captions | Korean voices + matching captions | Optional |
| Widescreen only | Original voices/captions | On |
| Disable all patch options | Original voices/captions | Off |

Voice-only keeps built-in movie captions and required Korean menus/fonts. Dubbing uses pre-generated AI Korean audio.

## Change options and restore

Close the game and launcher, reopen **the same installer version**, select options and run Check and Install selected. Use **Restore pre-install** to return to the installation baseline. Turning every option off is a separate operation from restoring that baseline. Changed files and owned settings/cache changes are checked and backed up; saved profiles are not overwritten. Keep the backup folder. Restore before an Xbox update; if already updated, use Xbox original-file repair instead of another build's backup.

## Smart App Control (SAC)

**The package is unsigned. SAC can block the installer, a bundled tool or a modified game DLL. A working installer does not guarantee the patched game can run. This update does not resolve SAC blocking.**

Disabling SAC reduces application protection for the entire PC. Re-enabling depends on Windows version and system state, and can block the patched game again. Do not assume turning it off only during installation is sufficient. The installer never changes security settings. Defer installation if your environment requires SAC enabled.

## Troubleshooting and verification

- Unsupported build/hash: check the exact build and Content path; obtain stock files with Xbox Verify and Repair. Do not mix old backups or force a mismatched patch.
- Game running: close its launcher too.
- Old audio/captions: close the game and rerun the same installer's Check; do not delete caches or saves manually.
- Wrong aspect/HUD: verify widescreen is installed, select an explicit 16:9 launcher preset, and restart.
- 4K performance: try 1080p and lower MSAA.

Report game/installer versions, selected options, resolution/MSAA, scene and exact error in [Issues](https://github.com/schultz1138/crimson-skies-korean-wide/issues). Remove private paths/account details from logs if needed.

See the [2611 verification record](https://github.com/schultz1138/crimson-skies-korean-wide/blob/main/unified/verification-2611-beta1.json) for actual gameplay coverage. Full-campaign and final listening review of every dubbed line remain incomplete.

Developers need owned 2611 stock Content, an owned 2608 stock Native DLL, extracted public 0.14.0 Beta 2, CPython and `pefile==2024.8.26`, `capstone==5.0.9`, `keystone-engine==0.9.2`. See the source-build command in the Korean guide and use a new output folder.
