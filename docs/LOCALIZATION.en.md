# Porting subtitles to another language

[English README](../README.en.md) · [Build guide](REPRODUCING.en.md) ·
[Contributing](../CONTRIBUTING.en.md)

For new language contributions, use the [0.12 language-pack workflow](MULTILINGUAL.en.md).
It provides declarative overlays, automatic discovery, generated font coverage
and selection through the owned patch launcher. The rest of this document records
the lower-level **0.11 porting approach** and source locations; its limitations
refer to that immutable release.

The published 0.11 beta is a Korean patch. The source provides a starting point for
another-language port, but the current build is not a general language-pack
loader. There is no `--language` switch, automatic locale discovery, SRT importer
or newly added runtime language selector.

For an initial development port, the existing **Korean resource slot** can be
used as the integration starting point: retain its resource IDs while replacing
visible text and supplying the correct glyphs. Users would still select Korean
in the launcher for that port. This is a development approach, not an already
tested Spanish/French/etc. release. Keeping Korean and additional languages
selectable together requires new locale routing and native-caption/font work.

## Locate the text

| Source | What it controls |
| --- | --- |
| `pipeline/assets/localization/native_captions.json` | 1,805 campaign audio entries and 1,901 timed radio/in-engine cinematic parts compiled into Native |
| `pipeline/assets/localization/unicode_ko.json` | Edits/appends to owned `unicode_KO.dat`, including tutorial, story and credits strings |
| `pipeline/assets/localization/tutorial.json` | Tutorial SDB event nodes, subtitle keys and timing-related actions |
| `pipeline/native/stages/translations/tutorial.linebreak-proposals.json` | Exact tutorial strings and UTF-16 forced-break records used by the native wrapper |
| `pipeline/assets/localization/bink_subtitles.json` | Movie subtitle database node/font edit recipe |
| `pipeline/assets/localization/fonts_ko.json` | Font database edit recipe |
| `pipeline/assets/localization/pandoraplaneupgrade_screen.json` | A UI font/property edit recipe |
| `pipeline/assets/config/font_metrics.json` | Generated font members, codepoint/advance sets and canonical font expectations |

These are edit recipes and authored additions, not an export of every original
game sentence. Unchanged strings/cues still come from the owned input game.
Translating the native radio corpus alone does not translate every menu, movie
or credit. Inspect the owned original resources and extend the semantic edit
recipes where additional text is needed.

## Preserve identity; translate visible text

In a native caption entry:

- Keep `audio` and its lowercase `basename` tied to the same real clip.
- Keep each `key` stable unless all referencing script/native paths are updated.
  `KR_` keys are lookup/protocol identifiers, not just labels to rename to a
  language code. Some tutorial channel recognition checks those prefixes.
- Translate `parts[].text`, including visible speaker names/prefixes.
- Keep clip `duration` tied to the actual audio. `offset` is seconds from clip start.
  Offsets must increase strictly and remain below the clip duration. Each part
  ends at the next part's offset, or at the clip duration for the last part.
- Store JSON as UTF-8; a `\n` in a text string becomes an actual subtitle line break.

The current compiler rejects embedded NULs and text exceeding **510 UTF-16LE
bytes per part**, leaving room for the terminator in a 512-byte output buffer.
This is a storage bound, not a readability target. Surrogate pairs consume
multiple UTF-16 code units; do not count Python characters as a substitute.

The canonical corpus is sorted by basename and asserts exactly 1,805 entries /
1,901 parts. Re-splitting dialogue or adding clips requires a deliberate update
to these expectations and review of the generated lookup/data layout.

[This Spanish example](examples/native_captions.es.example.json) translates one
existing five-part entry while retaining its identities/timings. It is a format
illustration, **not a complete corpus or a tested language pack**. It is not
automatically loaded. Replacing the full corpus with this example will fail
the canonical count checks.

The current canonical radio subset also lacks the sample's accented codepoints
U+00E1, U+00E9, U+00ED, U+00F1 and U+00F3. The example therefore needs font
coverage work as well as release-recipe changes before it can become a port.

For tutorial lines, synchronize the string-table text and used native formatter
records. The wrapper verifies `source_utf16le_sha256` and treats
`break_index_utf16` as a UTF-16 code-unit index pointing at an existing ASCII
space. The current recipe expects 12 forced-break records. Update the matching
records, indices, layout measurements and expectations together for a new port;
the historical `status` text in that proposal file is not a current test result.

## Cover the target alphabet

The current font generator uses a fixed Noto CJK KR Bold OTF, Pillow BASIC layout,
17px rasterization and 19px BMF cells. It rebuilds three subset fonts from the
codepoint/advance configuration. Existing Korean subsets are not automatically
expanded when you add translated text.

For each radio/story/credits surface:

1. Collect the printable codepoints from all translated text, speaker prefixes,
   punctuation, accents and symbols. Exclude layout control characters from
   the glyph set.
2. Check the chosen outline font's cmap for every required glyph. The generator
   rejects missing codepoints; a font's name alone does not establish coverage.
3. Add/review codepoint and advance records in the relevant font configuration.
   Preserve format/line metrics and the generated U+2588 credits backplate where
   required. Review bearings, clipping and advance widths in the actual UI.
4. Rebuild the fonts and review their expected sizes/hashes and database mappings.

Current records encode byte-sized width/height/advance and signed-byte bearings.
The renderer's encoding, glyph lookup and the fixed cells impose additional
limits; keep changes within those constraints or implement and test a new path.
Bitmap font presence does not demonstrate support for non-BMP characters,
combining-mark placement, bidirectional text, Arabic joining or Indic shaping.
Those are unverified and may require renderer/shaping changes beyond translating
text or choosing another OTF. Do not advertise a complex-script port as working
from a successful cmap check alone.

If another redistributable font is needed, update the pinned source URL/hash,
font validation, metrics, derived family naming and notices coherently. The
current `NOTO_SHA` and dependency fetcher deliberately reject a different OTF.
Follow the selected font's license; keep the original game's font extraction
on the developer's own machine.

## Layout and timing review

Measure rendered advance widths with the selected font, rather than wrapping by
character count. Existing tutorial proposals were reviewed for Korean; their
historical widths and break positions are not a layout guarantee for another
language. Review sentence boundaries, speaker prefixes, two-line placement,
objective separation and display duration at both 4:3 and 16:9.

Check the actual voice clip before changing timings. A longer translation may
need shorter wording or newly reviewed timed parts, not a duration extending
beyond the audio lifecycle. The current fonts/radio renderer do not imply that
every writing direction or line-breaking convention has been implemented.

## Build a separately versioned port

First reproduce the untouched Korean beta using the [build guide](REPRODUCING.en.md).
Then work in a fork/branch and document the intended language and coverage.
The default build is deliberately strict: both normal and `--game-only` modes
enforce the published Korean outputs. Translation edits are expected to fail
those golden checks.

A new port must coordinate at least:

- Semantic DB/string changes and the native timed/formatter text.
- Font coverage, selected resource slot and mappings (currently `_KO`).
- Caption counts, buffers, PE section/allocation bounds and relevant generated-code checks.
- Intentional intermediate/final hashes throughout the staged native and asset builders.
- The release ID/version, target/delta hashes in `manifest.json`, installer manifest
  pin, and package/installer reproducibility recipe.

For example, the stock hashes in the input profile remain the hashes of the
supported original game; a new translation does not justify weakening them.
New output expectations must come from reviewed outputs. Simply changing
`manifest.json`, disabling assertions or renaming `_KO` files is insufficient.
The existing installer would reject a changed manifest until its source pin
is updated, and the old normalization/package recipe is tied to the old EXE/ZIP.

## Translation PR checklist

- State the target language/script, resource-slot approach and translated surfaces.
- Preserve routing IDs; identify intentionally changed timing or part counts.
- Supply readable UTF-8 text data, font coverage/metrics notes and upstream notices.
- List untranslated or unverified lines; partial drafts may be submitted for review.
- For a buildable port, include new-version input/output expectations and the
  validation relevant to generated code, installation and restoration.
- Test representative tutorial, campaign radio, in-engine cinematic, movie and
  credits paths, accents/punctuation, long lines, and 4:3/16:9 positioning.
- Report which scenes and machines were actually tested. Do not extrapolate the
  Korean beta's coverage to an untested new-language build.
- Keep original game data, audio/video, completed DLLs, saves and private logs out
  of the PR. Share source and reviewed differential distributions instead.
