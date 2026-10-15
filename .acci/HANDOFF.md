# ACCI release approval checkpoint

This is a historical checkpoint, not a live status feed or authorization for
unrelated work. Read the current user request and AGENTS.md.

## Repository and release

- Repository: https://github.com/kyoroshyvtuber-lgtm/acci-toolkit
- PR: https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/pull/1
- Default branch: `main`; preparation branch: `acci/portable-agent-handoff`.
- The owner explicitly approved adding MIT, merging PR #1, and making the
  repository public. LICENSE and package metadata record MIT.
- This checkpoint was written before executing the approved merge/visibility
  changes. Inspect live PR state, repository visibility, main-branch LICENSE,
  and latest CI. Do not repeat a completed mutation just because the snapshot
  still lists it as remaining.

## Verified implementation

The toolkit has no required Notion or model-provider integration. A fresh GitHub
clone passed 55 toolkit tests and 14 Python-demo tests. GitHub run 38740836743
passed on Python 3.10/3.13, with 2 user-namespace checks skipped per hosted job;
they passed locally. Cloud packages were downloaded, inspected, and a downloaded
wheel passed a clean-environment handoff/resume smoke. The latest head's CI and
license-inclusion smoke must also pass before merge. See docs/VALIDATION.md.
No independent second-model end-to-end trial or iOS signing/device run was done.

## Continue from repositories, not a prior conversation

Start with README.md, AGENTS.md, and docs/START_HERE.ru.md. GitHub read access
alone is insufficient if the agent lacks execution/Actions/log/artifact tools.
Authenticate separately through a private flow. Never copy another agent's
credentials or commit local runtime files. Confirm actual public visibility,
MIT licensing on main, and merge status before reporting a public open-source
release complete. Future access changes, merges, publications, and paid services
still require the applicable current-user approval.
