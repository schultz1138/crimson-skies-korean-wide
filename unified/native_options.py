"""Compose optional caption/widescreen hooks from the public source build.

Inputs are outputs of pipeline/build.py and dubbing/build_captions.py. No
installed files or private frozen patch maps are read. Stock instructions and
dispatch records replace only the caption compiler's declared hook ranges.
"""
from pathlib import Path
import hashlib, json, struct
import pefile

NAME = 'xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll'
STOCK = 'd49d36bd5e6beb6bcc2198dd92d1d3c9116fa0b6584b0291e0a581e28faed86d'
CAPTION = 'cfb9d6558ff0035494af8866d72cccb0e369d2c6a1549825a699f7249154c650'
WIDE = '45c2c716da6c01f0937ce922dbfe2de89a3a9dfb163578757cfc5c5cc7e65f44'
DUB = '155003071b4f27d81e35871efd3b1b08cfad6f68d91dabf70cddcaa85a8cfe9b'

def digest(b): return hashlib.sha256(b).hexdigest()

def compose(stock, wide, dubbed, native_work, korean, widescreen, captions):
    """captions: off/original/dub; off retains game's movie subtitles."""
    a, b, d = [Path(p).read_bytes() for p in (stock, wide, dubbed)]
    assert [digest(x) for x in (a,b,d)] == [STOCK,WIDE,DUB]
    folder = Path(native_work)/'tree/native-host-v5'
    c = (folder/NAME).read_bytes()
    m = json.loads((folder/'manifest.json').read_text('utf-8'))
    assert digest(c)==m['patchedSha256']==CAPTION
    assert captions in ('off','original','dub')
    assert korean or captions=='off'
    if not korean and not widescreen: return a
    target = bytearray(b if widescreen else c)
    if captions=='dub':
        # Source-owned, fixed-size dictionaries; all code remains exact.
        p, q = pefile.PE(data=target), pefile.PE(data=d)
        for rva,n in [(0x2816f00,233964),(0x2804cc0,1028)]:
            at=p.get_offset_from_rva(rva)
            assert target[at:at+n]==pefile.PE(data=b).get_data(rva,n)
            target[at:at+n]=q.get_data(rva,n)
    if captions=='off':
        ranges = [(r['fileOffset'],4) for r in m['mapChanges']]
        ranges += [(r['fileOffset'],len(bytes.fromhex(r['after']))) for r in m['hooks']]
        # Widescreen stages must leave every compiler-owned hook byte intact.
        for at,n in ranges:
            assert target[at:at+n]==c[at:at+n], 'Caption/wide hook overlap'
            target[at:at+n]=a[at:at+n]
    p=pefile.PE(data=target)
    struct.pack_into('<I',target,p.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),p.generate_checksum())
    q=pefile.PE(data=target)
    assert q.verify_checksum() and not q.get_warnings(), q.get_warnings()
    if korean and widescreen and captions!='off':
        assert digest(target)==(DUB if captions=='dub' else WIDE)
    return bytes(target)
