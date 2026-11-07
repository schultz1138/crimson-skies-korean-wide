"""Header-preserving native renderer using verified INT3 alignment padding.

Every generated instruction is followed by a jump to its next instruction.
Internal branch destinations are relocated to the corresponding padding slot.
No existing function or diagnostic command is removed.
"""
from pathlib import Path
import hashlib,json,re,struct,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pythonlibs'))
import xbe_tools as X
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_GRP_CALL,CS_GRP_JUMP
from capstone.x86 import X86_OP_IMM
source=X.data
if hashlib.sha256(source).hexdigest()!='43048e59b75065e82c032859ac700c75cc2bd124f6ae817a7a2d2ca3e252aad2':raise ValueError('Unexpected XBE')
patched=bytearray(source)
K=Ks(KS_ARCH_X86,KS_MODE_32);C=Cs(CS_ARCH_X86,CS_MODE_32);C.detail=True
text=next(s for s in X.sections if s['name']=='.text')
lo,hi=text['va'],text['va']+text['size']
referenced=set()
for off in range(len(source)-3):
    target=struct.unpack_from('<I',source,off)[0]
    if lo<=target<hi:referenced.add(target)
raw=source[text['raw']:text['raw']+text['size']]
for off,byte in enumerate(raw):
    target=None;va=lo+off
    if byte in (0xe8,0xe9) and off+5<=len(raw):target=va+5+struct.unpack_from('<i',raw,off+1)[0]
    elif byte==0x0f and off+6<=len(raw) and 0x80<=raw[off+1]<=0x8f:target=va+6+struct.unpack_from('<i',raw,off+2)[0]
    elif (byte==0xeb or 0x70<=byte<=0x7f or 0xe0<=byte<=0xe3) and off+2<=len(raw):target=va+2+struct.unpack_from('<b',raw,off+1)[0]
    if target is not None and lo<=target<hi:referenced.add(target)
independent=json.loads((ROOT/'work/text-padding-island-review.json').read_text('utf-8'))
if independent['source_xbe_sha256']!=hashlib.sha256(source).hexdigest():raise ValueError('Padding review source mismatch')
independent_safe={item['va'] for item in independent['eligible_islands']}
caves=[]
for run in re.finditer(b'\xcc{15,}',raw):
    for start in range(run.start(),run.end()-14,15):
        va=lo+start
        if va not in independent_safe:continue
        if any(va<=target<va+15 for target in referenced):continue
        caves.append(dict(va=va,raw=text['raw']+start,length=15))
name_off=source.index(b'MsgUIStatus\0');NAME=X.file_to_va(name_off)
logical=0x400000
addresses={name:logical+offset for name,offset in [('channel',0),('dispatch',0x100),('draw',0x300),('destroy',0x400),('initialize',0x500)]}
channel=(ROOT/'work/radio-channel.asm').read_text('utf8')
runtime='--runtime' in sys.argv
if runtime:
    channel=channel.replace('jz tutorial','''jz tutorial
    cmp dword ptr [esp+0x14], 0x535f524b
    jne test_channel_name
    cmp dword ptr [esp+0x18], 0x55545f48
    jne test_channel_name
    cmp word ptr [esp+0x1c], 0x5f54
    jne test_channel_name
    mov edi, 2
    jmp done
test_channel_name:''',1)
templates={
'channel':channel,
'dispatch':f'''
    cmp dword ptr [esp+8], 2
    je radio
    jmp 0x111b00
radio:
    push ebp
    mov ebp, esp
    push ebx
    push esi
    push edi
    sub esp, 0x40
    mov esi, ecx
    mov ebx, [esi+0x9a4]
    test ebx, ebx
    jz finish
    mov edi, [ebx+0x74]
    cmp edi, 0x10000
    jae ready
    call 0x1000d0
    test eax, eax
    jz finish
    mov edi, eax
    mov [ebx+0x74], edi
    push esi
    push 0
    lea eax, [esi+0x9a8]
    push eax
    push dword ptr [0x2eb95c]
    push {NAME}
    lea eax, [esp+0x14]
    push eax
    mov ecx, dword ptr [0x3219c8]
    call 0x3d1a0
    push eax
    mov ecx, edi
    call 0xff500
    lea ecx, [esp]
    call 0x4cb40
    mov byte ptr [edi+0x58], 1
    mov dword ptr [edi+0x5c], -28
    mov dword ptr [edi+0x60], 0
    mov dword ptr [edi+0x64], 2
    mov dword ptr [edi+0x68], 1
    mov dword ptr [edi+0x6c], 0xffffffff
    mov dword ptr [edi+0x94], 0x3e800000
    mov dword ptr [edi+0x98], 0x40a00000
ready:
    cmp dword ptr [edi+0x74], 0
    je finish
    push dword ptr [ebp+8]
    mov ecx, edi
    call 0xffc50
finish:
    add esp, 0x40
    pop edi
    pop esi
    pop ebx
    pop ebp
    ret 8
''',
'draw': '''
    mov ecx, [ecx+0x74]
    cmp ecx, 0x10000
    jb done
    push dword ptr [esp+4]
    call 0xff860
done:
    ret 4
''',
'destroy': '''
    push esi
    mov esi, ecx
    mov ecx, [esi+0x74]
    mov dword ptr [esi+0x74], 0
    cmp ecx, 0x10000
    jb original
    push 1
    call 0xffc30
original:
    mov ecx, esi
    call 0xdd4e0
    jmp 0xddbb8
''',
'initialize': '''
    pushal
    mov ecx, [ecx+0x74]
    cmp ecx, 0x10000
    jb original
    push 1
    call 0xffc30
original:
    popal
    mov dword ptr [ecx+0x74], 0
    sub esp, 0x3c
    push ebx
    mov ebx, [esp+0x48]
    jmp 0xdd5a8
'''}
blocks=[];instructions=[]
for name,assembly in templates.items():
    code=bytes(K.asm(assembly,addr=addresses[name])[0]);decoded=list(C.disasm(code,addresses[name]))
    if sum(i.size for i in decoded)!=len(code):raise ValueError('Incomplete logical decoding')
    blocks.append(dict(name=name,logicalVA=addresses[name],assembly=assembly,instructions=decoded))
    instructions.extend(decoded)
if len(caves)<len(instructions):raise ValueError(f'Not enough verified caves: {len(caves)} for {len(instructions)}')
mapping={ins.address:caves[i]['va'] for i,ins in enumerate(instructions)}
relocations=[]
for block in blocks:
    insns=block['instructions']
    for index,ins in enumerate(insns):
        va=mapping[ins.address];operand=ins.op_str
        branch=(ins.group(CS_GRP_CALL) or ins.group(CS_GRP_JUMP)) and ins.operands and ins.operands[0].type==X86_OP_IMM
        target=None
        if branch:
            target=ins.operands[0].imm
            if logical<=target<logical+0x600:
                if target not in mapping:raise ValueError('Branch to noninstruction')
                target=mapping[target]
            operand=hex(target)
        code=bytes(K.asm(ins.mnemonic+' '+operand,addr=va)[0])
        terminal=ins.mnemonic in ('ret','retf','jmp')
        if not terminal:
            if index+1>=len(insns):raise ValueError('Unterminated generated block')
            nxt=mapping[insns[index+1].address]
            code+=b'\xe9'+struct.pack('<i',nxt-(va+len(code))-5)
        if len(code)>15:raise ValueError('Relocated instruction exceeds its slot')
        off=X.va_to_file(va)
        if source[off:off+15]!=b'\xcc'*15:raise ValueError('Cave preimage changed')
        patched[off:off+len(code)]=code
        decoded=list(C.disasm(code,va))
        if sum(x.size for x in decoded)!=len(code):raise ValueError('Incomplete relocated instruction')
        if branch and decoded[0].operands[0].imm!=target:raise ValueError('Relocated branch target mismatch')
        if not terminal and decoded[-1].operands[0].imm!=nxt:raise ValueError('Relocated fallthrough mismatch')
        relocations.append(dict(block=block['name'],logicalVA=hex(ins.address),va=hex(va),fileOffset=off,sourceInstruction=ins.mnemonic+' '+ins.op_str,bytes=code.hex(),disassembly=[x.mnemonic+' '+x.op_str for x in decoded]))

hooks=[]
def hook(va,before,after,purpose):
    off=X.va_to_file(va)
    if source[off:off+len(before)]!=before or len(before)!=len(after):raise ValueError('Hook preimage mismatch')
    patched[off:off+len(after)]=after;hooks.append(dict(va=hex(va),fileOffset=off,before=before.hex(),after=after.hex(),purpose=purpose))
def jump(origin,target,length):return b'\xe9'+struct.pack('<i',target-origin-5)+b'\x90'*(length-5)
entry={name:mapping[va] for name,va in addresses.items()}
hook(0x26c8a,bytes.fromhex('8b463cf7df1bff47'),jump(0x26c8a,entry['channel'],8),'Recognize Radio channel')
hook(0x26ced,bytes.fromhex('e80eae0e00'),b'\xe8'+struct.pack('<i',entry['dispatch']-0x26ced-5),'Independent radio dispatch')
hook(0x29f998,struct.pack('<I',0x120460),struct.pack('<I',entry['draw']),'Independent lower radio drawing')
hook(0xddbb0,bytes.fromhex('568bf1e828f9ffff'),jump(0xddbb0,entry['destroy'],8),'Release owned radio on Dialogue deletion')
hook(0xdd5a0,bytes.fromhex('83ec3c538b5c2448'),jump(0xdd5a0,entry['initialize'],8),'Release owned radio before Dialogue reinitialization')
headers=X.u32(0x108)
if patched[:headers]!=source[:headers] or len(patched)!=len(source):raise ValueError('Header/allocation changed')
out=ROOT/('runtime-radio' if runtime else 'tutorial-v5');out.mkdir(exist_ok=True)
(out/'default.patched.xbe').write_bytes(patched)
report=dict(status='Offline build; header-preserving runtime trial pending',originalSha256=hashlib.sha256(source).hexdigest(),patchedSha256=hashlib.sha256(patched).hexdigest(),bytes=len(patched),originalHeaderPreserved=True,originalSectionTablePreserved=True,eligiblePaddingSlots=len(caves),usedPaddingSlots=len(instructions),paddingSafety='INT3 runs >=15 bytes in the original executable preloaded .text; slots targeted by any raw absolute pointer or conservative relative branch scan are excluded.',radioStorage='Dialogue+0x74, previously unused legacy SubtitlePos.x; low scalar values are rejected as pointers, cleanup occurs on deletion and reinitialization.',hooks=hooks,entries={k:hex(v) for k,v in entry.items()},relocations=relocations,signature='Original XBE header, RSA signature and declared section digests are byte-identical. Modified instruction bytes intentionally differ from their original section digest; runtime acceptance remains unverified.',limitations=['Padding scans are conservative static evidence, not proof against all computed control-flow targets.','Native boot, lower-caption placement and lifetime behavior need runtime verification.'])
(out/'native-renderer.json').write_text(json.dumps(report,indent=2),'utf-8')
if runtime:
    patches=[dict(guestVA=int(r['va'],16),before='cc'*(len(bytes.fromhex(r['bytes']))),after=r['bytes'],purpose=r['block']+' code padding') for r in relocations]
    patches.extend(dict(guestVA=int(r['va'],16),before=r['before'],after=r['after'],purpose=r['purpose']) for r in hooks)
    (out/'runtime-patches.json').write_text(json.dumps(dict(format=1,originalXbeSha256=report['originalSha256'],offlinePatchedSha256=report['patchedSha256'],captionPrefix='KR_SH_TUT_',patches=patches,applyOrder='All code islands first, then entry hooks; validate every preimage before any write',limitations=['Fresh game session before UserMsg/HUD code is JIT compiled is required unless cache invalidation is separately established.','Guest-memory target identity and every preimage must match before application.']),indent=2),'utf-8')
print(json.dumps({k:report[k] for k in ('status','patchedSha256','originalHeaderPreserved','eligiblePaddingSlots','usedPaddingSlots','signature')},indent=2))
