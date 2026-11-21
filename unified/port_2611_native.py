"""Port the authored 2608 caption/HUD payloads to the pinned 2611 Native DLL."""
import hashlib
import re
import struct
from pathlib import Path

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_GRP_CALL, CS_GRP_JUMP, CS_GRP_RET
from capstone.x86_const import X86_OP_IMM, X86_OP_MEM, X86_REG_RIP

NEW_NATIVE = 'b59891070df50f50219a458fa541e05f4fac93b63eb67dca5ced00d38314a0e3'
OLD_NATIVE = 'd49d36bd5e6beb6bcc2198dd92d1d3c9116fa0b6584b0291e0a581e28faed86d'
OLD_MAP, NEW_MAP, MAP_END = 0x1457190, 0x14571a0, 0x27c4fd8


def require(condition, explanation):
    if not condition:
        raise ValueError(explanation)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def align(value, alignment):
    return ((value + alignment - 1) // alignment) * alignment


def add_sections(original, pe, specifications):
    """Append only the patch sections; keep the shipped section locations."""
    target = bytearray(original)
    header = pe.sections[-1].get_file_offset() + 40
    header_end = header + 40 * len(specifications)
    require(header_end <= pe.OPTIONAL_HEADER.SizeOfHeaders
            and not any(target[header:header_end]), 'Patch section headers do not fit')
    previous_end = pe.OPTIONAL_HEADER.SizeOfImage
    code_size = pe.OPTIONAL_HEADER.SizeOfCode
    data_size = pe.OPTIONAL_HEADER.SizeOfInitializedData
    for index, (name, rva, virtual_size, payload, flags) in enumerate(specifications):
        require(rva >= previous_end and rva % 4096 == 0, 'Patch section overlap')
        offset = align(len(target), pe.OPTIONAL_HEADER.FileAlignment)
        raw_size = align(len(payload), pe.OPTIONAL_HEADER.FileAlignment)
        target.extend(bytes(offset - len(target)))
        target.extend(payload)
        target.extend(bytes(raw_size - len(payload)))
        struct.pack_into('<8sIIIIIIHHI', target, header + 40 * index, name,
                         virtual_size, rva, raw_size, offset, 0, 0, 0, 0, flags)
        previous_end = align(rva + max(virtual_size, raw_size), 4096)
        if flags & 0x20:
            code_size += raw_size
        if flags & 0x40:
            data_size += raw_size
    struct.pack_into('<H', target, pe.FILE_HEADER.get_field_absolute_offset('NumberOfSections'),
                     len(pe.sections) + len(specifications))
    for name, value in [('SizeOfImage', previous_end), ('SizeOfCode', code_size),
                        ('SizeOfInitializedData', data_size)]:
        struct.pack_into('<I', target, pe.OPTIONAL_HEADER.get_field_absolute_offset(name), value)
    return target


def finish(target):
    pe = pefile.PE(data=target)
    struct.pack_into('<I', target, pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),
                     pe.generate_checksum())
    result = bytes(target)
    require(pefile.PE(data=result).verify_checksum(), 'Invalid rebuilt PE checksum')
    return result


def decoder():
    disasm = Cs(CS_ARCH_X86, CS_MODE_64)
    disasm.detail = True
    return disasm


def import_address(pe, name):
    pe.parse_data_directories(directories=[1])
    addresses = {entry.address - pe.OPTIONAL_HEADER.ImageBase
                 for library in pe.DIRECTORY_ENTRY_IMPORT
                 for entry in library.imports if entry.name == name}
    require(len(addresses) == 1, 'Expected unique import ' + name.decode())
    return addresses.pop()


def port_native(previous_stock, current_stock, previous_variant):
    old_raw, new_raw, variant_raw = (Path(path).read_bytes() for path in
                                    (previous_stock, current_stock, previous_variant))
    require(digest(old_raw) == OLD_NATIVE and digest(new_raw) == NEW_NATIVE,
            'Unexpected Native inputs')
    old_pe, new_pe, variant_pe = (pefile.PE(data=data, fast_load=True) for data in
                                  (old_raw, new_raw, variant_raw))
    old, new, variant = (pe.get_memory_mapped_image() for pe in (old_pe, new_pe, variant_pe))
    end = old_pe.OPTIONAL_HEADER.SizeOfImage
    base = old_pe.OPTIONAL_HEADER.ImageBase
    require(end == new_pe.OPTIONAL_HEADER.SizeOfImage == 0x27f5000
            and base == new_pe.OPTIONAL_HEADER.ImageBase == variant_pe.OPTIONAL_HEADER.ImageBase,
            'Native base or patch section placement changed')
    if variant_raw == old_raw:
        return new_raw, {'detours': 0, 'dispatchEntries': 0, 'relocatedBranches': 0}
    require([s.Name.rstrip(b'\0') for s in variant_pe.sections[6:]] in [
        [b'.kradio', b'.autocap'], [b'.kradio', b'.autocap', b'.wideui', b'.widesta']],
        'Unexpected authored Native sections')
    target = add_sections(new_raw, new_pe, [
        (s.Name, s.VirtualAddress, s.Misc_VirtualSize, s.get_data(), s.Characteristics)
        for s in variant_pe.sections[6:]])
    target_pe = pefile.PE(data=target, fast_load=True)

    def is_payload(address):
        return any(s.Characteristics & 0x20000000
                   and s.VirtualAddress <= address < s.VirtualAddress + s.Misc_VirtualSize
                   for s in variant_pe.sections[6:])

    address_map = {}
    roots = set()
    changed_entries = 0
    map_length = MAP_END - OLD_MAP
    for offset in range(0, map_length, 8):
        guest, before = struct.unpack_from('<II', old, OLD_MAP + offset)
        updated_guest, after = struct.unpack_from('<II', new, NEW_MAP + offset)
        variant_guest, routed = struct.unpack_from('<II', variant, OLD_MAP + offset)
        require(guest == updated_guest == variant_guest, 'Guest dispatch keys diverged')
        require(address_map.setdefault(before, after) == after, 'Ambiguous native dispatch alias')
        if routed != before:
            require(is_payload(routed), 'Dispatch hook leaves patch code')
            struct.pack_into('<I', target, new_pe.get_offset_from_rva(NEW_MAP + offset + 4), routed)
            roots.add(routed)
            changed_entries += 1

    disasm = decoder()
    hooks = []
    text_end = old_pe.sections[0].VirtualAddress + old_pe.sections[0].Misc_VirtualSize
    text_start = old_pe.sections[0].VirtualAddress
    # The only edits to original text are complete installed CALL/JMP detours
    # with optional NOP padding. Exact old/new preimages certify their transfer.
    for match in re.finditer(rb'[\xe8\xe9]', variant[text_start:text_end]):
        at = text_start + match.start()
        if old[at:at + 5] == variant[at:at + 5]:
            continue
        entry = at + 5 + struct.unpack_from('<i', variant, at + 1)[0]
        if not is_payload(entry):
            continue
        stop = at + 5
        while variant[stop] == 0x90 and variant[stop] != old[stop]:
            stop += 1
        require(old[at:stop] == new[at:stop] and address_map.get(at, at) == at,
                f'Native detour preimage changed at {at:#x}')
        require(sum(i.size for i in disasm.disasm(old[at:stop], base + at)) == stop - at,
                f'Native detour splits instruction at {at:#x}')
        loc = new_pe.get_offset_from_rva(at)
        target[loc:loc + stop - at] = variant[at:stop]
        hooks.append((at, stop))
        roots.add(entry)
    old_text = bytearray(old[text_start:text_end])
    for at, stop in hooks:
        old_text[at-text_start:stop-text_start] = variant[at:stop]
    require(old_text == variant[text_start:text_end], 'Unaccounted original Native code edit')
    for section in old_pe.sections[1:]:
        lo, hi = section.VirtualAddress, section.VirtualAddress + section.SizeOfRawData
        for start, stop in [(lo, min(hi, OLD_MAP)), (max(lo, MAP_END), hi)]:
            if start < stop:
                require(old[start:stop] == variant[start:stop], 'Unaccounted original Native data edit')

    thread_id = import_address(new_pe, b'GetCurrentThreadId')
    require(import_address(old_pe, b'GetCurrentThreadId') == thread_id == 0x1457060,
            'Native thread ID import changed')
    for at in (0x100a, 0x1056, 0x1077, 0x10f9):
        instruction = next(disasm.disasm(new[at:at+7], base+at))
        require(new[at:at+7] == old[at:at+7]
                and instruction.operands[-1].mem.disp + at + 7 == 0x27f16d0,
                'Native guest dispatch callback moved')

    # Follow the authored code entries, including every guest dispatch entry.
    # Data dictionaries and embedded literal tables are never decoded as code.
    visited, pending = set(), list(roots)
    relocated = 0
    while pending:
        at = pending.pop()
        while is_payload(at) and at not in visited:
            visited.add(at)
            instruction = next(disasm.disasm(variant[at:at+15], base+at, count=1), None)
            require(instruction is not None, f'Invalid authored instruction at {at:#x}')
            branch = instruction.group(CS_GRP_CALL) or instruction.group(CS_GRP_JUMP)
            for operand in instruction.operands:
                if branch and operand.type == X86_OP_IMM:
                    destination = operand.imm - base
                    if is_payload(destination):
                        pending.append(destination)
                        continue
                    require(text_start <= destination < text_end, 'Branch leaves authored image')
                    mapped = address_map.get(destination, destination)
                    require(old[destination:destination+8] == new[mapped:mapped+8],
                            f'Native continuation changed at {destination:#x}')
                    if mapped != destination:
                        require(instruction.imm_size == 4, 'Native short branch moved')
                        loc = target_pe.get_offset_from_rva(at) + instruction.imm_offset
                        struct.pack_into('<i', target, loc, mapped - at - instruction.size)
                        relocated += 1
                elif operand.type == X86_OP_MEM and operand.mem.base == X86_REG_RIP:
                    destination = at + instruction.size + operand.mem.disp
                    require(destination in (0, thread_id, 0x27f16d0)
                            or end <= destination < len(variant),
                            f'Unreviewed Native data reference {destination:#x}')
            if instruction.group(CS_GRP_RET) or instruction.mnemonic in ('jmp','int3','ud2'):
                break
            at += instruction.size
    return finish(target), {'detours': len(hooks), 'dispatchEntries': changed_entries,
                            'relocatedBranches': relocated, 'verifiedInstructions': len(visited)}
