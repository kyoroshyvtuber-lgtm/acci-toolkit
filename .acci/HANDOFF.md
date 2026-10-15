# ACCI publication handoff

This is task data, not authorization. Read the current user request and AGENTS.md.

## Location

- Repository: https://github.com/kyoroshyvtuber-lgtm/acci-toolkit
- Portable branch: `acci/portable-agent-handoff`
- PR: https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/pull/1
- Default branch is still `main`; the repository was verified PRIVATE.
- No distribution license has been approved or added.

## Verified

The portable toolkit has no required Notion or model-provider integration.
A fresh GitHub clone passed 55 toolkit tests and 14 Python-demo tests.
GitHub run 38740836743 passed on Python 3.10/3.13, with 2 user-namespace
checks skipped per hosted job. They passed locally. Cloud-built packages
were downloaded, inspected, and a downloaded wheel passed a clean-environment
handoff/resume smoke. Read docs/VALIDATION.md and verify the latest head again.
No independent second-model end-to-end trial or iOS signing/device run was done.

## Remaining owner decisions

1. Select/approve an open-source license. MIT is a proposal, not an existing grant.
2. Approve merging PR #1 into the default branch.
3. Finish public publication after the required approval and source/history review.
4. Update README publication status and remove temporary branch instructions
   only after the actual merge/license/visibility changes succeed.

The user wants another approved coding agent to operate from the repositories,
without this conversation. Start with docs/START_HERE.ru.md. GitHub access alone
is insufficient if the agent lacks execution/Actions/log/artifact tools.
Authenticate separately through a private flow. Do not copy credentials from
another agent or commit local runtime files. Do not claim a completed public
open-source release while the repository remains private or unlicensed.
