# Synthetic profile-manager tests

These tests use small generated stores. They require no installed game, original save files, SDK utilities, or network access. Windows, NTFS, Python 3, PowerShell, and the .NET Framework C# compiler are required.

From the repository root, choose a fresh, absent, short local workspace:

```powershell
py -3 -B multilingual/tests/profile_manager/run_profile_fixtures.py --source-dir multilingual/launcher --work C:\Temp\cs-profile-qa
```

The runner refuses an existing workspace and game/save-store paths. All fixture files, backups, transaction journals, compiler output, temporary files, and junctions stay inside the explicitly selected workspace. It never closes or launches the actual game, imports saves, calls a save provider, or reads installed profiles. The workspace remains available for inspection after the run.

The current suite has 512 assertions:

| Cohort | Assertions | Boundary |
|---|---:|---|
| Read-only store parser | 105 | Framing, identities, offsets, active/deleted states, stale selections, membership and blob bindings |
| Selected backup | 38 | Exact selected ZIP/XML/payloads, immutable backups, materialization and tamper rejection |
| Transaction priority paths | 60 | Three selected profiles, 13 failure points, four interrupted operations and exact restoration |
| Transaction adversarial paths | 49 | Journal ownership, latest-index preservation, atomic commit/rollback interruptions, locks and process/mutex conflicts |
| Restore priority paths | 40 | Absent/tombstone protocol, exact payloads, same-context refusals and rollback |
| Restore recovery and CAS | 33 | Folder/index gaps, captured-latest preservation and owned-folder references |
| Cross-version recovery | 3 | One frozen 0.12.1 authenticated pending delete recovered by current code |
| Restore form | 116 | Read-only inspection, explicit confirmation, conflicts, DTO copies, receipts and busy guards |
| Profile form | 53 | Selection, capabilities, verified receipts, explicit recovery and busy/reentry guards |
| GUI/CLI launch guard | 13 | Guard ordering and arguments, with an inert engine/service dependency |
| Actual NTFS junctions | 2 | Reparse rejection at store/account boundaries |

Counts are assertions, not live cloud tests. Production parser, backup, transaction, and UI code is compiled from the supplied source directory. Only these named fixture seams change in workspace copies:

- `DefaultWgsRoot` returns a generated fixture path.
- The transaction scope-directory resolver is shortened within the workspace for legacy Windows path limits.
- The language form's preference path points into the workspace.

The cross-version cohort compiles the authored MIT `LegacyProfileOperations_v0121.cs` separately. Its original SHA-256 is `3823ff894b008931942159d690f07b7ac59e0ecf53e77e1d9c5f47ad6e4b6910`; only the same workspace scope-directory seam is shortened. It is a test input, not runtime code or an SDK/game binary.

The production stopped-process callback is injected with synthetic states. GUI/CLI engine and service binding are inert test dependencies. Actual `File.Replace`, directory moves, DPAPI, HMAC checks, path guards, and NTFS junction handling are exercised.

`verification.json` records source and fixture hashes, cohort results, and limits. The host-package adapter and real provider/cloud protocol need separate validation. DPAPI/HMAC protects these integrity checks; it is not a security boundary against the same Windows principal decrypting and rewriting all data. Private SDK disassembly and original-code emulation evidence are not included in this directory.
