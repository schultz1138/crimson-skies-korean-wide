"""Generate the launcher JSON from the editable resolution preset contract."""
import json,hashlib
def generate_menu(stock,contract_path):
 assert hashlib.sha256(stock).hexdigest()=='82cf420a22fd50455e04b92879e7c3137ef085ab9a2c373640b11897dfd12096'
 menu=json.loads(stock);before=json.loads(stock)
 rows=sorted(json.loads(contract_path.read_text('utf8'))['presets'],key=lambda p:(p['width']*p['height'],p['width']))
 def label(p):
  common={7:'720p',9:'1080p',10:'1440p',11:'4K'}
  return f"{p['width']}×{p['height']} ({common[p['id']]}, {p['aspect']})"if p['id']in common else p['label']
 item=dict(Id='scaling',Label='렌더링 해상도',Description='선택한 해상도에 맞춰 화면 비율을 자동으로 조정합니다. 변경 사항은 다음 실행부터 적용됩니다.',Icon='monitor',Type='dropdown',
  Options=[label(p)for p in rows],ArgValues=[f"-scaling {p['integerScale']}@cs{p['id']}"for p in rows],Default='1280×960 (4:3)',LaunchOnly=True,LiveUpdate=False,IsLaunchArgument=True,Enabled=True,DynamicOptions='cs-resolution-presets-v1')
 menu['Categories'].append(dict(Id='graphics',Label='Graphics',Items=[item]))
 assert menu['Categories'][:-1]==before['Categories']
 return (json.dumps(menu,ensure_ascii=False,indent=2)+'\n').encode('utf8')
