test edi, edi
    jz tutorial
    cmp dword ptr [esi+0x1c], 0x10
    jb inline_name
    mov eax, [esi+8]
    jmp test_radio
inline_name:
    lea eax, [esi+8]
test_radio:
    mov edx, [eax]
    or edx, 0x20202020
    cmp edx, 0x69646172
    jne status
    mov dl, [eax+4]
    or dl, 0x20
    cmp dl, 0x6f
    jne status
    cmp byte ptr [eax+5], 0
    jne status
    mov edi, 2
    jmp done
tutorial:
    mov edi, 1
    jmp done
status:
    xor edi, edi
done:
    mov eax, [esi+0x3c]
    jmp 0x26c92