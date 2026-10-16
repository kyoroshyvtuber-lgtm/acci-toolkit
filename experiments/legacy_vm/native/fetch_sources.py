#!/usr/bin/env python3
"""Download pinned open-source archives, without executing their contents."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.request


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def fetch(lock, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for source in json.loads(Path(lock).read_text())["sources"]:
        path = destination / source["filename"]
        if path.is_file() and digest(path) == source["sha256"]:
            print("verified cached", source["name"])
            continue
        temporary = path.with_suffix(path.suffix + ".partial")
        try:
            request = urllib.request.Request(source["url"], headers={"User-Agent": "ACCI-source-fetch/0.1"})
            total = 0
            with urllib.request.urlopen(request, timeout=120) as r, temporary.open("wb") as w:
                while chunk := r.read(1024 * 1024):
                    total += len(chunk)
                    if total > 128 * 1024 * 1024:
                        raise ValueError("source archive exceeds download limit")
                    w.write(chunk)
            if digest(temporary) != source["sha256"]:
                raise ValueError("source checksum mismatch: " + source["name"])
            os.replace(temporary, path)
            print("downloaded and verified", source["name"])
        finally:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("lock")
    p.add_argument("destination")
    a = p.parse_args()
    fetch(a.lock, a.destination)