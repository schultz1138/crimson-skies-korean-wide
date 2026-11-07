"""Rasterize the OFL outline source; no cached glyph images or BMF postimages."""
from pathlib import Path
import io,json,hashlib,platform
from PIL import Image,ImageFont,features
import PIL,fontTools
from fontTools.ttLib import TTFont
from bmf import BMF,encode
HERE=Path(__file__).resolve().parent
NOTO_SHA='26d0c6748500a0444844280b308f5b62c7ae92ac6c6ac88148e502dd211eb52a'
def build_fonts(stock_fonts,font_path):
 font_path=Path(font_path)
 if hashlib.sha256(font_path.read_bytes()).hexdigest()!=NOTO_SHA:raise ValueError('Wrong pinned Noto CJK KR Bold2.004 source')
 versions=dict(python=platform.python_version(),Pillow=PIL.__version__,FreeType=features.version_module('freetype2'),fontTools=fontTools.__version__,layoutEngine='BASIC')
 if(PIL.__version__,versions['FreeType'],fontTools.__version__)!=('13.0.0','2.14.3','4.68.0'):raise ValueError('Use the pinned raster stack: '+str(versions))
 tt=TTFont(font_path);cmap=tt.getBestCmap();face=ImageFont.truetype(str(font_path),17,layout_engine=ImageFont.Layout.BASIC)
 config=json.loads((HERE/'config/font_metrics.json').read_text('utf8'));base=BMF(stock_fonts['ca/res/art/fonts/impact19Normal_KO.bmf'])
 if(base.height,base.descent,base.aa_bits,base.run_bits)!=(19,4,2,4):raise ValueError('Unexpected original KO font')
 result={'ca/res/art/fonts/kradio19.bmf':stock_fonts['ca/res/art/fonts/impact19Normal.bmf']};receipts=[]
 for f in config['fonts']:
  records={}
  for g in f['glyphs']:
   cp=g['codepoint'];advance=g['advance']
   if cp not in cmap:raise ValueError('Noto lacks codepoint '+hex(cp))
   if cp==0x2588:bmp=dict(width=17,height=19,advance=17,bearing_x=0,bearing_y=15,pixels=[4]*323)
   else:
    mask,offset=face.getmask2(chr(cp),mode='L',anchor='ls');image=Image.frombytes('L',mask.size,bytes(mask));crop=image.getbbox()
    if crop is None:bmp=dict(width=0,height=0,advance=advance,bearing_x=0,bearing_y=0,pixels=[])
    else:
     image=image.crop(crop);left=offset[0]+crop[0];top=offset[1]+crop[1];width,height=image.size
     nw=min(width,max(1,advance));nh=min(height,19)
     if(nw,nh)!=(width,height):
      if 0xac00<=cp<=0xd7a3:raise ValueError('Hangul must not be squeezed')
      image=image.resize((nw,nh),Image.Resampling.LANCZOS)
     width,height=image.size;top=max(-15,min(top,4-height));left=max(0,(advance-width)//2)
     bmp=dict(width=width,height=height,advance=advance,bearing_x=left,bearing_y=-top,pixels=[min(4,(v*4+127)//255)for v in image.tobytes()])
   records[cp]=encode(bmp,4,2)
  data=base.rebuild(records);got=hashlib.sha256(data).hexdigest()
  if got!=f['sha256']or len(data)!=f['bytes']:raise ValueError('Non-deterministic font '+f['member']+':'+got)
  result[f['member']]=data;receipts.append(dict(member=f['member'],bytes=len(data),sha256=got,glyphs=len(records)))
 return result,dict(versions=versions,sourceNotoSha256=NOTO_SHA,fonts=receipts)
