push ebp
mov ebp, esp
push ebx
push esi
push edi
mov eax, dword ptr [esi + 0x54]
cmp eax, 0x10000
jb original
mov eax, dword ptr [eax + 0x9a4]
cmp eax, 0x10000
jb original
cmp dword ptr [eax + 0x74], esi
jne original
mov eax, dword ptr [ebp + 0x10]
test eax, eax
je original
mov edi, dword ptr [ebp + 8]
test edi, edi
je original
mov ebx, edi
mov ecx, 0x100
scan:
cmp word ptr [ebx], 0
je original
cmp word ptr [ebx], 0xa
je split
add ebx, 2
sub ecx, 1
jne scan
jmp original
split:
mov eax, dword ptr [ebp + 0x10]
inc dword ptr [eax + 0x2c]
mov word ptr [ebx], 0
push dword ptr [ebp + 0x14]
push dword ptr [ebp + 0x10]
push dword ptr [ebp + 0xc]
push edi
call 0x12f280
add esp, 0x10
push dword ptr [ebp + 0x14]
push dword ptr [ebp + 0x10]
push dword ptr [ebp + 0xc]
lea eax, [ebx + 2]
push eax
call 0x12f280
add esp, 0x10
mov word ptr [ebx], 0xa
pop edi
pop esi
pop ebx
pop ebp
ret
original:
pop edi
pop esi
pop ebx
pop ebp
jmp 0x12f280
