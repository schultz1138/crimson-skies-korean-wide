# SPDX-License-Identifier: MIT
"""Fetch two pinned upstream build inputs. Python wheels use the separate hash lock."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.request
import zipfile

FONT = {
    "name": "NotoSansCJKkr-Bold.otf",
    "url": "https://raw.githubusercontent.com/notofonts/noto-cjk/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Sans/OTF/Korean/NotoSansCJKkr-Bold.otf",
    "sha256": "26d0c6748500a0444844280b308f5b62c7ae92ac6c6ac88148e502dd211eb52a",
    "maxBytes": 32 * 1024 * 1024,
}
XDELTA = {
    "name": "xdelta3-3.2.2-windows-x86_64.zip",
    "url": "https://github.com/jmacd/xdelta/releases/download/v3.2.2/xdelta3-3.2.2-windows-x86_64.zip",
    "sha256": "d48f7651d86b78fdca397057b46601f89131f37219675df736db70af44ec3379",
    "maxBytes": 4 * 1024 * 1024,
}
XDELTA_MEMBER = "xdelta3-3.2.2-windows-x86_64/xdelta3.exe"
XDELTA_SHA256 = "732980d52f9220dc81817ccdd0c295eadce8a0048a24c2a771a73f791ac824e9"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fetch_one(spec, directory):
    destination = directory / spec["name"]
    if destination.exists():
        if sha256(destination) != spec["sha256"]:
            raise ValueError("Existing dependency hash differs: " + spec["name"])
        return destination
    request = urllib.request.Request(spec["url"], headers={"User-Agent": "CrimsonSkies-Source-Reproduction/1"})
    descriptor, temporary = tempfile.mkstemp(prefix=".download-", dir=directory)
    temporary = Path(temporary)
    try:
        total = 0
        with os.fdopen(descriptor, "wb") as output, urllib.request.urlopen(request, timeout=60) as response:
            while True:
                data = response.read(1024 * 1024)
                if not data:
                    break
                total += len(data)
                if total > spec["maxBytes"]:
                    raise ValueError("Dependency exceeds expected size boundary")
                output.write(data)
        if sha256(temporary) != spec["sha256"]:
            raise ValueError("Upstream dependency hash differs: " + spec["name"])
        temporary.replace(destination)
        return destination
    finally:
        if temporary.exists():
            temporary.unlink()


def fetch_all(directory):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    font = fetch_one(FONT, directory)
    archive = fetch_one(XDELTA, directory)
    executable = directory / "xdelta3.exe"
    with zipfile.ZipFile(archive) as zipped:
        info = zipped.getinfo(XDELTA_MEMBER)
        if info.file_size != 340992:
            raise ValueError("Unexpected xdelta executable size")
        data = zipped.read(info)
    if hashlib.sha256(data).hexdigest() != XDELTA_SHA256:
        raise ValueError("Unexpected executable in upstream archive")
    if executable.exists():
        if sha256(executable) != XDELTA_SHA256:
            raise ValueError("Existing xdelta executable differs")
    else:
        with executable.open("xb") as output:
            output.write(data)
    report = {"font": {"file": font.name, "sha256": FONT["sha256"], "url": FONT["url"]},
              "xdeltaArchive": {"file": archive.name, "sha256": XDELTA["sha256"], "url": XDELTA["url"]},
              "xdeltaExecutable": {"file": executable.name, "sha256": XDELTA_SHA256}}
    (directory / "upstream-inputs.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(fetch_all(args.out), indent=2))
