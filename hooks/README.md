# Hook reference sources

These sources explain selected custom helpers in the accepted beta. They are not
a complete PE builder or a replacement for the validated VCDIFF distribution.

- `gpu_shadow_budget.py`: standalone offline assembler for the final pool10 helper.
  The emit function is unchanged from the accepted implementation; its private
  development imports were replaced with ordinary Keystone/Capstone imports.
  It selects 1536MiB only for preset11/N6/AA1-or-2/pool10/original384MiB with
  bounded source-owned configuration spans, otherwise preserving the original size.
  It replays the replaced ADD instruction and returns. It does not install hooks,
  register unwind records, change the AA proxy or modify a game file.
- `native-services.reference.asm`: generated helper assembly listing from final HUD
  Native v7. Each helper was assembled separately; repeated labels and RIP-relative
  placeholders are expected. This listing cannot be assembled as one object.
- `solid_policy.py`: final full-canvas rectangle policy transformation used by the
  HUD helper builder. It expects the builder's validated source-owned body list.

The release Native SHA-256 is
`45c2c716da6c01f0937ce922dbfe2de89a3a9dfb163578757cfc5c5cc7e65f44`.
The release GPU SHA-256 is
`f4d7784a007919a1e397405340855ac539c76f4abccfc6ecf8edebb2ed9835aa`.

Scope: exact packaged build2608.3123.1.0. Pointer numeric guards do not prove arbitrary
memory is mapped. These helpers rely on the validated source-owned call sites.
Installer QA does not substitute for graphics/ABI/runtime validation of new hooks.

The complete, source-built PE authoring chain is now available in ../pipeline/native; see ../docs/REPRODUCING.ko.md for the full source-to-release build.
