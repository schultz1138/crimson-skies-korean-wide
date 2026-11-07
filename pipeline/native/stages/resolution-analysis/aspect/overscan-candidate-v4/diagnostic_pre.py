"""V3 telemetry with explicitly zero-extended full guest32 stack admission."""
import re
REASONS={1:'eligible entry',2:'mode greater than2',3:'guestESP below10000',4:'guestESP aboveffffff00',5:'primitive mismatch',6:'count mismatch',7:'stride mismatch',8:'vertex pointer not ESP+delta',9:'vertex pointer upper bound',10:'X finite/range',11:'Y finite/range',12:'accepted',13:'paired quad stack overflow',14:'guestESP has nonzero upper32'}
FIELDS=['calls','eligibleCalls','acceptedCalls','lastEligibleReason','lastEligibleGuestEspLow32','lastComparedValue']

def full_guest32(body):
 assert body.count('cmp r14,0x10000')==body.count('cmp r14,0x7fffff00')==1
 out=[]
 for s in body:
  if s=='cmp r14,0x10000':out+=['mov eax,r14d','cmp r14,rax','jne done','cmp r14d,0x10000']
  elif s=='cmp r14,0x7fffff00':out+=['cmp r14d,0xffffff00']
  elif s=='cmp rdx,0x7fffff80':out+=['cmp edx,0xffffff80']
  elif s=='cmp rdx,0x7fffff60':out+=['cmp edx,0xffffff60']
  else:out.append(s)
 assert not any(s.startswith('cmp r14,0x')or s.startswith('cmp rdx,0x')for s in out)
 return out

def decorate(body,site,direct):
 out=[f'lea rdi,[r10+{0x440+(site-1)*24}]','inc dword ptr [rdi]','mov eax,[r10+4]','test eax,eax','jne diagnostic_eligible',
  'lea r11,[r10+0x4e8]',f'mov dword ptr [r11],{site}','mov eax,[r10+8]','mov [r11+4],eax',
  'mov dword ptr [r11+8],0','mov dword ptr [r11+12],0','test eax,eax','je diagnostic_zero_top_done','cmp eax,16','ja diagnostic_zero_top_done','dec eax',
  'lea rdx,[r10+rax*8+0x40]','mov ecx,[rdx]','mov [r11+8],ecx','mov ecx,[rdx+4]','mov [r11+12],ecx','diagnostic_zero_top_done:',
  'mov [r11+16],r14d','mov eax,[r10+12]','mov [r11+20],eax','jmp diagnostic_entered','diagnostic_eligible:',
  'inc dword ptr [rdi+4]','mov [rdi+16],r14d','mov dword ptr [rdi+12],1','mov [rdi+20],eax','diagnostic_entered:']
 def reason(number,value):return [f'mov dword ptr [rdi+12],{number}',f'mov [rdi+20],{value}']
 for s in body:
  if s=='cmp eax,2':out+=reason(2,'eax')+[s]
  elif s=='cmp r14,rax':out+=['mov dword ptr [rdi+12],14','mov rdx,r14','shr rdx,32','mov [rdi+20],edx',s]
  elif s=='cmp r14d,0x10000':out+=reason(3,'r14d')+[s]
  elif s=='cmp r14d,0xffffff00':out+=reason(4,'r14d')+[s]
  elif re.fullmatch(r'cmp dword ptr \[r15\+r14(?:\+(?:4|12))?\],(?:4|6|7|28)',s):
   memory,expected=s[len('cmp dword ptr '):].split(',');number=6 if '+4]'in memory else 7 if '+12]'in memory else 5
   out+=['mov eax,dword ptr '+memory]+reason(number,'eax')+['cmp eax,'+expected]
  elif s=='cmp rdx,rcx':out+=reason(8,'edx')+[s]
  elif s in ['cmp edx,0xffffff80','cmp edx,0xffffff60']:out+=reason(9,'edx')+[s]
  elif re.fullmatch(r'mov \[rbx\+(?:16|20|24|28)\],eax',s):out+=[s]+reason(10,'eax')
  elif re.fullmatch(r'mov \[rbx\+(?:32|36|40|44)\],eax',s):out+=[s]+reason(11,'eax')
  elif s=='mov dword ptr [rbx+4],1':out+=[s,'inc dword ptr [rdi+8]','mov dword ptr [rdi+12],12','mov dword ptr [rdi+20],0']
  elif s=='overflow:':out += [s,'cmp dword ptr [r10+4],0','je diagnostic_overflow_logged','mov dword ptr [rdi+12],13','mov eax,[r10+16]','mov [rdi+20],eax','diagnostic_overflow_logged:']
  else:out.append(s)
 assert out.count('inc dword ptr [rdi+8]')==1
 return out
