"""Secret detection and redaction for source trees, git history, archives and logs."""
from __future__ import annotations

import math
import os
import re
import subprocess
import zipfile
from pathlib import Path

RULES = [
    ("github-token", r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,255}\b"),
    ("github-fine-grained-pat", r"\bgithub_pat_[A-Za-z0-9_]{22,255}\b"),
    ("aws-access-key-id", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ("private-key", r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----"),
    ("slack-token", r"\bxox[abposr]-[A-Za-z0-9-]{10,}"),
    ("google-api-key", r"\bAIza[0-9A-Za-z_\-]{35}"),
    ("stripe-live-key", r"\b[rs]k_live_[0-9A-Za-z]{16,}"),
    ("openai-key", r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{32,}"),
    ("anthropic-key", r"\bsk-ant-[A-Za-z0-9_\-]{32,}"),
    ("notion-token", r"\b(?:secret_[A-Za-z0-9]{43}|ntn_[A-Za-z0-9]{40,})"),
    ("npm-token", r"\bnpm_[A-Za-z0-9]{36}\b"),
    ("jwt", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ("url-credentials", r"\b[a-z][a-z0-9+.-]{1,15}://[^/\s:@'\"]{1,64}:[^/\s:@'\"]{3,128}@[A-Za-z0-9.-]+"),
    ("generic-secret",
     r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|private[_-]?key)"
     r"\b[\"']?\s*[:=]\s*[\"']([^\"'\s]{8,})[\"']"),
]
COMPILED = [(name, re.compile(rx)) for name, rx in RULES]
PLACEHOLDER = re.compile(
    r"(?i)(\$\{|\{\{|\$[A-Z_]{3,}|<[a-z0-9_ -]+>|your[_-]|example|changeme|placeholder|dummy|xxxx|\*{4}|redacted)")
SENSITIVE = re.compile(
    r"(?i)(^|/)(\.env(\.[^/]+)?|[^/]*\.(p12|pfx|p8|mobileprovision|jks|keystore|pem|key|ppk)"
    r"|id_(rsa|dsa|ecdsa|ed25519)|\.netrc|\.npmrc|\.pypirc|[^/]*service[-_]?account[^/]*\.json|credentials(\.json)?)$")
SAFE_SUFFIX = (".example", ".sample", ".template", ".dist")
SKIP_DIRS = {".git", "node_modules", ".gradle", "__pycache__", ".venv", "venv", "Pods", "DerivedData"}
ARCHIVES = (".zip", ".whl", ".jar", ".apk", ".aab", ".pyz", ".ipa", ".nupkg")
LOW_SIGNAL = {"generic-secret", "url-credentials", "jwt"}


def entropy(s: str) -> float:
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in (s.count(ch) for ch in set(s))) if n else 0.0


def mask(s: str) -> str:
    return f"{s[:4]}…[{len(s)} chars]"


def scan_text(text: str, where: str = "<text>") -> list[dict]:
    found = []
    for lineno, line in enumerate(text.splitlines(), 1):
        line = line[:20000]
        for name, rx in COMPILED:
            for m in rx.finditer(line):
                value = m.group(1) if m.lastindex else m.group(0)
                if PLACEHOLDER.search(value):
                    continue
                if name == "generic-secret" and entropy(value) < 3.0:
                    continue
                found.append({"rule": name, "where": where, "line": lineno, "match": mask(m.group(0))})
    return found


def redact(text: str) -> str:
    """Aggressive redaction for logs/reports (no entropy threshold)."""
    for name, rx in COMPILED:
        def repl(m, name=name):
            value = m.group(1) if m.lastindex else m.group(0)
            return m.group(0) if PLACEHOLDER.search(value) else m.group(0).replace(value, f"[REDACTED:{name}]")
        text = rx.sub(repl, text)
    return text


def _scan_blob(data: bytes, where: str) -> list[dict]:
    if b"\x00" in data[:8192]:  # binary: only high-signal token formats
        return [f for f in scan_text(data.decode("latin-1"), where) if f["rule"] not in LOW_SIGNAL]
    return scan_text(data.decode("utf-8", "replace"), where)


def _scan_archive(path: Path, rel: str, max_member: int) -> list[dict]:
    found = []
    try:
        with zipfile.ZipFile(path) as z:
            for info in z.infolist()[:20000]:
                inner = f"{rel}!{info.filename}"
                if SENSITIVE.search(info.filename) and not info.filename.endswith(SAFE_SUFFIX):
                    found.append({"rule": "sensitive-file", "where": inner, "line": 0, "match": info.filename})
                if not info.is_dir() and info.file_size <= max_member:
                    found += _scan_blob(z.read(info), inner)
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError, ValueError) as e:
        found.append({"rule": "unreadable-archive", "where": rel, "line": 0, "match": str(e)[:80]})
    return found


def scan_path(root, max_bytes: int = 5 * 1024**2) -> list[dict]:
    root = Path(root)
    if root.is_file():
        base, files = root.parent, [root]
    else:
        base, files = root, []
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            files += [Path(dp, f) for f in fns]
    found = []
    for f in files:
        rel = f.relative_to(base).as_posix()
        if SENSITIVE.search(rel) and not rel.endswith(SAFE_SUFFIX):
            found.append({"rule": "sensitive-file", "where": rel, "line": 0, "match": f.name})
        if f.is_symlink() or not f.is_file():
            continue
        size = f.stat().st_size
        if rel.lower().endswith(ARCHIVES) and size <= 512 * 1024**2 and zipfile.is_zipfile(f):
            found += _scan_archive(f, rel, max_bytes)
        elif size <= max_bytes:
            found += _scan_blob(f.read_bytes(), rel)
    return found


def scan_git(repo) -> list[dict]:
    """Scan every commit reachable from any ref: added lines and commit messages."""
    r = subprocess.run(["git", "-C", str(repo), "log", "--all", "-p", "--no-color", "--no-ext-diff",
                        "--format=commit %H%n%B"], capture_output=True)
    found, commit = [], "?"
    for line in r.stdout.decode("utf-8", "replace").splitlines():
        if line.startswith("commit ") and len(line) == 47:
            commit = line[7:19]
            continue
        if line.startswith(("-", " ", "@@", "diff --git", "index ")):
            continue
        found += scan_text(line[1:] if line.startswith("+") else line, f"git:{commit}")
    return found
