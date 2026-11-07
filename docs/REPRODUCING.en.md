# Reproduce 0.11.0 beta 1 from source

[한국어](REPRODUCING.ko.md) | **English** · [English README](../README.en.md)

This pipeline generates game targets from authored translations, timing tables,
font settings and code generators. It then creates six new differential patches
and the installer ZIP. It does not obtain its results by decoding the previously
published patches or copying finished target DLLs.

For the separately versioned multilingual add-on, prepare the same dependencies
and follow [MULTILINGUAL.en.md](MULTILINGUAL.en.md). This page continues to
reproduce the exact accepted 0.11 release.

## Required inputs

- Windows x64 and **CPython3.12 x64**, with the hash-locked Windows wheels.
- Your own **unmodified `Content` copy of packaged build 2608.3123.1.0**.
- The pinned Noto Sans CJK KR Bold outline font and xdelta3 3.2.2.
- The Windows .NET Framework C# compiler for installer/ZIP reproduction.

Original game files are not distributed in this repository or the source ZIP.
Do not point this build at an already-patched installation. The five input hashes
must match the `stock` profile in [manifest.json](../manifest.json):

- `xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll`
- `Game/DefaultPackage.data/Data0000`
- `Game/DefaultPackage.data/Data0005`
- `VGPUDX12.dll`
- `EmuMenu/Assets/TitleMenuData.json`

The build reads these inputs and writes a separate new output tree. It does not
launch the game, patch process memory, read saves or perform an installation.

## Get the source

Use the complete source ZIP attached to the release, or clone the repository:

```powershell
git clone https://github.com/schultz1138/crimson-skies-korean-wide.git
cd crimson-skies-korean-wide
```

`source-v0.11.0-beta.1-r1` is the immutable original reconstruction snapshot.
`source-v0.11.0-beta.1-r2` adds these English/localization documents; the tested
`pipeline/` and `source/` inputs are unchanged. The original installer-release
tag `v0.11.0-beta.1` predates the full pipeline, so its automatic `Source code`
download is not the complete reconstruction source.

## Prepare dependencies

From the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r pipeline\requirements-win-cp312.txt
.\.venv\Scripts\python.exe pipeline\fetch_dependencies.py --out .deps
```

The requirements lock pins exact Windows x64/CPython3.12 wheels for Capstone,
Keystone, pefile, Pillow and fontTools. The fetcher downloads and hash-verifies
the Noto font at a fixed upstream commit and the official xdelta ZIP/executable.
The font is used directly; it does not need to be installed in Windows.

For offline builds, provide the same wheels and use
`--no-index --find-links wheelhouse` in the pip command. Place the exact
`NotoSansCJKkr-Bold.otf` and `xdelta3.exe` in your dependency directory.
Their hashes and upstream URLs are recorded in
[fetch_dependencies.py](../pipeline/fetch_dependencies.py).
Read `licenses/` and the dependency distributions' own license notices.

## Build the complete release

Replace the example paths with your owned stock copy and a new output path:

```powershell
.\.venv\Scripts\python.exe pipeline\build.py `
  --input-content D:\CrimsonSkies-original\Content `
  --dependencies .deps `
  --out D:\CrimsonSkies-build-001
```

The output directory must not already exist. It must be separate from the input:
neither inside the original folder nor an ancestor of it. Use a reasonably short
path and enough space for generated game files and intermediate PE images.
Keep those outputs private and outside version control.

The default C# compiler path is
`%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe`.
An explicit compiler path can be supplied through `--csc`.

Important outputs:

| Path below `--out` | Meaning |
| --- | --- |
| `generated-content/` | Five source-generated final game files |
| `native-work/intermediate-beta1-native/` | Source-built older-beta Native used to encode the upgrade delta |
| `distribution/CrimsonSkies-KO-Wide-0.11.0-beta.1.zip` | Recreated installer distribution |
| `reproduction-report.json` | Target hashes, dependency versions, original preservation and package results |

For the five game targets only, append `--game-only`. This skips C# compilation
and installer/ZIP packaging. **It still checks the canonical Korean targets**;
it is not an unlocked build or a language-selection option.

## How the stages fit together

1. `pipeline/assets/package_io.py` reads the owned package and validates its source hashes.
2. `pipeline/assets/localization/` supplies semantic subtitle/UI edits and timed text.
   Original records and unmodified cues are extracted from the owned game at build time.
3. `pipeline/assets/fonts.py` rasterizes the pinned Noto outline using explicit
   BASIC layout and codepoint/advance data in `config/font_metrics.json`.
4. The assets stage reconstructs the data ZIP and both complete Data volumes.
5. `pipeline/native/` assembles and lifts the radio routines, compiles timed
   captions, and generates the HUD, aspect/resolution, GPU and 4K AA PE changes.
   Every historical intermediate needed by the source recipe is freshly generated.
6. `pipeline/package_release.py` encodes six VCDIFFs, verifies their decoded
   results, compiles the C# installer, and packages the 28 release members.

Original glyph bitmaps and extracted game archives are not bundled as source.
New glyphs come from the pinned Noto input. The otherwise-unused Data5 archive
tail is reconstructed from standard historical ZIP metadata geometry, rather
than supplied as a hidden postimage cache.

## Exact reproducibility

The five targets must match `manifest.json`. The source-built older-beta Native
must match its declared input hash. Next, the pipeline verifies the six newly
encoded deltas, normalized installer, every release member and the whole ZIP.
The accepted installer ZIP SHA-256 is:

```text
a53382986c5e78aa189a8936249d9771bed7d357019e31c8b219c904f304dc42
```

Reference environment: CPython3.12.14 / zlib1.3.2, Pillow13.0.0 /
FreeType2.14.3 / BASIC layout, and fontTools4.68.0. Exact wheel hashes are in
the lock files. Compiler/reference-assembly identities are recorded in
[reference-toolchain.json](../pipeline/reference-toolchain.json).
File hashes are the final criterion: different compiler, rasterizer or compressor
bytes are rejected rather than silently declared equivalent.

The legacy C# compiler emits a changing COFF timestamp and Module MVID.
[installer_repro.py](../pipeline/installer_repro.py) locates only those two PE/CLI
metadata fields and sets the documented release identity. It does not replace IL
or resources. If the normalized whole EXE differs, it fails without writing the
normalized result. This is needed to reproduce the original installer bytes.

The [independent verification record](source-reproduction.json) covers a separate
public-source snapshot, fresh hash-locked dependencies and copied stock inputs.
The six previously released VCDIFFs were absent; all five targets had to match
before xdelta was allowed. Python-level access auditing and static source review
were used. This was not an OS sandbox or a trace of every trusted native tool's I/O.

## Authoring a new translation or patch

The default recipe is an exact reconstruction of the published **Korean** beta.
Changing text, fonts or code is expected to fail its canonical hash checks.
Those failures do not demonstrate that a language port is impossible, but they
also must not be bypassed and repackaged under the old validated release identity.

For a new version, review data/font coverage, timing, layout, generated code and
ABI/PE bounds; then update the release/version identity, intermediate and final
expectations, manifest, installer pins and package recipe together.
`--game-only` does not remove those requirements.

See [LOCALIZATION.en.md](LOCALIZATION.en.md) for the actual text locations,
other-language porting steps, font and shaping limits, and a translation example.
Source reconstruction does not extend the beta's gameplay verification scope.
