"""Test the shipping host verifier with synthetic XML and optional owned snapshots.

Only the new fixture output is written. No installed game, registry, settings,
cache or save data is changed; owned XML is not copied into the report/archive.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess,sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from build import compile_setup
from release import require_new_output,sha

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--owned-manifest',type=Path,action='append',default=[])
    a=p.parse_args();out=a.out.resolve()
    require_new_output(out,[a.package.resolve(),*[p.resolve() for p in a.owned_manifest]])
    snapshots=[dict(sha256=sha(p),bytes=p.stat().st_size) for p in a.owned_manifest]
    out.mkdir(parents=True);fixture=out/'fixture';fixture.mkdir()
    shutil.copyfile(a.package/'manifest.json',fixture/'manifest.json')
    cd=out/'compile';compile_setup(fixture,cd)
    shutil.copyfile(HERE/'HostMetadataTests.cs',cd/'HostMetadataTests.cs')
    executable=fixture/'HostMetadataTests.exe'
    csc=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    command=[str(csc),'/nologo','/codepage:65001','/target:exe','/main:HostMetadataTests','/out:'+str(executable),
             *['/r:'+x for x in ['System.Core.dll','System.Windows.Forms.dll','System.Drawing.dll','System.Web.Extensions.dll','System.Xml.dll']],
             *[str(p) for p in sorted(cd.glob('*.cs'))]]
    r=subprocess.run(command,capture_output=True,timeout=60)
    if r.returncode:raise RuntimeError((r.stdout+r.stderr).decode('utf-8','replace'))
    r=subprocess.run([str(executable),str(out/'xml'),*[str(p.resolve()) for p in a.owned_manifest]],capture_output=True,timeout=60,
                     encoding='utf-8-sig',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
    (out/'results.txt').write_text(r.stdout+r.stderr,encoding='utf-8')
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    match=re.search(r'PASS_HOST_METADATA assertions=(\d+) ownedSnapshots=(\d+)',r.stdout)
    if not match:raise ValueError('Host test report missing')
    assert snapshots==[dict(sha256=sha(p),bytes=p.stat().st_size) for p in a.owned_manifest]
    report=dict(status='PASS_HOST_METADATA',assertions=int(match[1]),ownedSnapshots=int(match[2]),
                ownedInputs=snapshots,ownedInputsUnchanged=True,installedGameWrites=0,metadataDistributed=False,
                hostVerifierSha256=sha(HERE.parent/'source/HostManifest.cs'))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(r.stdout.strip())

if __name__=='__main__':main()
