# Contributing

[한국어](CONTRIBUTING.md) | **English**

Reproducible bug reports, translations, subtitle timing/layout reviews, font
coverage work and code improvements are welcome. Issues and PR descriptions
may be written in English or Korean.

## Report a problem

Include the game build, patch version, mission/scene, reproduction steps,
expected and actual behavior, internal render resolution and AA option.
For subtitles, include the relevant audio ID or displayed line if known.
State which part of the campaign you actually tested.

Do not upload game binaries, extracted archives, audio/video, save files,
crash dumps or logs containing account details/private paths. Review screenshots
for personal information before sharing them.

## Build and code changes

Follow the [English source-build guide](docs/REPRODUCING.en.md) and describe the
validation relevant to your change in the PR. The reference build reproduces
the existing beta; a deliberately different patch needs a new reviewed release
identity and updated expectations, not a disabled hash guard.

Installer changes should preserve input verification, immutable backups,
installation-before restoration and unrelated user settings. A source rebuild
is not proof of correct runtime behavior for a changed PE hook.

`pipeline/` contains the complete generator. `hooks/` retains older reference
listings; it is not the complete authoring entry point.

## Translate into another language

Start with the [0.12 language-pack guide](docs/MULTILINGUAL.en.md). Describe the
target language, script, intended resource slot and scope: campaign radio,
tutorial, cinematics, UI and/or credits. Partial translation drafts are useful
when their coverage and untranslated entries are explicit.

Preserve audio identities and lookup keys. Submit readable UTF-8 translation
data and record timing/font changes. For review, a separate language-labelled
draft is preferable to silently overwriting the canonical Korean corpus.
The multilingual builder automatically discovers declarative packs below
`multilingual/packs/locales`, resolves missing entries to Korean, checks glyphs
and packages the launcher choices. Include the pack source and actual coverage;
do not submit full generated game files.

The immutable 0.11 pipeline still enforces its canonical Korean hashes. Use the
separate `multilingual/build.py` entry point for language variants. Complex
shaping and right-to-left scripts need additional renderer work and testing.

Keep upstream copyright and license notices with redistributed derived fonts
or dependencies. Do not commit original game assets or completed game DLLs.
