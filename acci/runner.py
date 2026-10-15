"""Logged, resource-limited, credential-free command execution inside one project workspace."""
from __future__ import annotations

import collections
import os
import resource
import shlex
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path

from . import secretscan, workspace

PASS_ENV = ("PATH", "LANG", "LC_ALL", "TERM", "TZ", "JAVA_HOME", "ANDROID_HOME", "ANDROID_SDK_ROOT")
_UNSHARE: bool | None = None


HIDE = 'mount -t tmpfs -o size=64k,mode=700 tmpfs "$0" && exec "$@"'


def unshare_ok() -> bool:
    """Unprivileged user namespaces available (network + mount isolation)."""
    global _UNSHARE
    if _UNSHARE is None:
        try:
            _UNSHARE = bool(shutil.which("unshare")) and all(
                subprocess.run(["unshare", f, "true"], capture_output=True, timeout=10).returncode == 0
                for f in ("-rn", "-rm"))
        except (OSError, subprocess.TimeoutExpired):
            _UNSHARE = False
    return _UNSHARE


def secrets_dir() -> Path:
    return workspace.HOME / "secrets"


def _limits(mem_mb, cpu_s, fsize_mb):
    def apply():
        os.setsid()
        if mem_mb:
            resource.setrlimit(resource.RLIMIT_DATA, (mem_mb << 20, mem_mb << 20))
        if cpu_s:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s + 10))
        if fsize_mb:
            resource.setrlimit(resource.RLIMIT_FSIZE, (fsize_mb << 20, fsize_mb << 20))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        os.nice(5)
    return apply


def run(project: str, cmd, cwd=None, timeout: int = 1800, mem_mb: int = 3072, cpu_s: int = 3600,
        fsize_mb: int = 4096, network: bool = True, env: dict | None = None, label: str | None = None,
        tail_lines: int = 40) -> dict:
    pdir = workspace.project_dir(project)
    base = pdir.resolve()
    wd = Path(cwd).resolve() if cwd else (pdir / "src").resolve()
    if wd != base and base not in wd.parents:
        raise PermissionError(f"cwd {wd} is outside project {project!r}")
    home = pdir / "tmp" / "home"
    home.mkdir(parents=True, exist_ok=True)
    e = {k: os.environ[k] for k in PASS_ENV if k in os.environ}  # parent secrets are never inherited
    e.update(HOME=str(home), TMPDIR=str(pdir / "tmp"), CI="1", ACCI_PROJECT=project,
             GIT_TERMINAL_PROMPT="0", PIP_DISABLE_PIP_VERSION_CHECK="1", PYTHONDONTWRITEBYTECODE="1")
    e.update({k: str(v) for k, v in (env or {}).items()})
    argv = list(cmd) if isinstance(cmd, (list, tuple)) else ["bash", "-c", cmd]
    shown = secretscan.redact(cmd if isinstance(cmd, str) else shlex.join(cmd))
    if not network and not unshare_ok():
        raise RuntimeError("network isolation unavailable (no unprivileged user namespaces)")
    secret_path = secrets_dir()
    if secret_path.is_dir() and any(secret_path.iterdir()) and not unshare_ok():
        raise RuntimeError("credential directory cannot be hidden: user namespaces unavailable; "
                           "use a separate credential-free container/VM, not an unprotected fallback")
    hidden = unshare_ok() and secret_path.is_dir()
    if hidden or not network:  # orchestrator credentials are invisible to project commands
        flags = "-rm" + ("" if network else "n")
        argv = (["unshare", flags, "--", "bash", "-c", HIDE, str(secrets_dir()), *argv] if hidden
                else ["unshare", "-rn", "--", *argv])
    logs = pdir / "logs"
    seq = len(list(logs.glob("cmd-*.log"))) + 1
    log_path = logs / f"cmd-{seq:04d}-{time.strftime('%Y%m%d-%H%M%S')}.log"
    tail = collections.deque(maxlen=max(tail_lines, 1))
    t0, timed_out = time.time(), False
    with open(log_path, "w", encoding="utf-8") as lf:
        lf.write(f"$ {shown}\n# cwd={wd} timeout={timeout}s mem={mem_mb}MB cpu={cpu_s}s network={network} "
                 f"secrets_hidden={hidden}\n")
        lf.flush()
        proc = subprocess.Popen(argv, cwd=wd, env=e, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, preexec_fn=_limits(mem_mb, cpu_s, fsize_mb))

        def pump():
            for raw in iter(proc.stdout.readline, b""):
                line = secretscan.redact(raw.decode("utf-8", "replace").rstrip("\r\n"))
                lf.write(line + "\n")
                tail.append(line)

        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(proc.pid, sig)
                    proc.wait(timeout=10)
                    break
                except ProcessLookupError:
                    break
                except subprocess.TimeoutExpired:
                    continue
        try:  # reap leftover background processes of this command
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        reader.join(timeout=15)
        secs = round(time.time() - t0, 1)
        lf.write(f"# exit={proc.returncode} timed_out={timed_out} secs={secs}\n")
    res = {"exit": proc.returncode, "timed_out": timed_out, "secs": secs, "log": log_path.name,
           "secrets_hidden": hidden, "tail": list(tail)}
    workspace.journal(project, type="cmd", label=label, cmd=shown[:500], cwd=str(wd.relative_to(base)),
                      exit=proc.returncode, timed_out=timed_out, secs=secs, log=log_path.name)
    return res
