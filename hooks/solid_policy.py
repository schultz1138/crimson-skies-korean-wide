"""Source-owned uniform screen RECT semantics, using only journaled XY."""
def full_canvas_policy(body):
 out=[];removed=0;inserted=0;i=0
 while i<len(body):
  s=body[i]
  # Only the canonical Solid12 helper requires validated savedY at legacyID0.
  # This performs4additional4B guest reads atID0; later ID0 mutation remainsX-only.
  if s=='test r9d,r9d'and i+1<len(body)and body[i+1].startswith('je skip_y_'):
   removed+=1;i+=2;continue
  out.append(s)
  if s=='skip_y_3:':
   inserted+=1
   for field,offsets,operation,bound in [
    ('minX',[16,20,24,28],'minss',0),('maxX',[16,20,24,28],'maxss',0x44200000),
    ('minY',[32,36,40,44],'minss',0),('maxY',[32,36,40,44],'maxss',0x43f00000)]:
    out.append(f'movss xmm0,[rbx+{offsets[0]}]')
    out += [f'{operation} xmm0,[rbx+{n}]'for n in offsets[1:]]
    out += ['xorps xmm7,xmm7']if bound==0 else[f'mov eax,{bound}','movd xmm7,eax']
    out += ['comiss xmm0,xmm7',('ja'if operation=='minss'else'jb')+' solid_not_full_canvas']
   out += ['mov dword ptr [rdi+12],15','mov dword ptr [rdi+20],0','jmp done','solid_not_full_canvas:']
  i+=1
 assert removed==4 and inserted==1
 assert out.index('solid_not_full_canvas:')<next(n for n,s in enumerate(out)if s.startswith('movss [rsi+'))
 return out
