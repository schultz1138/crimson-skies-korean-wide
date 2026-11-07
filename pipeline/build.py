# SPDX-License-Identifier: MIT
"""Rebuild the five game targets and optionally the entire accepted beta ZIP."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import zlib

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
NATIVE_NAME = "xefu_2ae70168_ceb51ba7_9b9c95a0_541622e1_d1689465.dll"
MANIFEST_SHA = "f80c775038edd5673fee39362d5e82e607353ceb0ee59bfeea2776172ba4251e"
FONT_SHA = "26d0c6748500a0444844280b308f5b62c7ae92ac6c6ac88148e502dd211eb52a"
BETA1_SHA = "cfb9d6558ff0035494af8866d72cccb0e369d2c6a1549825a699f7249154c650"
VERSIONS = {"capstone": "5.0.9", "keystone-engine": "0.9.2", "pefile": "2024.8.26",
            "Pillow": "13.0.0", "fonttools": "4.68.0"}


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for part in iter(lambda: source.read(4*1024*1024), b""):
            h.update(part)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stage(name, script, arguments):
    print(json.dumps({"stage": name, "state": "starting"}), flush=True)
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")
    environment.pop("PYTHONPATH", None)
    result = subprocess.run([sys.executable, "-B", str(script), *map(str, arguments)],
                            cwd=script.parent, env=environment, capture_output=True, timeout=1200)
    if result.returncode:
        raise RuntimeError(name+": "+result.stderr.decode("utf-8", errors="replace")[-5000:]+
                           result.stdout.decode("utf-8", errors="replace")[-3000:])
    print(json.dumps({"stage": name, "state": "passed"}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-content", required=True, type=Path,
                        help="Unmodified supported build's Content folder; read only")
    parser.add_argument("--out", required=True, type=Path, help="A new, separate build output directory")
    parser.add_argument("--dependencies", required=True, type=Path,
                        help="Directory prepared by fetch_dependencies.py or matching offline files")
    parser.add_argument("--game-only", action="store_true", help="Verify five game targets without C# or ZIP packaging")
    parser.add_argument("--csc", type=Path, help="Optional .NET Framework C# compiler path")
    args = parser.parse_args()
    require(os.name == "nt" and sys.maxsize > 2**32, "Reference pipeline requires Windows x64")
    require(sys.version_info[:2] == (3, 12), "Use CPython3.12 and the hash-locked Windows wheels")
    installed = {name: importlib.metadata.version(name) for name in VERSIONS}
    require(installed == VERSIONS, "Dependency versions differ from the reference lock: "+str(installed))
    from PIL import features
    require(features.version_module("freetype2") == "2.14.3", "FreeType2.14.3 is required for the reference glyph rasters")
    original = args.input_content.resolve(strict=True)
    output = args.out.resolve()
    dependencies = args.dependencies.resolve(strict=True)
    require(not output.exists(), "Build output already exists; use a new directory")
    require(output != original and original not in output.parents and output not in original.parents,
            "Output must be separate from original game files")
    require(sha256(REPO / "manifest.json") == MANIFEST_SHA, "Supported release manifest differs")
    manifest = json.loads((REPO / "manifest.json").read_text("utf-8-sig"))
    before = {}
    for i, entry in enumerate(manifest["files"]):
        p = original / entry["path"]
        before[entry["path"]] = sha256(p)
        require(before[entry["path"]] == manifest["profiles"][0]["sha256"][i],
                "Wrong original file: "+entry["path"]+"; use an unmodified stock copy")
    font = dependencies / "NotoSansCJKkr-Bold.otf"
    require(sha256(font) == FONT_SHA, "Wrong Noto upstream font")
    output.mkdir(parents=True)
    target = output / "generated-content"
    native_work = output / "native-work"
    stage("subtitle-font-and-package-data", HERE / "assets/build.py", [
        "--input-content", original, "--output-content", target, "--font", font])
    stage("native-gpu-and-menu", HERE / "native/build.py", [
        "--input-content", original, "--output-content", target, "--work-dir", native_work,
        "--captions", HERE / "assets/localization/native_captions.json"])
    targets = {}
    for entry in manifest["files"]:
        path = target / entry["path"]
        digest = sha256(path)
        require(digest == entry["targetSha256"] and path.stat().st_size == entry["targetBytes"],
                "Generated target differs: "+entry["path"])
        targets[entry["path"]] = {"sha256": digest, "bytes": path.stat().st_size}
    beta1 = native_work / "intermediate-beta1-native" / NATIVE_NAME
    require(sha256(beta1) == BETA1_SHA, "Source-generated beta1 native base differs")
    package = None
    if not args.game_only:
        stage("installer-six-deltas-and-release-zip", HERE / "package_release.py", [
            "--repo-root", REPO, "--input-content", original, "--target-content", target,
            "--beta1-native", beta1, "--dependencies", dependencies,
            "--out", output / "distribution", *(["--csc", args.csc] if args.csc else [])])
        package = json.loads((output / "distribution/package-report.json").read_text("utf-8"))
    for name, digest in before.items():
        require(sha256(original / name) == digest, "Original file changed during the build")
    report = {"schema": "source-reproduction-v1", "status": "PASS", "targets": targets,
              "sourceGeneratedBeta1NativeSha256": BETA1_SHA,
              "originalFiveFilesByteUnchanged": True, "publishedDeltasUsedAsBuildInputs": False,
              "python": platform.python_version(), "zlib": zlib.ZLIB_RUNTIME_VERSION,
              "dependencies": installed, "freeType": features.version_module("freetype2"),
              "package": package, "endingGameplayCoverageChanged": False}
    (output / "reproduction-report.json").write_text(json.dumps(report, indent=2)+"\n", "utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
