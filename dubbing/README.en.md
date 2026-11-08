# Dubbing/caption source and release builds

[한국어](README.md) · [Player installation](../docs/DUBBING.en.md)

`audio/` contains the pinned 21-file audio/menu installer, its manifest and its transaction engine. `captions/` contains the final 1,901 native radio parts, 42 tutorial strings, 328 single-line movie nodes, movie script attribution/windows, tutorial breaks, the two-style catalog, the local-payload bootstrap and the launcher/profile sources.

The finalized generated voices are supplied to players as VCDIFF assets. `build_audio.py` reproduces those deltas from owned before/after game files; it does not synthesize voices. This alpha does not publish the private TTS request journals or claim byte-identical re-synthesis from a remote generative API. The caption pipeline rebuilds game files directly from declarative source, without reading release VCDIFFs or completed Native DLLs as replacement payloads.

## Toolchain

Use Windows x64 and CPython 3.12. Install the hash-pinned dependencies from `pipeline/requirements-win-cp312.txt` using the existing [reproduction guide](../docs/REPRODUCING.en.md). In particular, the raster stack is Pillow13.0.0 / FreeType2.14.3 / fontTools4.68.0; native assembly uses the existing pinned pefile, Keystone and Capstone packages.

Use Noto Sans CJK KR Bold2.004 (`NotoSansCJKkr-Bold.otf`), SHA-256 `26d0c6748500a0444844280b308f5b62c7ae92ac6c6ac88148e502dd211eb52a`, and the xdelta3 3.2.2 executable from the existing release, SHA-256 `732980d52f9220dc81817ccdd0c295eadce8a0048a24c2a771a73f791ac824e9`. Windows' .NET Framework4 C# compiler builds the tools. No TTS key is required for these builds.

## Caption game files from source

Prepare an owned copy with the full Korean dub installed and its **original translation captions** selected. All three source hashes must match `captions/dub-caption-catalog.json`. Keep output outside the input game tree.

```powershell
python dubbing/build_captions.py --full-dub-content D:\FullDub-original-captions\Content --font D:\deps\NotoSansCJKkr-Bold.otf --out D:\build\alpha2-captions
```

The builder adds only required glyphs while preserving existing glyph records, rebuilds the movie DB and Unicode table, rebuilds fixed native caption tables from the existing source packer, preserves the Native code/sections/imports/unwind metadata, and emits the cache-refreshing ZIP length. It verifies these exact outputs:

| File | SHA-256 |
|---|---|
| Native caption DLL | `155003071b4f27d81e35871efd3b1b08cfad6f68d91dabf70cddcaa85a8cfe9b` |
| Data0000 | `1d5d728ec8edebdeb2d8d74ef809a43b2cf067c68002fddfadad36457ee87183` |
| Data0005 | `e537ccfa9d37db33d7c9fb39004dd84e90e87aa76eb251575a852e0606b5be9d` |

Build a distributable caption package:

```powershell
python dubbing/package_captions.py --full-dub-content D:\FullDub-original-captions\Content --caption-content D:\build\alpha2-captions\Content --xdelta D:\deps\xdelta3.exe --out D:\build\caption-package
```

This compiles both executables and creates six forward/reverse VCDIFFs. It **does not distribute the local 15MB caption span payloads**. `PrepareSubtitleLauncher.exe` reconstructs those from each player's owned, hash-verified game. Both already-selected caption states are supported. Unknown inputs or local payloads are refused; the preparation program never writes game files. Profile management remains in the original caption launcher.

## Audio package from finalized assets

Use a verified 0.11 foundation copy for `--source-content` and the finalized full-dub copy with original translation captions and the Korean routing menu for `--dubbed-content`:

```powershell
python dubbing/build_audio.py --source-content D:\Foundation011\Content --dubbed-content D:\FullDub-original-captions\Content --xdelta D:\deps\xdelta3.exe --out D:\build\audio-package
```

Every source/target guard and every regenerated delta must match `audio/manifest.json`. The installer stages and verifies all replacements before committing, retains restoration backups, rejects unknown mixed states, and preserves settings/save data. `AUDIO_TRANSACTION_FIXTURE` is an explicit test-only compile symbol for isolated transaction tests; distributed binaries are built without it. Never enable it in a player release.

`audio/VoiceCache.cs` handles the existing English `cinematics_dialog_sound.zip` cache (two changed WAVs). It binds the selected game to the registered package using metadata-only file identities, validates the known XTAF layout and archive hashes, clones the title-local cache, changes only the owned ZIP data ranges, compares every unowned byte, then atomically replaces the host cache file with a pre-change backup. It never changes FAT/directory records or purges the cache. An interrupted game installation can repeat this idempotent refresh; unrecognized caches are refused. Normal restore refreshes only the selected ZIP in the **current** cache, preserving later checkpoint/other-cache changes.

Run the self-contained synthetic cache tests with owned original and finalized dialogue inputs:

```powershell
python dubbing/tests/voice_cache_roundtrip.py --bundle D:\build\audio-package --source-content D:\Foundation011\Content --dubbed-content D:\FullDub-original-captions\Content --out D:\scratch\cache-test-001
```

The scratch directory must be new and outside the repository and inputs. The compiled fixture uses only a synthetic cache path and scratch backup folder. It never writes the installed cache or input game files.

Compiled tool executables can have toolchain-dependent build metadata. The checks above concern exact game outputs and release VCDIFF hashes; package metadata pins the newly compiled executables for each build.

## Editing and validation

Native captions retain original audio identities, part offsets and durations. Tutorial strings are LF-free in Unicode and use the reviewed formatter breaks. Movie lines use separate positioned single-line nodes; embedded LF is not a supported Bink newline. Their page timing is a reviewed approximation, not word alignment.

After changing source, regenerate font coverage, wrapping, target hashes, deltas, catalogs and compiled pins coherently. The declared fixed Native allocations must not overflow. Movie node and property records must sort by resolved case-insensitive names. A changed movie data release must use a different supported logical `data.zip` length from the preceding release, with EOCD still exactly22bytes before EOF. Do not add ZIP comments.

See [verification](../docs/dubbing-alpha2-verification.json). Preserve the MIT and third-party/font notices in redistributed tools. Do not commit generated game files, movies, raw source audio, private backups, machine-local evidence paths or credentials.
