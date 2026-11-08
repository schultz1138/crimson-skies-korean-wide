# 0.13.0 Alpha 2 — Korean dubbing and matching captions

This unofficial AI Korean dub covers 1,847 dialogue WAVs (1,943 speech parts) and 56 movies. Final Gemini TTS performances include duration fitting, level adjustments and radio processing. **Players do not need a Google account, API key or TTS generation.**

The supported game is the existing **Windows x64 package 2608.3123.1.0**, not an original Xbox console installation. You must own the game separately.

## Installation

Use the release assets, not GitHub's automatically generated Source code archives.

1. Install the [0.11.0 beta 1 foundation](https://github.com/schultz1138/crimson-skies-korean-wide/releases/tag/v0.11.0-beta.1). If a 0.12 subtitle pack is active, restore that pack with its own launcher first so the installation returns to the 0.11 foundation. Keep your save profiles.
2. Close the game and original Play window. Extract `CrimsonSkies-Korean-Dub-0.13.0-alpha.2.zip`, run `KoreanDubInstaller.exe`, select the game folder or `Content`, and use **Check → Install dub**. Allow roughly 14GB of additional free space for staging and backups.
3. Extract `CrimsonSkies-Dub-Subtitles-0.13.0-alpha.2.zip` separately. Run `PrepareSubtitleLauncher.exe`, select the same game, and click **Open**. This first step materializes both caption payloads locally from your owned game without writing game files.
4. Choose **한국어 — 더빙 대사 자막** (captions matching the final spoken Korean script) and **Apply and open**. Continue through the original Play window. Both dubbing and captions are rendered inside the game; there is no separate subtitle overlay.

Keep each package's tools, deltas and JSON files together. After preparation, `MultilingualLauncher.exe` can be opened directly. Run preparation again for a different machine or fresh game installation.

The audio installer alone enables Korean audio. The caption package adds the choice between the existing Korean translation and captions matching the final dub script. **Both caption styles retain Korean audio.** The old English/Spanish example packs are not provided as compatible Full Dub packs in this alpha.

## Restore and upgrades

To restore English audio, close the game and Play window, restore the **original translation captions** with the Alpha 2 caption launcher, then use **Restore** in `KoreanDubInstaller.exe`. This returns the audio files and launcher language menu to their pre-dub 0.11 state. Restoring audio while modified captions remain active is rejected by the hash checks.

Backups are under `%LOCALAPPDATA%\CrimsonSkiesFullDubPublic\Backups` and `%LOCALAPPDATA%\CrimsonSkiesSubtitlePacks\Backups`. Retain them for restoration. Unknown/mixed mods are refused rather than overwritten.

For older private test builds or the local Alpha 1/Alpha 2 prototype, restore the original translation captions with the old tool first. The new public launcher does not adopt another tool's backup ownership. A public full-dub installation starts from 0.11 and does not require any intermediate dubbing prototypes.

Selected profile backup/delete/ZIP restore remains available in the caption launcher. Audio/caption installation does not edit save profiles, resolution or AA settings. The voice installer includes a launcher menu that routes the game through its Korean resource slot.

An existing English cinematic dialogue ZIP cache is refreshed in the install/restore direction, with a pre-change cache backup. This applies only to the registered supported installation and preserves checkpoint, index, allocation and all other cache bytes. Copied game trees do not modify the registered title's shared cache.

## Cache fix

The game refreshes cached `data.zip` by comparing **file lengths only**. Equal-length changes can leave old movie captions active. Original translation uses 15,113,239 bytes and Alpha 2 dub captions use 15,113,240, forcing a refresh in either direction. One padding byte is added before the ZIP central directory, with its offset and the disc-directory length updated. ZIP comments are unsupported by the native EOF-minus-22 parser. Future changed dub revisions must choose a different supported logical length from the previous revision.

## Validation and limits

All 21 audio/menu deltas decode to the finalized full-file hashes. Full-sized isolated copies passed audio install/restore/reinstall and unknown-source/corrupt-delta refusals. The public caption bootstrap passed both source directions, style switching/restoration and corrupt-local-payload refusal. All three source-rebuilt caption game files match the locally accepted Alpha 2 exactly. The user confirmed modified movie captions appear in actual play.

Synthetic XTAF cache tests also cover install/English restoration, atomic rollback, idempotence, unknown ZIP/cyclic allocation/wrong-format refusal, and preservation of checkpoints and unrelated cache edits. The actual registered cache layout/association was probed read-only. This does not certify a complete campaign playthrough. Movie page boundaries are based on final speech windows and reading pace, not word-level forced alignment.

Release ZIPs contain tools, VCDIFFs, metadata and license notices. They do not include original game DLLs, SVOD volumes, complete Bink movies, original audio, private backups or API keys. See [source build instructions](../dubbing/README.en.md).
