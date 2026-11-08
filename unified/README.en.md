# Crimson Skies Selective Unified Setup — 0.14.0 Alpha 1

Offline component installer for an owned Windows x64 **2608.3123.1.0** game.
Extract the entire ZIP, close the game and original Play window, then run
`CrimsonSkiesSetup.exe`. Select the game folder or Content, check, install,
and open the original launcher. No earlier patch installation or API key is
needed when starting from exact stock files.

[Download on GitHub](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.14.0-alpha.1) · [한국어](README.md)
The installer ZIP is `CrimsonSkies-Unified-0.14.0-alpha.1.zip`; the source ZIP is separate.

Choose Korean text/fonts, widescreen/high resolutions, Korean voices, and
original-translation or spoken-dub captions. Widescreen works independently.
Korean voices/captions select the required Korean foundation automatically.
“Movies only” disables added radio/in-engine captions and preserves the
game's movie subtitles. Unchecking all components selects the stock composition.
Switch components by running this same tool again.

Exact public 0.11 is also a supported initial state. Restore old 0.12 packs
with their own launcher first. For pre-existing Alpha2, restore captions,
then audio with the old tools before migration. Old backup ownership is
not adopted. Restore returns to this installer's first installation-before
state, stock or 0.11; retain all older tools/backups as needed.

Allow about **14GB** extra for the complete dub. Only changing files are
backed up/staged. All chosen results are verified before atomic file swaps.
A journal supports rollback/recovery after interruption. Unknown files are
refused. The targeted Alpha2 movie voice cache refresh preserves checkpoints
and every unowned cache byte. Resolution/language settings are migrated;
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

The ZIP contains only VCDIFFs, managed tools, metadata and notices. Optional
Native composition restores only the source caption compiler's declared
hooks/dispatch ranges. Disabling wide uses the public pre-wide caption stage,
stock GPU and stock resolution menu. Default full installation preserves
Alpha2 Native/volume outputs. Normal gameplay was confirmed after reinstalling
the default complete selection. Other component combinations and a complete
campaign playthrough still need verification; this is an alpha. Installer MIT;
font SIL OFL; see bundled notices.

## Installer tests

`tests/transactions.py` uses small synthetic file identities with the actual
component graph and engine. It covers all selections, rollback, forced-process
exit/recovery, tampered inputs/deltas/backups and unrelated settings preservation.
The `UNIFIED_TEST` executable is never shipped.

```powershell
python unified/tests/transactions.py --package D:\unified-014-build\CrimsonSkies-Unified-0.14.0-alpha.1 --out D:\unified-synthetic-001
python unified/tests/owned_roundtrip.py --package D:\unified-014-build\CrimsonSkies-Unified-0.14.0-alpha.1 --stock D:\owned-stock\Content --out D:\unified-owned-test-001
```

Both require a fresh scratch directory. The full-size test copies owned stock
inputs and uses isolated settings/backups without changing the installed game.
These checks do not certify gameplay. Profile management remains available in
the older separate launcher; it is not included in this setup preview's UI.
