# SPDX-License-Identifier: MIT
"""Canonicalize the two legacy C# compiler build-identity fields, not code.

The .NET Framework compiler used by this release emits a wall-clock PE COFF
timestamp and a random Module Version ID. Restoring the documented release
identity makes otherwise identical compiler output byte-reproducible. The final
SHA-256 check rejects any different IL, resources, references or PE layout.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

EXPECTED_SHA256 = "14a7bc17ac4440aede259cbb7d2a91028836508d99159e24c67a2dae2de4ce24"
# Filled from the original release's PE/CLI metadata, not an executable payload.
RELEASE_TIMESTAMP = 1793987854
RELEASE_MVID_HEX = "72e46705c9ea94439d89703d9b907d3c"


def metadata_locations(data):
    def u16(at): return struct.unpack_from("<H", data, at)[0]
    def u32(at): return struct.unpack_from("<I", data, at)[0]
    pe = u32(0x3c)
    if data[:2] != b"MZ" or data[pe:pe+4] != b"PE\0\0":
        raise ValueError("Not a PE image")
    count, optional_size = u16(pe+6), u16(pe+20)
    optional = pe+24
    directory = optional + (112 if u16(optional) == 0x20b else 96)

    def raw(rva):
        for i in range(count):
            section = optional + optional_size + 40*i
            vs, va, size, pointer = struct.unpack_from("<IIII", data, section+8)
            if va <= rva < va + max(vs, size):
                result = pointer + rva - va
                if result >= len(data): break
                return result
        raise ValueError("RVA is not backed by this PE image")

    cli = raw(u32(directory+14*8))
    metadata = raw(u32(cli+8))
    if data[metadata:metadata+4] != b"BSJB":
        raise ValueError("Missing CLI metadata root")
    position = metadata+16+u32(metadata+12)
    position = (position+3) & ~3
    streams = u16(position+2)
    position += 4
    stream = {}
    for _ in range(streams):
        offset, size = u32(position), u32(position+4)
        end = data.index(0, position+8, min(position+40, len(data)))
        name = bytes(data[position+8:end]).decode("ascii")
        stream[name] = (metadata+offset, size)
        position = (end+1+3) & ~3
    tables = stream.get("#~", stream.get("#-"))
    if not tables or "#GUID" not in stream:
        raise ValueError("Required CLI streams are absent")
    tables = tables[0]
    heaps = data[tables+6]
    valid = struct.unpack_from("<Q", data, tables+8)[0]
    position = tables+24
    rows = {}
    for table in range(64):
        if valid & (1 << table):
            rows[table] = u32(position)
            position += 4
    if rows.get(0) != 1:
        raise ValueError("Expected one Module metadata row")
    string_size = 4 if heaps & 1 else 2
    guid_size = 4 if heaps & 2 else 2
    mvid_index = int.from_bytes(data[position+2+string_size:position+2+string_size+guid_size], "little")
    guid, guid_bytes = stream["#GUID"]
    if not 1 <= mvid_index <= guid_bytes // 16:
        raise ValueError("Invalid module MVID index")
    return pe+8, guid+16*(mvid_index-1)


def normalize(path):
    path = Path(path)
    data = bytearray(path.read_bytes())
    stamp, mvid = metadata_locations(data)
    before = {"timestamp": struct.unpack_from("<I", data, stamp)[0], "mvidHex": data[mvid:mvid+16].hex()}
    struct.pack_into("<I", data, stamp, RELEASE_TIMESTAMP)
    data[mvid:mvid+16] = bytes.fromhex(RELEASE_MVID_HEX)
    actual = hashlib.sha256(data).hexdigest()
    if actual != EXPECTED_SHA256:
        raise ValueError("Compiler output differs beyond the two identity fields: " + actual)
    path.write_bytes(data)
    return {"sha256": actual, "timestampOffset": stamp, "mvidOffset": mvid,
            "onlyIdentityFieldsCanonicalized": True, "before": before}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("installer", type=Path)
    args = parser.parse_args()
    print(json.dumps(normalize(args.installer), indent=2))
