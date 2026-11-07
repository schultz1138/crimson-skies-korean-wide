"""Read user-owned SVOD files and write new copies. No installed path defaults."""
from pathlib import Path
import struct,hashlib
STOCK={'Data0000':'ecbaddb51756283208012ee6da904c50f96c8cbc73c55ea5a56fdab5304f3c7d','Data0005':'2d1a1d974179abd5b0feaf444e486d1c6b4e29e7ff13afa120c4881700323069'}
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def locate(offset):
 block,within=divmod(offset,4096);fi,w=divmod(block,41412);group,slot=divmod(w,204)
 return f'Data{fi:04}',(2+group*205+slot)*4096+within,within
class Package:
 def __init__(self,content,verify=True):
  self.content=Path(content).resolve();self.folder=self.content/'Game/DefaultPackage.data';self.handles={}
  if verify:
   for name,sha in STOCK.items():
    path=self.folder/name
    if path.stat().st_size!=170459136 or digest(path)!=sha:raise ValueError('Unsupported original '+name)
  vd=self.read(0,2048)
  if vd[:20]!=b'MICROSOFT*XBOX*MEDIA':raise ValueError('Not the supported XDVDFS volume')
  sector,size=struct.unpack_from('<II',vd,20);self.root_start=(sector-32)*2048;raw=self.read(self.root_start,size);todo=[0];seen=set();self.entries=[]
  while todo:
   p=todo.pop()
   if p in seen or p<0 or p+14>len(raw):raise ValueError('Invalid root directory tree')
   seen.add(p);left,right,sector,size,attr,n=struct.unpack_from('<HHIIBB',raw,p)
   if not n or p+14+n>len(raw):raise ValueError('Invalid filename')
   name=raw[p+14:p+14+n].decode('ascii')
   self.entries.append(dict(name=name,sector=sector,size=size,directory=bool(attr&16),sizeField=self.root_start+p+8))
   todo.extend(v*4 for v in[left,right]if v)
 def read(self,offset,length):
  if offset<0 or length<0:raise ValueError('Negative source range')
  out=bytearray()
  while len(out)<length:
   name,physical,within=locate(offset+len(out))
   if name not in STOCK:raise ValueError('Build requires unsupported data volume '+name)
   if name not in self.handles:self.handles[name]=(self.folder/name).open('rb')
   f=self.handles[name];f.seek(physical);take=min(length-len(out),4096-within);b=f.read(take)
   if len(b)!=take:raise ValueError('Short source read')
   out+=b
  return bytes(out)
 def entry(self,name):
  found=[e for e in self.entries if e['name'].lower()==name.lower()and not e['directory']]
  if len(found)!=1:raise ValueError('Expected one root file '+name)
  return found[0]
 def file(self,name):
  e=self.entry(name);return self.read((e['sector']-32)*2048,e['size'])
 def close(self):
  for f in self.handles.values():f.close()
  self.handles.clear()
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
def extract_owned_file(content,name):
 with Package(content)as package:return package.file(name)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input-content',required=True);p.add_argument('--extract',required=True,choices=['default.xbe','ConfigNames.bin','data.zip','fonts.zip']);p.add_argument('--out',required=True);a=p.parse_args()
 out=Path(a.out).resolve()
 if out.exists():raise SystemExit('Refusing to overwrite extraction output')
 source=Path(a.input_content).resolve()
 if out.is_relative_to(source):raise SystemExit('Extraction output must be outside source Content')
 out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(extract_owned_file(source,a.extract));print(str(out))
