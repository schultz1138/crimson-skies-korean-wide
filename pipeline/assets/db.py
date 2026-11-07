"""Version203 game DB codec. Untouched original records come from user input."""
import struct
def cstring(pool,p):
 end=pool.find(b'\0',p)
 if p<0 or end<0:raise ValueError('Bad DB string')
 return pool[p:end].decode('latin1')
def globals_from_bytes(b):
 count=struct.unpack_from('<I',b,4)[0];base=20+count*4
 return[cstring(b,base+struct.unpack_from('<I',b,20+4*i)[0])for i in range(count)]
def parse(b,names):
 h=list(struct.unpack_from('<15I',b));assert h[0]==203 and h[2]==len(b)-60
 pool=b[60:60+h[3]];local=[struct.unpack_from('<I',b,60+h[3]+i*4)[0]for i in range(h[7])]
 assert h[4]==h[3]+4*h[7]and h[5]==h[4]+8*h[8]and h[6]==h[5]+8*h[9]and h[6]+8*h[10]==len(b)-60
 props=[list(struct.unpack_from('<HHI',b,60+h[6]+i*8))for i in range(h[10])]
 nodes=[list(struct.unpack_from('<HHI',b,60+h[5]+i*8))for i in range(h[9])]
 roots=[list(struct.unpack_from('<4H',b,60+h[4]+i*8))for i in range(h[8])]
 return dict(header=h,pool=pool,local=local,props=props,nodes=nodes,roots=roots,names=names)
def name(d,key):return d['names'][(~key)&65535]if key&32768 else cstring(d['pool'],d['local'][key])
def write(d):
 h=d['header'][:];pool=d['pool'];local=d['local'];roots=d['roots'];nodes=d['nodes'];props=d['props']
 h[3]=len(pool);h[7]=len(local);h[8]=len(roots);h[9]=len(nodes);h[10]=len(props)
 h[4]=h[3]+4*h[7];h[5]=h[4]+8*h[8];h[6]=h[5]+8*h[9];h[2]=h[6]+8*h[10]
 return struct.pack('<15I',*h)+pool+b''.join(struct.pack('<I',x)for x in local)+b''.join(struct.pack('<4H',*x)for x in roots)+b''.join(struct.pack('<HHI',*x)for x in nodes)+b''.join(struct.pack('<HHI',*x)for x in props)
def strip_descriptions(d):
 if d['local']:raise ValueError('Script local table unexpected')
 desc=(~d['names'].index('Desc'))&65535;props=d['props'];pool=d['pool'];removed=[]
 empty=next(v for k,t,v in props if t==4 and cstring(pool,v)=='')
 for k,t,start in props:
  if k!=desc or t!=4:continue
  end=pool.find(b'\0',start)+1
  if end<=start+1 or any(start<r and end>l for l,r in removed):continue
  unsafe=any(k2!=desc and t2 in[3,4]and v2<end and v2+(12 if t2==3 else pool.find(b'\0',v2)+1-v2)>start for k2,t2,v2 in props)
  if not unsafe:removed.append((start,end))
 removed.sort()
 def remap(v):
  if any(l<=v<r for l,r in removed):raise ValueError('Live description pointer')
  return v-sum(r-l for l,r in removed if v>=r)
 pieces=[];cursor=0
 for l,r in removed:pieces.append(pool[cursor:l]);cursor=r
 pieces.append(pool[cursor:]);d['pool']=b''.join(pieces)
 for p in props:
  if p[1]in[3,4]:p[2]=remap(empty if any(l<=p[2]<r for l,r in removed)else p[2])
 return d
