# Code signing policy

**Status: preparation only. No signing provider has approved this project yet.**
The public `v0.14.0-alpha.1` installer and its `tools/xdelta3.exe` are unsigned.
A second-PC test reproduced a Windows Code Integrity block on the installer,
with Smart App Control enabled. This is not a corrupt-download diagnosis.
Checksums and GitHub attestations do not provide Windows Authenticode trust.

The next candidate is `0.14.0-alpha.2`. Do not replace the published alpha.1
assets or describe an unsigned candidate as fixing Smart App Control.
No Windows protection settings or certificate stores need to be changed by
these build/release scripts. A signature check is separate from a real
installation, game launch, restoration, and SmartScreen reputation test.

## Free route and its outstanding dependency

[SignPath Foundation](https://signpath.org/) is a candidate for free OSS
signing, subject to its [eligibility review](https://signpath.org/terms.html).
It requires verifiable source builds, product/version metadata and manual
release approval. Acceptance is not guaranteed, especially for a new project.

Apply for the **installer binary built from this repository**, not the game
or the third-party decoder. The program does not transmit information to
networked systems. The game and its original launcher retain their own
network/privacy behavior. Source/build downloads and signing-service requests
occur only in the maintainer's build process.

Proposed project roles are author/reviewer/approver: `schultz1138` (repository
owner). The owner must confirm roles, configure the provider and satisfy its
account/MFA requirements personally. No service application has been submitted
by these changes. Add provider attribution only after acceptance; do not claim
that SignPath already signs this project.

**xdelta is a separate blocker.** Foundation rules do not let this project sign
an unchanged upstream executable under its own certificate. Inclusion in a
signed ZIP/MSI does not demonstrate that a child EXE can execute under SAC.
Obtain a trusted, timestamped signature from the upstream maintainers/another
authorized provider, or have a different dependency strategy reviewed before
claiming compatibility. No upstream signature or exception is assumed here.
With the current unsigned decoder, finalization deliberately fails even if
the installer alone becomes signed.

For the application, explain that the installer is MIT, supports only owned
game files, ships deltas rather than full game files, operates offline, and
preserves reversible backups. Disclose the game-derived delta data and the
separate xdelta dependency to the reviewer; signing eligibility is their call.
Do not submit private game inputs, saves, user paths, credentials, or backups.

Microsoft's [SAC signing documentation](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control)
requires a trusted provider. Self-signing or a .NET strong name is insufficient.
Azure [Public Trust eligibility](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart)
currently includes South Korean organizations, while individual eligibility
is limited to the US/Canada. It is not a free immediate solution for a Korean
individual. Do not create a paid account without the owner's decision.

## Order of operations

1. Finalize the trusted signature on the exact pinned xdelta code.
2. Put the **signed tool's full-file SHA-256** in `manifest.json`.
3. Compile the installer with that manifest hash and the new release ID.
4. Sign the compiled installer, including a trusted timestamp.
5. Check both embedded signatures, unchanged executable code, all deltas,
   manifest pins, product/version metadata and final ZIP checksum.
6. Test stock → install → same-scene gameplay → restore on a SAC-enabled PC.
   Publish only after recording the actual results and remaining limits.

Signing the decoder after step 3 invalidates the pinned tool hash. Signing the
installer changes its full-file hash; generate the published checksum last.
Keep the old installer/backups for existing alpha.1 installations. Restore
them with that installer before moving to this new release; receipt ownership
and manifest binding are not silently migrated across versions.

## Prepare without executing the downloaded installer or decoder

The `prepare` command validates the pinned public alpha.1 manifest, installer,
decoder, and every delta, then compiles a new installer from current source.
It does not decode patches, open game files, or launch either downloaded EXE.
Preparation needs Python's standard library and Windows' existing .NET
Framework compiler. Signature verification additionally requires PowerShell 7
(`pwsh` on PATH, also used by the GitHub workflow). Its normal script policy
must allow the checked-in verifier; a policy denial is an error, never a cue
to change policy or retry with bypass flags. Use new output directories
outside the repository and inputs.

```powershell
python unified/release.py prepare --bundle D:\download\CrimsonSkies-Unified-0.14.0-alpha.1 --out D:\signing-prep
```

Without `--signed-xdelta`, this creates **only a preparation candidate**, no
release ZIP. It is useful for review/metadata checks and cannot be finalized.
Once an authorized provider supplies the signed, otherwise unchanged decoder:

```powershell
python unified/release.py prepare --bundle D:\download\CrimsonSkies-Unified-0.14.0-alpha.1 --signed-xdelta D:\signed\xdelta3.exe --out D:\signing-prep-final
```

The signed tool must have identical code/resources to the pinned original;
only Authenticode/checksum/alignment changes are accepted. Windows must also
verify its embedded signature, code-signing EKU and timestamp. These are two
independent checks: byte normalization is not a trust verification algorithm.

Submit **only** the resulting `CrimsonSkiesSetup.exe` from a GitHub-hosted
source build to the approved installer signing project. The workflow's
unsigned artifact is a review artifact, never a public installer release.
Configure SignPath origin verification and restrict product name to
`Crimson Skies Korean Wide` and file version to `0.14.0.2` for this candidate.
Follow the provider's manual approval step; do not grant automatic approval.

Put the signed installer back into its prepared bundle, then run:

```powershell
python unified/release.py finalize --bundle D:\signing-prep-final\CrimsonSkies-Unified-0.14.0-alpha.2 --preparation D:\signing-prep-final\preparation.json --out D:\signed-candidate
```

Failure creates no archive. Success writes the ZIP, `SHA256SUMS.txt` and a
fresh `release-report.json`. The old maintainer gameplay report is not copied
as proof of this new executable. Source hashes and signer identities are
recorded; the result remains explicitly `gameplayVerified: false`.

Full source game builds also stage the output without producing an unsigned
release ZIP. They accept `--signed-xdelta` after the pinned original tool has
generated/validated the deltas; the same finalizer then applies.

## Validation

```powershell
python -m unittest discover -s unified/tests -p test_release.py -v
```

The tests cover signing-order mistakes, code substitution, tampered deltas,
unexpected executable files, metadata and unsigned-release rejection. Their
success-path signature validator is mocked; they do not certify a real
certificate. Run the Windows signature check and SAC gameplay test again on
the final signed artifacts.

[SignPath GitHub integration](https://docs.signpath.io/trusted-build-systems/github)
explains build-origin verification and signing request configuration.

The checked-in workflow runs tests and compiles a review candidate on
GitHub-hosted Windows. It never publishes a release. After approval, configure
the `code-signing` environment with required reviewer approval, the secret
`SIGNPATH_API_TOKEN`, and variables `SIGNPATH_ORGANIZATION_ID`,
`SIGNPATH_PROJECT_SLUG`, `SIGNPATH_POLICY_SLUG`, `SIGNPATH_ARTIFACT_SLUG`.
Review `signpath-installer.xml` with the provider. The optional manual signing
job also refuses to proceed until an authorized signed decoder URL and SHA256
are committed to `signing-input.json`; preparation verifies both its unchanged
code and Windows trust before pinning it. Do not put tokens in that JSON.
An [application draft](SIGNPATH-APPLICATION.txt) is provided for owner review.
