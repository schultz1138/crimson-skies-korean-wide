"""Build the 2611 GPU compatibility candidate using the existing emitters."""
import importlib.util
import json
import struct
import sys
from pathlib import Path

import pefile
from capstone import CS_GRP_CALL
from capstone.x86_const import X86_OP_IMM, X86_OP_MEM, X86_REG_RIP

from port_2611_native import add_sections, align, decoder, digest, finish, import_address, require

GPU_SHA = 'b4190ad13cfee52e814c20086705179970cd9c2268c243fd6b9345925745a8ca'
STAGES = Path(__file__).resolve().parents[1] / 'pipeline/native/stages'


def source(relative):
    path = STAGES / relative
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def port_gpu(path):
    raw = Path(path).read_bytes()
    require(digest(raw) == GPU_SHA, 'Unexpected 2611 GPU file')
    pe = pefile.PE(data=raw)
    base = pe.OPTIONAL_HEADER.ImageBase
    image = pe.get_memory_mapped_image()
    md = decoder()

    def instruction(rva):
        return next(md.disasm(image[rva:rva+15], base+rva, count=1))

    def check_call(rva, expected, indirect=False):
        ins = instruction(rva)
        require(ins.group(CS_GRP_CALL), f'Expected GPU call at {rva:#x}')
        operand = ins.operands[0]
        if indirect:
            require(operand.type == X86_OP_MEM and operand.mem.base == X86_REG_RIP
                    and rva+ins.size+operand.mem.disp == expected and ins.size == 6,
                    'Unexpected GPU DPI call')
        else:
            require(operand.type == X86_OP_IMM and operand.imm == base+expected and ins.size == 5,
                    'Unexpected GPU presentation call')

    get_rect = import_address(pe, b'GetClientRect')
    check_call(0xd68e9, 0x86f9c)
    for rva in (0x3bc69, 0xd6a76):
        check_call(rva, 0x80a10)
        require(image[rva-11:rva] == bytes.fromhex('4d8b8436b80c0000488bd7')
                or image[rva-14:rva].endswith(bytes.fromhex('488bd7488bc8')),
                'Blit call register inputs changed')
    for rva in (0x5ad57, 0x7c5aa):
        check_call(rva, get_rect, indirect=True)
    require(image[0x5a18c:0x5a192] == bytes.fromhex('4805ffff0000')
            and image[0x5a1ad:0x5a1b2] == bytes.fromhex('ffc583fd0e'),
            'GPU heap alignment or pool loop changed')
    scaling = 0x582ab
    scaling_instructions = list(md.disasm(image[scaling:scaling+9],base+scaling))
    require([(i.mnemonic,i.op_str) for i in scaling_instructions] == [
        ('mov','dword ptr [rbx + 0x68], eax'),('xor','r8d, r8d'),
        ('mov','dword ptr [rbx + 0x60], eax')], 'GPU scaling startup changed')
    config = instruction(0x5a220)
    require(config.operands[1].mem.base == X86_REG_RIP
            and config.address-base+config.size+config.operands[1].mem.disp == 0x7071f8,
            'GPU configuration pointer moved')
    require(image[0xd6868:0xd686e] == bytes.fromhex('8b86500e0000')
            and image[0xd6876:0xd687c] == bytes.fromhex('8b8e540e0000'),
            'GPU crop members moved')

    leaf = source('widescreen-analysis/ui/final-present/final_present_leaf.py')
    blit = source('resolution-analysis/gpu/final_call_proxy_v3.py')
    parser = source('resolution-analysis/shared/preset_decoder.py')
    dpi = source('resolution-analysis/gpu/dpi_rect_proxy_v2.py')
    budget = source('resolution-analysis/aspect/4k-aa-source-v1/shadow_heap_budget_v5.py')
    rx = pe.OPTIONAL_HEADER.SizeOfImage
    rw = rx + 0x2a000
    require(rx == 0x7a1000, 'Unexpected GPU image end')
    code, state = bytearray(rw-rx), bytearray(0x1000)
    state[:8] = struct.pack('<4sI', b'CSRG', 2)

    def put(rva, payload):
        target, offset = (state, rva-rw) if rva>=rw else (code, rva-rx)
        require(0<=offset<=len(target)-len(payload) and not any(target[offset:offset+len(payload)]),
                'GPU patch sections overlap')
        target[offset:offset+len(payload)] = payload

    leaf_at, blit_at, parser_at, dpi_at, budget_at = (rx + x for x in (0, 0x1000, 0x2000, 0x3000, 0x4000))
    table, unwind, ex_at, imports_at = (rx + x for x in (0x5000, 0x5800, 0x6000, 0x2a00))
    put(leaf_at, leaf.emit(base+leaf_at, base+0x86f9c)[0])
    proxy, _, proxy_meta = blit.emit(base+blit_at, base+parser_at, base+table, base+rw, base+0x80a10)
    put(blit_at, proxy)
    parse, parse_meta = parser.emit(base+parser_at, base+rw+0x100)
    put(parser_at, parse)
    dpi_code, _, dpi_meta = dpi.emit_dpi(base+dpi_at, base+parser_at, base+rw+0x200, base+get_rect, base+rw+0x80)
    put(dpi_at, dpi_code)
    budget_code, _, budget_meta = budget.emit(base+budget_at, base+rw+0x300,
                                             cache=base+rw+0x100, config=base+0x7071f8,
                                             pool='saved-rbp')
    put(budget_at, budget_code)
    startup_at = rx+0x4800
    startup_code, _ = budget.aa_preserved(base+startup_at,base+parser_at,base+rw+0x120)
    put(startup_at, startup_code)
    put(table, blit.table_bytes(json.loads(parser.CONTRACT_PATH.read_text('utf-8'))))

    # Pinned stock unwinding stays intact. Append records for the four
    # new nonleaf functions to its relocated exception directory.
    ed = pe.OPTIONAL_HEADER.DATA_DIRECTORY[3]
    old_pdata = pe.get_data(ed.VirtualAddress, ed.Size)
    rows = list(struct.iter_unpack('<III', old_pdata))
    functions = [(blit_at, blit_at+len(proxy), proxy_meta['unwind']),
                 (dpi_at, dpi_at+len(dpi_code), dpi_meta['unwindHex']),
                 (budget_at, budget_at+len(budget_code), budget_meta['unwindHex']),
                 (startup_at, startup_at+len(startup_code), '011104951103090112000150')]
    functions.extend((f['beginVA']-base, f['endVA']-base, f['unwindHex'])
                     for f in parse_meta['unwindFunctions'])
    for begin, end, encoded in sorted(functions):
        data = bytes.fromhex(encoded)
        put(unwind, data)
        rows.append((begin, end, unwind))
        unwind = align(unwind+len(data), 4)
    require(all(a[1]<=b[0] for a,b in zip(rows, rows[1:])), 'Overlapping GPU unwind ranges')
    pdata = b''.join(struct.pack('<III', *row) for row in rows)
    put(ex_at, pdata)

    # Preserve every shipped import and its IAT address. Add a separate
    # thunk for the same scoped DPI API already used by 2608.
    imports = pe.OPTIONAL_HEADER.DATA_DIRECTORY[1]
    original_desc = b''.join(group.struct.__pack__() for group in pe.DIRECTORY_ENTRY_IMPORT)
    require(image[imports.VirtualAddress:imports.VirtualAddress+len(original_desc)+20]
            == original_desc+bytes(20), 'Unexpected GPU import descriptors')
    int_at, hint_at, name_at = imports_at+0x200, imports_at+0x220, imports_at+0x260
    extra_desc = struct.pack('<IIIII', int_at,0,0,name_at,rw+0x200)
    new_imports = original_desc+extra_desc+bytes(20)
    put(imports_at, new_imports)
    thunk = struct.pack('<QQ', hint_at, 0)
    put(int_at, thunk)
    put(hint_at, b'\0\0SetThreadDpiAwarenessContext\0')
    put(name_at, b'USER32.dll\0')
    put(rw+0x200, thunk)

    # Keep every original section and remove the certificate directory of
    # this derived image. An edited DLL cannot carry the original signature.
    security = pe.OPTIONAL_HEADER.DATA_DIRECTORY[4]
    certificate_start = security.VirtualAddress
    require(certificate_start == max(s.PointerToRawData+s.SizeOfRawData for s in pe.sections)
            and certificate_start+security.Size == len(raw), 'Unexpected GPU certificate extent')
    target = add_sections(raw[:certificate_start], pe, [
        (b'.csres', rx, len(code), code, 0x60000020),
        (b'.csrw', rw, len(state), state, 0xc0000040)])
    struct.pack_into('<II', target, security.get_file_offset(), 0, 0)
    struct.pack_into('<II', target, ed.get_file_offset(), ex_at, len(pdata))
    struct.pack_into('<II', target, imports.get_file_offset(), imports_at, len(new_imports))
    hooks = {0xd68e9:(leaf_at,5),0x3bc69:(blit_at,5),0xd6a76:(blit_at,5),
             0x5ad57:(dpi_at,6),0x7c5aa:(dpi_at,6),0x5a18c:(budget_at,6)}
    for rva, (dest, length) in hooks.items():
        at = pe.get_offset_from_rva(rva)
        target[at:at+length] = b'\xe8'+struct.pack('<i',dest-rva-5)+b'\x90'*(length-5)
    # Replay both original scale stores in the startup shim and replay XOR
    # in the caller to restore its flags. Prime the preset before allocating.
    at = pe.get_offset_from_rva(scaling)
    target[at:at+9] = b'\xe8'+struct.pack('<i',startup_at-scaling-5)+bytes(scaling_instructions[1].bytes)+b'\x90'
    result = finish(target)
    out = pefile.PE(data=result)
    require(out.get_data(ex_at, len(old_pdata)) == old_pdata, 'GPU stock unwinding changed')
    require(import_address(out, b'GetClientRect') == get_rect
            and import_address(out, b'SetThreadDpiAwarenessContext') == rw+0x200,
            'Derived GPU import binding differs')
    expected = bytearray(raw[pe.OPTIONAL_HEADER.SizeOfHeaders:certificate_start])
    for site, length in [*((site, hook[1]) for site,hook in hooks.items()), (scaling,9)]:
        at = pe.get_offset_from_rva(site)
        offset = at-pe.OPTIONAL_HEADER.SizeOfHeaders
        expected[offset:offset+length] = result[at:at+length]
    require(result[pe.OPTIONAL_HEADER.SizeOfHeaders:certificate_start] == expected,
            'Unexpected writes to the shipped GPU sections')
    return result, {'hookRvas': [hex(x) for x in (*hooks,scaling)], 'stockUnwindRows':len(old_pdata)//12,
                    'appendedUnwindRows': len(functions), 'sha256':digest(result)}
