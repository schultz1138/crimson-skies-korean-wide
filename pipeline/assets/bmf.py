"""Offline TN/BMF v2 codec reconstructed from the user's native XFONT paths.

No game writes. Existing glyph records are preserved byte-for-byte when rebuilt.
"""
from pathlib import Path
import struct,hashlib,json,zlib,binascii

sha=lambda b:hashlib.sha256(b).hexdigest()
class BMF:
 def __init__(self,data):
  self.data=data
  if data[:4]!=b'TN\x02\0':raise ValueError('Unsupported font')
  self.n,self.range_count=struct.unpack_from('<HH',data,4)
  self.fallback=struct.unpack_from('<H',data,8)[0]
  self.height,self.descent,self.aa_bits,self.run_bits=struct.unpack_from('<4B',data,10)
  self.offsets=list(struct.unpack_from('<'+'I'*self.n,data,16))
  if self.offsets[-1]!=len(data):raise ValueError('Sentinel')
  if any(a>b for a,b in zip(self.offsets,self.offsets[1:])):raise ValueError('Offsets not ordered')
  self.range_at=16+self.n*4;self.bitmap_at=self.range_at+self.range_count*6
  self.ranges=[struct.unpack_from('<3H',data,self.range_at+i*6) for i in range(self.range_count)]
  self.index={}
  for start,count,at in self.ranges:
   for delta in range(count):
    gi,bits=struct.unpack_from('<HH',data,self.bitmap_at+(at+delta)*4)
    for bit in range(16):
     if bits&(1<<bit):
      cp=((start+delta)<<4)|bit
      if cp in self.index or gi>=self.n-1:raise ValueError('Bad cmap')
      self.index[cp]=gi;gi+=1
  self.records={cp:data[self.offsets[gi]:self.offsets[gi+1]] for cp,gi in self.index.items()}
  if len(self.records)!=self.n-1:raise ValueError('Unmapped glyph records')
 def decode(self,record):return decode(record,self.run_bits,self.aa_bits)
 def rebuild(self,records):
  cps=sorted(records);blocks={}
  for gi,cp in enumerate(cps):
   block,bit=divmod(cp,16)
   if block not in blocks:blocks[block]=[gi,0]
   blocks[block][1]|=1<<bit
  blockkeys=sorted(blocks);ranges=[]
  for at,block in enumerate(blockkeys):
   if ranges and block==ranges[-1][0]+ranges[-1][1]:ranges[-1][1]+=1
   else:ranges.append([block,1,at])
  if len(cps)+1>65535 or len(ranges)>65535:raise ValueError('16-bit font table overflow')
  table_at=16+(len(cps)+1)*4+len(ranges)*6+len(blockkeys)*4
  offsets=[table_at]
  for cp in cps:offsets.append(offsets[-1]+len(records[cp]))
  if offsets[-1]>0xffffffff:raise ValueError('32-bit offset overflow')
  header=bytearray(self.data[:16]);struct.pack_into('<HH',header,4,len(cps)+1,len(ranges))
  return bytes(header)+struct.pack('<'+'I'*len(offsets),*offsets)+b''.join(struct.pack('<3H',*r) for r in ranges)+b''.join(struct.pack('<HH',*blocks[b]) for b in blockkeys)+b''.join(records[cp] for cp in cps)

def decode(record,run_bits=4,aa_bits=2):
 if len(record)<5:raise ValueError('Short glyph')
 h,w,advance,bx,by=struct.unpack_from('<BBBbb',record)
 total=h*w;raw=record[5:];pos=0;pixels=[];state=0;tokens=0
 def take(n):
  nonlocal pos
  if pos+n>len(raw)*8:raise ValueError('Truncated glyph stream')
  out=0
  for bit in range(n):out|=((raw[(pos+bit)//8]>>((pos+bit)%8))&1)<<bit
  pos+=n;return out
 while len(pixels)<total:
  tokens+=1
  if tokens>total*8+100:raise ValueError('Zero token loop')
  run=0
  while True:
   value=take(run_bits);run+=value
   if value<(1<<run_bits)-1:break
  if run==0 and aa_bits:
   alpha=take(aa_bits)
   if alpha:
    pixels.append(alpha);continue
  if len(pixels)+run>total:raise ValueError(('Run exceeds bitmap',len(pixels),run,total))
  pixels.extend([state*(1<<aa_bits)]*run)
  state^=1
 return {'height':h,'width':w,'advance':advance,'bearing_x':bx,'bearing_y':by,'pixels':pixels,'consumed_bits':pos,'stream_bits':len(raw)*8}

def encode(bitmap,run_bits=4,aa_bits=2,pad=3):
 h,w,advance,bx,by=(bitmap[k] for k in ['height','width','advance','bearing_x','bearing_y'])
 if not(0<=h<=255 and 0<=w<=255 and 0<=advance<=255 and -128<=bx<=127 and -128<=by<=127):raise ValueError('Metric range')
 pixels=bitmap['pixels'];full=1<<aa_bits
 if len(pixels)!=h*w or any(not 0<=x<=full for x in pixels):raise ValueError('Pixel range')
 bits=[];state=0;pos=0;maxrun=(1<<run_bits)-1
 def put(v,n):bits.extend((v>>b)&1 for b in range(n))
 def run(v):
  while v>=maxrun:put(maxrun,run_bits);v-=maxrun
  put(v,run_bits)
 while pos<len(pixels):
  value=pixels[pos]
  if 0<value<full:
   put(0,run_bits);put(value,aa_bits);pos+=1;continue
  target=int(value==full)
  if target!=state:
   put(0,run_bits)
   if aa_bits:put(0,aa_bits)
   state^=1;continue
  end=pos+1
  while end<len(pixels) and pixels[end]==value:end+=1
  run(end-pos);state^=1;pos=end
 raw=bytearray((len(bits)+7)//8+pad)
 for at,bit in enumerate(bits):raw[at//8]|=bit<<(at%8)
 record=struct.pack('<BBBbb',h,w,advance,bx,by)+raw
 if decode(record,run_bits,aa_bits)['pixels']!=pixels:raise ValueError('Roundtrip mismatch')
 return record
