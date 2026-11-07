"""Reviewed source-bound caption data and two translator-ABI host services.

This module only builds offline artifacts. The guest update routine provides a
512-byte writable UTF16 output buffer; no host pointer is passed to game code.
"""
from pathlib import Path
import json,struct,hashlib
ROOT=Path(__file__).resolve().parent.parent

def fnv(text):
 h=0x811c9dc5
 for b in text.encode('ascii'):
  h=((h^b)*0x1000193)&0xffffffff
 return h

def pack_dictionary(entries,data_rva):
 count=len(entries);partcount=sum(len(e['parts'])for e in entries)
 b=bytearray(count*32+partcount*16);cursor=count*32;rows=[]
 for index,e in enumerate(entries):
  part_at=cursor;cursor+=len(e['parts'])*16
  name=e['basename'].encode('ascii')+b'\0';name_at=len(b);b.extend(name)
  while len(b)%4:b.append(0)
  parts=[]
  for n,p in enumerate(e['parts']):
   text=p['text'].encode('utf-16le')+b'\0\0';text_at=len(b);b.extend(text)
   while len(b)%4:b.append(0)
   end=e['parts'][n+1]['offset']if n+1<len(e['parts'])else e['duration']
   struct.pack_into('<fIIf',b,part_at+16*n,p['offset'],data_rva+text_at,len(text),end)
   parts.append({**p,'end':end,'textRVA':data_rva+text_at,'textBytes':len(text)})
  struct.pack_into('<IIfIIIII',b,index*32,fnv(e['basename']),len(name)-1,e['duration'],len(parts),data_rva+name_at,data_rva+part_at,0,0)
  rows.append({**e,'index':index,'hash':fnv(e['basename']),'parts':parts})
 fade_at=len(b);b.extend(struct.pack('<f',0.25))
 return bytes(b),{'entryTableRVA':data_rva,'fadeRVA':data_rva+fade_at,'count':count,'parts':partcount,'bytes':len(b),'entries':rows}

def guest_return():
 return '''mov r8d, dword ptr [r14+r15]
 lea r14d, [r14+4]
 mov r9, qword ptr [rip+DISPATCH]
 jmp qword ptr [r9+r8*8]'''

def build_lookup(c,rva,metadata):
 # Exact case-insensitive basename matching after any path prefix. FNV is only
 # a filter; every matching hash is followed by a complete string comparison.
 asm=f'''
 mov r8d, ecx
 lea r8, [r8+r15]
 mov r10, r8
 xor ecx, ecx
scan_path:
 mov dl, byte ptr [r8+rcx]
 test dl, dl
 jz path_ready
 cmp dl, 47
 je path_separator
 cmp dl, 92
 jne path_next
path_separator:
 lea r10, [r8+rcx+1]
path_next:
 inc ecx
 cmp ecx, 256
 jb scan_path
 jmp not_found
path_ready:
 mov r8, r10
 mov eax, 0x811c9dc5
 mov r11, r8
hash_loop:
 movzx edx, byte ptr [r11]
 test edx, edx
 jz hash_ready
 cmp dl, 65
 jb hash_lowered
 cmp dl, 90
 ja hash_lowered
 add dl, 32
hash_lowered:
 xor eax, edx
 imul eax, eax, 0x1000193
 inc r11
 jmp hash_loop
hash_ready:
 lea r9, [rip+ENTRY_TABLE]
 xor ecx, ecx
entry_loop:
 cmp dword ptr [r9], eax
 jne entry_next
 mov r10d, dword ptr [r9+16]
 lea r11, [rip+IMAGE_BASE]
 add r10, r11
 mov r11, r8
compare_name:
 mov dl, byte ptr [r11]
 cmp dl, 65
 jb compare_lowered
 cmp dl, 90
 ja compare_lowered
 add dl, 32
compare_lowered:
 cmp dl, byte ptr [r10]
 jne entry_next
 test dl, dl
 jz found
 inc r10
 inc r11
 jmp compare_name
entry_next:
 add r9, 32
 inc ecx
 cmp ecx, {metadata['count']}
 jb entry_loop
not_found:
 mov eax, 0xffffffff
 jmp lookup_return
found:
 mov eax, ecx
lookup_return:
 {guest_return()}
 '''
 return c.assemble64(asm,rva,{'ENTRY_TABLE':metadata['entryTableRVA'],'IMAGE_BASE':0})

def build_part(c,rva,metadata,allow_delayed_start=False):
 # XMM0 is elapsed game time since the first observed playing frame. The
 # selected paragraph is copied as exact UTF16, including its terminating NUL.
 initial_guard='comiss xmm0, dword ptr [r10]\n jb part_expired'if allow_delayed_start else''
 asm=f'''
 cmp ecx, {metadata['count']}
 jae part_expired
 mov r8d, ecx
 shl r8d, 5
 lea r9, [rip+ENTRY_TABLE]
 add r9, r8
 comiss xmm0, dword ptr [r9+8]
 jae part_expired
 xor eax, eax
 mov r10d, dword ptr [r9+20]
 lea r11, [rip+IMAGE_BASE]
 add r10, r11
 {initial_guard}
 mov ecx, dword ptr [r9+12]
choose_part:
 cmp ecx, 1
 jbe chosen
 comiss xmm0, dword ptr [r10+16]
 jb chosen
 add r10, 16
 inc eax
 dec ecx
 jmp choose_part
chosen:
 movss xmm1, dword ptr [r10+12]
 subss xmm1, xmm0
 addss xmm1, dword ptr [rip+FADE]
 movd edx, xmm1
 mov r8d, dword ptr [r14+r15+4]
 lea r8, [r8+r15]
 mov ecx, dword ptr [r10+8]
 cmp ecx, 512
 ja part_expired
 mov r10d, dword ptr [r10+4]
 lea r11, [rip+IMAGE_BASE]
 add r10, r11
copy_word:
 mov r11w, word ptr [r10]
 mov word ptr [r8], r11w
 add r10, 2
 add r8, 2
 sub ecx, 2
 jnz copy_word
 jmp part_return
part_expired:
 mov eax, 0xffffffff
 xor edx, edx
part_return:
 {guest_return()}
 '''
 return c.assemble64(asm,rva,{'ENTRY_TABLE':metadata['entryTableRVA'],'IMAGE_BASE':0,'FADE':metadata['fadeRVA']})
