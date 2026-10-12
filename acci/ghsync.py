"""Local git workspace <-> GitHub helpers.

Primary path: real git over HTTPS with the owner's token (bin/acci-git, orchestrator only).
Fallback path (no token in the sandbox): payloads for the GitHub MCP connector's push_files,
plus tree comparison by git blob SHA-1 against MCP directory listings.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from . import secretscan

MAX_PART_BYTES = 900_000  # MCP tool-argument files are limited to 1 MiB


def git(repo, *args: str, check: bool = True, binary: bool = False):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.decode(errors='replace').strip()[:400]}")
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def local_tree(root) -> dict:
    root = Path(root)
    if (root / ".git").exists():
        paths = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split("\0")
    else:
        paths = [p.relative_to(root).as_posix() for p in root.rglob("*") if ".git" not in p.parts]
    return {rel: blob_sha((root / rel).read_bytes()) for rel in filter(None, paths)
            if (root / rel).is_file() and not (root / rel).is_symlink()}


def remote_tree(listing_files) -> tuple[dict, set]:
    """Merge GitHub contents listings / git trees saved from MCP or API results."""
    files, dirs = {}, set()
    for lf in listing_files:
        data = json.loads(Path(lf).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("tree") or data.get("entries") or [data]
        for e in data:
            if not isinstance(e, dict) or not e.get("path"):
                continue
            dirs.add(e["path"].rsplit("/", 1)[0] if "/" in e["path"] else "")
            if e.get("type") in ("file", "blob") and e.get("sha"):
                files[e["path"]] = e["sha"]
    return files, dirs


def compare(local: dict, remote: dict, listed_dirs: set | None = None) -> dict:
    if listed_dirs is not None:
        local = {p: s for p, s in local.items() if (p.rsplit("/", 1)[0] if "/" in p else "") in listed_dirs}
    changed = sorted(p for p in local if p in remote and remote[p] != local[p])
    only_local = sorted(p for p in local if p not in remote)
    only_remote = sorted(p for p in remote if p not in local)
    return {"identical": not (changed or only_local or only_remote),
            "same": sum(1 for p in local if remote.get(p) == local[p]),
            "changed": changed, "only_local": only_local, "only_remote": only_remote}


def mark_synced(repo, branch: str) -> str:
    head = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "update-ref", f"refs/acci/synced/{branch}", head)
    return head


def build_payload(repo, base: str, owner: str, name: str, branch: str, message: str, out_dir,
                  allow_delete: bool = False) -> dict:
    repo, out_dir = Path(repo), Path(out_dir)
    res = {"base": base, "head": None, "files": [], "bytes": 0, "parts": [], "deletes": [],
           "exec_bit_notes": [], "problems": []}
    if git(repo, "status", "--porcelain"):
        res["problems"].append("working tree has uncommitted changes: commit them locally first")
        return res
    res["head"] = git(repo, "rev-parse", "HEAD").strip()
    raw = git(repo, "diff", "--name-status", "--no-renames", "-z", base, "HEAD").split("\0")
    files = []
    for status, path in zip(raw[0::2], raw[1::2]):
        if status.startswith("D"):
            res["deletes"].append(path)
            continue
        data = git(repo, "show", f"HEAD:{path}", binary=True)
        if b"\0" in data:
            res["problems"].append(f"{path}: binary file cannot go through push_files (use git push)")
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            res["problems"].append(f"{path}: not UTF-8 text")
            continue
        leaks = secretscan.scan_text(text, path)
        if leaks:
            res["problems"] += [f"{x['where']}:{x['line']}: possible secret ({x['rule']})" for x in leaks]
            continue
        files.append({"path": path, "content": text})
    if res["deletes"] and not allow_delete:
        res["problems"].append(f"{len(res['deletes'])} deletions need explicit approval (--allow-delete)")
    res["exec_bit_notes"] = [ln.strip() for ln in git(repo, "diff", "--summary", base, "HEAD").splitlines()
                             if "100755" in ln]
    parts, cur, size = [], [], 0
    for f in files:
        n = len(json.dumps(f, ensure_ascii=False).encode())
        if n > MAX_PART_BYTES:
            res["problems"].append(f"{f['path']}: too large for one MCP call ({n} bytes)")
            continue
        if cur and size + n > MAX_PART_BYTES:
            parts.append(cur)
            cur, size = [], 0
        cur.append(f)
        size += n
    if cur:
        parts.append(cur)
    res["files"] = [f["path"] for f in files]
    res["bytes"] = sum(len(f["content"].encode()) for f in files)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("push-*.json"):
        old.unlink()
    if not res["problems"]:
        for i, part in enumerate(parts, 1):
            msg = message if len(parts) == 1 else f"{message} (part {i}/{len(parts)})"
            p = out_dir / f"push-{i}.json"
            p.write_text(json.dumps({"owner": owner, "repo": name, "branch": branch, "message": msg,
                                     "files": part}, ensure_ascii=False), encoding="utf-8")
            res["parts"].append(str(p))
    return res
