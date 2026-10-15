# ACCI — Agent Cloud Coding Infrastructure

**A provider-independent development toolkit, not a model or a hosted agent.**
Give an approved coding agent this repository, a task, and access to the target
GitHub project. It can follow the same documented edit → test → build →
inspect → fix → verify → PR workflow without this chat or a Notion account.

**License:** [MIT](LICENSE). Use, modify, and redistribute the source under
the terms of that license.

- **For agents:** read [AGENTS.md](AGENTS.md).
- **Для владельца:** [как передать проект другому ИИ + готовое сообщение](docs/START_HERE.ru.md).
- **Capabilities/access:** [docs/ACCESS.md](docs/ACCESS.md).
- **Task commands:** [docs/RUNBOOK.md](docs/RUNBOOK.md).
- **Security limits:** [docs/SECURITY.md](docs/SECURITY.md).
- **Validation and untested paths:** [docs/VALIDATION.md](docs/VALIDATION.md).
- **iPhone apps:** [tests, simulator evidence and opt-in IPA export](docs/IOS.md).
- **Games:** [Godot/Unity profiles and limits](docs/GAMES.md).
- **Optional unattended tasks:** [disabled-by-default bounded executor](docs/AUTONOMY.md).

## What is included

| Component | Purpose |
| --- | --- |
| Python CLI `acci` | Project workspaces, task state, attempt limits, checkpoints |
| ZIP intake | Inspect/extract archives; reject traversal, symlinks, bombs and corrupt entries |
| Stack detection | Suggest project-specific build/test commands and runner families |
| Command runner | Clean environment, time/resource limits, logs, optional Linux namespaces |
| Secret scanner/redactor | Best-effort checks of source, git history, archives and logs |
| GitHub helpers | Authenticated Git/CLI operations and connector payload/tree comparison |
| CI templates | Python, Node, Android, iOS/macOS, Windows/.NET; Godot/Unity profiles |
| iOS validation | XCTest/UI tests, disposable simulator, launch/screenshot, `.xcresult`, SHA-256 |
| Signed IPA helper | Separate owner-gated export, profile/certificate checks, cleanup; never store upload |
| `examples/ci-demo/` | Python/Android/iOS demo, native tests and self-contained workflows |
| `examples/godot-demo/` | Headless gameplay tests, resource-pack export and packaged startup smoke |
| Optional executor | One source proposal, separate credential-free validation, review PR |
| `acci handoff` / `resume` | Reviewed repository-based checkpoint for a different agent |
| Tests + toolkit CI | Regression tests, package build and clean-wheel install checks |

There is no Notion SDK or LLM API dependency. Notion can be an optional dashboard;
the authoritative code, instructions, workflows, and reviewed handoff live in Git.
The default toolkit does not call a model or grant GitHub access. The optional
executor calls an explicitly configured provider only after owner activation;
it is disabled in the committed policy and workflow gate. External agents need
no provider key in ACCI.

## Quick start

The orchestrator runs on **Linux with Python 3.10+, Bash and Git**.
Full GitHub operation also needs GitHub CLI and approved authentication.
Target applications can build on Linux, Windows, or macOS through Actions.
Windows/macOS host support for the local orchestrator is not claimed.

```bash
git clone https://github.com/kyoroshyvtuber-lgtm/acci-toolkit.git
cd acci-toolkit
bash bin/bootstrap.sh --dev
source .venv/bin/activate
export ACCI_HOME="$HOME/.local/share/acci"  # private runtime state, outside this checkout
acci doctor --offline
acci --help
python -m pytest -q
```

`bin/acci` also runs from a source checkout without package installation.
`python -m acci` and an installed wheel include the CI templates.
The bootstrap only sets up a local virtual environment; it does not authenticate,
change repository visibility, publish packages, or start cloud builds.

If `gh` is absent, review and run `bash bin/install-gh.sh` on Linux
(x86-64/ARM64). It downloads the official release and verifies its release
SHA-256 checksum. Alternatively install GitHub CLI through your normal method.
See [ACCESS](docs/ACCESS.md) for private login and least-privilege permissions.

`ACCI_HOME` is configurable. Without it, the CLI uses `/data/acci` when `/data`
is writable, otherwise `$XDG_DATA_HOME/acci` or `$HOME/.local/share/acci`.
Runtime layout:

```text
$ACCI_HOME/
  projects/<name>/
    src/          # working copy
    state.json    # local task checkpoint
    inbox/        # supplied archives
    artifacts/    # downloaded outputs
    logs/         # command logs + journal.jsonl
    tmp/          # disposable build HOME/TMPDIR
  secrets/        # private orchestrator credentials; NEVER commit
  audit.jsonl
  trash/
```

## Reuse the demo

Copy the **contents** of `examples/ci-demo/` into a separate, approved target
repository, including `.github/` and `.acci/`. Do not nest it under another
directory unless you also adapt the workflows.
Python, Android and unsigned iOS CI run on push/PR in the copied demo; platform
probes remain manual. Signed iOS export is a separate opt-in workflow.
Review triggers and runner costs before pushing.

## Pass work to another agent

```bash
acci handoff my-project
# Review .acci/handoff.json and .acci/HANDOFF.md in that project's src,
# then explicitly commit/push those two files on the task branch.
```

The next agent installs ACCI, clones the same branch into a fresh project
workspace, reads the handoff, and runs:

```bash
acci resume my-project --from .acci/handoff.json
```

Credentials, conversation history, logs, binaries and local files are not
implicitly transferred. The next agent must verify the actual remote commit
and CI again.

## Important limits

- "Any agent" means a model with the necessary **approved execution tools**.
  GitHub read access alone or a connector without Actions/log/artifact tools
  cannot reproduce the full workflow.
- Templates require adaptation to the target project. Detection of a stack
  is not proof that every stack's build path works.
- An iOS simulator build is not a signed iPhone installation or App Store
  release. Signing, store publication, and production credentials are separate.
- Engine profiles are not proof of every game's iOS export. Godot resource packs,
  Unity Xcode projects, device builds and finished games are different outputs.
- The optional executor only changes existing allowlisted source; it cannot
  scaffold an entire app, change tests/policy, merge or activate paid services.
- Actions availability/cost depends on the owner's plan and policy.
- Resource limits, redaction and namespace hiding are not a complete sandbox.
  Use a separate credential-free container/VM for untrusted code.
- Work on task branches and PRs; get approval before merging, public releases,
  visibility/access changes, destructive operations, or paid services.
- This repository is MIT-licensed; respect licenses of dependencies and target projects.
