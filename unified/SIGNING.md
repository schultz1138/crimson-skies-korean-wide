# Code signing policy

**Normal fan-patch distribution is an unsigned ZIP. Signing is optional.**
SignPath enrollment and certificates are not prerequisites for packaging this
community patch. No application has been submitted; optional SignPath setup
is on hold. The installer and bundled upstream xdelta are currently unsigned.

A second-PC test reproduced a Code Integrity block with Smart App Control
enabled. Package checksums do not grant Windows execution permission. These
tools do not change Windows protection settings or certificate stores.

## Normal ZIP packaging

From the exact public Alpha 1 bundle, rebuild the installer from source and
keep the existing verified game-target/delta graph:

```powershell
python unified/release.py prepare --bundle D:\download\CrimsonSkies-Unified-0.14.0-alpha.1 --out D:\alpha2-build
python unified/release.py finalize --bundle D:\alpha2-build\CrimsonSkies-Unified-0.14.0-alpha.2 --preparation D:\alpha2-build\preparation.json --out D:\alpha2-build\release
```

Use new output directories outside the source and input bundle. Preparation
uses Python's standard library and Windows' existing .NET Framework compiler.
Neither command executes the downloaded installer/decoder or accesses the
installed game. Ordinary packaging does not call the signature verifier.

The result contains the ZIP, `SHA256SUMS.txt`, and `release-report.json`.
Every prepared file, manifest/delta hash, executable code identity and archived
byte is checked. Normal mode requires the installer bytes to remain identical
to preparation. The report states `signatureVerification: not-requested` and
`gameplayVerified: false`; it does not imply successful installation/gameplay.
The old published Alpha 1 cannot be repackaged by these commands.

Full source game builds (`unified/build.py`) produce the same normal ZIP in
their `release` subdirectory. `--prepare-only` stages files without a ZIP.
Keep the old installer/backups for existing Alpha 1 installations and restore
with that version before moving to Alpha 2; receipt ownership is version-bound.

## Optional signed distribution

If signing is wanted later, the order remains important:

1. Obtain an authorized, trusted, timestamped signature on the pinned xdelta code.
2. Pass `--signed-xdelta` during preparation, so its final hash is in the manifest.
3. Compile the installer with that manifest hash, then sign the installer.
4. Finalize with **`--require-signatures`** to verify both embedded signatures,
   code-signing EKU, timestamps, code identities and installer product/version.

```powershell
python unified/release.py finalize --bundle D:\signed-prep\CrimsonSkies-Unified-0.14.0-alpha.2 --preparation D:\signed-prep\preparation.json --out D:\signed-release --require-signatures
```

Strict signature verification requires PowerShell 7 (`pwsh`) and a normal
script policy allowing the checked-in verifier. A denied script is an error;
no policy changes or bypass flags are used. Only this opt-in mode permits an
Authenticode-only installer change after preparation. Signing the decoder
after manifest compilation still invalidates its full-file hash.

[SignPath Foundation](https://signpath.org/) is one possible free OSS provider,
subject to [eligibility review](https://signpath.org/terms.html). Its project
certificate cannot be used to sign unchanged upstream xdelta under our identity.
That restriction concerns the optional signed route, not normal ZIP packaging.
Disclose the game-derived delta data when asking about eligibility. Provider
approval and the authorized decoder signature are not currently available.

The dormant workflow signing job requires manual invocation on `main`, the
`code-signing` environment, an approved provider and the signed decoder input.
It does not run for normal packages or publish releases. The normal Windows
job tests and builds the unsigned package independently. The optional
application draft at `unified/SIGNPATH-APPLICATION.txt` in the source repository
has not been sent.

## Validation

Release policy tests cover normal unsigned packaging, strict signed rejection,
tampering, signing order, archive mutation and immutable published versions.
Signed success-path unit tests mock the verifier; they do not certify a real
certificate. Windows CI also tests the real preset UI and isolated synthetic
install/recovery transactions. These checks do not replace game-play testing.

[Microsoft SAC documentation](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/overview)
explains Windows trust decisions. [SignPath integration](https://docs.signpath.io/trusted-build-systems/github)
is relevant only if that optional service is adopted later.
