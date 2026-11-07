# SPDX-License-Identifier: MIT
"""Strict declarative locale-pack validation. No pack code is imported/executed."""
from pathlib import Path,PurePosixPath
import collections,json,re,unicodedata
MAX_JSON=4*1024*1024
ID=re.compile(r'^[a-z]{2,3}(?:-[A-Z][a-z]{3})?(?:-[A-Z]{2}|-[0-9]{3})?$')
FONT='noto-cjk-kr-bold-2.004'

def pairs(items):
 out={}
 for k,v in items:
  if k in out:raise ValueError('Duplicate JSON key: '+str(k))
  out[k]=v
 return out

def read_json(path,limit=MAX_JSON):
 p=Path(path)
 if p.stat().st_size>limit:raise ValueError('JSON exceeds size boundary')
 def reject_constant(x):raise ValueError('Nonfinite JSON number: '+x)
 return json.loads(p.read_text('utf-8'),object_pairs_hook=pairs,parse_constant=reject_constant)

def fields(obj,required,optional=()):
 if not isinstance(obj,dict)or set(obj)-set(required)-set(optional)or set(required)-set(obj):raise ValueError('Unexpected/missing fields; expected '+str(required))

def text(value,native=False,label='text'):
 if not isinstance(value,str)or not value or len(value.encode('utf-16le',errors='surrogatepass'))>510:raise ValueError(label+': expected nonempty text of at most255 UTF16 units')
 if unicodedata.normalize('NFC',value)!=value:raise ValueError(label+': use NFC text')
 for c in value:
  cp=ord(c);cat=unicodedata.category(c)
  if cp>65535 or 0xd800<=cp<=0xdfff or cat in['Cc','Cf','Cs','Co','Cn']and not(native and c=='\n')or unicodedata.combining(c)or unicodedata.bidirectional(c)in['R','AL','AN']:
   raise ValueError(label+': unsupported codepoint U+%04X'%cp)
 if not native and any(c in value for c in['"','\r','\n','\\']):raise ValueError(label+': quotes, CR/LF and backslashes are not accepted by this Unicode-table serializer')
 if native and(value.count('\n')>1 or any(not line.strip()for line in value.split('\n'))):raise ValueError(label+': use one or two nonempty caption lines')
 return value

def local_file(root,name):
 if not isinstance(name,str)or '\\'in name or ':'in name:raise ValueError('Pack paths must be relative POSIX filenames')
 pure=PurePosixPath(name)
 if pure.is_absolute()or not pure.parts or any(p in['.','..']for p in pure.parts)or str(pure)!=name:raise ValueError('Unsafe pack path')
 p=(root/name).resolve()
 if not p.is_relative_to(root.resolve())or not p.is_file():raise ValueError('Pack path escapes its root or is absent')
 return p

def load_pack(path):
 path=Path(path).resolve();p=read_json(path,65536)
 fields(p,['schema','id','displayName','version','base','status','overlays','font'])
 if type(p['schema'])is not int or p['schema']!=1 or not isinstance(p['id'],str)or not ID.fullmatch(p['id']):raise ValueError('Unsupported pack schema/id')
 if not isinstance(p['displayName'],str)or not 1<=len(p['displayName'])<=64 or p['displayName']!=p['displayName'].strip()or not p['displayName'].strip()or unicodedata.normalize('NFC',p['displayName'])!=p['displayName']or any(unicodedata.category(c)[0]=='C'for c in p['displayName']):raise ValueError('Invalid display name')
 if not isinstance(p['version'],str)or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.]+)?',p['version']):raise ValueError('Invalid pack version')
 if p['base']!='ko-KR'or p['status']not in['baseline','partial','complete']:raise ValueError('Unsupported fallback/status')
 if p['id']=='ko-KR'and p['status']!='baseline'or p['id']!='ko-KR'and p['status']=='baseline':raise ValueError('Only ko-KR is the canonical baseline')
 if not isinstance(p['overlays'],list)or len(p['overlays'])>8 or any(not isinstance(x,str)for x in p['overlays'])or len(set(p['overlays']))!=len(p['overlays']):raise ValueError('Expected at most8 distinct overlay files')
 fields(p['font'],['source','extraCodepoints'])
 if p['font']['source']!=FONT or not isinstance(p['font']['extraCodepoints'],list):raise ValueError('Unsupported font source')
 cps=p['font']['extraCodepoints']
 if len(cps)>4096 or any(type(x)is not int or not 32<=x<65536 for x in cps)or len(set(cps))!=len(cps):raise ValueError('Invalid extra codepoints')
 for cp in cps:text(chr(cp),True,'extraCodepoints')
 overlays={'nativeCaptions':{},'strings':{}}
 for name in p['overlays']:
  value=read_json(local_file(path.parent,name));fields(value,['schema','nativeCaptions','strings'])
  if type(value['schema'])is not int or value['schema']!=1:raise ValueError('Unsupported overlay schema')
  for kind in overlays:
   if not isinstance(value[kind],dict):raise ValueError('Overlay namespace must be an object')
   for key,new in value[kind].items():
    if not isinstance(key,str)or not key or len(key)>512:raise ValueError('Invalid translation key')
    if key in overlays[kind]:raise ValueError('Duplicate translation across overlays: '+key)
    overlays[kind][key]=text(new,kind=='nativeCaptions',key)
 if p['id']=='ko-KR'and(any(overlays[k]for k in overlays)or cps):raise ValueError('Canonical ko-KR must have no overrides')
 return p,overlays

def registry(directory):
 result=[];ids=set();labels=set()
 for path in sorted(Path(directory).glob('*/locale.json')):
  p,_=load_pack(path);key=p['id'].casefold();label=p['displayName'].casefold()
  if key in ids or label in labels:raise ValueError('Locale ID/display-name collision')
  ids.add(key);labels.add(label);result.append(dict(id=p['id'],displayName=p['displayName'],status=p['status'],manifest=path.relative_to(directory).as_posix()))
 return result

FORMAT=re.compile(r'%(?:[0-9]+\$)?[-+ #0]*(?:[0-9]+|\*)?(?:\.(?:[0-9]+|\*))?[hlL]?[diuoxXfFeEgGaAcspn%]|\{[0-9]+(?:[^{}]*)\}|~\[[^\]\r\n]+\]')
def preserve_format(original,translated,key):
 if FORMAT.findall(original)!=FORMAT.findall(translated):raise ValueError('Formatting tokens changed: '+key)