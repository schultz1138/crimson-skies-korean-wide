"""Exact 2611 Emu host guards observed from the registered, unmodified host.

The protected Emu.exe remains untouched. Only our preset decoders change;
unknown hosts still return the original fallback without calling an IAT.
"""
import importlib.util
import struct
from pathlib import Path

HOST_2611 = dict(timestamp=0x6aeab07e, imageSize=0xda3000,
                 setterRva=0x5298c, commandLineIat=0xad338,
                 setter=bytes.fromhex('488b1505790d00488bca480fbae909480fbaf20984c0480f45d1488915eb780d00'))


def preset_decoder():
    path = Path(__file__).resolve().parents[1] / 'pipeline/native/stages/resolution-analysis/shared/preset_decoder.py'
    spec = importlib.util.spec_from_file_location('cs_preset_decoder', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def retarget_native_decoder(target, pe):
    """Replace an entire exact old emitter output, keeping code/unwind extents."""
    rva = 0x2853000
    at = pe.get_offset_from_rva(rva)
    if target[at:at+2] != b'\x8b\x05':
        raise ValueError('Missing Native preset decoder')
    base = pe.OPTIONAL_HEADER.ImageBase
    cache = base + rva + 6 + struct.unpack_from('<i', target, at+2)[0]
    decoder = preset_decoder()
    before, old_meta = decoder.emit(base+rva, cache)
    after, new_meta = decoder.emit(base+rva, cache, HOST_2611)
    if (target[at:at+len(before)] != before or len(before) != len(after)
            or old_meta['unwindFunctions'] != new_meta['unwindFunctions']):
        raise ValueError('Native preset decoder preimage or unwind extent changed')
    target[at:at+len(after)] = after
    return dict(rva=hex(rva), codeBytes=len(after), host='2611.323.502.0',
                oldCodeSha256=old_meta['codeSha256'], codeSha256=new_meta['codeSha256'])
