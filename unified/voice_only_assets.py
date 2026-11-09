"""Remove authored tutorial caption events from caption-off asset variants.

The original tutorial script preserves mission instructions, dialogue triggers
and gameplay. Only new output copies are written; installed files are inputs.
"""
from pathlib import Path
import copy
import hashlib
import io
import json
import shutil
import struct
import sys
import zipfile

ASSETS = Path(__file__).resolve().parents[1] / 'pipeline' / 'assets'
sys.path.append(str(ASSETS))
from package_io import Package, locate, digest

MEMBER = 'ca/res/sh_tutorial.sdb'
STOCK_SCRIPT = '8838dd3f46bd64f14aa6453d8ad487a3cb23e67b0b7a870ce66753fb2fefe18c'
CAPTION_SCRIPT = '24ee16ad3a1e4ff9927f35fc89ebf048a752e4876b85320abdbf8656094037b1'
INPUTS = {
    'foundation': ('91f96697337e6717dcdfaa99eb321196c3521da33295e77e54fb6777c92ed487',
                   '68317f440ba24f74a832346f9ddf400f6a3076a743cd8e80b67be62aa5484e31'),
    'full-dub': ('97a4167d5321ed61821ac414b0191b432c37ceff3f9ed4fa822717223c791531',
                 'e24a1398a97f79dfe65e20aff9ebaef7587fd823bdf9e8554d4fec2e67442cb5'),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def replace_member_fixed_size(original, replacement):
    """Retain the ZIP allocation and every other member's decoded bytes."""
    with zipfile.ZipFile(io.BytesIO(original)) as source:
        infos = source.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or names.count(MEMBER) != 1:
            raise ValueError('Expected one tutorial member without duplicate names')
        if source.comment:
            raise ValueError('Unexpected archive comment')
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', allowZip64=False) as target:
            for info in infos:
                target.writestr(copy.copy(info), replacement if info.filename == MEMBER else source.read(info))
        compact = stream.getvalue()
        eocd = bytearray(compact[-22:])
        if eocd[:4] != b'PK\x05\x06' or struct.unpack_from('<H', eocd, 20)[0]:
            raise ValueError('Unexpected ZIP footer')
        central = struct.unpack_from('<I', eocd, 16)[0]
        padding = len(original) - len(compact)
        if padding < 0:
            raise ValueError('Restored tutorial exceeds the owned archive allocation')
        struct.pack_into('<I', eocd, 16, central + padding)
        result = compact[:central] + bytes(padding) + compact[central:-22] + eocd
        if len(result) != len(original):
            raise ValueError('Archive allocation changed')
        with zipfile.ZipFile(io.BytesIO(result)) as checked:
            if checked.namelist() != names or checked.testzip() is not None:
                raise ValueError('Rebuilt archive failed validation')
            for name in names:
                expected = replacement if name == MEMBER else source.read(name)
                if checked.read(name) != expected:
                    raise ValueError('Unexpected member change: ' + name)
        return result


def build_variant(stock, localized, out, variant):
    stock, localized, out = [Path(path).resolve() for path in (stock, localized, out)]
    if out.exists() or any(out.is_relative_to(path) or path.is_relative_to(out) for path in (stock, localized)):
        raise ValueError('Use a new output separate from both inputs')
    if variant not in INPUTS:
        raise ValueError('Unknown localized baseline')
    data = Path('Game/DefaultPackage.data')
    for name, expected in zip(('Data0000', 'Data0005'), INPUTS[variant]):
        if digest(localized / data / name) != expected:
            raise ValueError('Localized input mismatch: ' + name)
    with Package(stock) as original, Package(localized, verify=False) as current:
        with zipfile.ZipFile(io.BytesIO(original.file('data.zip'))) as archive:
            script = archive.read(MEMBER)
        source_zip = current.file('data.zip')
        with zipfile.ZipFile(io.BytesIO(source_zip)) as archive:
            if sha(script) != STOCK_SCRIPT or sha(archive.read(MEMBER)) != CAPTION_SCRIPT:
                raise ValueError('Unexpected stock or injected tutorial script')
        rebuilt = replace_member_fixed_size(source_zip, script)
        entry = current.entry('data.zip')
        start = (entry['sector'] - 32) * 2048
        folder = out / data
        folder.mkdir(parents=True)
        for name in ('Data0000', 'Data0005'):
            shutil.copyfile(localized / data / name, folder / name)
        with (folder / 'Data0005').open('r+b') as target:
            pos = 0
            while pos < len(rebuilt):
                name, offset, within = locate(start + pos)
                if name != 'Data0005':
                    raise ValueError('Unexpected tutorial archive volume')
                count = min(4096 - within, len(rebuilt) - pos)
                target.seek(offset)
                target.write(rebuilt[pos:pos + count])
                pos += count
    with Package(out, verify=False) as checked:
        with zipfile.ZipFile(io.BytesIO(checked.file('data.zip'))) as archive:
            if sha(archive.read(MEMBER)) != STOCK_SCRIPT:
                raise ValueError('Original tutorial was not restored')
    report = dict(variant=variant, changedMember=MEMBER, restoredScriptSha256=STOCK_SCRIPT,
                  archiveBytes=len(rebuilt), archiveSha256=sha(rebuilt),
                  path='Game/DefaultPackage.data/Data0005', sha256=digest(folder / 'Data0005'),
                  bytes=(folder / 'Data0005').stat().st_size,
                  data0000Unchanged=digest(folder / 'Data0000') == INPUTS[variant][0])
    (out / 'voice-only-assets.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock', required=True, type=Path)
    parser.add_argument('--localized', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--variant', choices=INPUTS, required=True)
    args = parser.parse_args()
    print(json.dumps(build_variant(args.stock, args.localized, args.out, args.variant), indent=2))
