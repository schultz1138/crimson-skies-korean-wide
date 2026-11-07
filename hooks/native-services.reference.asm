; quad_pre_10
pushfq
push rax
push rbx
push rcx
push rdx
push rbp
push rsi
push rdi
push r8
push r9
push r10
push r11
push r12
push r13
push r14
push r15
mov rbp,rsp
and rsp,-16
sub rsp,0xb0
mov [rsp+0xa0],rbp
movdqu [rsp+32],xmm0
movdqu [rsp+48],xmm1
movdqu [rsp+64],xmm2
movdqu [rsp+80],xmm3
movdqu [rsp+96],xmm4
movdqu [rsp+112],xmm5
movdqu [rsp+128],xmm6
movdqu [rsp+144],xmm7
call qword ptr [rip]
mov r11d,eax
lea r10,[rip]
mov ecx,8
scan:
mov eax,[r10]
cmp eax,r11d
je found
test eax,eax
jne next_slot
xor eax,eax
lock cmpxchg dword ptr [r10],r11d
je found
next_slot:
add r10,0x500
dec ecx
jne scan
jmp done
found:
lea rdi,[rip]
mov rax,r10
sub rax,rdi
xor edx,edx
mov ecx,0x500
div ecx
shl eax,7
lea rdi,[rdi+rax+10752]
inc dword ptr [rdi]
mov eax,[r10+4]
test eax,eax
jne diagnostic_eligible
lea r11,[r10+0x4e8]
mov dword ptr [r11],10
mov eax,[r10+8]
mov [r11+4],eax
mov dword ptr [r11+8],0
mov dword ptr [r11+12],0
test eax,eax
je diagnostic_zero_top_done
cmp eax,16
ja diagnostic_zero_top_done
dec eax
lea rdx,[r10+rax*8+0x40]
mov ecx,[rdx]
mov [r11+8],ecx
mov ecx,[rdx+4]
mov [r11+12],ecx
diagnostic_zero_top_done:
mov [r11+16],r14d
mov eax,[r10+12]
mov [r11+20],eax
jmp diagnostic_entered
diagnostic_eligible:
inc dword ptr [rdi+4]
mov [rdi+16],r14d
mov dword ptr [rdi+12],1
mov [rdi+20],eax
diagnostic_entered:
cmp dword ptr [r10+20],0
jne overflow
mov eax,[r10+16]
cmp eax,16
jae overflow
imul eax,eax,56
lea rbx,[r10+rax+0xc0]
mov dword ptr [rbx],10
mov dword ptr [rbx+4],0
mov [rbx+48],r12
inc dword ptr [r10+16]
mov eax,[r10+4]
test eax,eax
je done
mov dword ptr [rdi+12],2
mov [rdi+20],eax
cmp eax,2
ja done
mov eax,r14d
mov dword ptr [rdi+12],14
mov rdx,r14
shr rdx,32
mov [rdi+20],edx
cmp r14,rax
jne done
mov dword ptr [rdi+12],3
mov [rdi+20],r14d
cmp r14d,0x10000
jb done
mov dword ptr [rdi+12],4
mov [rdi+20],r14d
cmp r14d,0xffffff00
ja done
mov eax,dword ptr [r15+r14+4]
mov dword ptr [rdi+12],6
mov [rdi+20],eax
cmp eax,4
jne done
mov edx,[r15+r14]
lea rcx,[r14+92]
mov dword ptr [rdi+12],8
mov [rdi+20],edx
cmp rdx,rcx
jne done
mov dword ptr [rdi+12],9
mov [rdi+20],edx
cmp edx,0xffffff80
ja done
lea rsi,[r15+rdx]
mov [rbx+8],rsi
call 6484733952
mov r9d,eax
lea rdx,[rip]
shl eax,5
add rdx,rax
movss xmm1,[rdx]
movss xmm4,[rdx+4]
movss xmm2,[rdx+8]
movss xmm5,[rdx+12]
xorps xmm3,xmm3
xorps xmm6,xmm6
mov eax,[rsi+0]
mov [rbx+16],eax
mov dword ptr [rdi+12],10
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
test r9d,r9d
je skip_y_0
mov eax,[rsi+4]
mov [rbx+32],eax
mov dword ptr [rdi+12],11
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
skip_y_0:
mov eax,[rsi+28]
mov [rbx+20],eax
mov dword ptr [rdi+12],10
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
test r9d,r9d
je skip_y_1
mov eax,[rsi+32]
mov [rbx+36],eax
mov dword ptr [rdi+12],11
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
skip_y_1:
mov eax,[rsi+56]
mov [rbx+24],eax
mov dword ptr [rdi+12],10
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
test r9d,r9d
je skip_y_2
mov eax,[rsi+60]
mov [rbx+40],eax
mov dword ptr [rdi+12],11
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
skip_y_2:
mov eax,[rsi+84]
mov [rbx+28],eax
mov dword ptr [rdi+12],10
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
test r9d,r9d
je skip_y_3
mov eax,[rsi+88]
mov [rbx+44],eax
mov dword ptr [rdi+12],11
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
skip_y_3:
cmp dword ptr [r10+4],2
jne transform_x
movss xmm2,[rbx+16]
addss xmm2,[rbx+20]
addss xmm2,[rbx+24]
addss xmm2,[rbx+28]
mov eax,0x3e800000
movd xmm0,eax
mulss xmm2,xmm0
movaps xmm3,xmm2
test r9d,r9d
je transform_x
movss xmm5,[rbx+32]
addss xmm5,[rbx+36]
addss xmm5,[rbx+40]
addss xmm5,[rbx+44]
mulss xmm5,xmm0
movaps xmm6,xmm5
transform_x:
movss xmm0,[rbx+16]
subss xmm0,xmm3
mulss xmm0,xmm1
addss xmm0,xmm2
movss [rsi+0],xmm0
movss xmm0,[rbx+20]
subss xmm0,xmm3
mulss xmm0,xmm1
addss xmm0,xmm2
movss [rsi+28],xmm0
movss xmm0,[rbx+24]
subss xmm0,xmm3
mulss xmm0,xmm1
addss xmm0,xmm2
movss [rsi+56],xmm0
movss xmm0,[rbx+28]
subss xmm0,xmm3
mulss xmm0,xmm1
addss xmm0,xmm2
movss [rsi+84],xmm0
mov dword ptr [rbx+4],1
inc dword ptr [rdi+8]
mov dword ptr [rdi+12],12
mov dword ptr [rdi+20],0
test r9d,r9d
je done
movss xmm0,[rbx+32]
subss xmm0,xmm6
mulss xmm0,xmm4
addss xmm0,xmm5
movss [rsi+4],xmm0
movss xmm0,[rbx+36]
subss xmm0,xmm6
mulss xmm0,xmm4
addss xmm0,xmm5
movss [rsi+32],xmm0
movss xmm0,[rbx+40]
subss xmm0,xmm6
mulss xmm0,xmm4
addss xmm0,xmm5
movss [rsi+60],xmm0
movss xmm0,[rbx+44]
subss xmm0,xmm6
mulss xmm0,xmm4
addss xmm0,xmm5
movss [rsi+88],xmm0
mov dword ptr [rbx+4],3
jmp done
overflow:
cmp dword ptr [r10+4],0
je diagnostic_overflow_logged
mov dword ptr [rdi+12],13
mov eax,[r10+16]
mov [rdi+20],eax
diagnostic_overflow_logged:
inc dword ptr [r10+20]
jmp done
done:
movdqu xmm0,[rsp+32]
movdqu xmm1,[rsp+48]
movdqu xmm2,[rsp+64]
movdqu xmm3,[rsp+80]
movdqu xmm4,[rsp+96]
movdqu xmm5,[rsp+112]
movdqu xmm6,[rsp+128]
movdqu xmm7,[rsp+144]
mov rsp,[rsp+0xa0]
pop r15
pop r14
pop r13
pop r12
pop r11
pop r10
pop r9
pop r8
pop rdi
pop rsi
pop rbp
pop rdx
pop rcx
pop rbx
pop rax
popfq
ret

; quad_post_10
pushfq
push rax
push rbx
push rcx
push rdx
push rbp
push rsi
push rdi
push r8
push r9
push r10
push r11
push r12
push r13
push r14
push r15
mov rbp,rsp
and rsp,-16
sub rsp,0xb0
mov [rsp+0xa0],rbp
movdqu [rsp+32],xmm0
movdqu [rsp+48],xmm1
movdqu [rsp+64],xmm2
movdqu [rsp+80],xmm3
movdqu [rsp+96],xmm4
movdqu [rsp+112],xmm5
movdqu [rsp+128],xmm6
movdqu [rsp+144],xmm7
call qword ptr [rip]
mov r11d,eax
lea r10,[rip]
mov ecx,8
scan:
mov eax,[r10]
cmp eax,r11d
je found
test eax,eax
jne next_slot
xor eax,eax
lock cmpxchg dword ptr [r10],r11d
je found
next_slot:
add r10,0x500
dec ecx
jne scan
jmp done
found:
cmp dword ptr [r10+20],0
je normal_post
dec dword ptr [r10+20]
jmp done
normal_post:
mov eax,[r10+16]
test eax,eax
je done
dec eax
imul edx,eax,56
lea rbx,[r10+rdx+0xc0]
cmp dword ptr [rbx],10
jne mismatch
cmp [rbx+48],r12
jne mismatch
mov [r10+16],eax
mov edx,[rbx+4]
test edx,1
je done
mov rsi,[rbx+8]
mov eax,[rbx+16]
mov [rsi+0],eax
mov eax,[rbx+20]
mov [rsi+28],eax
mov eax,[rbx+24]
mov [rsi+56],eax
mov eax,[rbx+28]
mov [rsi+84],eax
test edx,2
je restored
mov eax,[rbx+32]
mov [rsi+4],eax
mov eax,[rbx+36]
mov [rsi+32],eax
mov eax,[rbx+40]
mov [rsi+60],eax
mov eax,[rbx+44]
mov [rsi+88],eax
restored:
mov dword ptr [rbx+4],0
jmp done
mismatch:
mov dword ptr [r10+4],0
jmp done
done:
movdqu xmm0,[rsp+32]
movdqu xmm1,[rsp+48]
movdqu xmm2,[rsp+64]
movdqu xmm3,[rsp+80]
movdqu xmm4,[rsp+96]
movdqu xmm5,[rsp+112]
movdqu xmm6,[rsp+128]
movdqu xmm7,[rsp+144]
mov rsp,[rsp+0xa0]
pop r15
pop r14
pop r13
pop r12
pop r11
pop r10
pop r9
pop r8
pop rdi
pop rsi
pop rbp
pop rdx
pop rcx
pop rbx
pop rax
popfq
ret

; quad_pre_11
pushfq
push rax
push rbx
push rcx
push rdx
push rbp
push rsi
push rdi
push r8
push r9
push r10
push r11
push r12
push r13
push r14
push r15
mov rbp,rsp
and rsp,-16
sub rsp,0xb0
mov [rsp+0xa0],rbp
movdqu [rsp+32],xmm0
movdqu [rsp+48],xmm1
movdqu [rsp+64],xmm2
movdqu [rsp+80],xmm3
movdqu [rsp+96],xmm4
movdqu [rsp+112],xmm5
movdqu [rsp+128],xmm6
movdqu [rsp+144],xmm7
call qword ptr [rip]
mov r11d,eax
lea r10,[rip]
mov ecx,8
scan:
mov eax,[r10]
cmp eax,r11d
je found
test eax,eax
jne next_slot
xor eax,eax
lock cmpxchg dword ptr [r10],r11d
je found
next_slot:
add r10,0x500
dec ecx
jne scan
jmp done
found:
lea rdi,[rip]
mov rax,r10
sub rax,rdi
xor edx,edx
mov ecx,0x500
div ecx
shl eax,7
lea rdi,[rdi+rax+10776]
inc dword ptr [rdi]
mov eax,[r10+4]
test eax,eax
jne diagnostic_eligible
lea r11,[r10+0x4e8]
mov dword ptr [r11],11
mov eax,[r10+8]
mov [r11+4],eax
mov dword ptr [r11+8],0
mov dword ptr [r11+12],0
test eax,eax
je diagnostic_zero_top_done
cmp eax,16
ja diagnostic_zero_top_done
dec eax
lea rdx,[r10+rax*8+0x40]
mov ecx,[rdx]
mov [r11+8],ecx
mov ecx,[rdx+4]
mov [r11+12],ecx
diagnostic_zero_top_done:
mov [r11+16],r14d
mov eax,[r10+12]
mov [r11+20],eax
jmp diagnostic_entered
diagnostic_eligible:
inc dword ptr [rdi+4]
mov [rdi+16],r14d
mov dword ptr [rdi+12],1
mov [rdi+20],eax
diagnostic_entered:
cmp dword ptr [r10+20],0
jne overflow
mov eax,[r10+16]
cmp eax,16
jae overflow
imul eax,eax,56
lea rbx,[r10+rax+0xc0]
mov dword ptr [rbx],11
mov dword ptr [rbx+4],0
mov [rbx+48],r12
inc dword ptr [r10+16]
mov eax,[r10+4]
test eax,eax
je done
mov dword ptr [rdi+12],2
mov [rdi+20],eax
cmp eax,2
ja done
mov eax,r14d
mov dword ptr [rdi+12],14
mov rdx,r14
shr rdx,32
mov [rdi+20],edx
cmp r14,rax
jne done
mov dword ptr [rdi+12],3
mov [rdi+20],r14d
cmp r14d,0x10000
jb done
mov dword ptr [rdi+12],4
mov [rdi+20],r14d
cmp r14d,0xffffff00
ja done
mov eax,dword ptr [r15+r14]
mov dword ptr [rdi+12],5
mov [rdi+20],eax
cmp eax,7
jne done
mov eax,dword ptr [r15+r14+4]
mov dword ptr [rdi+12],6
mov [rdi+20],eax
cmp eax,4
jne done
mov eax,dword ptr [r15+r14+12]
mov dword ptr [rdi+12],7
mov [rdi+20],eax
cmp eax,28
jne done
mov edx,[r15+r14+8]
lea rcx,[r14+136]
mov dword ptr [rdi+12],8
mov [rdi+20],edx
cmp rdx,rcx
jne done
mov dword ptr [rdi+12],9
mov [rdi+20],edx
cmp edx,0xffffff80
ja done
lea rsi,[r15+rdx]
mov [rbx+8],rsi
call 6484733952
mov r9d,eax
lea rdx,[rip]
shl eax,5
add rdx,rax
movss xmm1,[rdx]
movss xmm4,[rdx+4]
movss xmm2,[rdx+8]
movss xmm5,[rdx+12]
xorps xmm3,xmm3
xorps xmm6,xmm6
mov eax,[rsi+0]
mov [rbx+16],eax
mov dword ptr [rdi+12],10
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
test r9d,r9d
je skip_y_0
mov eax,[rsi+4]
mov [rbx+32],eax
mov dword ptr [rdi+12],11
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
skip_y_0:
mov eax,[rsi+28]
mov [rbx+20],eax
mov dword ptr [rdi+12],10
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
test r9d,r9d
je skip_y_1
mov eax,[rsi+32]
mov [rbx+36],eax
mov dword ptr [rdi+12],11
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
skip_y_1:
mov eax,[rsi+56]
mov [rbx+24],eax
mov dword ptr [rdi+12],10
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
test r9d,r9d
je skip_y_2
mov eax,[rsi+60]
mov [rbx+40],eax
mov dword ptr [rdi+12],11
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
skip_y_2:
mov eax,[rsi+84]
mov [rbx+28],eax
mov dword ptr [rdi+12],10
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
test r9d,r9d
je skip_y_3
mov eax,[rsi+88]
mov [rbx+44],eax
mov dword ptr [rdi+12],11
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
skip_y_3:
cmp dword ptr [r10+4],2
jne transform_x
movss xmm2,[rbx+16]
addss xmm2,[rbx+20]
addss xmm2,[rbx+24]
addss xmm2,[rbx+28]
mov eax,0x3e800000
movd xmm0,eax
mulss xmm2,xmm0
movaps xmm3,xmm2
test r9d,r9d
je transform_x
movss xmm5,[rbx+32]
addss xmm5,[rbx+36]
addss xmm5,[rbx+40]
addss xmm5,[rbx+44]
mulss xmm5,xmm0
movaps xmm6,xmm5
transform_x:
movss xmm0,[rbx+16]
subss xmm0,xmm3
mulss xmm0,xmm1
addss xmm0,xmm2
movss [rsi+0],xmm0
movss xmm0,[rbx+20]
subss xmm0,xmm3
mulss xmm0,xmm1
addss xmm0,xmm2
movss [rsi+28],xmm0
movss xmm0,[rbx+24]
subss xmm0,xmm3
mulss xmm0,xmm1
addss xmm0,xmm2
movss [rsi+56],xmm0
movss xmm0,[rbx+28]
subss xmm0,xmm3
mulss xmm0,xmm1
addss xmm0,xmm2
movss [rsi+84],xmm0
mov dword ptr [rbx+4],1
inc dword ptr [rdi+8]
mov dword ptr [rdi+12],12
mov dword ptr [rdi+20],0
test r9d,r9d
je done
movss xmm0,[rbx+32]
subss xmm0,xmm6
mulss xmm0,xmm4
addss xmm0,xmm5
movss [rsi+4],xmm0
movss xmm0,[rbx+36]
subss xmm0,xmm6
mulss xmm0,xmm4
addss xmm0,xmm5
movss [rsi+32],xmm0
movss xmm0,[rbx+40]
subss xmm0,xmm6
mulss xmm0,xmm4
addss xmm0,xmm5
movss [rsi+60],xmm0
movss xmm0,[rbx+44]
subss xmm0,xmm6
mulss xmm0,xmm4
addss xmm0,xmm5
movss [rsi+88],xmm0
mov dword ptr [rbx+4],3
jmp done
overflow:
cmp dword ptr [r10+4],0
je diagnostic_overflow_logged
mov dword ptr [rdi+12],13
mov eax,[r10+16]
mov [rdi+20],eax
diagnostic_overflow_logged:
inc dword ptr [r10+20]
jmp done
done:
movdqu xmm0,[rsp+32]
movdqu xmm1,[rsp+48]
movdqu xmm2,[rsp+64]
movdqu xmm3,[rsp+80]
movdqu xmm4,[rsp+96]
movdqu xmm5,[rsp+112]
movdqu xmm6,[rsp+128]
movdqu xmm7,[rsp+144]
mov rsp,[rsp+0xa0]
pop r15
pop r14
pop r13
pop r12
pop r11
pop r10
pop r9
pop r8
pop rdi
pop rsi
pop rbp
pop rdx
pop rcx
pop rbx
pop rax
popfq
ret

; quad_post_11
pushfq
push rax
push rbx
push rcx
push rdx
push rbp
push rsi
push rdi
push r8
push r9
push r10
push r11
push r12
push r13
push r14
push r15
mov rbp,rsp
and rsp,-16
sub rsp,0xb0
mov [rsp+0xa0],rbp
movdqu [rsp+32],xmm0
movdqu [rsp+48],xmm1
movdqu [rsp+64],xmm2
movdqu [rsp+80],xmm3
movdqu [rsp+96],xmm4
movdqu [rsp+112],xmm5
movdqu [rsp+128],xmm6
movdqu [rsp+144],xmm7
call qword ptr [rip]
mov r11d,eax
lea r10,[rip]
mov ecx,8
scan:
mov eax,[r10]
cmp eax,r11d
je found
test eax,eax
jne next_slot
xor eax,eax
lock cmpxchg dword ptr [r10],r11d
je found
next_slot:
add r10,0x500
dec ecx
jne scan
jmp done
found:
cmp dword ptr [r10+20],0
je normal_post
dec dword ptr [r10+20]
jmp done
normal_post:
mov eax,[r10+16]
test eax,eax
je done
dec eax
imul edx,eax,56
lea rbx,[r10+rdx+0xc0]
cmp dword ptr [rbx],11
jne mismatch
cmp [rbx+48],r12
jne mismatch
mov [r10+16],eax
mov edx,[rbx+4]
test edx,1
je done
mov rsi,[rbx+8]
mov eax,[rbx+16]
mov [rsi+0],eax
mov eax,[rbx+20]
mov [rsi+28],eax
mov eax,[rbx+24]
mov [rsi+56],eax
mov eax,[rbx+28]
mov [rsi+84],eax
test edx,2
je restored
mov eax,[rbx+32]
mov [rsi+4],eax
mov eax,[rbx+36]
mov [rsi+32],eax
mov eax,[rbx+40]
mov [rsi+60],eax
mov eax,[rbx+44]
mov [rsi+88],eax
restored:
mov dword ptr [rbx+4],0
jmp done
mismatch:
mov dword ptr [r10+4],0
jmp done
done:
movdqu xmm0,[rsp+32]
movdqu xmm1,[rsp+48]
movdqu xmm2,[rsp+64]
movdqu xmm3,[rsp+80]
movdqu xmm4,[rsp+96]
movdqu xmm5,[rsp+112]
movdqu xmm6,[rsp+128]
movdqu xmm7,[rsp+144]
mov rsp,[rsp+0xa0]
pop r15
pop r14
pop r13
pop r12
pop r11
pop r10
pop r9
pop r8
pop rdi
pop rsi
pop rbp
pop rdx
pop rcx
pop rbx
pop rax
popfq
ret

; quad_pre_12
pushfq
push rax
push rbx
push rcx
push rdx
push rbp
push rsi
push rdi
push r8
push r9
push r10
push r11
push r12
push r13
push r14
push r15
mov rbp,rsp
and rsp,-16
sub rsp,0xb0
mov [rsp+0xa0],rbp
movdqu [rsp+32],xmm0
movdqu [rsp+48],xmm1
movdqu [rsp+64],xmm2
movdqu [rsp+80],xmm3
movdqu [rsp+96],xmm4
movdqu [rsp+112],xmm5
movdqu [rsp+128],xmm6
movdqu [rsp+144],xmm7
call qword ptr [rip]
mov r11d,eax
lea r10,[rip]
mov ecx,8
scan:
mov eax,[r10]
cmp eax,r11d
je found
test eax,eax
jne next_slot
xor eax,eax
lock cmpxchg dword ptr [r10],r11d
je found
next_slot:
add r10,0x500
dec ecx
jne scan
jmp done
found:
lea rdi,[rip]
mov rax,r10
sub rax,rdi
xor edx,edx
mov ecx,0x500
div ecx
shl eax,7
lea rdi,[rdi+rax+10800]
inc dword ptr [rdi]
mov eax,[r10+4]
test eax,eax
jne diagnostic_eligible
lea r11,[r10+0x4e8]
mov dword ptr [r11],12
mov eax,[r10+8]
mov [r11+4],eax
mov dword ptr [r11+8],0
mov dword ptr [r11+12],0
test eax,eax
je diagnostic_zero_top_done
cmp eax,16
ja diagnostic_zero_top_done
dec eax
lea rdx,[r10+rax*8+0x40]
mov ecx,[rdx]
mov [r11+8],ecx
mov ecx,[rdx+4]
mov [r11+12],ecx
diagnostic_zero_top_done:
mov [r11+16],r14d
mov eax,[r10+12]
mov [r11+20],eax
jmp diagnostic_entered
diagnostic_eligible:
inc dword ptr [rdi+4]
mov [rdi+16],r14d
mov dword ptr [rdi+12],1
mov [rdi+20],eax
diagnostic_entered:
cmp dword ptr [r10+20],0
jne overflow
mov eax,[r10+16]
cmp eax,16
jae overflow
imul eax,eax,56
lea rbx,[r10+rax+0xc0]
mov dword ptr [rbx],12
mov dword ptr [rbx+4],0
mov [rbx+48],r12
inc dword ptr [r10+16]
mov eax,[r10+4]
test eax,eax
je done
mov dword ptr [rdi+12],2
mov [rdi+20],eax
cmp eax,2
ja done
mov eax,r14d
mov dword ptr [rdi+12],14
mov rdx,r14
shr rdx,32
mov [rdi+20],edx
cmp r14,rax
jne done
mov dword ptr [rdi+12],3
mov [rdi+20],r14d
cmp r14d,0x10000
jb done
mov dword ptr [rdi+12],4
mov [rdi+20],r14d
cmp r14d,0xffffff00
ja done
mov eax,dword ptr [r15+r14]
mov dword ptr [rdi+12],5
mov [rdi+20],eax
cmp eax,7
jne done
mov eax,dword ptr [r15+r14+4]
mov dword ptr [rdi+12],6
mov [rdi+20],eax
cmp eax,4
jne done
mov eax,dword ptr [r15+r14+12]
mov dword ptr [rdi+12],7
mov [rdi+20],eax
cmp eax,28
jne done
mov edx,[r15+r14+8]
lea rcx,[r14+16]
mov dword ptr [rdi+12],8
mov [rdi+20],edx
cmp rdx,rcx
jne done
mov dword ptr [rdi+12],9
mov [rdi+20],edx
cmp edx,0xffffff80
ja done
lea rsi,[r15+rdx]
mov [rbx+8],rsi
call 6484733952
mov r9d,eax
lea rdx,[rip]
shl eax,5
add rdx,rax
movss xmm1,[rdx]
movss xmm4,[rdx+4]
movss xmm2,[rdx+8]
movss xmm5,[rdx+12]
xorps xmm3,xmm3
xorps xmm6,xmm6
mov eax,[rsi+0]
mov [rbx+16],eax
mov dword ptr [rdi+12],10
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
mov eax,[rsi+4]
mov [rbx+32],eax
mov dword ptr [rdi+12],11
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
skip_y_0:
mov eax,[rsi+28]
mov [rbx+20],eax
mov dword ptr [rdi+12],10
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
mov eax,[rsi+32]
mov [rbx+36],eax
mov dword ptr [rdi+12],11
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
skip_y_1:
mov eax,[rsi+56]
mov [rbx+24],eax
mov dword ptr [rdi+12],10
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
mov eax,[rsi+60]
mov [rbx+40],eax
mov dword ptr [rdi+12],11
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
skip_y_2:
mov eax,[rsi+84]
mov [rbx+28],eax
mov dword ptr [rdi+12],10
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
mov eax,[rsi+88]
mov [rbx+44],eax
mov dword ptr [rdi+12],11
mov [rdi+20],eax
and eax,0x7fffffff
cmp eax,0x47800000
ja done
skip_y_3:
movss xmm0,[rbx+16]
minss xmm0,[rbx+20]
minss xmm0,[rbx+24]
minss xmm0,[rbx+28]
xorps xmm7,xmm7
comiss xmm0,xmm7
ja solid_not_full_canvas
movss xmm0,[rbx+16]
maxss xmm0,[rbx+20]
maxss xmm0,[rbx+24]
maxss xmm0,[rbx+28]
mov eax,1142947840
movd xmm7,eax
comiss xmm0,xmm7
jb solid_not_full_canvas
movss xmm0,[rbx+32]
minss xmm0,[rbx+36]
minss xmm0,[rbx+40]
minss xmm0,[rbx+44]
xorps xmm7,xmm7
comiss xmm0,xmm7
ja solid_not_full_canvas
movss xmm0,[rbx+32]
maxss xmm0,[rbx+36]
maxss xmm0,[rbx+40]
maxss xmm0,[rbx+44]
mov eax,1139802112
movd xmm7,eax
comiss xmm0,xmm7
jb solid_not_full_canvas
mov dword ptr [rdi+12],15
mov dword ptr [rdi+20],0
jmp done
solid_not_full_canvas:
cmp dword ptr [r10+4],2
jne transform_x
movss xmm2,[rbx+16]
addss xmm2,[rbx+20]
addss xmm2,[rbx+24]
addss xmm2,[rbx+28]
mov eax,0x3e800000
movd xmm0,eax
mulss xmm2,xmm0
movaps xmm3,xmm2
test r9d,r9d
je transform_x
movss xmm5,[rbx+32]
addss xmm5,[rbx+36]
addss xmm5,[rbx+40]
addss xmm5,[rbx+44]
mulss xmm5,xmm0
movaps xmm6,xmm5
transform_x:
movss xmm0,[rbx+16]
subss xmm0,xmm3
mulss xmm0,xmm1
addss xmm0,xmm2
movss [rsi+0],xmm0
movss xmm0,[rbx+20]
subss xmm0,xmm3
mulss xmm0,xmm1
addss xmm0,xmm2
movss [rsi+28],xmm0
movss xmm0,[rbx+24]
subss xmm0,xmm3
mulss xmm0,xmm1
addss xmm0,xmm2
movss [rsi+56],xmm0
movss xmm0,[rbx+28]
subss xmm0,xmm3
mulss xmm0,xmm1
addss xmm0,xmm2
movss [rsi+84],xmm0
mov dword ptr [rbx+4],1
inc dword ptr [rdi+8]
mov dword ptr [rdi+12],12
mov dword ptr [rdi+20],0
test r9d,r9d
je done
movss xmm0,[rbx+32]
subss xmm0,xmm6
mulss xmm0,xmm4
addss xmm0,xmm5
movss [rsi+4],xmm0
movss xmm0,[rbx+36]
subss xmm0,xmm6
mulss xmm0,xmm4
addss xmm0,xmm5
movss [rsi+32],xmm0
movss xmm0,[rbx+40]
subss xmm0,xmm6
mulss xmm0,xmm4
addss xmm0,xmm5
movss [rsi+60],xmm0
movss xmm0,[rbx+44]
subss xmm0,xmm6
mulss xmm0,xmm4
addss xmm0,xmm5
movss [rsi+88],xmm0
mov dword ptr [rbx+4],3
jmp done
overflow:
cmp dword ptr [r10+4],0
je diagnostic_overflow_logged
mov dword ptr [rdi+12],13
mov eax,[r10+16]
mov [rdi+20],eax
diagnostic_overflow_logged:
inc dword ptr [r10+20]
jmp done
done:
movdqu xmm0,[rsp+32]
movdqu xmm1,[rsp+48]
movdqu xmm2,[rsp+64]
movdqu xmm3,[rsp+80]
movdqu xmm4,[rsp+96]
movdqu xmm5,[rsp+112]
movdqu xmm6,[rsp+128]
movdqu xmm7,[rsp+144]
mov rsp,[rsp+0xa0]
pop r15
pop r14
pop r13
pop r12
pop r11
pop r10
pop r9
pop r8
pop rdi
pop rsi
pop rbp
pop rdx
pop rcx
pop rbx
pop rax
popfq
ret

; quad_post_12
pushfq
push rax
push rbx
push rcx
push rdx
push rbp
push rsi
push rdi
push r8
push r9
push r10
push r11
push r12
push r13
push r14
push r15
mov rbp,rsp
and rsp,-16
sub rsp,0xb0
mov [rsp+0xa0],rbp
movdqu [rsp+32],xmm0
movdqu [rsp+48],xmm1
movdqu [rsp+64],xmm2
movdqu [rsp+80],xmm3
movdqu [rsp+96],xmm4
movdqu [rsp+112],xmm5
movdqu [rsp+128],xmm6
movdqu [rsp+144],xmm7
call qword ptr [rip]
mov r11d,eax
lea r10,[rip]
mov ecx,8
scan:
mov eax,[r10]
cmp eax,r11d
je found
test eax,eax
jne next_slot
xor eax,eax
lock cmpxchg dword ptr [r10],r11d
je found
next_slot:
add r10,0x500
dec ecx
jne scan
jmp done
found:
cmp dword ptr [r10+20],0
je normal_post
dec dword ptr [r10+20]
jmp done
normal_post:
mov eax,[r10+16]
test eax,eax
je done
dec eax
imul edx,eax,56
lea rbx,[r10+rdx+0xc0]
cmp dword ptr [rbx],12
jne mismatch
cmp [rbx+48],r12
jne mismatch
mov [r10+16],eax
mov edx,[rbx+4]
test edx,1
je done
mov rsi,[rbx+8]
mov eax,[rbx+16]
mov [rsi+0],eax
mov eax,[rbx+20]
mov [rsi+28],eax
mov eax,[rbx+24]
mov [rsi+56],eax
mov eax,[rbx+28]
mov [rsi+84],eax
test edx,2
je restored
mov eax,[rbx+32]
mov [rsi+4],eax
mov eax,[rbx+36]
mov [rsi+32],eax
mov eax,[rbx+40]
mov [rsi+60],eax
mov eax,[rbx+44]
mov [rsi+88],eax
restored:
mov dword ptr [rbx+4],0
jmp done
mismatch:
mov dword ptr [r10+4],0
jmp done
done:
movdqu xmm0,[rsp+32]
movdqu xmm1,[rsp+48]
movdqu xmm2,[rsp+64]
movdqu xmm3,[rsp+80]
movdqu xmm4,[rsp+96]
movdqu xmm5,[rsp+112]
movdqu xmm6,[rsp+128]
movdqu xmm7,[rsp+144]
mov rsp,[rsp+0xa0]
pop r15
pop r14
pop r13
pop r12
pop r11
pop r10
pop r9
pop r8
pop rdi
pop rsi
pop rbp
pop rdx
pop rcx
pop rbx
pop rax
popfq
ret
