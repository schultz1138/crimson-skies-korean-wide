; Flat logical x86 function. Parent replaces service symbols before assembly.
; ECX=currently live Dialogue*, main/HUD thread only. No arguments, plainRET.
; Preserves EBX/ESI/EDI/EBP and ESP; EAX/ECX/EDX,XMM0-2 are volatile.
; QUERY_SERVICE: ECX=D -> EAX=playingA/0, EDX=actualASCIIfilename.
; LOOKUP_SERVICE: ECX=filename -> EAX=dictIndex/0xffffffff.
; PART_SERVICE: ECX=index,XMM0=elapsed,push512byteoutput;
;   EAX=partIndex/0xffffffff,EDX=remainingdisplayfloatbits incl0.25fade;
;   cdecl: parent caller removes the one4byteoutputargument.
; RADIO_DISPATCH: ECX=HUD,pushchannel2,pushUTF16text;calleeRET8.
; Text buffer [EBP-0x214,EBP-0x15] is exactly512bytes.
; Locals: [EBP-0x10] filename/partIndex,[EBP-0x14] lookupIndex.

auto_core:
    push ebp
    mov ebp, esp
    push ebx
    push esi
    push edi
    sub esp, 0x208
    mov esi, ecx
    call QUERY_SERVICE
    test eax, eax
    je core_done
    mov ebx, eax
    mov dword ptr [ebp-0x10], edx

    mov edi, dword ptr [esi+0x78]
    lea eax, [edi-0x10000]
    cmp eax, 0x7ffeff00
    jae core_no_state
    cmp dword ptr [edi], 0x43534155
    jne core_no_state
    cmp dword ptr [edi+8], ebx
    jne core_lookup
    cmp dword ptr [edi+4], 0
    je core_lookup
    cmp dword ptr [edi+12], 0xffffffff
    je core_done
    jmp core_part

core_no_state:
    xor edi, edi
core_lookup:
    mov ecx, dword ptr [ebp-0x10]
    call LOOKUP_SERVICE
    mov dword ptr [ebp-0x14], eax
    cmp eax, 0xffffffff
    jne core_matched
    test edi, edi
    je core_done
    ; Existing owned state can cache a nonmatch. Never allocate for a nonmatch.
    mov dword ptr [edi+4], 1
    mov dword ptr [edi+8], ebx
    mov dword ptr [edi+12], 0xffffffff
    mov dword ptr [edi+16], 0
    mov dword ptr [edi+20], 0xffffffff
    mov dword ptr [edi+24], 0
    mov dword ptr [edi+28], 0
    jmp core_done

core_matched:
    test edi, edi
    jne core_initialize_state
    push 32
    call 0x131880
    add esp, 4
    test eax, eax
    je core_done
    mov edi, eax
core_initialize_state:
    mov dword ptr [edi], 0x43534155
    mov dword ptr [edi+4], 1
    mov dword ptr [edi+8], ebx
    mov eax, dword ptr [ebp-0x14]
    mov dword ptr [edi+12], eax
    movss xmm0, dword ptr [0x3219c0]
    movss dword ptr [edi+16], xmm0
    mov dword ptr [edi+20], 0xffffffff
    mov dword ptr [edi+24], 1
    mov dword ptr [edi+28], 0
    mov dword ptr [esi+0x78], edi

core_part:
    mov ecx, dword ptr [edi+12]
    movss xmm0, dword ptr [0x3219c0]
    subss xmm0, dword ptr [edi+16]
    lea eax, [ebp-0x214]
    push eax
    call PART_SERVICE
    add esp, 4
    cmp eax, 0xffffffff
    je core_expired
    mov dword ptr [edi+28], edx
    cmp eax, dword ptr [edi+20]
    je core_done
    mov dword ptr [ebp-0x10], eax

    mov ecx, dword ptr [esi+0x54]
    lea eax, [ecx-0x10000]
    cmp eax, 0x7ffef000
    jae core_done
    cmp dword ptr [ecx+0x9a4], esi
    jne core_done
    push 2
    lea eax, [ebp-0x214]
    push eax
    call RADIO_DISPATCH

    ; The dispatcher has no success return. Commit only if its owned native
    ; MsgUI and FontRef exist; leave presentedPart unchanged to retry otherwise.
    mov ecx, dword ptr [esi+0x74]
    lea eax, [ecx-0x10000]
    cmp eax, 0x7ffeff00
    jae core_done
    cmp dword ptr [ecx], 0x2c270c
    jne core_done
    mov eax, dword ptr [ecx+0x74]
    sub eax, 0x10000
    cmp eax, 0x7ffeff00
    jae core_done
    mov eax, dword ptr [ebp-0x10]
    mov dword ptr [edi+20], eax
    mov dword ptr [edi+24], 1
    movss xmm0, dword ptr [0x3219c0]
    addss xmm0, dword ptr [edi+28]
    movss dword ptr [ecx+0x9c], xmm0
    ; Deliberately do not change Radio+0x98 DisplayTime (manualT42 stays5sec).
    jmp core_done

core_expired:
    mov dword ptr [edi+24], 0
core_done:
    add esp, 0x208
    pop edi
    pop esi
    pop ebx
    pop ebp
    ret
