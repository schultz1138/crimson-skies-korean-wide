; ECX=liveDialogue during the parent's init/destroy wrapper.
; PlainRET; preserves nonvolatiles; outerPUSHAL/POPAL preserves all callerGPRs.
; Clear Dialogue+0x78 first. Free only a bounded pointer with our exact magic.

auto_free_state:
    push esi
    mov esi, ecx
    lea eax, [esi-0x10000]
    cmp eax, 0x7ffeff00
    jae free_state_done
    mov eax, dword ptr [esi+0x78]
    mov dword ptr [esi+0x78], 0
    lea ecx, [eax-0x10000]
    cmp ecx, 0x7ffeff00
    jae free_state_done
    cmp dword ptr [eax], 0x43534155
    jne free_state_done
    mov dword ptr [eax], 0
    push eax
    call 0x1318a0
    add esp, 4
free_state_done:
    pop esi
    ret
