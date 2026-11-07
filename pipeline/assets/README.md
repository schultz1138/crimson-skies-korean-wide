# Korean asset source build

This directory builds the exact release `Data0000` and `Data0005` from the supported user-owned original Content files. It contains authored Korean text/timing/DB edits, font compatibility metrics and source code. It contains no original game files, extracted ZIPs, font bitmaps, audio, movies, target files, patches or historical build caches.

Use Windows x64 CPython 3.12.14 and the repository's hash-locked `requirements-win-cp312.txt`: Pillow 13.0.0 (FreeType 2.14.3), fontTools 4.68.0. The font renderer explicitly selects Pillow BASIC layout. The Noto input is Noto Sans CJK KR Bold 2.004, commit `f8d157532fbfaeda587e826d4cd5b21a49186f7c`, SHA-256 `26d0c6748500a0444844280b308f5b62c7ae92ac6c6ac88148e502dd211eb52a`. The repository's `fetch_dependencies.py` downloads this pinned OTF from upstream; `fonts.py` independently verifies it. Noto is licensed under SIL OFL 1.1, © 2014–2021 Adobe. Keep the upstream OFL/copyright notice with redistributed derived fonts; generated modified faces use the family CS Korean Sans. Dependency licenses are supplied by their wheels and the release notices.

Run from the repository's pipeline root:

```powershell
python assets/build.py --input-content C:/owned-original/Content --output-content C:/build/assets/Content --font C:/build/dependencies/NotoSansCJKkr-Bold.otf
python assets/package_io.py --input-content C:/owned-original/Content --extract default.xbe --out C:/build/original.xbe
```

The builder verifies the original volume hashes before extracting root `data.zip`, `fonts.zip` and `ConfigNames.bin`. Only original Data0000 and Data0005 are needed by this stage. Output must be a separate directory; existing output Data files are rejected. It never selects an installed game path, starts a game or reads settings/saves. The XBE extractor is stdlib-only and returns the original XBE (SHA-256 `43048e59b75065e82c032859ac700c75cc2bd124f6ae817a7a2d2ca3e252aad2`), for the separate native builder.

The build stages are:

1. Remove safe editor-only `Desc` pool strings in the 50 listed scripts. Runtime nodes, properties and live strings are retained; an overlap check prevents deleting referenced bytes. Tutorial edits are handled separately.
2. Apply the readable DB plans in `localization/`: tutorial event/caption nodes, Bink cue/font nodes and two UI font/property edits. Original records/cues come from the input game at build time. The tables name new strings, nodes, properties, types and original-record identities; they are not binary replacement spans.
3. Apply the 23 Korean string corrections and 126 appended lines in `unicode_ko.json`. The native caption builder separately consumes `native_captions.json` (1,805 audio entries/1,901 caption parts). The tutorial's 42 additional strings are in the Unicode table, with event nodes in `tutorial.json`.
4. Rasterize all glyphs of the three Korean BMFs from the pinned Noto font at 17 px. `font_metrics.json` contains readable codepoint/advance compatibility data, not glyph rasters. Original BMF format/line metrics come from the owned stock font. `kradio19.bmf` is an unchanged original English-font alias extracted from `fonts.zip`, never bundled in this source directory. The U+2588 credits backplate is a programmatically drawn solid rectangle.
5. Rebuild the stored ZIP using original member metadata and deterministic metadata for the four authored font additions. Zero padding fills the original allocation minus 18 bytes. Preserve the installed release's otherwise-unused tail by generating the eight historical ZIP EOCD *metadata records* from counts, filename lengths and standard ZIP geometry; no prior ZIP or unknown tail bytes are inputs.
6. Copy the two owned volumes to the separate output, write the new ZIP and its root-directory size field, and verify both complete output hashes. `assets-build.json` records versions, font hashes and output hashes.

Expected outputs (each 170,459,136 bytes):

| File | SHA-256 |
| --- | --- |
| Data0000 | `91f96697337e6717dcdfaa99eb321196c3521da33295e77e54fb6777c92ed487` |
| Data0005 | `68317f440ba24f74a832346f9ddf400f6a3076a743cd8e80b67be62aa5484e31` |

The default build checks the canonical release hashes at every stage. When authoring a different translation/font, deliberately update the corresponding expected hashes/configuration and the native caption/font coverage inputs. The fixed-size ZIP allocation must still fit. Reproducing the current release requires no such changes.