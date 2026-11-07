# Declarative subtitle language packs — 0.12 alpha

A source language pack contains JSON text and font coverage declarations. It cannot name a DLL, executable, installer action, command, script or download. The compiler reads the supported user-owned stock Content and the canonical 0.11 source pipeline, then produces coherent language-specific data and native-builder inputs. It does not install or start anything. The original 0.11 reproducible build remains unchanged.

Included packs:

| ID | Status | Explicit sample translations |
| --- | --- | --- |
| `ko-KR` | Canonical baseline | Existing Korean content, no overrides; exact 0.11 Data hashes |
| `en-US` | **Partial starter** | 1 native part, 3 tutorial lines, 1 movie line, 1 credits role, 4 UI labels |
| `es-ES` | **Partial 5-part example** | First five parts of one native dialogue; all other text falls back to Korean |

The English and Spanish examples demonstrate the mechanism. They are not complete translations and have not been verified through a full playthrough. Audio remains the original language. Every missing key has an explicit Korean fallback entry in the build report.

## Build one pack

Use the same pinned Windows x64 CPython 3.12.14, Pillow 13.0.0/FreeType 2.14.3, fontTools 4.68.0 and Noto Sans CJK KR Bold 2.004 OTF as `pipeline/assets`. Install the repository's hash-locked requirements and use its dependency fetcher. The compiler checks the Noto hash and four canonical source hashes before building.

```powershell
python multilingual/packs/catalog.py
python multilingual/packs/compile.py --pipeline pipeline --input-content C:/owned-stock/Content --pack multilingual/packs/locales/en-US/locale.json --font C:/build/dependencies/NotoSansCJKkr-Bold.otf --out C:/build/en-US
```

`--out` must be a new/empty directory outside the stock Content, source pipeline and source pack. No installed game path is selected automatically.

Outputs:

- `Content/Game/DefaultPackage.data/Data0000` and `Data0005` — rebuilt from the owned original, not from VCDIFF patches.
- `resolved/assets/localization/native_captions.json` — all original stable part identities, audio filenames, offsets and durations retained; only selected text values change.
- `resolved/assets/localization/unicode_ko.json` — source DB/string edits for the language. The internal resource carrier remains `_KO`; the language label is managed by the patch launcher, not by pretending the game has another built-in locale.
- `resolved/assets/config/font_metrics.json` — readable codepoints/advances with regenerated font hashes.
- `resolved/native/tutorial.linebreak-proposals.json` — language-specific tutorial formatter records; audio/events unchanged.
- `locale-build.json` — locale identity, exact file hashes, per-surface translated/fallback key counts, font additions, layout and native input paths.
- `catalog.private.json` — translation template/context extracted from the owned original. It includes original-dependent text; keep it in the private build directory, not in a public source pack.

Compiled Content contains original-dependent game files and must stay private. Public distribution should use the release tools to generate forward deltas and hashes; publish source overlays, not full Data volumes or DLLs. The resolved source files are inputs for the separate native variant adapter. Do not run the old canonical asset builder on a modified resolved tree: that builder intentionally enforces the exact 0.11 target hashes. A selectable installed language requires the coherent **Native + Data0000 + Data0005** bundle, prepared by the integration tools. Never apply just these two data files to a running game.

The owned patch launcher selects a compiled bundle while both the original launcher and Emu are stopped, then opens the original Play window. Runtime file switching, watchers and language-pack scripts are not part of this design.

## Add a language

1. Copy `locales/en-US` to a new locale directory. Use a unique BCP47-style ID such as `fr-FR`, a unique display name, your pack version and `status: "partial"`.
2. Keep `base: "ko-KR"` and the pinned `font.source`. List relative JSON overlay files in `overlays`; use forward slashes. No absolute paths, traversal, escaping symlinks, duplicate files or external font paths are accepted.
3. Add text values to the two namespaces in an overlay. Native part keys come from canonical `native_captions.json`; tutorial/movie/credits/UI keys come from `catalog.private.json`. Tutorial keys start `KR_SH_TUT_`; authored credits role keys start `KR_CREDITS_ROLE_`. The six `KR_CREDITS_BG_` backplates are structural geometry and cannot be translated.
4. Build and inspect `locale-build.json`. Unlisted translations use the exact canonical Korean value, never an empty placeholder. `status: "complete"` is accepted only when every translatable native and Unicode key is explicitly supplied; this checks coverage, not linguistic quality.
5. Build the native variant from the resolved inputs, package the three matching files and perform gameplay/font/layout QA. Do not claim a complete language based on sample coverage.

Example overlay:

```json
{
  "schema": 1,
  "nativeCaptions": {
    "KR_CINE_AX_ACT_BRAVERY_001_SOLOHO": "Soloho: This is the test of courage."
  },
  "strings": {
    "Music": "Music",
    "KR_SH_TUT_003": "Betty: Shoot a few of the big balloons in front of you."
  }
}
```

There is no implicit overlay precedence: duplicate JSON keys or repeated translation keys across files are errors. JSON must be UTF-8 without a BOM. Unknown fields/IDs are errors. `locale.schema.json` and `overlay.schema.json` aid editors; `validation.py` is the normative validator and additionally checks duplicate fields, Unicode, original identities and layout. The source-pack catalog rejects ID/display-name collisions.

## Text, formatting and fonts

Native captions accept one or two lines, at most 255 BMP UTF-16 units. LF can separate two nonempty lines; quotes are ordinary native text. New native translations and tutorial formatter records are measured using the generated radio BMF advances. The compiler replaces one space with LF when useful, targets a balanced two-line layout and rejects lines wider than 560 native pixels. Audio timing and part boundaries are never changed. Movie/credits overrides are limited to 127 UTF-16 units and 560 pixels per existing cue.

Unicode-table overlays reject double quotes, CR, LF and backslashes because the original table serializer has no proved escape grammar. This prevents injecting another table line. Tutorial text stays single-line in the table; the separate formatter supplies its displayed break. Existing printf/composite placeholders and color tags must remain in the same order and spelling.

Supported text is NFC BMP with the pinned Noto BASIC renderer. NUL/control/private-use/unassigned characters, non-BMP characters, RTL scripts and combining shaping are rejected. This alpha does not claim Arabic/Indic/emoji support.

Font coverage is checked by surface:

- Native dialogue and tutorial text use the generated radio font.
- Source-bound Korean Bink/movie cues use the generated story font.
- Authored credits roles use the generated credits font; the solid backplate stays intact.
- Other UI keys may still use original KO registry fonts. A new glyph in the radio font does **not** fix those fonts. A translated UI value must fit the intersection of the actual original `impact24Normal_KO`, `gillsans16normal_KO`, `anna38bold_KO` and `impact19Normal_KO` cmaps; radio coverage is also retained. If this conservative check fails, the compiler reports the key/codepoint instead of silently drawing a fallback glyph. Source UI font routing and final layout still need visual QA.

Required new glyphs are collected automatically. Optional integer `font.extraCodepoints` adds unused future glyphs to all three generated fonts. Every glyph must exist in the pinned Noto font; its advance is measured deterministically and written to the resolved metrics. Existing 0.11 glyph metrics are retained, so the canonical Korean pack remains byte exact. Spanish demonstrates source-generated `á é í ñ ó` additions in the radio font.

The compiler preserves stored ZIP metadata, validates the fixed archive allocation and reconstructs the standard historical EOCD tail metadata without a private ZIP or opaque tail cache. If a large language/font exceeds the allocation, the build fails with a size error; it does not overwrite neighbouring game data.