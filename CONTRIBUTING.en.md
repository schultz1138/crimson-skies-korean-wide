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

Start with the [localization porting guide](docs/LOCALIZATION.en.md). Describe the
target language, script, intended resource slot and scope: campaign radio,
tutorial, cinematics, UI and/or credits. Partial translation drafts are useful
when their coverage and untranslated entries are explicit.

Preserve audio identities and lookup keys. Submit readable UTF-8 translation
data and record timing/font changes. For review, a separate language-labelled
draft is preferable to silently overwriting the canonical Korean corpus.
Such draft files are not automatically loaded by the current build.

The current code has no generic `--language` profile loader or extra runtime
language selector. A buildable port also needs coordinated font/resource,
code-generation and release-recipe changes. Complex shaping and right-to-left
scripts need additional renderer investigation and testing.

Keep upstream copyright and license notices with redistributed derived fonts
or dependencies. Do not commit original game assets or completed game DLLs.
