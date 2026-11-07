; ECX=liveDialogue before originalDD9E0 can stop/free/advance its audio.
; PlainRET; preserves EBX/ESI/EDI/EBP. EAX/ECX/EDX may change.
; Reset the owned state before calling the native fade setter or original code.

auto_end:
    push ebx
    push esi
    push edi
    mov esi, ecx
    lea eax, [esi-0x10000]
    cmp eax, 0x7ffeff00
    jae end_done
    mov ebx, dword ptr [esi+0x78]
    lea eax, [ebx-0x10000]
    cmp eax, 0x7ffeff00
    jae end_done
    cmp dword ptr [ebx], 0x43534155
    jne end_done
    mov edi, dword ptr [ebx+24]
    mov dword ptr [ebx+4], 0
    mov dword ptr [ebx+8], 0
    mov dword ptr [ebx+12], 0xffffffff
    mov dword ptr [ebx+16], 0
    mov dword ptr [ebx+20], 0xffffffff
    mov dword ptr [ebx+24], 0
    mov dword ptr [ebx+28], 0
    cmp edi, 1
    jne end_done
    mov ecx, dword ptr [esi+0x74]
    lea eax, [ecx-0x10000]
    cmp eax, 0x7ffeff00
    jae end_done
    cmp dword ptr [ecx], 0x2c270c
    jne end_done
    push 0x28e928
    call 0xffc50
end_done:
    pop edi
    pop esi
    pop ebx
    ret
