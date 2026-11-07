# SPDX-License-Identifier: MIT
"""Print validated source-pack identities; no game files are read."""
from pathlib import Path
import argparse,json
from validation import registry
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packs',type=Path,default=Path(__file__).resolve().parent/'locales');a=p.parse_args();print(json.dumps(dict(schema=1,locales=registry(a.packs)),ensure_ascii=False,indent=2))