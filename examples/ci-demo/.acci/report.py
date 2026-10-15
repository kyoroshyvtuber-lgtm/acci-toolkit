#!/usr/bin/env python3
"""ACCI CI report: job status, step outcomes, toolchain versions, test results, artifact
hashes and failing-step log tails -> job summary + comment on the branch's open PR."""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

TOKEN_RX = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,}|(?:AKIA|ASIA)[0-9A-Z]{16}"
                      r"|xox[abposr]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_\-]{35}|sk-[A-Za-z0-9_\-]{32,})"
                      r"|-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")
MAX_BODY = 60000


def env(key, default=""):
    return os.environ.get(key, default)


def junit():
    total = bad = skipped = 0
    failures = []
    for path in sorted(set(glob.glob("**/test-results*.xml", recursive=True) + glob.glob("**/TEST-*.xml", recursive=True))):
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError):
            continue
        for suite in ([root] if root.tag == "testsuite" else root.iter("testsuite")):
            total += int(suite.get("tests", 0))
            bad += int(suite.get("failures", 0)) + int(suite.get("errors", 0))
            skipped += int(suite.get("skipped", 0))
            for case in suite.iter("testcase"):
                for kind in ("failure", "error"):
                    el = case.find(kind)
                    if el is not None:
                        failures.append(f"{case.get('classname', '')}::{case.get('name', '')}: "
                                        f"{(el.get('message') or '').strip()[:300]}")
    return total, bad, skipped, failures


def main() -> int:
    logs = Path(env("ACCI_LOG_DIR", "acci-logs"))
    status = env("ACCI_JOB_STATUS", "unknown")
    try:
        steps = json.loads(env("ACCI_STEPS", "{}") or "{}")
    except ValueError:
        steps = {}
    sha = env("GITHUB_SHA")
    run_url = f"{env('GITHUB_SERVER_URL')}/{env('GITHUB_REPOSITORY')}/actions/runs/{env('GITHUB_RUN_ID')}"
    icon = {"success": "✅", "failure": "❌"}.get(status, "⚠️")
    out = [f"<!-- acci-report workflow={env('GITHUB_WORKFLOW')} job={env('GITHUB_JOB')} sha={sha} run={env('GITHUB_RUN_ID')} -->",
           f"### {icon} ACCI CI · {env('ACCI_TITLE', env('GITHUB_JOB'))}: `{status}`", "",
           f"- Commit `{sha[:12]}` on `{env('GITHUB_REF_NAME')}`",
           f"- Run: {run_url} (attempt {env('GITHUB_RUN_ATTEMPT', '1')})",
           f"- Runner: {env('RUNNER_OS')} {env('RUNNER_ARCH')}, image {env('ImageOS', '?')} {env('ImageVersion', '?')}",
           "", "| Step | Outcome |", "|---|---|"]
    for sid, s in steps.items():
        o = s.get("outcome", "?")
        out.append(f"| `{sid}` | {'✅' if o == 'success' else '❌' if o == 'failure' else '⏭️'} {o} |")
    total, bad, skipped, failures = junit()
    if total:
        out += ["", f"**Tests:** {total} total · {bad} failed · {skipped} skipped"]
        out += [f"- ❌ `{f}`" for f in failures[:25]]
    files = sorted({f for pat in env("ACCI_ARTIFACT_PATHS").split() for f in glob.glob(pat, recursive=True)
                    if os.path.isfile(f)})
    if files:
        out += ["", "**Artifacts:**"]
        for f in files[:25]:
            digest = hashlib.sha256(Path(f).read_bytes()).hexdigest()
            out.append(f"- `{f}` · {os.path.getsize(f):,} bytes · sha256 `{digest}`")
        if env("ACCI_ARTIFACT_URL"):
            out.append(f"- Download (GitHub login): {env('ACCI_ARTIFACT_URL')} · artifact id `{env('ACCI_ARTIFACT_ID')}`")
    versions = logs / "versions.txt"
    if versions.exists():
        out += ["", "<details><summary>Toolchain versions</summary>", "", "```text",
                versions.read_text(errors="replace")[:4000].strip(), "```", "</details>"]
    for sid, s in steps.items():
        if s.get("outcome") == "failure":
            lf = logs / f"{sid}.log"
            tail = lf.read_text(errors="replace").splitlines()[-80:] if lf.exists() else ["(no captured log, see run page)"]
            out += ["", f"<details open><summary>Log tail · {sid}</summary>", "", "```text", *tail, "```", "</details>"]
    body = TOKEN_RX.sub("[REDACTED]", "\n".join(out))
    if len(body) > MAX_BODY:
        body = body[:MAX_BODY] + "\n…(truncated)"
    if env("GITHUB_STEP_SUMMARY"):
        with open(env("GITHUB_STEP_SUMMARY"), "a", encoding="utf-8") as f:
            f.write(body + "\n")
    pr = env("ACCI_PR_NUMBER")
    if not pr and env("GH_TOKEN"):
        r = subprocess.run(["gh", "pr", "list", "-R", env("GITHUB_REPOSITORY"), "--head", env("GITHUB_REF_NAME"),
                            "--state", "open", "--json", "number", "-q", ".[0].number"], capture_output=True, text=True)
        pr = r.stdout.strip()
    if pr:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as t:
            t.write(body)
        r = subprocess.run(["gh", "pr", "comment", pr, "-R", env("GITHUB_REPOSITORY"), "--body-file", t.name],
                           capture_output=True, text=True)
        print(f"PR #{pr} comment: {'posted' if r.returncode == 0 else 'failed: ' + r.stderr.strip()[:300]}")
    else:
        print("No open PR for this branch: report written to the job summary only.")
    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
