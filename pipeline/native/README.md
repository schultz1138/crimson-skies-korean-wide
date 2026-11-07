# Native, GPU and launcher source build

This directory contains the authored assembly, x86-to-x64 lifting code, scoped
UI geometry policies, resolution presets, PE section/map/relocation handling,
and Win64 unwind construction used by the integrated release. It does not
contain a game DLL, executable, captured process image, VCDIFF decoder input,
or a previously built target. Generated intermediate images and manifests
are produced in a new work directory on every run.

Use Python 3.12 and the pinned packages in `requirements.txt`. These scripts
run on the build host without loading or executing the input game code.
Windows builds use explicit extended paths for long work/output filenames.

```
python native/build.py --input-content STOCK/Content --output-content OUT/Content --work-dir WORK/native --original-xbe WORK/default.xbe --captions assets/localization/native_captions.json
```

`default.xbe` must be extracted from the owned stock package by
`assets/package_io.py`. Its SHA-256 is checked. Alternatively omit
`--original-xbe` and provide `--assets-source assets`; the builder calls
`extract_owned_file(input_content, 'default.xbe')` itself. The same assets
directory supplies the shared caption table unless `--captions` is explicit.
The caption source is editable JSON containing 1,805 audio records and 1,901
timed text parts. The tutorial's separately authored line-break strings and
radio routines remain in `stages/translations` and `stages/work/*.asm`.

The input directory supplies exactly the release's five stock files. This
stage directly reads the stock Native/GPU/Menu; `package_io.py` validates
Data0000 and Data0005 before extracting the XBE. The assets stage generates
Data0000/5 separately. Existing Data0000/5 outputs are preserved; the three
Native/GPU/Menu output paths must not already exist. Input, output, public
source and work trees must be separate. The work directory must be empty.

The resulting three files have these SHA-256 values:

| File | SHA-256 |
| --- | --- |
| Native xefu DLL | `45c2c716da6c01f0937ce922dbfe2de89a3a9dfb163578757cfc5c5cc7e65f44` |
| VGPUDX12.dll | `f4d7784a007919a1e397405340855ac539c76f4abccfc6ecf8edebb2ed9835aa` |
| EmuMenu/Assets/TitleMenuData.json | `200b609e7b279c25814fb42ed1dd1cdcd6f3203b670dc3b05749a6ee26686265` |

The intermediate Korean beta 0.10.0-beta.1 Native DLL is also emitted at
`WORK/native/intermediate-beta1-native/xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll`.
Its SHA-256 is
`cfb9d6558ff0035494af8866d72cccb0e369d2c6a1549825a699f7249154c650`.
This is generated from stock, not read from an old installation.

`build-report.json` records every stage hash. The build checks exact stock,
intermediate and final hashes as well as instruction boundaries, source-byte
pins, PE checksums, dispatch-map aliases and bounded byte-change allowlists.
Historical audit-receipt and runtime-image reads have been removed from the
authoring path. Independent machine-code/runtime QA is separate from building;
the historical status descriptions in stage manifests are provenance, not new
claims of runtime validation.

The native chain assembles radio guest routines, lifts them into the original
dispatch ABI, compiles the timed corpus, appends typed HUD/menu/movie services,
repairs the declared PE reservation, and regenerates the preset decoder and
twelve bounded quad paths. Later stages preserve old generated ranges while
adding the reviewed geometry/diagnostic policy. The GPU chain assembles the
present leaf, exact visible crop proxy, preset parser, DPI scope, AA preference
preservation, and the scoped 4K/AA pool budget helper. Each new nonleaf GPU
frame includes its authored unwind metadata. Existing native UI helper unwind
limitations are unchanged by source publication.

`menu.py` constructs the launcher graphics category from human-editable labels,
dimensions and IDs in `stages/resolution-analysis/shared/preset-contract-v1.json`.
It preserves the original language category and does not copy a final menu
postimage. Numeric legacy keys in the preset contract document protocol history;
visible options use the human-readable labels.
