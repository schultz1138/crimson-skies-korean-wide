; Read-only logical x86 helper, assembly origin 0x600000.
; ECX = a currently live Dialogue* obtained by the main/HUD-thread caller.
; EAX = logical audio instance if its matching physical buffer is playing, else0.
; EDX = actual ASCII resource filename guest pointer if playing, else0.
; Preserves EBX/ESI/EDI/EBP and guest ESP; no parameters, plain RET.
; Pointer bounds reject null/legacy scalars/kernel half, not stale allocations.
; Caller must own/validate Dialogue lifetime; no arbitrary-memory probing.

query_playing:
    push ebp
    mov ebp, esp
    push ebx
    push esi
    push edi
    sub esp, 12
    mov esi, ecx

    ; User-heap range [0x10000,0x7fffff00); reserve256bytes for field reads.
    lea eax, [esi-0x10000]
    cmp eax, 0x7ffeff00
    jae query_fail
    cmp dword ptr [esi], 0x29f974
    jne query_fail
    cmp dword ptr [esi+0x5c], 1
    jne query_fail
    mov ebx, dword ptr [esi+0xc8]
    lea eax, [ebx-0x10000]
    cmp eax, 0x7ffeff00
    jae query_fail
    mov ecx, dword ptr [ebx+8]
    lea eax, [ecx-0x10000]
    cmp eax, 0x7ffeff00
    jae query_fail
    mov edi, dword ptr [ecx]
    lea eax, [edi-0x10000]
    cmp eax, 0x7ffeff00
    jae query_fail
    ; API-owned critical-section address: the helper never dereferences it.
    ; Live Xbox memory confirms a valid address in the kernel half.
    mov eax, dword ptr [edi+0x54]
    test eax, eax
    je query_fail
    mov dword ptr [ebp-20], eax
    push eax
    call dword ptr [0x28e484]

    ; Revalidate linkage while holding the physical voice's existing lock.
    cmp dword ptr [esi+0x5c], 1
    jne query_locked_fail
    cmp dword ptr [esi+0xc8], ebx
    jne query_locked_fail
    cmp dword ptr [edi+0x14], ebx
    jne query_locked_fail
    mov ecx, dword ptr [ebx+8]
    lea eax, [ecx-0x10000]
    cmp eax, 0x7ffeff00
    jae query_locked_fail
    cmp dword ptr [ecx], edi
    jne query_locked_fail
    mov ecx, dword ptr [ebx]
    lea eax, [ecx-0x10000]
    cmp eax, 0x7ffeff00
    jae query_locked_fail
    cmp dword ptr [ecx+0x20], 16
    jb query_inline_name
    mov edx, dword ptr [ecx+12]
    jmp query_name_ready
query_inline_name:
    lea edx, [ecx+12]
query_name_ready:
    lea eax, [edx-0x10000]
    cmp eax, 0x7ffeff00
    jae query_locked_fail
    cmp byte ptr [edx], 0
    je query_locked_fail
    mov dword ptr [ebp-24], edx
    mov eax, edx
    mov ecx, 256
query_name_scan:
    cmp byte ptr [eax], 0
    je query_name_valid
    add eax, 1
    sub ecx, 1
    jne query_name_scan
    jmp query_locked_fail
query_name_valid:
    ; Opaque DSound interface: passed to the original API, never dereferenced here.
    ; Native buffer interfaces need not occupy the game user-heap half.
    mov eax, dword ptr [edi+0x24]
    test eax, eax
    je query_locked_fail
    mov dword ptr [ebp-16], 0
    lea ecx, [ebp-16]
    push ecx
    push eax
    call 0x2383fc
    test eax, eax
    jne query_locked_fail
    test byte ptr [ebp-16], 1
    je query_locked_fail
    push dword ptr [ebp-20]
    call dword ptr [0x28e488]
    mov eax, ebx
    mov edx, dword ptr [ebp-24]
    jmp query_done

query_locked_fail:
    push dword ptr [ebp-20]
    call dword ptr [0x28e488]
query_fail:
    xor eax, eax
    xor edx, edx
query_done:
    add esp, 12
    pop edi
    pop esi
    pop ebx
    pop ebp
    ret
