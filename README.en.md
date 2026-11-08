# Crimson Skies Korean & Widescreen Patch

## 0.14.0 Alpha 1: selective unified setup

**[Download unified setup](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.14.0-alpha.1)** · [Install, restore and source builds](unified/README.en.md) · [Verification record](unified/verification.json)

Extract **`CrimsonSkies-Unified-0.14.0-alpha.1.zip`** and run `CrimsonSkiesSetup.exe`. Select Korean text/fonts, independent widescreen, Korean voices and caption style in one screen, directly from stock. No separate 0.11 installation or API key is needed. The same tool switches components, creates backups and restores them.

Supports exact stock or the public 0.11 foundation. Restore existing 0.12 packs with their old launcher first. For 0.13 dubbing, restore **captions → audio** before migrating. Allow about 14GB extra for the complete dub. Profile management remains in the older separate launcher.

All 12 component selections passed installer tests and full-size install/restore checks passed. **Normal gameplay was confirmed after reinstalling the default complete selection.** Other component combinations and an entire campaign playthrough still need gameplay verification; this is an alpha prerelease.

## 0.13.0 Alpha 2: Korean dubbing and matching captions

**[Download Alpha 2](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.13.0-alpha.2)** · [Install/restore guide](docs/DUBBING.en.md) · [Source builds](dubbing/README.en.md)

Adds finalized AI Korean dialogue for 1,847 WAVs and 56 movies, a caption style matching the spoken script, and a movie-caption cache fix. Install the **0.11 foundation → audio ZIP's `KoreanDubInstaller.exe` → caption ZIP's `PrepareSubtitleLauncher.exe`**, then select **한국어 — 더빙 대사 자막**. Players need no API key or TTS generation.

Restore active 0.12 subtitle packs with their own launcher before installing. To return to English audio, restore the original translation captions first, then restore the audio installer. Profile management remains available. Complete campaign playtesting is still in progress, so this is a prerelease.

## 0.12.2 alpha 1: profile backup, deletion and restoration

**[Download 0.12.2 alpha](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.12.2-alpha.1)** · [Profile Manager guide](docs/PROFILE_MANAGER.en.md)

Back up one selected profile to ZIP, delete it after backup verification and confirmation, or restore a missing profile from its backup. Existing profiles are never overwritten; other profiles and shared title data are verified. Interrupted-operation recovery is included. Supports Windows x64 **2608.3123.1.0** and the backup's original account/save-store context.

Subtitle language packs require the installed **0.11.0 beta 1 foundation**. Existing 0.12 users can close the game and Play window and extract this bundle into a new folder. The language catalog and recovery identity remain unchanged. [512 synthetic assertions and separate provider observations](docs/profile-manager-verification.json) · [Run the public tests](multilingual/tests/profile_manager/README.md).

[한국어](README.md) | **English**

An unofficial community patch for **Crimson Skies: High Road to Revenge**:
native bottom-screen Korean subtitles, widescreen resolutions, HUD alignment,
and a fix that preserves AA at 4K.

**[Download 0.11.0 beta 1](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.11.0-beta.1)** ·
[Build from source](docs/REPRODUCING.en.md) ·
[Contribute another language](docs/MULTILINGUAL.en.md)

New: [0.12 multilingual alpha](docs/MULTILINGUAL.en.md), a separately versioned
add-on with declarative language packs and launcher selection. English/Spanish
are partial contributor examples.

> Supports the exact **Windows x64 packaged build 2608.3123.1.0**.
> You must provide your own game. Full campaign playthrough verification is
> still incomplete, so the patch is released as a beta.

## Features

- Built-in bottom-screen Korean radio and in-engine cinematic subtitles, with line breaks.
- Movie and credits subtitle data, plus CS Korean Sans derived from Noto Sans CJK KR Bold.
- Eleven internal render resolutions, from 640×480 to 3840×2160, with automatic 4:3/16:9 selection.
- Alignment fixes for the radar map, rocket count, enemy health bars, and pause-menu objective box.
- Preservation of the selected AA option at 4K.
- SHA-256 input verification, installation-before backups, resume/recovery, and restoration.

Resolution choices control **internal rendering**. The final presentation follows
the game window and monitor; selecting 4K on a 1080p display downscales the result.

## Install or restore

1. Download **`CrimsonSkies-KO-Wide-0.11.0-beta.1.zip`** from the release page.
   GitHub's automatically generated `Source code` archives are not installers.
2. Save your progress, close the game and the launcher containing the Play button,
   and extract the entire ZIP.
3. Run `KoreanWidePatchInstaller.exe`, select the game folder or its `Content`
   folder, check its state, and install the integrated patch.
4. Launch the game normally and select **한국어 (Korean)** as the game language.
   No separate subtitle program or system-wide font installation is required.

The current installer UI is Korean:

| Button | Meaning |
| --- | --- |
| 폴더 선택 | Select folder |
| 상태 검사 | Check installation state |
| 통합 패치 설치 | Install integrated patch |
| 설치 전 상태로 복구 | Restore the state before this version was installed |

Supported starting states are the exact stock files or the public Korean beta
`0.10.0-beta.1`. Unknown mixtures, other builds and unrelated modifications are
rejected. Installation/recovery recommends about 2GB of combined extra free space
on the game and backup drives. Per-user backups are stored under
`%LOCALAPPDATA%\CrimsonSkiesKoreanPatch\Backups`.

Restoration returns to the **installation-before state**: stock if installed from
stock, or the older Korean beta if upgraded from that beta. Keep older installers
and their backups if you also want to undo the older patch. Save files are not
read or changed. An already-matching installation without this installer's own
backup cannot acquire a stock restore history merely by running it again.

## Complete source build

The public pipeline builds the game targets from authored text, timing tables,
font configuration, assembly and PE generators. Previously released VCDIFFs and
finished DLLs are not reconstruction inputs.

| Location | Purpose |
| --- | --- |
| `pipeline/assets/` | Extract owned inputs; edit subtitle/UI data; rasterize fonts; rebuild Data0000/Data0005 |
| `pipeline/assets/localization/` | Editable Korean text, timing and semantic database edit recipes |
| `pipeline/native/` | Radio AOT, bottom captions, HUD, resolutions, GPU/4K AA and PE generation |
| `source/` | Complete C# installer/recovery source |
| `pipeline/package_release.py` | Generate six deltas, compile the installer and reproduce the release ZIP |
| `pipeline/requirements-win-cp312.txt` | Hash-locked Windows x64 / CPython3.12 dependencies |
| `licenses/` | Font, installer, xdelta and bundled dependency notices |

After preparing the environment in the [English build guide](docs/REPRODUCING.en.md):

```powershell
.\.venv\Scripts\python.exe pipeline\build.py --input-content D:\CrimsonSkies-original\Content --dependencies .deps --out D:\CrimsonSkies-build-001
```

Use an unmodified owned input copy and a new, separate output directory.
`--game-only` skips installer/ZIP packaging; it still enforces the canonical
Korean output hashes. It is not a custom-language mode.

The immutable `source-v0.11.0-beta.1-r1` snapshot is the original verified source
release. The `source-v0.11.0-beta.1-r2` snapshot adds English documentation and
localization guidance with the same build inputs. Download the named source ZIP
from the release page or clone this repository. `hooks/` contains earlier
reference listings; the complete authoring pipeline is in `pipeline/`.

## Other languages and contributions

Translations, subtitle timing reviews, font coverage work, reproducible bug
reports and code improvements are welcome. See [CONTRIBUTING.en.md](CONTRIBUTING.en.md)
and the [localization porting guide](docs/LOCALIZATION.en.md).

The current release contains **Korean subtitles**. Its runtime and release recipe
are tied to the Korean resource slot and canonical Korean hashes. The source can
serve as a starting point for a language port, but adding another language requires
reviewed data/font changes and a separately versioned build. Those limits describe the immutable 0.11 release.

The new [0.12 multilingual alpha](docs/MULTILINGUAL.en.md) adds declarative pack
discovery and a patch-launcher language selector on top of that foundation.
It includes Korean plus explicitly partial English/Spanish examples.
The existing 0.11 build remains unchanged.

## Verification and known limits

The installer passed 191 independent controls and two full-size stock/older-beta
install→restore roundtrips. Source reconstruction reproduced the five final game
files, source-built older-beta Native, three fonts, six deltas, installer and all
28 release members. The complete installer ZIP is byte-identical to the accepted
beta. See the [independent source-reproduction record](docs/source-reproduction.json).

Tutorial subtitles, the Sea Haven boss cinematic and a subsequent mission, HUD
alignment, and final 4K/4x MSAA gameplay received user confirmation. Remaining limits:

- Every scene through the ending has not been verified in actual play.
- Four short foreign-language shouts still need their exact original wording identified.
- The final 4K report did not record the exact mission or play duration.
- Physical 4K-monitor presentation and long sessions across different PCs need further testing.
- The source audit used Python-level access tracing, source review and pinned tools;
  it was not an OS security sandbox or a trace of every native-library I/O operation.

Installer ZIP SHA-256:

```text
a53382986c5e78aa189a8936249d9771bed7d357019e31c8b219c904f304dc42
```

## Licensing

The installer and directly authored source are [MIT-licensed](LICENSE).
The converted fonts use SIL OFL 1.1; xdelta3 3.2.2 and its bundled dependencies
retain their own licenses. Read [FONT-NOTICE.txt](FONT-NOTICE.txt),
[THIRD-PARTY-NOTICES.txt](THIRD-PARTY-NOTICES.txt), and `licenses/` before redistributing.
The MIT license does not grant rights to the original game, audio, video or trademarks.
This project is not affiliated with Microsoft or the original developers.
