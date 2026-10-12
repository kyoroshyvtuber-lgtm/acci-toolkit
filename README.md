# ACCI: Autonomous Cloud Coding Infrastructure (sandbox toolkit)

Owner talks to the agent (Notion AI) from a phone. The agent works in a persistent Linux sandbox
(`/data/acci`), keeps state in `projects/<name>/state.json` + the Notion database «ACCI · Задачи»,
pushes to GitHub on its own branches, and builds in GitHub Actions (Linux / Android, Windows, macOS / iOS).

## Components
| Component | Where | What it does |
|---|---|---|
| Orchestrator | Notion AI agent + `acci state` | PLAN → INSPECT → IMPLEMENT → BUILD → TEST → ANALYZE → FIX → VERIFY → REPORT, resumable |
| Workspace | `acci init/ingest/run/clean/trash` | one dir per project; logs; journal; limits; no shared secrets |
| ZIP intake | `acci inspect-zip/ingest` | Zip Slip, symlinks, special files, bombs, CRC, duplicates; never overwrites a working copy |
| Detection | `acci detect` | Android, iOS (Xcode/XcodeGen/SwiftPM), Flutter, RN, Node/Electron, Python, .NET, JVM, Rust, Go, CMake |
| Runner | `acci run` | `RLIMIT_DATA/CPU/FSIZE`, wall timeout + process-group kill, clean env, optional `--no-net`, secrets dir hidden via mount namespace, redacted logs |
| Secrets | `acci scan [--git]`, `acci redact` | tokens/keys/private keys/sensitive files in trees, archives (APK/whl/zip), git history, logs |
| GitHub | `bin/acci-git`, `bin/acci-gh` | orchestrator-only; token in `secrets/` (0700), injected by the gh credential helper, output redacted |
| GitHub (fallback) | `acci payload/compare/synced` | when only the Notion GitHub MCP connector is available: push_files payloads + blob-SHA tree checks |
| Cloud CI | `templates/ci-*.yml` + `report.py` | python, node, android, ios (unsigned sim + optional signed .ipa), windows-dotnet; report → PR comment |

## Runbook (one task)
```bash
A=/data/acci/toolkit/bin/acci; G=/data/acci/toolkit/bin/acci-git; H=/data/acci/toolkit/bin/acci-gh
$A ingest <proj> <upload.zip>            # or: $G clone https://github.com/<o>/<r> projects/<proj>/src
$A state <proj> --task "<task>" --plan inspect,implement,build,test,push,ci,pr,report --repo <o>/<r>
$A detect <proj>                          # stacks, build/test commands, runners
cd projects/<proj>/src && git switch -c acci/<topic>
#  ... edit files (minimal change) ...
$A run <proj> --no-net -- "<lint/test/build>"   # local loop; $A attempt <proj> <error-key> limits retries
$A scan projects/<proj>/src --git        # must be 0 findings before push
$G -C projects/<proj>/src push -u origin acci/<topic>     # never to main/default branch
$H pr create -R <o>/<r> --head acci/<topic> --base main --title ... --body ...
$H run watch -R <o>/<r> <run-id>; $H run view -R <o>/<r> <run-id> --log-failed
$H run download -R <o>/<r> <run-id> -D projects/<proj>/artifacts/<run-id>   # verify sha256 + smoke test
$A state <proj> --step report --link pr=<url> --link run=<url>
```

## Rules enforced by the orchestrator
- Work on `acci/*` branches + PR; no direct pushes to the default branch without explicit permission.
- Delete files only when the task says so (`acci payload --allow-delete`); projects go to `trash/`, never `rm -rf`.
- Confirm with the owner before: deleting a repo, public releases, permission changes, paid minutes/services.
- Never print/commit tokens; project commands never see `secrets/`; logs are redacted.
- Max 3 automatic fix attempts per error signature, then re-analyse and change strategy.
- Never delete/skip tests or disable checks to get a green build; artifacts are verified, not just "exist".

## Restore on a fresh sandbox
1. Restore `toolkit/` (GitHub repo `acci-toolkit` or the ZIP attached to the Notion hub page).
2. Install gh: see `bin/install-gh.sh` (verifies the release checksum).
3. Owner re-authorizes GitHub (token → `secrets/gh` via `gh auth login --with-token`).
4. Project state: Notion «ACCI · Задачи» row + branch on GitHub (`acci/*`) + `state.json` if present.
