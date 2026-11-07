"""Compile the editable timed caption corpus into the original AOT map ABI."""
from pathlib import Path
import sys,re,json,os
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'native-auto-caption'))
from aot_compile import AotCompiler
from scouting_data import pack_dictionary,build_lookup,build_part

def main():
 c=AotCompiler()
 services={n:c.add_service(n)for n in ['lookup','part','forward_init','forward_destroy']}
 legacy=json.loads((ROOT/'runtime-radio/native-renderer.json').read_text('utf8'))['entries']
 symbols={'QUERY_SERVICE':0x600000,'LOOKUP_SERVICE':services['lookup'],'PART_SERVICE':services['part'],
  'RADIO_DISPATCH':int(legacy['dispatch'],16),'CORE_SERVICE':0x610000,'END_SERVICE':0x620000,
  'FREESTATE_SERVICE':0x630000,'OLD_V2_INIT_FORWARD':services['forward_init'],'OLD_V2_DESTROY_FORWARD':services['forward_destroy']}
 def bound(text):
  for name,value in sorted(symbols.items(),key=lambda x:-len(x[0])):text=re.sub(r'\b'+re.escape(name)+r'\b',hex(value),text)
  return text
 for name,file,logical in [('query','query-playing-api-interfaces.asm',0x600000),('core','core.asm',0x610000),('end','end.asm',0x620000),('free_state','free-state.asm',0x630000)]:
  c.add_guest(name,bound((ROOT/'native-auto-caption'/file).read_text('utf8')),logical)
 hooks=(ROOT/'native-auto-caption/hooks.asm').read_text('utf8')
 bodies=dict(re.findall(r'^(auto_\w+):\s*\n(.*?)(?=^auto_\w+:|\Z)',hooks,re.M|re.S))
 for name,label,logical in [('update_hook','auto_update_hook',0x640000),('end_hook','auto_end_hook',0x650000),('initialize_hook','auto_initialize_hook',0x660000),('destroy_hook','auto_destroy_hook',0x670000)]:c.add_guest(name,bound(bodies[label]),logical)
 c.layout()
 entries=json.loads(Path(os.environ['CS_NATIVE_CAPTIONS']).read_text('utf8'))['entries']
 assert len(entries)==1805 and sum(len(e['parts'])for e in entries)==1901
 assert [e['basename']for e in entries]==sorted(e['basename']for e in entries)
 for e in entries:
  assert e['basename']==e['audio'].lower() and 0<e['duration']<3600
  last=-1
  for p in e['parts']:
   assert last<p['offset']<e['duration'];last=p['offset']
   assert '\0'not in p['text'] and len(p['text'].encode('utf-16le'))<=510
 data,metadata=pack_dictionary(entries,c.data_rva);c.set_data(data)
 old_init=c.original_host(int(legacy['initialize'],16));old_destroy=c.original_host(int(legacy['destroy'],16))
 c.compile({'lookup':lambda cc,rva:build_lookup(cc,rva,metadata),
  'part':lambda cc,rva:build_part(cc,rva,metadata,allow_delayed_start=True),
  'forward_init':lambda cc,rva:cc.assemble64(f'jmp {cc.image_base+old_init:#x}',rva),
  'forward_destroy':lambda cc,rva:cc.assemble64(f'jmp {cc.image_base+old_destroy:#x}',rva)})
 for va,span,name in [(0xddef0,3,'update_hook'),(0xdd9e0,4,'end_hook'),(0xdd5a0,8,'initialize_hook'),(0xddbb0,8,'destroy_hook')]:c.add_hook(va,span,name,next((h['after']for h in c.baseM['hooks']if h['guestVA']==va),None))
 m=c.finish(ROOT/'native-host-v5')
 print(json.dumps({'stage':'captions','sha256':m['patchedSha256'],'bytes':m['patchedBytes']}))
if __name__=='__main__':main()
