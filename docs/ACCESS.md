# Tools and least-privilege access

## Full CLI route

The agent needs a Linux shell, Python 3.10+, Bash, Git, and GitHub CLI (`gh`).
Use the platform's approved GitHub connection or an interactive/device login.
Do not paste a PAT, Apple certificate, or private key into a chat.

`bin/acci-gh` and `bin/acci-git` find `gh` in this order:
`ACCI_GH`, `$ACCI_HOME/opt/gh`, then `PATH`.
Their private configuration defaults to `$ACCI_HOME/secrets/gh`.
`ACCI_GH_CONFIG_DIR` or an existing `GH_CONFIG_DIR` can explicitly override it.
The project runner does not inherit GitHub token environment variables.
Credentials stored outside `$ACCI_HOME/secrets` are **not** hidden by ACCI.

For the private configuration:

```bash
mkdir -p "$ACCI_HOME/secrets/gh"
chmod 700 "$ACCI_HOME/secrets" "$ACCI_HOME/secrets/gh"
GH_CONFIG_DIR="$ACCI_HOME/secrets/gh" gh auth login --web --git-protocol https
bin/acci-gh repo view OWNER/REPO
```

If device authentication is offered, show the user the verification URL and
one-time code for their own browser. Do not handle their password.
Check the authenticated account and selected repository before writing.

## Repository access

For an existing repository, grant only the operations used by the task:

| Operation | Fine-grained permission |
| --- | --- |
| Read/write source and task branches | Contents: read/write |
| Change `.github/workflows` | Workflows: read/write |
| Create/update PRs and their reports | Pull requests: read/write |
| Inspect, dispatch, download Actions results | Actions: read/write for dispatch; read for inspection |
| Repository identity | Metadata: read |

Provider, organization, and token policies may impose additional restrictions.
Validate each needed operation rather than assuming a permission label works.
An OAuth integration must also include the chosen repository.
Public source can be read without write access; public does not mean anyone can push.
Administration is only needed for administrative tasks, not routine development.

## Connector-only route

A connector with content, branch, and PR tools can perform those operations.
`acci payload/compare/synced` helps when a local checkout exists but direct Git
authentication is unavailable. Read the actual connector schema; tool names vary.

**The GitHub MCP toolset used in the original session did not expose Actions
dispatch, logs, or artifact download.** Such a connector alone cannot reproduce
the full verified loop. A push-triggered workflow can start a build, but a link
or green badge is not a replacement for inspecting logs and artifacts.
Use approved CLI/API tools for the missing operations or report partial coverage.

## Build credentials and costs

Unsigned simulator builds need no Apple signing credentials. Device builds
need valid signing material and project-specific export settings. TestFlight
and App Store distribution require the owner's Apple Developer setup.
Android debug builds differ from production signing and store release.
Real device signing and publication were not validated by the demo. Profile
checking/cleanup tests are not a real signed-IPA run. See [IOS.md](IOS.md).

Check the owner's current GitHub Actions plan, runner availability, limits,
and organization policy. Do not assume any runner or build is free.
No workflow in this repository publishes to a store or registry automatically.
The optional model executor is disabled; provider/model/key and spending
approval are separate. It is not required for an external coding agent.
See [AUTONOMY.md](AUTONOMY.md).