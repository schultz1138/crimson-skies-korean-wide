"""Read-only XBE cross-reference and disassembly helper for the user's copy."""
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "pythonlibs"))
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

data = (ROOT / "work/default.original.xbe").read_bytes()
u32 = lambda p: struct.unpack_from("<I", data, p)[0]
base = u32(0x104)
sections = []
for i in range(u32(0x11C)):
    p = u32(0x120) - base + 0x38 * i
    flags, va, vsize, raw, size, nameva = struct.unpack_from("<6I", data, p)
    namep = nameva - base
    name = data[namep:data.index(0, namep)].decode("ascii", "replace")
    sections.append(dict(name=name, va=va, vsize=vsize, raw=raw, size=size, flags=flags))

def file_to_va(offset):
    for s in sections:
        if s["raw"] <= offset < s["raw"] + s["size"]:
            return s["va"] + offset - s["raw"]
    return base + offset if offset < u32(0x108) else None

def va_to_file(va):
    for s in sections:
        if s["va"] <= va < s["va"] + s["size"]:
            return s["raw"] + va - s["va"]
    return va - base if base <= va < base + u32(0x108) else None

def disassemble(va, length=256):
    off = va_to_file(va)
    if off is None:
        raise ValueError(f"Unmapped address {va:#x}")
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.skipdata = True
    for ins in md.disasm(data[off:off + length], va):
        print(f"{ins.address:08x}  {ins.bytes.hex():22s} {ins.mnemonic:8s} {ins.op_str}")

def find_string(text):
    needle = text.encode("ascii") + b"\0"
    start = 0
    while (off := data.find(needle, start)) >= 0:
        start = off + 1
        va = file_to_va(off)
        print(f"STRING {text!r} off={off:#x} va={va:#x}")
        reference = struct.pack("<I", va)
        rp = 0
        while (rp := data.find(reference, rp)) >= 0:
            rva = file_to_va(rp)
            print(f"  REF off={rp:#x} va={rva:#x} bytes={data[max(0,rp-12):rp+16].hex()}")
            rp += 1

if __name__ == "__main__":
    if sys.argv[1] == "find":
        for text in sys.argv[2:]:
            find_string(text)
    elif sys.argv[1] == "disasm":
        disassemble(int(sys.argv[2], 0), int(sys.argv[3], 0) if len(sys.argv) > 3 else 256)
    elif sys.argv[1] == "data":
        off = va_to_file(int(sys.argv[2], 0))
        size = int(sys.argv[3], 0) if len(sys.argv) > 3 else 128
        for p in range(off, off + size, 16):
            chunk = data[p:p + 16]
            print(f"{file_to_va(p):08x} {chunk.hex(' '):48s} " + "".join(chr(c) if 32 <= c < 127 else "." for c in chunk))
    elif sys.argv[1] == "xref":
        va = int(sys.argv[2], 0)
        needle = struct.pack("<I", va)
        p = 0
        while (p := data.find(needle, p)) >= 0:
            print(f"off={p:#x} va={file_to_va(p):#x} {data[max(0,p-8):p+12].hex()}")
            p += 1
    else:
        print(sections)
