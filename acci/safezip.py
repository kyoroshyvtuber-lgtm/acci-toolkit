"""Safe ZIP inspection and extraction.

Rejects absolute paths/drive letters, `..` traversal, symlinks, special files, encrypted
members, duplicate entries, too many members, oversized members/totals, suspicious
compression ratios (zip bombs), data exceeding declared sizes and CRC errors.
Never creates symlinks, never applies setuid/setgid bits, never writes outside dest.
"""
from __future__ import annotations

import hashlib
import os
import stat
import zipfile
from pathlib import Path

LIMITS = {
    "max_members": 20_000,
    "max_total_bytes": 2 * 1024**3,
    "max_member_bytes": 512 * 1024**2,
    "max_ratio": 200,
    "max_path_len": 400,
    "max_depth": 40,
}
NESTED = (".zip", ".jar", ".apk", ".aab", ".ipa", ".tar", ".gz", ".tgz", ".7z", ".rar", ".xz", ".bz2")


class UnsafeArchive(Exception):
    def __init__(self, report: dict):
        super().__init__("unsafe archive: " + "; ".join(report.get("problems", [])[:8]))
        self.report = report


def _norm(name: str) -> str:
    return name.replace("\\", "/")


def _mode(info: zipfile.ZipInfo) -> int:
    return (info.external_attr >> 16) & 0xFFFF


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def member_problems(info: zipfile.ZipInfo, limits: dict = LIMITS) -> list[str]:
    name = _norm(info.filename)
    parts = [p for p in name.split("/") if p not in ("", ".")]
    mode = _mode(info)
    fmt = stat.S_IFMT(mode)
    checks = [
        (not parts, "empty name"),
        (name.startswith("/") or (len(name) > 1 and name[1] == ":"), "absolute path"),
        (".." in parts, "path traversal"),
        ("\x00" in name, "NUL byte in name"),
        (len(name) > limits["max_path_len"], "path too long"),
        (len(parts) > limits["max_depth"], "path too deep"),
        (stat.S_ISLNK(mode), "symlink"),
        (bool(fmt) and fmt not in (stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK), "special file"),
        (bool(info.flag_bits & 0x1), "encrypted member"),
        (info.file_size > limits["max_member_bytes"], f"member too large ({info.file_size} bytes)"),
        (info.file_size > 1024**2 and info.file_size > limits["max_ratio"] * max(info.compress_size, 1),
         "suspicious compression ratio (zip bomb?)"),
    ]
    return [f"{info.filename!r}: {msg}" for bad, msg in checks if bad]


def inspect(zip_path, limits: dict = LIMITS) -> dict:
    p = Path(zip_path)
    rep = {"archive": str(p), "ok": False, "problems": [], "warnings": []}
    if not p.is_file():
        rep["problems"].append("file not found or not a regular file")
        return rep
    rep["size"] = p.stat().st_size
    rep["sha256"] = sha256_file(p)
    if not zipfile.is_zipfile(p):
        rep["problems"].append("not a ZIP archive")
        return rep
    try:
        zf = zipfile.ZipFile(p)
    except (zipfile.BadZipFile, OSError, ValueError) as e:
        rep["problems"].append(f"corrupt ZIP: {e}")
        return rep
    with zf:
        infos = zf.infolist()
        rep["members"] = len(infos)
        if len(infos) > limits["max_members"]:
            rep["problems"].append(f"too many members ({len(infos)})")
        total = files = dirs = 0
        exact, folded, tops, nested = set(), {}, set(), []
        for info in infos:
            rep["problems"].extend(member_problems(info, limits))
            if _mode(info) & (stat.S_ISUID | stat.S_ISGID):
                rep["warnings"].append(f"{info.filename!r}: setuid/setgid bit will be dropped")
            raw = _norm(info.filename).lstrip("/")
            name = raw.rstrip("/")
            if name in exact:
                rep["problems"].append(f"{info.filename!r}: duplicate entry")
            exact.add(name)
            if folded.setdefault(name.lower(), name) != name:
                rep["warnings"].append(f"{info.filename!r}: case-insensitive collision with {folded[name.lower()]!r}")
            total += info.file_size
            if info.is_dir():
                dirs += 1
            else:
                files += 1
                if name.lower().endswith(NESTED):
                    nested.append(name)
            tops.add(raw.split("/")[0] if "/" in raw else "")
        rep.update(files=files, dirs=dirs, total_uncompressed=total, nested_archives=nested[:50])
        rep["single_root"] = next(iter(tops)) if len(tops) == 1 and "" not in tops else None
        if total > limits["max_total_bytes"]:
            rep["problems"].append(f"total uncompressed size too large ({total} bytes)")
        if not rep["problems"]:
            try:
                bad = zf.testzip()
            except Exception as e:  # noqa: BLE001 - any decoder error means corruption
                bad = f"{type(e).__name__}: {e}"
            if bad:
                rep["problems"].append(f"integrity (CRC) failure: {bad}")
    rep["ok"] = not rep["problems"]
    return rep


def extract(zip_path, dest, limits: dict = LIMITS, strip_root: bool = True) -> dict:
    rep = inspect(zip_path, limits)
    if not rep["ok"]:
        raise UnsafeArchive(rep)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    if any(dest.iterdir()):
        raise UnsafeArchive({**rep, "ok": False, "problems": [f"destination {dest} is not empty"]})
    root = dest.resolve()
    strip = rep["single_root"] + "/" if strip_root and rep.get("single_root") else ""
    written = 0
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = _norm(info.filename).lstrip("/")
            if strip and name.startswith(strip):
                name = name[len(strip):]
            if not name.strip("/"):
                continue
            target = (root / name).resolve()
            if target != root and root not in target.parents:
                raise UnsafeArchive({**rep, "ok": False, "problems": [f"{info.filename!r} escapes destination"]})
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            mode = 0o755 if _mode(info) & 0o111 else 0o644
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
            size = 0
            with os.fdopen(fd, "wb") as out, zf.open(info) as src:
                while chunk := src.read(1 << 20):
                    size += len(chunk)
                    written += len(chunk)
                    if size > info.file_size or written > limits["max_total_bytes"]:
                        raise UnsafeArchive({**rep, "ok": False,
                                             "problems": [f"{info.filename!r}: data exceeds declared size"]})
                    out.write(chunk)
    rep.update(extracted_to=str(root), bytes_written=written, stripped_root=strip.rstrip("/") or None)
    return rep
