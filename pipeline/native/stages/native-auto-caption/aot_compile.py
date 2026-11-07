"""Offline x86-to-native compiler for this exact, immutable caption-v2 DLL.

Logical x86 instructions use independently reviewed, unused INT3 addresses only
as dispatch keys. No guest image bytes are changed. Generated native code and
read-only tables live in a new RX PE section; finish() writes workspace files.
"""
from __future__ import annotations

import ast
import bisect
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pythonlibs'))
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_MODE_64, CS_GRP_CALL, CS_GRP_JUMP
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
from keystone import Ks, KS_ARCH_X86, KS_MODE_32, KS_MODE_64

BASE_SHA256 = 'f4432e0adb3a97a027cdc00fef98a20df2f0b784b467578a7b4550119e7f0cd3'
ORIGINAL_HOST_SHA256 = 'd49d36bd5e6beb6bcc2198dd92d1d3c9116fa0b6584b0291e0a581e28faed86d'
ORIGINAL_XBE_SHA256 = '43048e59b75065e82c032859ac700c75cc2bd124f6ae817a7a2d2ca3e252aad2'
DLL_NAME = 'xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll'
MAP_BEGIN, MAP_END = 0x1457190, 0x27c4fd8
MAP_COUNT = (MAP_END - MAP_BEGIN) // 8
GPR64 = {'eax': 'rax', 'ecx': 'rcx', 'edx': 'rdx', 'ebx': 'rbx',
         'esp': 'r14', 'ebp': 'rbp', 'esi': 'rsi', 'edi': 'rdi'}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _align(value, alignment):
    return (value + alignment - 1) // alignment * alignment


def _clean_asm(assembly):
    return '\n'.join(line.split(';', 1)[0] for line in assembly.splitlines())


@dataclass
class GuestProgram:
    name: str
    asm: str
    logicalVA: int
    code: bytes
    instructions: list
    guest_keys: dict
    host_rvas: dict

    @property
    def guestVA(self):
        return self.guest_keys[self.instructions[0].address]

    @property
    def hostRVA(self):
        return self.host_rvas[self.instructions[0].address]


class AotCompiler:
    instruction_slot_bytes = 192
    service_slot_bytes = 4096
    dispatch_ptr_rva = 0x27f16d0

    def __init__(self):
        self.base_path = ROOT / 'native-host-v2' / DLL_NAME
        self.base_bytes = self.base_path.read_bytes()
        if _sha(self.base_bytes) != BASE_SHA256:
            raise ValueError('Immutable native-v2 candidate hash mismatch')
        self.baseM = json.loads((ROOT / 'native-host-v2/manifest.json').read_text('utf8'))
        if self.baseM['patchedSha256'] != BASE_SHA256:
            raise ValueError('Native-v2 manifest identity mismatch')
        self.original_bytes = (ROOT / 'native-host-v1/original.xefu.dll').read_bytes()
        if _sha(self.original_bytes) != ORIGINAL_HOST_SHA256:
            raise ValueError('Original native source hash mismatch')
        self.xbe = (ROOT / 'work/default.original.xbe').read_bytes()
        if _sha(self.xbe) != ORIGINAL_XBE_SHA256:
            raise ValueError('Original guest source hash mismatch')
        self.pe = pefile.PE(data=self.base_bytes)
        self.image_base = self.pe.OPTIONAL_HEADER.ImageBase
        self.map_file = self.pe.get_offset_from_rva(MAP_BEGIN)
        self._cs32 = Cs(CS_ARCH_X86, CS_MODE_32)
        self._cs32.detail = True
        self._cs64 = Cs(CS_ARCH_X86, CS_MODE_64)
        self._cs64.detail = True
        self._ks32 = Ks(KS_ARCH_X86, KS_MODE_32)
        self._ks64 = Ks(KS_ARCH_X86, KS_MODE_64)
        self.programs = {}
        self.services = {}
        self._logical = {}
        self._keys = self._available_keys()
        self._key_cursor = 0
        self._laid_out = False
        self._compiled = False
        self._hooks = []
        self._data = b''
        self.generated = []
        self.service_records = []

    def _record(self, guestVA, original=False):
        guestVA = int(guestVA)
        key = guestVA - 0x10000
        if not 0 <= key <= 0xffffffff:
            raise ValueError(f'Out-of-range guest key {guestVA:#x}')
        raw = self.original_bytes if original else self.base_bytes
        lo, hi = 0, MAP_COUNT
        while lo < hi:
            mid = (lo + hi) // 2
            value = struct.unpack_from('<I', raw, self.map_file + mid * 8)[0]
            if value < key:
                lo = mid + 1
            else:
                hi = mid
        off = self.map_file + lo * 8
        if lo == MAP_COUNT or struct.unpack_from('<I', raw, off)[0] != key:
            raise ValueError(f'Unmapped guest key {guestVA:#x}')
        return off + 4, struct.unpack_from('<I', raw, off + 4)[0]

    def original_host(self, guestVA):
        """Return the current BASE-V2 MAP host RVA, including v2 replacements."""
        return self._record(guestVA)[1]

    def _xbe_offset(self, va):
        image_base = struct.unpack_from('<I', self.xbe, 0x104)[0]
        section_count, section_va = struct.unpack_from('<II', self.xbe, 0x11c)
        for n in range(section_count):
            at = section_va - image_base + n * 0x38
            _, start, _, raw, size = struct.unpack_from('<5I', self.xbe, at)
            if start <= va < start + size:
                return raw + va - start
        raise ValueError(f'Guest VA outside original section bytes {va:#x}')

    def _available_keys(self):
        evidence = json.loads((ROOT / 'work/text-padding-island-review.json').read_text('utf8'))
        if evidence['source_xbe_sha256'] != ORIGINAL_XBE_SHA256:
            raise ValueError('INT3 island evidence source mismatch')
        used = {r['guestVA'] for r in self.baseM['mapChanges']}
        # Match the original scattered builder's intentionally conservative
        # all-byte absolute/relative target scan, in addition to the review.
        referenced = self._referenced_guest_targets()
        keys, retained, excluded, target_excluded = [], [], [], []
        for cave in evidence['eligible_islands']:
            start = cave['va']
            if cave['bytes'] != 15 or cave['end_exclusive'] != start + 15:
                raise ValueError('Unexpected independently reviewed island size')
            off = self._xbe_offset(start)
            if off != cave['file_offset'] or self.xbe[off:off + 15] != b'\xcc' * 15:
                raise ValueError(f'INT3 island preimage mismatch {start:#x}')
            if cave['preimage_hex'] != 'cc' * 15:
                raise ValueError('INT3 evidence preimage mismatch')
            reference_index = bisect.bisect_left(referenced, start)
            has_raw_target = reference_index < len(referenced) and referenced[reference_index] < start + 15
            if has_raw_target:
                target_excluded.append(start)
            if any(start <= key < start + 15 for key in used):
                excluded.append(start)
                continue
            if has_raw_target:
                continue
            for key in range(start, start + 15):
                _, original = self._record(key, original=True)
                _, current = self._record(key)
                if current != original:
                    raise ValueError('Unused island contains a modified map entry')
                keys.append(key)
            retained.append(start)
        if len(keys) != len(set(keys)):
            raise ValueError('Overlapping independent INT3 island evidence')
        self.key_evidence = {'eligible_islands': len(evidence['eligible_islands']),
                             'excluded_whole_islands': len(excluded),
                             'conservative_target_excluded_islands': len(target_excluded),
                             'combined_eligible_islands_before_v2_exclusion': len(evidence['eligible_islands']) - len(target_excluded),
                             'retained_islands': len(retained),
                             'available_keys': len(keys),
                             'source_xbe_sha256': ORIGINAL_XBE_SHA256,
                             'retained_island_starts': retained}
        return keys

    def _referenced_guest_targets(self):
        image_base = struct.unpack_from('<I', self.xbe, 0x104)[0]
        count, section_va = struct.unpack_from('<II', self.xbe, 0x11c)
        text = None
        for index in range(count):
            at = section_va - image_base + index * 0x38
            _, va, _, raw, size, name_va = struct.unpack_from('<6I', self.xbe, at)
            name_at = name_va - image_base
            name = self.xbe[name_at:self.xbe.index(0, name_at)]
            if name == b'.text':
                text = (va, raw, size)
                break
        if text is None:
            raise ValueError('Original XBE has no .text section')
        lo, raw_offset, size = text
        hi = lo + size
        referenced = set()
        for off in range(len(self.xbe) - 3):
            value = struct.unpack_from('<I', self.xbe, off)[0]
            if lo <= value < hi:
                referenced.add(value)
        raw = self.xbe[raw_offset:raw_offset + size]
        for off, byte in enumerate(raw):
            target = None
            va = lo + off
            if byte in (0xe8, 0xe9) and off + 5 <= len(raw):
                target = va + 5 + struct.unpack_from('<i', raw, off + 1)[0]
            elif byte == 0x0f and off + 6 <= len(raw) and 0x80 <= raw[off + 1] <= 0x8f:
                target = va + 6 + struct.unpack_from('<i', raw, off + 2)[0]
            elif (byte == 0xeb or 0x70 <= byte <= 0x7f or 0xe0 <= byte <= 0xe3) and off + 2 <= len(raw):
                target = va + 2 + struct.unpack_from('<b', raw, off + 1)[0]
            if target is not None and lo <= target < hi:
                referenced.add(target)
        return sorted(referenced)

    def _reserve_key(self):
        if self._key_cursor == len(self._keys):
            raise ValueError('No unused reviewed guest dispatch keys remain')
        key = self._keys[self._key_cursor]
        self._key_cursor += 1
        return key

    def _check_new_name(self, name):
        if self._laid_out:
            raise ValueError('Cannot add programs/services after layout')
        if not isinstance(name, str) or not name or name in self.programs or name in self.services:
            raise ValueError(f'Duplicate or invalid entry name {name!r}')

    def add_service(self, name):
        self._check_new_name(name)
        key = self._reserve_key()
        self.services[name] = {'name': name, 'guestVA': key}
        return key

    def add_guest(self, name, asm, logicalVA):
        self._check_new_name(name)
        logicalVA = int(logicalVA)
        source = _clean_asm(asm)
        encoded, _ = self._ks32.asm(source, addr=logicalVA)
        code = bytes(encoded or [])
        instructions = list(self._cs32.disasm(code, logicalVA))
        if not instructions or sum(i.size for i in instructions) != len(code):
            raise ValueError(f'Incomplete logical x86 decoding: {name}')
        end = logicalVA + len(code)
        for old in self.programs.values():
            if logicalVA < old.logicalVA + len(old.code) and old.logicalVA < end:
                raise ValueError('Overlapping logical guest program ranges')
        if self._key_cursor + len(instructions) > len(self._keys):
            raise ValueError('Insufficient reviewed keys for flat guest program')
        keys = {i.address: self._reserve_key() for i in instructions}
        program = GuestProgram(name, asm, logicalVA, code, instructions, keys, {})
        self.programs[name] = program
        self._logical.update({i.address: (program, i) for i in instructions})
        return program

    def layout(self):
        if self._laid_out:
            return self
        last = self.pe.sections[-1]
        self.section_rva = _align(last.VirtualAddress + max(last.Misc_VirtualSize, last.SizeOfRawData),
                                  self.pe.OPTIONAL_HEADER.SectionAlignment)
        self.section_raw = _align(len(self.base_bytes), self.pe.OPTIONAL_HEADER.FileAlignment)
        cursor = self.section_rva
        for program in self.programs.values():
            for instruction in program.instructions:
                program.host_rvas[instruction.address] = cursor
                cursor += self.instruction_slot_bytes
        cursor = _align(cursor, 16)
        for service in self.services.values():
            service['hostRVA'] = cursor
            cursor += self.service_slot_bytes
        self._virtual_hosts = {program.guest_keys[logical]: rva
                               for program in self.programs.values()
                               for logical, rva in program.host_rvas.items()}
        self._virtual_hosts.update({service['guestVA']: service['hostRVA'] for service in self.services.values()})
        self.data_rva = _align(cursor, 16)
        self._laid_out = True
        return self

    def guest_entry(self, name):
        return self.programs[name].guestVA if name in self.programs else self.services[name]['guestVA']

    def host_entry(self, name):
        if not self._laid_out:
            raise ValueError('Call layout before requesting host entries')
        return self.programs[name].hostRVA if name in self.programs else self.service_rva(name)

    def service_rva(self, name):
        if not self._laid_out:
            raise ValueError('Call layout before requesting service RVAs')
        return self.services[name]['hostRVA']

    def set_data(self, data):
        if self._compiled:
            raise ValueError('Cannot change data after compile')
        self._data = bytes(data)

    @staticmethod
    def _symbol_expression(expression, symbols):
        def visit(node):
            if isinstance(node, ast.Constant) and type(node.value) is int:
                return node.value
            if isinstance(node, ast.Name) and node.id in symbols:
                return int(symbols[node.id])
            if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
                return visit(node.left) + (1 if isinstance(node.op, ast.Add) else -1) * visit(node.right)
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                return (1 if isinstance(node.op, ast.UAdd) else -1) * visit(node.operand)
            raise ValueError(f'Unsupported RIP symbol expression: {expression}')
        return visit(ast.parse(expression.strip(), mode='eval').body)

    def assemble64(self, asm, rva, symbolRvas=None):
        """Assemble labels and fix [rip + SYMBOL +/- constant] to symbol RVAs."""
        if isinstance(asm, (list, tuple)):
            asm = '\n'.join(asm)
        asm = _clean_asm(asm)
        symbols = {'DISPATCH': self.dispatch_ptr_rva}
        symbols.update(symbolRvas or {})
        fixups = {}
        def replace(match):
            expression = match.group(1).strip()
            # Numeric RIP expressions are already literal displacements.
            names = re.findall(r'\b[A-Za-z_]\w*\b', re.sub(r'0x[0-9a-fA-F]+', '', expression))
            if not names:
                return match.group(0)
            target = self._symbol_expression(expression.lstrip('+').strip(), symbols)
            sentinel = 0x5e000000 + len(fixups)
            fixups[sentinel] = target
            return f'[rip + {sentinel:#x}]'
        adjusted = re.sub(r'\[\s*rip\s*([^\]]*)\]', replace, asm, flags=re.I)
        encoding, _ = self._ks64.asm(adjusted, addr=self.image_base + int(rva))
        code = bytearray(encoding or [])
        decoded = list(self._cs64.disasm(bytes(code), self.image_base + int(rva)))
        if sum(i.size for i in decoded) != len(code):
            raise ValueError('Incomplete assembled x64 decoding')
        applied = set()
        for instruction in decoded:
            for operand in instruction.operands:
                if operand.type != X86_OP_MEM or self._cs64.reg_name(operand.mem.base) != 'rip':
                    continue
                if operand.mem.disp not in fixups:
                    continue
                sentinel = operand.mem.disp
                if sentinel in applied or instruction.disp_size != 4:
                    raise ValueError('Unexpected RIP fixup encoding')
                offset = instruction.address - self.image_base - int(rva)
                displacement = fixups[sentinel] - (int(rva) + offset + instruction.size)
                if not -(1 << 31) <= displacement < (1 << 31):
                    raise ValueError('RIP symbol is outside signed32 reach')
                struct.pack_into('<i', code, offset + instruction.disp_offset, displacement)
                applied.add(sentinel)
        if applied != set(fixups):
            raise ValueError('Unresolved RIP symbol fixup')
        return bytes(code)

    def _operand(self, op):
        if op.type == X86_OP_REG:
            name = self._cs32.reg_name(op.reg)
            return 'r14d' if name == 'esp' else name
        if op.type == X86_OP_IMM:
            return hex(op.imm & 0xffffffff)
        if op.type == X86_OP_MEM:
            return self._memory(op)
        raise ValueError('Unsupported guest operand')

    def _memory(self, op):
        memory = op.mem
        if memory.segment or memory.index:
            raise ValueError('Guest memory requires unsegmented single-base addressing')
        name = self._cs32.reg_name(memory.base)
        if name and name not in GPR64:
            raise ValueError('Unsupported guest memory base')
        address = 'r15' + (' + ' + GPR64[name] if name else '')
        displacement = memory.disp
        if not name and displacement < 0:
            displacement &= 0xffffffff
        if not -(1 << 31) <= displacement < (1 << 31):
            raise ValueError('Guest absolute address needs an unsupported address scratch')
        if displacement:
            address += (' + ' if displacement >= 0 else ' - ') + hex(abs(displacement))
        return {1: 'byte', 2: 'word', 4: 'dword', 8: 'qword', 16: 'xmmword'}[op.size] + ' ptr [' + address + ']'

    @staticmethod
    def _gpush(value):
        return ['lea r14d, [r14 - 4]', 'mov dword ptr [r14 + r15], ' + value]

    def _gret(self, immediate=0):
        return ['mov r8d, dword ptr [r14 + r15]',
                f'lea r14d, [r14 + {4 + immediate}]',
                'mov r9, qword ptr [rip + DISPATCH]', 'jmp qword ptr [r9 + r8*8]']

    def _target(self, logical_or_guest):
        if logical_or_guest in self._logical:
            program, _ = self._logical[logical_or_guest]
            return program.host_rvas[logical_or_guest]
        if logical_or_guest in self._virtual_hosts:
            return self._virtual_hosts[logical_or_guest]
        # Landing inside a generated logical instruction is always an error.
        if any(p.logicalVA <= logical_or_guest < p.logicalVA + len(p.code) for p in self.programs.values()):
            raise ValueError('Guest branch target splits a logical instruction')
        return self.original_host(logical_or_guest)

    def _lift(self, program, instruction):
        ins = instruction
        m = ins.mnemonic
        next_logical = ins.address + ins.size
        if m == 'push':
            op = ins.operands[0]
            if op.size != 4:
                raise ValueError('Only32bit guest PUSH is supported')
            if op.type == X86_OP_REG and self._cs32.reg_name(op.reg) == 'esp':
                return ['mov r8d, r14d'] + self._gpush('r8d')
            if op.type == X86_OP_MEM:
                return ['mov r8d, ' + self._memory(op)] + self._gpush('r8d')
            return self._gpush(self._operand(op))
        if m == 'pop':
            op = ins.operands[0]
            if op.size != 4:
                raise ValueError('Only32bit guest POP is supported')
            if op.type == X86_OP_MEM or (op.type == X86_OP_REG and self._cs32.reg_name(op.reg) == 'esp'):
                return ['mov r8d, dword ptr [r14 + r15]', 'lea r14d, [r14 + 4]',
                        'mov ' + self._operand(op) + ', r8d']
            return ['mov ' + self._operand(op) + ', dword ptr [r14 + r15]', 'lea r14d, [r14 + 4]']
        if m == 'pushal':
            return ['lea r14d, [r14 - 32]'] + [
                f'mov dword ptr [r14 + r15 + {off}], {reg}' for off, reg in
                [(28, 'eax'), (24, 'ecx'), (20, 'edx'), (16, 'ebx'), (8, 'ebp'), (4, 'esi'), (0, 'edi')]
            ] + ['lea r8d, [r14 + 32]', 'mov dword ptr [r14 + r15 + 12], r8d']
        if m == 'popal':
            return [f'mov {reg}, dword ptr [r14 + r15 + {off}]' for off, reg in
                    [(0, 'edi'), (4, 'esi'), (8, 'ebp'), (16, 'ebx'), (20, 'edx'), (24, 'ecx'), (28, 'eax')]
                    ] + ['lea r14d, [r14 + 32]']
        if m == 'ret':
            return self._gret(ins.operands[0].imm if ins.operands else 0)
        if ins.group(CS_GRP_CALL):
            if next_logical not in program.guest_keys:
                raise ValueError('Guest CALL has no next logical instruction return key')
            return_key = program.guest_keys[next_logical]
            op = ins.operands[0]
            if op.type == X86_OP_IMM:
                return self._gpush(hex(return_key)) + [f'jmp {self.image_base + self._target(op.imm):#x}']
            if (op.type == X86_OP_MEM and not op.mem.base and not op.mem.index and
                    not op.mem.segment and op.size == 4 and op.mem.disp in (0x28e484, 0x28e488)):
                return ['mov r8d, ' + self._memory(op)] + self._gpush(hex(return_key)) + [
                    'mov r9, qword ptr [rip + DISPATCH]', 'jmp qword ptr [r9 + r8*8]']
            raise ValueError('Indirect guest CALL is restricted to absolute critical-section IAT28e484/28e488')
        if ins.group(CS_GRP_JUMP):
            if m not in {'jmp', 'ja', 'jae', 'jb', 'jbe', 'je', 'jg', 'jge', 'jl', 'jle',
                          'jne', 'jno', 'jnp', 'jns', 'jo', 'jp', 'js'}:
                raise ValueError('Guest branch needs an explicit counter/address-size contract: ' + m)
            if ins.operands[0].type != X86_OP_IMM:
                raise ValueError('Indirect guest JMP is unsupported')
            return [f'{m} {self.image_base + self._target(ins.operands[0].imm):#x}']
        if m == 'lea':
            op = ins.operands[1]
            if op.mem.segment or op.mem.index:
                raise ValueError('Guest LEA requires unsegmented single-base addressing')
            name = self._cs32.reg_name(op.mem.base)
            if not name:
                return ['mov ' + self._operand(ins.operands[0]) + ', ' + hex(op.mem.disp & 0xffffffff)]
            if name not in GPR64:
                raise ValueError('Unsupported guest LEA base')
            disp = op.mem.disp
            address = GPR64[name] + ((' + ' if disp >= 0 else ' - ') + hex(abs(disp)) if disp else '')
            return ['lea ' + self._operand(ins.operands[0]) + ', [' + address + ']']
        allowed = {'mov', 'cmp', 'test', 'neg', 'sbb', 'inc', 'add', 'sub', 'xor',
                   'or', 'and', 'movzx', 'nop', 'movss', 'subss', 'addss', 'comiss'}
        if m not in allowed:
            raise ValueError(f'Unsupported guest opcode {m} at{ins.address:#x}')
        return [m + (' ' + ', '.join(self._operand(op) for op in ins.operands) if ins.operands else '')]

    def compile(self, service_builders):
        self.layout()
        if self._compiled:
            raise ValueError('Compiler instance is already compiled')
        if set(service_builders) != set(self.services):
            raise ValueError('Service builder names do not exactly match registered services')
        self._payload = bytearray(b'\xcc' * (self.data_rva - self.section_rva) + self._data)
        for program in self.programs.values():
            for ins in program.instructions:
                lines = self._lift(program, ins)
                if ins.mnemonic not in ('jmp', 'ret'):
                    next_logical = ins.address + ins.size
                    if next_logical not in program.host_rvas:
                        raise ValueError('Unterminated flat logical guest program')
                    lines.append(f'jmp {self.image_base + program.host_rvas[next_logical]:#x}')
                rva = program.host_rvas[ins.address]
                code = self.assemble64(lines, rva)
                if len(code) > self.instruction_slot_bytes:
                    raise ValueError('Lifted instruction exceeds native slot')
                at = rva - self.section_rva
                self._payload[at:at + len(code)] = code
                self.generated.append({'name': program.name, 'logicalVA': ins.address,
                                       'guestVA': program.guest_keys[ins.address], 'hostRVA': rva,
                                       'source': ins.mnemonic + (' ' + ins.op_str if ins.op_str else ''),
                                       'sourceHex': ins.bytes.hex(), 'hex': code.hex(), 'assembly': lines})
        for name, service in self.services.items():
            code = bytes(service_builders[name](self, service['hostRVA']))
            if not code or len(code) > self.service_slot_bytes:
                raise ValueError('Empty/oversize native service: ' + name)
            decoded = list(self._cs64.disasm(code, self.image_base + service['hostRVA']))
            if sum(ins.size for ins in decoded) != len(code):
                raise ValueError('Incomplete native service disassembly: ' + name)
            at = service['hostRVA'] - self.section_rva
            self._payload[at:at + len(code)] = code
            self.service_records.append({**service, 'bytes': len(code), 'reservedBytes': self.service_slot_bytes, 'hex': code.hex()})
        self._compiled = True
        return self

    def add_hook(self, guestVA, originalGuestSpan, programName, expectedCurrentNativeHexOptional=None):
        self.layout()
        guestVA = int(guestVA)
        if isinstance(originalGuestSpan, int):
            length = originalGuestSpan
            off = self._xbe_offset(guestVA)
            guest = self.xbe[off:off + length]
        else:
            guest = bytes.fromhex(originalGuestSpan) if isinstance(originalGuestSpan, str) else bytes(originalGuestSpan)
            length = len(guest)
            off = self._xbe_offset(guestVA)
            if self.xbe[off:off + length] != guest:
                raise ValueError('Original guest hook preimage mismatch')
        guest_instructions = list(self._cs32.disasm(guest, guestVA))
        if length <= 0 or sum(ins.size for ins in guest_instructions) != length:
            raise ValueError('Guest hook span splits an instruction')
        start, end = self.original_host(guestVA), self.original_host(guestVA + length)
        span = end - start
        if not 5 <= span <= 256:
            raise ValueError('Invalid/noncontiguous native hook span')
        file_off = self.pe.get_offset_from_rva(start)
        old = self.base_bytes[file_off:file_off + span]
        decoded = list(self._cs64.disasm(old, self.image_base + start))
        if sum(ins.size for ins in decoded) != span:
            raise ValueError('Native hook span splits an instruction')
        expected = expectedCurrentNativeHexOptional
        if expected is not None:
            expected = bytes.fromhex(expected) if isinstance(expected, str) else bytes(expected)
            if old != expected:
                raise ValueError('Current native hook preimage mismatch')
        previous = next((h for h in self.baseM['hooks'] if h['guestVA'] == guestVA), None)
        if previous and (old.hex() != previous['after'] or span != len(bytes.fromhex(previous['after']))):
            raise ValueError('Replacement hook does not match entire base-v2 hook')
        for base_hook in self.baseM['hooks']:
            base_begin = base_hook['fileOffset']
            base_end = base_begin + len(bytes.fromhex(base_hook['after']))
            if max(file_off, base_begin) < min(file_off + span, base_end) and base_hook is not previous:
                raise ValueError('New hook partially overlaps a different base-v2 hook')
        if any(max(file_off, h['fileOffset']) < min(file_off + span, h['fileOffset'] + len(bytes.fromhex(h['after']))) for h in self._hooks):
            raise ValueError('New native hooks overlap')
        target = self.host_entry(programName)
        delta = target - (start + 5)
        new = b'\xe9' + struct.pack('<i', delta) + b'\x90' * (span - 5)
        record = {'guestVA': guestVA, 'guestOriginalHex': guest.hex(), 'guestSpanBytes': length,
                  'hostRVA': start, 'fileOffset': file_off, 'before': old.hex(), 'after': new.hex(),
                  'payloadRVA': target, 'program': programName,
                  'purpose': 'Native automatic-caption ' + programName}
        if previous:
            record['previousV2Hook'] = previous
        self._hooks.append(record)
        return record

    def finish(self, outFolder):
        if not self._compiled:
            raise ValueError('Call compile before finish')
        out = Path(outFolder).resolve()
        if not out.is_relative_to(ROOT.resolve()) or out in (self.base_path.parent.resolve(), (ROOT / 'native-host-v1').resolve()):
            raise ValueError('Output must be a separate workspace folder')
        patched = bytearray(self.base_bytes)
        allowed = []
        new_map = []
        for entry in self.generated + self.service_records:
            va, rva = entry['guestVA'], entry['hostRVA']
            file_off, before = self._record(va)
            struct.pack_into('<I', patched, file_off, rva)
            allowed.append((file_off, file_off + 4))
            new_map.append({'guestVA': va, 'fileOffset': file_off, 'beforeRVA': before, 'afterRVA': rva})
        if len({r['guestVA'] for r in new_map}) != len(new_map):
            raise ValueError('Duplicate new dispatch map keys')
        for hook in self._hooks:
            off, code = hook['fileOffset'], bytes.fromhex(hook['after'])
            patched[off:off + len(code)] = code
            allowed.append((off, off + len(code)))
        section_header = self.pe.sections[-1].get_file_offset() + 40
        if section_header + 40 > self.pe.OPTIONAL_HEADER.SizeOfHeaders or any(patched[section_header:section_header + 40]):
            raise ValueError('No empty PE section header room')
        raw_size = _align(len(self._payload), self.pe.OPTIONAL_HEADER.FileAlignment)
        if not raw_size:
            raise ValueError('No native payload')
        patched.extend(b'\0' * (self.section_raw - len(patched)))
        patched.extend(self._payload)
        patched.extend(b'\0' * (raw_size - len(self._payload)))
        patched[section_header:section_header + 40] = struct.pack(
            '<8s6I2HI', b'.autocap', len(self._payload), self.section_rva, raw_size,
            self.section_raw, 0, 0, 0, 0, 0x60000020)
        allowed.append((section_header, section_header + 40))
        for field, size, value in [
            ('NumberOfSections', 2, len(self.pe.sections) + 1),
            ('SizeOfImage', 4, _align(self.section_rva + len(self._payload), self.pe.OPTIONAL_HEADER.SectionAlignment)),
            ('SizeOfCode', 4, self.pe.OPTIONAL_HEADER.SizeOfCode + raw_size),
            ('CheckSum', 4, 0)
        ]:
            structure = self.pe.FILE_HEADER if field == 'NumberOfSections' else self.pe.OPTIONAL_HEADER
            off = structure.get_field_absolute_offset(field)
            struct.pack_into('<H' if size == 2 else '<I', patched, off, value)
            allowed.append((off, off + size))
        checksum_off = self.pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum')
        final_pe = pefile.PE(data=bytes(patched))
        struct.pack_into('<I', patched, checksum_off, final_pe.generate_checksum())
        allowed.sort()
        cursor = 0
        for start, end in allowed:
            if start > cursor and patched[cursor:start] != self.base_bytes[cursor:start]:
                raise ValueError(f'Unexpected immutable-base modification before{start:#x}')
            cursor = max(cursor, end)
        if patched[cursor:len(self.base_bytes)] != self.base_bytes[cursor:]:
            raise ValueError('Unexpected immutable-base tail modification')
        merged_hooks = [h for h in self.baseM['hooks'] if h['guestVA'] not in {h['guestVA'] for h in self._hooks}] + self._hooks
        output = out / DLL_NAME
        manifest = {
            'format': 3, 'status': 'Offline automatic-caption candidate; not installed or runtime verified',
            'source': self.baseM['source'], 'sourceSha256': BASE_SHA256,
            'immutableBase': str(self.base_path), 'originalHostSha256': ORIGINAL_HOST_SHA256,
            'compilerSourceSha256': _sha(Path(__file__).read_bytes()),
            'originalGuestXbeSha256': ORIGINAL_XBE_SHA256,
            'patchedSha256': _sha(patched), 'output': str(output),
            'originalBytes': len(self.base_bytes), 'patchedBytes': len(patched),
            'originalGuestXbeUnchanged': True, 'assetsUnchanged': True,
            'guestVtableWrite': False, 'dispatchPointerRVA': self.dispatch_ptr_rva,
            'section': {'name': '.autocap', 'rva': self.section_rva, 'raw': self.section_raw,
                        'virtualBytes': len(self._payload), 'rawBytes': raw_size, 'characteristics': '0x60000020'},
            'data': {'rva': self.data_rva, 'bytes': len(self._data), 'sha256': _sha(self._data)},
            'entries': {name: {'guestVA': self.guest_entry(name), 'hostRVA': self.host_entry(name)}
                        for name in list(self.programs) + list(self.services)},
            'mapChanges': self.baseM['mapChanges'] + new_map, 'newMapChanges': new_map,
            'hooks': merged_hooks, 'newHooks': self._hooks,
            'generated': self.generated, 'services': self.service_records,
            'keyAllocation': {**self.key_evidence, 'reserved_keys': self._key_cursor},
            'verification': {'immutableBaseHashMatched': True, 'guestKeyPreimagesAll15CC': True,
                             'wholeV2UsedIslandsExcluded': True, 'newKeysUnique': True,
                             'conservativeRawAbsoluteAndRelativeTargetsExcluded': True,
                             'modifiedBaseBytesWithinExplicitAllowlist': True,
                             'installedWrites': False},
            'limitations': ['Lifted x86 contracts and host services require the parent offline harness and runtime review.',
                            'Only the two audited critical-section absolute guest IAT calls are supported indirectly.']
        }
        out.mkdir(parents=True, exist_ok=True)
        output.write_bytes(patched)
        (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf8')
        return manifest
