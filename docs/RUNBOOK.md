# One task, any approved agent

Start from the repository root. The examples below use a Bash shell.
Replace `OWNER/REPO`, branch names, commands, and task text with the actual task.

```bash
source .venv/bin/activate
export ACCI_HOME="$HOME/.local/share/acci"
TK="$PWD"
A="$TK/.venv/bin/acci"
G="$TK/bin/acci-git"
H="$TK/bin/acci-gh"

$A doctor --offline
$A init demo --repo OWNER/REPO --branch acci/my-task
$G clone https://github.com/OWNER/REPO.git "$ACCI_HOME/projects/demo/src"
cd "$ACCI_HOME/projects/demo/src"
git switch -c acci/my-task
$A state demo --task "Actual user request" \
  --plan inspect,implement,build,test,push,ci,verify,report
$A detect demo
```

Read the source, project instructions, and existing tests. Inspect the working
tree before changing it. Record actual progress with
`acci state demo --step inspect --status done --note "What was verified"`.

```bash
# After editing; adapt to the actual stack:
$A run demo --timeout 300 -- "python3 -m pytest -q"
$A attempt demo "specific-error-signature"  # only when attempting a fix
$A scan "$PWD" --git
git add path/to/intended/files
git diff --cached
git commit -m "Describe the change"
$G push -u origin acci/my-task
$H pr create -R OWNER/REPO --head acci/my-task --base main \
  --title "Actual change" --body "Changes, verification, and limitations"
```

Use the repository's actual default branch, not necessarily `main`.
Do not blindly stage everything or discard unrelated changes.
Export the appropriate templates **and** their report helper if the target
does not already have CI:

```bash
$A template ci-ios.yml --out .github/workflows/ios.yml
$A template report.py --out .acci/report.py
```

Review triggers, runner cost, `IOS_DIR`, scheme, permissions, and signing before
committing. The iOS template produces an unsigned simulator app by default;
its optional signing path requires separate owner setup and validation.

```bash
$H run list -R OWNER/REPO --branch acci/my-task --limit 5
# Select the actual run for the exact pushed commit:
$H run watch -R OWNER/REPO RUN_ID
$H run view -R OWNER/REPO RUN_ID --log-failed
$H run download -R OWNER/REPO RUN_ID \
  -D "$ACCI_HOME/projects/demo/artifacts/RUN_ID"
```

Check full logs as needed. Validate archive integrity, hashes, expected files,
metadata, tests, and a stack-appropriate smoke run. Do not run an untrusted
download alongside credentials. A successful compile is not device testing.

```bash
$A state demo --step verify --status done --note "Exact checks performed" \
  --link pr=https://github.com/OWNER/REPO/pull/PR_NUMBER \
  --link run=https://github.com/OWNER/REPO/actions/runs/RUN_ID
$A handoff demo
git diff -- .acci/
# Review privacy and correctness, then explicitly commit/push the handoff.
```

For a fresh agent: install ACCI, clone the task branch into a new project's
`src`, read `.acci/HANDOFF.md`, then run
`acci resume demo --from .acci/handoff.json` from that source directory.
This restores the task checkpoint, not missing code, artifacts, credentials,
or proof that the remote state is unchanged.