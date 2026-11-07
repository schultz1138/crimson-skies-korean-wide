"""Apply readable authored DB nodes/properties; never read a postimage."""
import struct
import db
def apply_plan(source,names,plan):
 d=db.parse(source,names)
 if plan.get('stripDescriptions'):d=db.strip_descriptions(d)
 source_props=[p[:]for p in d['props']];old_nodes=[n[:]for n in d['nodes']];old_roots=[r[:]for r in d['roots']]
 added_offsets=[]
 for text in plan['appendStrings']:
  if '\0'in text or any(ord(x)>127 for x in text):raise ValueError('New DB strings must be ASCII')
  added_offsets.append(len(d['pool']));d['pool']+=text.encode('ascii')+b'\0'
 def string(ref):
  if ref['kind']=='added':p=added_offsets[ref['index']]
  elif ref['kind']=='originalProperty':
   old=source_props[ref['index']]
   if old[1]!=4:raise ValueError('String reference does not name an original string property')
   p=old[2]
  elif ref['kind']=='originalLocalName':p=d['local'][ref['index']]
  else:raise ValueError('Unsupported semantic string reference')
  if db.cstring(d['pool'],p)!=ref['text']:raise ValueError('String source mismatch')
  return p
 def key(name):
  if name in names:return(~names.index(name))&65535
  local=[db.cstring(d['pool'],x)for x in d['local']]
  if name not in local:raise ValueError('Unknown DB node/property '+name)
  return local.index(name)
 def prop(p):
  kind=p['kind'];typ={'integer':0,'float':1,'string':4}[kind]
  value=string(p['value'])if typ==4 else struct.unpack('<I',struct.pack('<f',p['value']))[0]if typ==1 else p['value']&0xffffffff
  return[key(p['name']),typ,value]
 for edit in plan['propertyEdits']:
  i=edit['index']
  if db.name(d,d['props'][i][0])!=edit['property']['name']:raise ValueError('Edited property identity mismatch')
  d['props'][i]=prop(edit['property'])
 for item in plan['appendLocalNames']:d['local'].append(string(item))
 additions=[]
 for item in plan['newNodes']:
  first=len(d['props']);ps=[prop(p)for p in item['properties']];d['props']+=ps
  additions.append([key(item['name']),first,len(ps)])
 if plan['nodePlacement']=='sortedRoot':
  for root in sorted(old_roots,key=lambda r:r[2]):
   rootname=db.name(d,root[0]);extra=[(i,n)for i,n in enumerate(additions)if plan['newNodes'][i]['root']==rootname]
   old=old_nodes[root[2]:root[2]+root[3]];merged=old+[n for i,n in extra];merged.sort(key=lambda n:db.name(d,n[0]).lower())
   root[2]=len(d.setdefault('_rebuilt',[]));root[3]=len(merged);d['_rebuilt']+=merged
  d['nodes']=d.get('_rebuilt',[]);d['roots']=old_roots
 elif plan['nodePlacement']=='afterOriginal':
  result=[];mapping={}
  for i,n in enumerate(old_nodes):
   mapping[i]=len(result);result.append(n)
   result.extend(additions[j]for j,item in enumerate(plan['newNodes'])if item['afterOriginal']==i)
  d['nodes']=result
  for r in old_roots:
   r[2]=mapping[r[2]];r[3]+=sum(1 for item in plan['newNodes']if item['root']==db.name(d,r[0]))
  d['roots']=old_roots
 else:raise ValueError('Unknown node placement')
 return db.write(d)
