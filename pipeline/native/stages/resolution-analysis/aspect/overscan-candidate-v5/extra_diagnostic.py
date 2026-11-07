"""V4 logger for sites8/9; extra telemetry stays in separate existing RW tail."""
from pathlib import Path
import importlib.util,re
P=Path(__file__).resolve().parent.parent/'overscan-candidate-v4/diagnostic_pre.py'
S=importlib.util.spec_from_file_location('immutable_v4_diagnostic_source',P);BASE=importlib.util.module_from_spec(S);S.loader.exec_module(BASE)
REASONS=BASE.REASONS;FIELDS=BASE.FIELDS;full_guest32=BASE.full_guest32

def decorate(body,site,direct):
 assert site in (8,9) and direct
 # The prologue's successful source-owned slot scan guarantees R10=state+
 # index*0x500 for index0..7. Compute that index after64-bit subtraction,
 # then use32-bit DIV by the fixed nonzero0x500, without a host call.
 out=['lea rdi,[rip]','mov rax,r10','sub rax,rdi','xor edx,edx','mov ecx,0x500','div ecx','shl eax,6',
  f'lea rdi,[rdi+rax+{0x2800+(site-8)*24}]','inc dword ptr [rdi]','mov eax,[r10+4]','test eax,eax','jne diagnostic_eligible',
  'lea r11,[r10+0x4e8]',f'mov dword ptr [r11],{site}','mov eax,[r10+8]','mov [r11+4],eax',
  'mov dword ptr [r11+8],0','mov dword ptr [r11+12],0','test eax,eax','je diagnostic_zero_top_done','cmp eax,16','ja diagnostic_zero_top_done','dec eax',
  'lea rdx,[r10+rax*8+0x40]','mov ecx,[rdx]','mov [r11+8],ecx','mov ecx,[rdx+4]','mov [r11+12],ecx','diagnostic_zero_top_done:',
  'mov [r11+16],r14d','mov eax,[r10+12]','mov [r11+20],eax','jmp diagnostic_entered','diagnostic_eligible:',
  'inc dword ptr [rdi+4]','mov [rdi+16],r14d','mov dword ptr [rdi+12],1','mov [rdi+20],eax','diagnostic_entered:']
 def reason(n,value):return [f'mov dword ptr [rdi+12],{n}',f'mov [rdi+20],{value}']
 for s in body:
  if s=='cmp eax,2':out+=reason(2,'eax')+[s]
  elif s=='cmp r14,rax':out+=['mov dword ptr [rdi+12],14','mov rdx,r14','shr rdx,32','mov [rdi+20],edx',s]
  elif s=='cmp r14d,0x10000':out+=reason(3,'r14d')+[s]
  elif s=='cmp r14d,0xffffff00':out+=reason(4,'r14d')+[s]
  elif re.fullmatch(r'cmp dword ptr \[r15\+r14(?:\+(?:4|12))?\],(?:4|6|7|28|36)',s):
   memory,expected=s[len('cmp dword ptr '):].split(',');n=6 if '+4]'in memory else 7 if '+12]'in memory else 5
   out+=['mov eax,dword ptr '+memory]+reason(n,'eax')+['cmp eax,'+expected]
  elif s=='cmp rdx,rcx':out+=reason(8,'edx')+[s]
  elif s in ['cmp edx,0xffffff80','cmp edx,0xffffff60']:out+=reason(9,'edx')+[s]
  elif re.fullmatch(r'mov \[rbx\+(?:16|20|24|28)\],eax',s):out+=[s]+reason(10,'eax')
  elif re.fullmatch(r'mov \[rbx\+(?:32|36|40|44)\],eax',s):out+=[s]+reason(11,'eax')
  elif s=='mov dword ptr [rbx+4],1':out+=[s,'inc dword ptr [rdi+8]','mov dword ptr [rdi+12],12','mov dword ptr [rdi+20],0']
  elif s=='overflow:':out+=[s,'cmp dword ptr [r10+4],0','je diagnostic_overflow_logged','mov dword ptr [rdi+12],13','mov eax,[r10+16]','mov [rdi+20],eax','diagnostic_overflow_logged:']
  else:out.append(s)
 assert ('cmp eax,36'in out) == (site==8)
 assert out.count('inc dword ptr [rdi+8]')==1
 return out
