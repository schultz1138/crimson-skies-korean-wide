# Subtitle language packs — 0.12 alpha

> The 0.12.2 alpha release adds selected backup-ZIP restoration to [Profile Manager](PROFILE_MANAGER.en.md), refusing existing-profile conflicts. Its distribution version changes, while the 0.12.0 catalog bytes/recovery namespace remain compatible. Historical verification hashes in `multilingual-verification.json` describe the original 0.12 release.


[한국어](MULTILINGUAL.ko.md) | **English** · [README](../README.en.md)

This alpha adds declarative translation packs and a language selector in an owned
patch launcher. It prepares the selected pack while the game is stopped, then
opens the original Play window. Subtitles continue to render inside the game.

The original `0.11.0-beta.1` Korean/widescreen release and its reproducible source
pipeline are unchanged. This add-on requires that exact installed foundation and
Windows packaged x64 game build **2608.3123.1.0**.

[Download the 0.12 alpha add-on](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.12.2-alpha.1).

## Included languages

| Pack | Current coverage |
| --- | --- |
| `ko-KR` | Existing Korean baseline; no translation overrides |
| `en-US` | Partial starter: 1 native dialogue part, 3 tutorial lines, 1 movie cue, 1 credits role, 4 UI labels |
| `es-ES` | Sample: 5 parts of one native dialogue |

English and Spanish are examples for contributors, not complete language releases.
Missing entries use Korean. Audio, cue identities and timing remain unchanged.
The launcher shows the translated/total counts before applying a pack.

## Use the language launcher

1. Install [0.11.0 beta 1](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.11.0-beta.1)
   if the exact five foundation files are not already installed.
2. Extract the entire `CrimsonSkies-Multilingual-0.12.2-alpha.1.zip` to a writable
   local folder. Keep its catalog, patches, tools and notices together.
3. Save your progress and close both the game and its original Play window.
4. Run `MultilingualLauncher.exe`, select the game folder or `Content`, then
   select a subtitle language. **Check** inspects files without changing them.
5. Choose **Apply & open**, then click Play in the original launcher. Its single
   game-language option shows the active pack ID; choose another pack in the
   patch launcher after closing both programs.

The game uses its Korean resource slot as the internal carrier for every pack.
The managed Play-window entry routes the selected ID through `-locale ko-KR`;
setting the game's built-in English locale would bypass these resources.
Resolution, AA and other settings are preserved. If no saved language setting
exists, the original launcher's managed default supplies the correct route.

**Restore 0.11** returns the three content files and original resolution menu to
the accepted Korean/widescreen foundation. It selectively restores the saved
game-language preference if that preference still belongs to this tool. It does
not undo 0.11, touch saves, or overwrite unrelated changes to user settings.
Use the original 0.11 installer and its own backups to undo that foundation.

Backups and recovery records are kept per game path/release under
`%LOCALAPPDATA%\CrimsonSkiesSubtitlePacks\Backups`. Keep them until restoration is
no longer needed. The tool rejects unknown game-file mixtures. If a switch is
interrupted, close the game and Play window and run it again; it validates its
four-file undo set before recovering the previous coherent selection.

Before using a rebuilt bundle with a different catalog, choose **Restore 0.11**
in the old bundle first. Keep that bundle and its backups until the restore
finishes. Catalog-specific recovery records are separate; a new catalog cannot
restore an older catalog's active pack.

## Build the add-on from source

Prepare the stock input copy, pinned Python environment and dependency directory
in [REPRODUCING.en.md](REPRODUCING.en.md). Do not use the installed patched game as
the build input. From the repository root:

```powershell
.\.venv\Scripts\python.exe multilingual\build.py `
  --input-content D:\CrimsonSkies-original\Content `
  --dependencies .deps `
  --out D:\CrimsonSkies-multilingual-001
```

Use a new output directory, outside the source, dependencies and original game.
The build regenerates the canonical 0.11 foundation, discovers all locale
manifests, builds their assets and native text data, verifies freshly encoded
forward deltas, then compiles a launcher pinned to that catalog. It does not use
previously released patches or finished game DLLs as reconstruction inputs.

| Output below `--out` | Use |
| --- | --- |
| `CrimsonSkies-Multilingual-0.12.2-alpha.1.zip` | Distributable add-on |
| `bundle/CrimsonSkies-Multilingual-0.12.2-alpha.1/` | Same public payload unpacked |
| `build-report.json` | File identities and build result; may contain private absolute paths |
| `work/` | Private original-dependent full targets, extracted context, logs and intermediate files |

Publish the named bundle ZIP, not `work/`. The bundle includes only forward
deltas, the owned launcher, pinned xdelta tool, count reports and notices.
`--skip-launcher` creates private staging only and deliberately produces no
distributable ZIP. `--pack-root` accepts an alternate source-pack directory.

For launcher-only edits, `--package-from D:\prior-private-full-build --repo-root .
--out D:\new-package` can reuse a retained private source build. It verifies the
canonical images, every locale target, catalog and freshly decoded deltas before
recompiling. A published ZIP/delta-only directory is rejected; this mode cannot
add translations or change a catalog. New language/text changes use the full
stock-input build above.

The launcher compiler's timestamp, module MVID and verified compiler-owned private
type GUID are normalized from the source/catalog identity. IL and other metadata
are unchanged. Two independent final compilations and packaging runs produced
the same launcher and ZIP; the final source/packaging provenance is recorded in
the verification file below.

## Add another language

1. Copy [the English starter](../multilingual/packs/locales/en-US/locale.json)
   and its overlay into a new folder below `multilingual/packs/locales`.
2. Set a unique locale ID and display name. Retain `base: "ko-KR"`, the pinned
   font source and `status: "partial"` until all translatable entries are supplied.
3. Edit the JSON overlays. Native dialogue keys come from
   `pipeline/assets/localization/native_captions.json`. For tutorial, movie,
   credits and UI keys, inspect the private context catalog generated by a pack
   build. Never publish that original-dependent context catalog.
4. Run `multilingual/build.py` again. Discovery and launcher choices are automatic;
   adding an ordinary language needs no C# enum, launcher edit or new native code.
5. Review coverage and glyph/layout errors, then test the pack in the game. Send
   a PR with declarative source files and the scenes actually verified.

An overlay contains `schema`, `nativeCaptions` and `strings`. Omitted keys fall
back to Korean; duplicate or unknown keys fail. Pack manifests cannot run code,
name arbitrary DLLs or download a font. See the [pack format guide](../multilingual/packs/README.md)
and its schemas for full validation rules and a one-pack build command.

Current text support is NFC BMP, left-to-right text using the pinned Noto BASIC
renderer. Arabic/Indic shaping, RTL and emoji are outside this alpha. Radio,
movie and credits glyphs are generated from source; UI translations must fit the
intersection of the game's four actual Korean UI-font cmaps. A glyph added to the
radio font does not expand those original UI fonts. Overlong lines, unsupported
glyphs and changed formatting tokens fail the build instead of silently rendering
replacement characters. Complex scripts require additional renderer/font work.

## Implementation and verification boundary

`multilingual/packs/` validates and resolves translations, rebuilds fonts and data.
`multilingual/runtime/native_variant.py` keeps the existing native dispatch,
executable code and unwind tables, and appends read-only language data when needed.
`multilingual/launcher/` verifies the catalog, stages Native/Data0000/Data0005 and
the managed Play-window JSON as one recoverable transaction, and selectively
migrates `game-language`. No runtime loader, overlay or background watcher is used.

Automated native execution, asset inspection and transaction tests do not establish
that every scene has been played. The 0.11 campaign-wide playthrough remains
incomplete, and the sample languages need actual font/layout/gameplay review.
See [multilingual-verification.json](multilingual-verification.json) for the
source-bound automated checks and the separate physical-playtest status.

The repository MIT license covers authored code and translations; original game
files retain their rights. Preserve all font/xdelta/dependency notices when
redistributing bundles. New packs should only contain text you may contribute.
