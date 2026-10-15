"""Isolated per-project workspaces, resumable state, journals and an audit log.

ACCI_HOME (configurable; /data/acci or a user-writable data directory by default):
  projects/<name>/src        working copy (git)
  projects/<name>/inbox      uploaded archives / extracted copies awaiting merge
  projects/<name>/artifacts  verified build outputs
  projects/<name>/logs       command logs + journal.jsonl
  projects/<name>/tmp        disposable; HOME/TMPDIR of executed commands
  projects/<name>/state.json task, plan, completed steps, fix attempts, links
  audit.jsonl                administrative actions (repos, PRs, deletions, permissions)
  trash/                     projects are moved here instead of being deleted
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path

def default_home() -> Path:
    """Keep existing /data installations working; otherwise use a user-writable location."""
    if os.environ.get("ACCI_HOME"):
        return Path(os.environ["ACCI_HOME"]).expanduser().resolve()
    if Path("/data").is_dir() and os.access("/data", os.W_OK):
        return Path("/data/acci")
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "acci"


HOME = default_home()
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
SUBDIRS = ("src", "inbox", "artifacts", "logs", "tmp")


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def project_dir(name: str, must_exist: bool = True) -> Path:
    if not NAME_RE.match(name or ""):
        raise ValueError(f"invalid project name {name!r}: use a-z, 0-9, '.', '_' or '-'")
    path = HOME / "projects" / name
    if must_exist and not (path / "state.json").is_file():
        raise FileNotFoundError(f"project {name!r} is not initialised (acci init {name})")
    return path


def audit(action: str, **fields) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    with open(HOME / "audit.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now(), "action": action, **fields}, ensure_ascii=False) + "\n")


def _write_state(path: Path, state: dict) -> None:
    state["updated"] = now()
    tmp = path.with_name("state.json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def init(name: str, repo: str | None = None, branch: str | None = None) -> Path:
    path = project_dir(name, must_exist=False)
    for sub in SUBDIRS:
        (path / sub).mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    if not (path / "state.json").exists():
        _write_state(path / "state.json", {
            "project": name, "repo": repo, "branch": branch, "created": now(),
            "task": None, "stage": "new", "plan": [], "remaining": [], "steps": [],
            "attempts": {}, "links": {},
        })
        audit("project.init", project=name, repo=repo, branch=branch)
    return path


def load_state(name: str) -> dict:
    return json.loads((project_dir(name) / "state.json").read_text(encoding="utf-8"))


def save_state(name: str, state: dict) -> None:
    _write_state(project_dir(name) / "state.json", state)


def journal(name: str, **event) -> None:
    with open(project_dir(name) / "logs" / "journal.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now(), **event}, ensure_ascii=False) + "\n")


def update(name: str, **fields) -> dict:
    state = load_state(name)
    state.update({k: v for k, v in fields.items() if v is not None})
    save_state(name, state)
    return state


def set_task(name: str, task: str, plan: list[str]) -> dict:
    state = load_state(name)
    state.update(task=task, stage="plan", plan=list(plan), remaining=list(plan), attempts={})
    save_state(name, state)
    journal(name, type="task", task=task, plan=plan)
    return state


def step(name: str, step_name: str, status: str = "done", note: str | None = None) -> dict:
    """Record orchestrator progress; status: start | done | fail | skip | blocked."""
    if status not in ("start", "done", "fail", "skip", "blocked"):
        raise ValueError(f"bad status {status!r}")
    state = load_state(name)
    state["steps"].append({"ts": now(), "step": step_name, "status": status, "note": note})
    if status in ("done", "skip") and step_name in state["remaining"]:
        state["remaining"].remove(step_name)
    state["stage"] = f"{step_name}:{status}"
    save_state(name, state)
    journal(name, type="step", step=step_name, status=status, note=note)
    return state


def link(name: str, key: str, url: str) -> None:
    state = load_state(name)
    state["links"][key] = url
    save_state(name, state)


def attempt(name: str, key: str, limit: int = 3) -> tuple[int, bool]:
    """Count automatic fix attempts per error signature; True once the budget is exhausted."""
    state = load_state(name)
    n = state["attempts"].get(key, 0) + 1
    state["attempts"][key] = n
    save_state(name, state)
    journal(name, type="attempt", key=key, n=n, limit=limit)
    return n, n > limit


def clean_tmp(name: str) -> None:
    tmp = project_dir(name) / "tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    journal(name, type="clean_tmp")


def trash(name: str, confirm: str) -> Path:
    """Projects are never rm -rf'ed: moved to HOME/trash after an explicit confirmation."""
    if confirm != name:
        raise PermissionError("confirmation must repeat the project name")
    src = project_dir(name)
    dst = HOME / "trash" / f"{name}-{time.strftime('%Y%m%d-%H%M%S')}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), dst)
    audit("project.trash", project=name, moved_to=str(dst))
    return dst


def list_projects() -> list[dict]:
    root = HOME / "projects"
    out = []
    for path in sorted(root.iterdir()) if root.is_dir() else []:
        f = path / "state.json"
        if f.is_file():
            s = json.loads(f.read_text(encoding="utf-8"))
            out.append({k: s.get(k) for k in ("project", "repo", "branch", "task", "stage", "updated")})
    return out
