# Source-built Native subtitle variants

`native_variant.py` builds a language variant from the exact canonical 0.11
Native DLL (`45c2c716…`). The canonical DLL is generated from the five owned
stock files by the published source pipeline. The adapter does not load the
DLL, modify a process, or change an installed game.

```
python native_variant.py --base-native BASE.dll --pipeline REPOSITORY/pipeline --captions RESOLVED/assets/localization/native_captions.json --tutorial-format RESOLVED/native/tutorial.linebreak-proposals.json --output NEW.dll --report NEW.json
```

The Python API is `build(base_native, caption_source, tutorial_source, pipeline)`
and returns `(dll_bytes, report_dict)`. Dependencies match the public Native
pipeline: Capstone 5.0.9, Keystone 0.9.2 and pefile 2024.8.26. Tests additionally
use Unicorn. The CLI requires separate, new output/report files and supports
Windows extended paths.

The 1,805 audio identities, their order/durations, all 1,901 part keys and all
timing offsets must match the canonical authored corpus exactly. Only text
changes. Native paragraphs remain one or two lines and at most 510 UTF16 bytes
plus the terminator. The pack compiler owns glyph coverage, measured layout,
subtitle/tutorial/movie/credits fallback and asset/font generation. This adapter
also validates the tutorial identities, per-string UTF16 hashes and reviewed
breaks at existing spaces.

For a changed Native corpus, the adapter appends one read-only initialized-data
section, `.cslang`, at RVA `0x2864000`, bounded to 2 MiB. It contains the generated
dictionary and tutorial formatting table. It regenerates the two existing
authored leaf services at RVAs `0x2812f00` and `0x2813f00` from the published AOT
assembly and admits only their RIP table-displacement changes. It retargets
the existing tutorial formatter's table LEA at `0x27ff2c8`. All other existing
code bytes, section headers, imports, relocations, dispatch-map values and the
unwind directory remain exact. No executable section, function or host frame
is added. PE sizes, initialized-data size and checksum are updated explicitly.

An unchanged Native corpus/tutorial table is an identity operation: KO remains
byte-identical to the canonical 0.11 DLL. An asset-only translation can therefore
also retain that exact Native hash.

Independent verification executed emitted lookup, timed-part and formatter code
in Unicorn (55 contract outcomes, 5,583 executions). This does not run the game
renderer or establish physical gameplay. See
[the verification record](../../docs/multilingual-verification.json).

Language selection is owned by the patch launcher. It switches the coherent
Native/Data0000/Data0005 variant while both Emu and EmuMenu are stopped, then
opens the original Play window. `EmuMenuLaunchArguments.txt` is not changed.
