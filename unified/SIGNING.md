# Code signing policy

**Normal fan-patch distribution is an unsigned ZIP. Signing is optional.**
SignPath enrollment and certificates are not prerequisites for packaging this
community patch. The installer-only SignPath application is on hold at draft
stage; it has not been submitted or approved. The installer and upstream xdelta
are currently unsigned. The owner manually disabled SAC on the test PC before
installation/gameplay tests. This is not a SAC-enabled compatibility test.

A second-PC test reproduced a Code Integrity block with Smart App Control
enabled. Package checksums do not grant Windows execution permission. These
tools do not change Windows protection settings or certificate stores.

## Maintainer roles and privacy

Proposed author, reviewer and signing approver: [schultz1138](https://github.com/schultz1138),
subject to the provider's requirements for a solo maintainer. The owner will
confirm GitHub/SignPath MFA and manually approve each signing request.
The installer sends no user data over the network. The original game/launcher,
opened only at the user's request, retains its own network/privacy behavior.
Build downloads and provider signing requests are maintainer-side operations.
No provider attribution is claimed before acceptance.

## Normal ZIP packaging

From the exact public Alpha 1 bundle, rebuild the installer from source and
add the verified caption-off deltas and owned-asset cache fingerprints:

```powershell
python unified/release.py prepare --bundle D:\download\CrimsonSkies-Unified-0.14.0-alpha.1 --out D:\beta1-build
python unified/release.py finalize --bundle D:\beta1-build\CrimsonSkies-Unified-0.14.0-beta.1 --preparation D:\beta1-build\preparation.json --out D:\beta1-build\release
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
with that version before moving to Beta 1; receipt ownership is version-bound.

## Optional future application: installer-only signing

The unsubmitted draft covers **CrimsonSkiesSetup.exe only**, built from our C#
source by a GitHub-hosted Windows job. It does not request a signature for the
unchanged upstream xdelta, game files, deltas, voices or fonts.

1. Prepare normally, keeping the exact pinned upstream decoder and its hash.
2. After provider approval, submit only the GitHub-built installer artifact.
3. Manually approve the signing request and put the signed installer back in
   the same prepared bundle.
4. Finalize with **`--require-installer-signature`**. This checks its trusted
   embedded signature, code-signing EKU, timestamp, code identity and product/
   version metadata. All decoder/delta/file hashes remain enforced.

```powershell
python unified/release.py finalize --bundle D:\signed-prep\CrimsonSkies-Unified-0.14.0-beta.1 --preparation D:\signed-prep\preparation.json --out D:\signed-release --require-installer-signature
```

Signature verification requires PowerShell 7 (`pwsh`) and a normal
script policy allowing the checked-in verifier. A denied script is an error;
no policy changes or bypass flags are used. Only this opt-in mode permits an
Authenticode-only installer change after preparation. The report explicitly
states `signatureVerification: installer-only`; it does not imply that xdelta
is signed or that SAC compatibility/gameplay have been certified.

A separate version-only invocation of the pinned unsigned `xdelta3 -V`
returned exit code 0 on the test PC on 2026-11-09. The installer was blocked
by Code Integrity while SAC was enabled. Actual decoder patch operations and
game/restore tests use the owner's SAC-off test environment. Signed-installer
execution and SAC-enabled installation remain unverified. A signed installer
alone also does not establish that every bundled executable will be allowed.

[SignPath Foundation](https://signpath.org/) is one possible free OSS provider,
subject to [eligibility review](https://signpath.org/terms.html). Its project
certificate cannot be used to sign unchanged upstream xdelta under our identity.
The installer-only request respects that restriction. Disclose the game-derived
delta data and ask whether this scope qualifies if the application is resumed.
No provider review or approval is currently in progress.

The dormant workflow signing job requires manual invocation on `main`, the
`code-signing` environment and an approved installer signing provider.
It does not run for normal packages or publish releases. The normal Windows
job tests and builds the unsigned package independently. The optional
application draft at `unified/SIGNPATH-APPLICATION.txt` in the source repository
has not been sent. The owner checklist is `unified/SIGNPATH-STEPS.ko.txt`.

If both executables are signed by authorized providers later,
`--require-signatures` remains the optional all-binaries verification mode.
It is mutually exclusive with installer-only verification. Any decoder signing
must happen before manifest compilation (`--signed-xdelta`), because it changes
the full-file hash. It is not a prerequisite for the current application.

## Validation

Release policy tests cover normal unsigned packaging, strict signed rejection,
tampering, signing order, archive mutation and immutable published versions.
Signed success-path unit tests mock the verifier; they do not certify a real
certificate. Windows CI also tests the real preset UI and isolated synthetic
install/recovery transactions. These checks do not replace game-play testing.

[Microsoft SAC documentation](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/overview)
explains Windows trust decisions. [SignPath integration](https://docs.signpath.io/trusted-build-systems/github)
is relevant only if that optional service is adopted later.
