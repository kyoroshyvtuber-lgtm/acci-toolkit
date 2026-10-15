"""ACCI command line (sandbox side). See `acci -h`."""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import __version__, detect, ghsync, handoff, ios, runner, safezip, secretscan, workspace

TEMPLATES = Path(__file__).with_name("templates")
NOT_SECRETS = {"unreadable-archive"}


def emit(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def _ver(cmd):
    if not shutil.which(cmd[0]):
        return None
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"
    lines = (r.stdout.strip() or r.stderr.strip()).splitlines()
    return lines[0][:120] if lines else f"exit {r.returncode}"


def _target(arg: str) -> Path:
    p = Path(arg)
    return p if p.exists() else workspace.project_dir(arg) / "src"


def c_doctor(a):
    tools = {name: _ver(cmd) for name, cmd in {
        "python3": ["python3", "--version"], "node": ["node", "--version"], "npm": ["npm", "--version"],
        "git": ["git", "--version"], "java": ["java", "-version"], "docker": ["docker", "--version"],
        "gh": [str(workspace.HOME / "opt" / "gh") if (workspace.HOME / "opt" / "gh").is_file()
               else "gh", "--version"], "gradle": ["gradle", "--version"],
        "dotnet": ["dotnet", "--version"], "go": ["go", "version"], "cargo": ["cargo", "--version"],
        "zip": ["zip", "-v"], "curl": ["curl", "--version"], "unshare": ["unshare", "--version"]}.items()}
    net = {}
    for url in (() if a.offline else ("https://api.github.com", "https://github.com", "https://pypi.org/simple/",
                "https://registry.npmjs.org/", "https://dl.google.com/android/repository/repository2-3.xml",
                "https://services.gradle.org/versions/current")):
        if not shutil.which("curl"):
            net[url] = "curl is not installed"
            continue
        r = subprocess.run(["curl", "-sS", "-m", "10", "-o", "/dev/null", "-w", "%{http_code}", url],
                           capture_output=True, text=True)
        net[url] = r.stdout.strip() if r.returncode == 0 else (r.stderr.strip()[:80] or "error")
    with open("/proc/meminfo") as f:
        mem_kb = int(next(line.split()[1] for line in f if line.startswith("MemTotal")))
    workspace.HOME.mkdir(parents=True, exist_ok=True)
    du = shutil.disk_usage(workspace.HOME)
    emit({"acci": __version__, "os": platform.platform(), "arch": platform.machine(), "cpus": os.cpu_count(),
          "mem_gb": round(mem_kb / 1024**2, 1), "disk_free_gb": round(du.free / 1e9, 1),
          "acci_home": str(workspace.HOME), "uid": os.getuid(), "tools": tools, "network": net,
          "namespaces (net isolation + secret hiding)": runner.unshare_ok()})


def c_init(a):
    path = workspace.init(a.project, a.repo, a.branch)
    emit({"project": a.project, "path": str(path)})


def c_ls(a):
    emit(workspace.list_projects())


def c_inspect_zip(a):
    rep = safezip.inspect(a.zip)
    emit(rep)
    return 0 if rep["ok"] else 2


def c_ingest(a):
    pdir = workspace.init(a.project)
    ts = time.strftime("%Y%m%d-%H%M%S")
    staging = pdir / "tmp" / f"extract-{ts}"
    try:
        rep = safezip.extract(a.zip, staging)
    except safezip.UnsafeArchive as e:
        shutil.rmtree(staging, ignore_errors=True)  # never keep half-extracted data
        workspace.journal(a.project, type="ingest", ok=False, archive=str(a.zip),
                          problems=e.report.get("problems", [])[:20])
        emit({"ok": False, "problems": e.report.get("problems", [])[:50],
              "warnings": e.report.get("warnings", [])[:20]})
        return 2
    src = pdir / "src"
    if src.is_dir() and not any(src.iterdir()):
        src.rmdir()
        dest = src
    else:
        dest = pdir / "inbox" / f"zip-{ts}"  # an existing working copy is never overwritten
    shutil.move(str(staging), dest)
    det = detect.detect(dest)
    leaks = secretscan.scan_path(dest)
    keep = ("archive", "size", "sha256", "members", "files", "dirs", "total_uncompressed", "stripped_root",
            "nested_archives", "warnings")
    report = {"ok": True, "archive": {k: rep.get(k) for k in keep}, "extracted_to": str(dest),
              "detect": det, "secrets": leaks[:200]}
    rp = pdir / "logs" / f"ingest-{ts}.json"
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    workspace.journal(a.project, type="ingest", ok=True, archive=str(a.zip), sha256=rep["sha256"],
                      dest=str(dest), stacks=[s["stack"] for s in det["stacks"]], secrets=len(leaks),
                      report=rp.name)
    report["detect"] = {k: det[k] for k in ("files", "bytes", "stacks", "docs", "tests", "ci", "top_level",
                                            "extensions", "large_files")}
    report["secrets"] = leaks[:20]
    report["report_file"] = str(rp)
    emit(report)
    return 0


def c_detect(a):
    emit(detect.detect(_target(a.target)))


def c_run(a):
    cmd = list(a.cmd)
    while cmd and cmd[0] == "--":
        cmd.pop(0)
    if not cmd:
        raise ValueError("usage: acci run <project> [options] -- <command>")
    pdir = workspace.project_dir(a.project)
    res = runner.run(a.project, cmd[0] if len(cmd) == 1 else cmd, cwd=(pdir / a.cwd) if a.cwd else None,
                     timeout=a.timeout, mem_mb=a.mem, cpu_s=a.cpu, network=not a.no_net, label=a.label,
                     tail_lines=a.tail)
    print("\n".join(res["tail"]))
    print(f"# exit={res['exit']} timed_out={res['timed_out']} secs={res['secs']} "
          f"secrets_hidden={res['secrets_hidden']} log=logs/{res['log']}")
    return 0 if res["exit"] == 0 else 1


def c_scan(a):
    found = []
    for p in a.paths:
        if a.git:
            found += secretscan.scan_git(p)
        found += secretscan.scan_path(p)
    real = [f for f in found if f["rule"] not in NOT_SECRETS]
    emit({"findings": len(real), "notes": len(found) - len(real), "items": found[:200]})
    return 1 if real else 0


def c_redact(a):
    sys.stdout.write(secretscan.redact(sys.stdin.read()))


def c_state(a):
    if a.task:
        workspace.set_task(a.project, a.task, [s.strip() for s in (a.plan or "").split(",") if s.strip()])
    if a.repo or a.branch:
        workspace.update(a.project, repo=a.repo, branch=a.branch)
    if a.step:
        workspace.step(a.project, a.step, a.status, a.note)
    for kv in a.link or []:
        k, _, v = kv.partition("=")
        workspace.link(a.project, k, v)
    state = workspace.load_state(a.project)
    if not a.full:
        state["steps"] = state["steps"][-12:]
    emit(state)


def c_attempt(a):
    n, exhausted = workspace.attempt(a.project, a.key, a.limit)
    emit({"key": a.key, "attempt": n, "limit": a.limit, "exhausted": exhausted,
          "advice": "stop retrying: re-analyse the root cause and change strategy" if exhausted else "retry allowed"})
    return 3 if exhausted else 0


def c_audit(a):
    fields = dict(kv.split("=", 1) for kv in a.fields if "=" in kv)
    workspace.audit(a.action, **fields)
    emit({"logged": a.action, **fields})


def c_clean(a):
    workspace.clean_tmp(a.project)
    emit({"cleaned": a.project})


def c_trash(a):
    emit({"moved_to": str(workspace.trash(a.project, a.confirm))})


def c_payload(a):
    pdir = workspace.project_dir(a.project)
    res = ghsync.build_payload(pdir / "src", a.base, a.owner, a.repo, a.branch, a.message,
                               pdir / "tmp" / "payloads", a.allow_delete)
    workspace.journal(a.project, type="payload", branch=a.branch, files=len(res["files"]),
                      parts=len(res["parts"]), deletes=len(res["deletes"]), problems=res["problems"][:10])
    emit(res)
    return 0 if not res["problems"] else 2


def c_synced(a):
    head = ghsync.mark_synced(workspace.project_dir(a.project) / "src", a.branch)
    workspace.journal(a.project, type="synced", branch=a.branch, local=head, remote=a.remote_sha)
    emit({"branch": a.branch, "local_head": head, "remote_commit": a.remote_sha})


def c_compare(a):
    files, dirs = ghsync.remote_tree(a.listings)
    emit(ghsync.compare(ghsync.local_tree(_target(a.target)), files, None if a.all else dirs))


def c_template(a):
    if Path(a.name).name != a.name:
        raise ValueError("template name must be a filename, not a path")
    f = Path(__file__).with_name("ios.py") if a.name == "ios.py" else TEMPLATES / a.name
    if not f.is_file():
        raise FileNotFoundError(f"no template {a.name!r}; available: {sorted(p.name for p in TEMPLATES.iterdir())}")
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, a.out)
        emit({"written": a.out})
    else:
        sys.stdout.write(f.read_text(encoding="utf-8"))


def c_handoff(a):
    emit(handoff.export(a.project))


def c_resume(a):
    emit(handoff.resume(a.project, a.source, replace=a.replace))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="acci", description=f"ACCI toolkit {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def cmd(name, fn, help_text, *args):
        sp = sub.add_parser(name, help=help_text)
        sp.set_defaults(fn=fn)
        for arg in args:
            sp.add_argument(arg)
        return sp

    sp = cmd("doctor", c_doctor, "diagnose sandbox capabilities")
    sp.add_argument("--offline", action="store_true", help="skip network probes")
    sp = cmd("init", c_init, "create an isolated project workspace", "project")
    sp.add_argument("--repo")
    sp.add_argument("--branch")
    cmd("ls", c_ls, "list projects")
    cmd("inspect-zip", c_inspect_zip, "validate a ZIP without extracting", "zip")
    cmd("ingest", c_ingest, "safely extract a ZIP into a project and analyse it", "project", "zip")
    cmd("detect", c_detect, "detect stacks and build/test commands", "target")
    sp = cmd("run", c_run, "run a command with limits, isolation and logging", "project")
    sp.add_argument("--cwd")
    sp.add_argument("--timeout", type=int, default=1800)
    sp.add_argument("--mem", type=int, default=3072, help="MB (RLIMIT_DATA)")
    sp.add_argument("--cpu", type=int, default=3600, help="CPU seconds")
    sp.add_argument("--no-net", action="store_true")
    sp.add_argument("--label")
    sp.add_argument("--tail", type=int, default=40)
    sp.add_argument("cmd", nargs="*", help="command after `--`")
    sp = cmd("scan", c_scan, "secret scan of paths (and git history with --git)")
    sp.add_argument("paths", nargs="+")
    sp.add_argument("--git", action="store_true")
    cmd("redact", c_redact, "redact secrets from stdin")
    sp = cmd("state", c_state, "show/update resumable task state", "project")
    sp.add_argument("--task")
    sp.add_argument("--plan", help="comma-separated stages")
    sp.add_argument("--repo")
    sp.add_argument("--branch")
    sp.add_argument("--step")
    sp.add_argument("--status", default="done")
    sp.add_argument("--note")
    sp.add_argument("--link", action="append", help="key=url")
    sp.add_argument("--full", action="store_true")
    sp = cmd("attempt", c_attempt, "count a fix attempt for an error signature", "project", "key")
    sp.add_argument("--limit", type=int, default=3)
    sp = cmd("audit", c_audit, "record an administrative action", "action")
    sp.add_argument("fields", nargs="*", help="key=value")
    cmd("clean", c_clean, "wipe a project's tmp/", "project")
    sp = cmd("trash", c_trash, "move a project to trash (never rm -rf)", "project")
    sp.add_argument("--confirm", required=True)
    sp = cmd("payload", c_payload, "build MCP push_files payloads (fallback path)", "project")
    for opt in ("--base", "--owner", "--repo", "--branch", "--message"):
        sp.add_argument(opt, required=True)
    sp.add_argument("--allow-delete", action="store_true")
    sp = cmd("synced", c_synced, "mark local HEAD as pushed for a branch", "project")
    sp.add_argument("--branch", required=True)
    sp.add_argument("--remote-sha")
    sp = cmd("compare", c_compare, "compare a local tree with remote listings by blob SHA", "target")
    sp.add_argument("listings", nargs="+")
    sp.add_argument("--all", action="store_true", help="also report local files outside listed dirs")
    sp = cmd("template", c_template, "print/copy a CI template", "name")
    sp.add_argument("--out")
    cmd("handoff", c_handoff, "export reviewed task state into the project's .acci/ directory", "project")
    sp = cmd("resume", c_resume, "restore task state from a repository handoff", "project")
    sp.add_argument("--from", dest="source", required=True, help="path to .acci/handoff.json")
    sp.add_argument("--replace", action="store_true", help="explicitly replace an existing nonempty task")
    ios.add_parsers(sub.add_parser("ios", help="iOS simulator checks and explicit signed IPA export"))
    return p


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    tail = []
    if "--" in argv:  # everything after the first `--` is the command, verbatim
        i = argv.index("--")
        argv, tail = argv[:i], argv[i + 1:]
    a = build_parser().parse_args(argv)
    if hasattr(a, "cmd"):
        a.cmd = list(a.cmd) + tail
    try:
        return a.fn(a) or 0
    except (ValueError, FileNotFoundError, PermissionError, RuntimeError) as e:
        print(f"acci: error: {e}", file=sys.stderr)
        return 2
