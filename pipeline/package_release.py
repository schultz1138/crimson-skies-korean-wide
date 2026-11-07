# SPDX-License-Identifier: MIT
"""Re-encode all six deltas and reproduce the accepted installer ZIP from source outputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
import zlib
from installer_repro import normalize

RELEASE = "CrimsonSkies-KO-Wide-0.11.0-beta.1"
ZIP_SHA256 = "a53382986c5e78aa189a8936249d9771bed7d357019e31c8b219c904f304dc42"
MANIFEST_SHA256 = "f80c775038edd5673fee39362d5e82e607353ceb0ee59bfeea2776172ba4251e"
TOOL_SHA256 = "732980d52f9220dc81817ccdd0c295eadce8a0048a24c2a771a73f791ac824e9"
SOURCES = ["InstallerEngine.cs", "SelectionMigration.cs", "SelectionPolicy.cs", "InstallerUi.cs"]


def sha256(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(4*1024*1024), b""):
            result.update(chunk)
    return result.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def execute(command, env=None):
    result = subprocess.run([str(part) for part in command], capture_output=True,
                            env=env, timeout=300)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace")[:2000] or
                           result.stdout.decode("utf-8", errors="replace")[:2000])


def package(repo, original, target, beta1_native, dependencies, output, csc=None):
    repo, original, target, beta1_native, dependencies, output = map(
        lambda path: Path(path).resolve(), [repo, original, target, beta1_native, dependencies, output])
    require(original != output and original not in output.parents and output not in original.parents,
            "Package output must be separate from the original game folder")
    require(not output.exists(), "Use a new package output directory")
    require(sha256(repo / "manifest.json") == MANIFEST_SHA256, "Release manifest differs")
    manifest = json.loads((repo / "manifest.json").read_text("utf-8-sig"))
    expected = json.loads((Path(__file__).parent / "expected-release-files.json").read_text("utf-8"))
    tool = dependencies / "xdelta3.exe"
    require(sha256(tool) == TOOL_SHA256, "Use the pinned xdelta3 executable")
    stage = output / "stage" / RELEASE
    stage.mkdir(parents=True)
    decoded = output / "decode-verification"
    decoded.mkdir()
    env = dict(os.environ)
    env.pop("XDELTA", None)
    for i, file in enumerate(manifest["files"]):
        original_path, final_path = original / file["path"], target / file["path"]
        require(sha256(original_path) == manifest["profiles"][0]["sha256"][i], "Wrong original game file")
        require(final_path.stat().st_size == file["targetBytes"] and
                sha256(final_path) == file["targetSha256"], "Source-generated target differs")
        for j, source in enumerate(file["sources"]):
            before = beta1_native if i == 0 and j == 1 else original_path
            require(before.stat().st_size == source["sourceBytes"] and
                    sha256(before) == source["sourceSha256"], "Wrong source-generated delta base")
            delta = stage / source["delta"]
            delta.parent.mkdir(parents=True, exist_ok=True)
            execute([tool, "-e", "-9", "-A", "-D", "-s", before, final_path, delta], env)
            require(delta.stat().st_size == source["deltaBytes"] and
                    sha256(delta) == source["deltaSha256"], "Re-encoded VCDIFF differs")
            reconstructed = decoded / f"{i}-{j}.bin"
            execute([tool, "-d", "-D", "-R", "-s", before, delta, reconstructed], env)
            require(sha256(reconstructed) == file["targetSha256"], "Delta decode verification failed")
    for name in expected["files"]:
        if name == "CHECKSUMS.sha256" or name == "KoreanWidePatchInstaller.exe" or name.startswith("patches/"):
            continue
        destination = stage / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tool if name == "tools/xdelta3.exe" else repo / name, destination)
    if csc is None:
        csc = Path(os.environ.get("WINDIR", "C:/Windows")) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    csc = Path(csc)
    require(csc.is_file(), "Windows .NET Framework C# compiler is required")
    executable = stage / "KoreanWidePatchInstaller.exe"
    # The legacy compiler has classic Windows path limits. Compile our four
    # sources in a short, owned temporary directory; no game inputs go there.
    temporary_parent = Path(tempfile.gettempdir()).resolve()
    with tempfile.TemporaryDirectory(prefix="CSKO-source-", dir=temporary_parent) as temporary:
        temporary = Path(temporary).resolve()
        require(temporary.parent == temporary_parent, "Unexpected compiler temporary directory")
        for name in SOURCES:
            shutil.copyfile(repo / "source" / name, temporary / name)
        compiled = temporary / "KoreanWidePatchInstaller.exe"
        execute([csc, "/nologo", "/codepage:65001", "/target:winexe", "/optimize+",
                 "/r:System.Windows.Forms.dll", "/r:System.Drawing.dll", "/r:System.Web.Extensions.dll",
                 "/r:System.Xml.dll", "/out:"+str(compiled), *[temporary / name for name in SOURCES]])
        installer = normalize(compiled)
        shutil.copyfile(compiled, executable)
    names = set(expected["files"])
    checksum_text = "".join(sha256(stage / name)+"  "+name+"\n" for name in sorted(names-{"CHECKSUMS.sha256"}))
    (stage / "CHECKSUMS.sha256").write_text(checksum_text, encoding="utf-8", newline="\n")
    actual_names = {p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()}
    require(actual_names == names and len(names) == 28, "Unexpected package inventory")
    for name, digest in expected["files"].items():
        require(sha256(stage / name) == digest, "Release member differs: " + name)
    archive = output / (RELEASE+".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
        for name in sorted(names):
            info = zipfile.ZipInfo(RELEASE+"/"+name, date_time=(2026, 11, 7, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            zipped.writestr(info, (stage / name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = sha256(archive)
    require(digest == ZIP_SHA256, "ZIP bytes differ; check reference Python/zlib toolchain: " + zlib.ZLIB_RUNTIME_VERSION)
    archive.with_name(archive.name+".sha256").write_text(digest+"  "+archive.name+"\n", "ascii")
    report = {"status": "PASS", "files": len(names), "regeneratedDeltas": 6,
              "allReleaseMembersByteExact": True, "archiveSha256": digest,
              "archiveBytes": archive.stat().st_size, "installer": installer,
              "python": sys.version.split()[0], "zlib": zlib.ZLIB_RUNTIME_VERSION,
              "inputPublishedDeltasUsed": False, "gameOrSettingsModified": False}
    # Keep build-specific random input identities local; the normalized output is public.
    (output / "package-report.json").write_text(json.dumps(report, indent=2)+"\n", "utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--input-content", type=Path, required=True)
    parser.add_argument("--target-content", type=Path, required=True)
    parser.add_argument("--beta1-native", type=Path, required=True)
    parser.add_argument("--dependencies", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--csc", type=Path)
    args = parser.parse_args()
    print(json.dumps(package(args.repo_root, args.input_content, args.target_content,
                             args.beta1_native, args.dependencies, args.out, args.csc), indent=2))
