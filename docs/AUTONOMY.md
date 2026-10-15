# Two ways to work with an agent

## External coding agent (default; no model key required)

Give an approved coding agent ACCI, a target repository and a task. It follows
`AGENTS.md`, uses its own tools/GitHub access, tests/builds, inspects artifacts and
opens a PR. This remains the route for large changes, new apps/assets/dependencies
and arbitrary providers. ACCI does not grant access or promise identical code.

## Bounded unattended tasks (optional, disabled)

`.github/workflows/agent.yml` implements **one-request proposal → separate
validation → review PR** for this repository's demo sources, not a general
daemon/arbitrary shell agent. It never merges, signs, releases or uploads apps.

The committed `.acci/agent.json` has `enabled: false`, no provider/model.
Repository variable `ACCI_AGENT_ENABLED=true` is independently required.
Opening an issue or pushing this PR does not activate paid provider calls.

### Enforced scope

- Fixed official OpenAI Responses or Anthropic Messages HTTPS endpoint; no
  arbitrary endpoint, inherited proxy, redirects, tools or model-supplied shell.
- Explicit owner-selected model; **one request per task/run**, no automatic retry.
  Timeout and hard context/file/change/output-token ceilings.
- Existing tracked UTF-8 source only, in explicit writable roots. No new files,
  deletion, symlinks/hardlinks, binaries, detected secrets, test/dependency/CI/
  hidden configuration or instruction edits.
- Exact base SHA, policy digest and original file hashes checked again on apply.
  Every change is validated before the first write.
- Task/source scanning before submission and output scanning before apply.
  Scanners cannot detect every secret or malicious source behavior.
- Existing tests are read-only context; validation commands are trusted workflow
  code, never model output.

### Separate machines/credentials

| Job | Capability | Work |
| --- | --- | --- |
| `propose` | Model key only in one step; repository read | Reads selected files as data; one request; immutable source bundle; never executes project/generated code |
| `validate` | No model/signing/write keys; no persisted checkout auth | Revalidates bundle; fixed Python regressions/demo/package checks |
| `validate-ios` | Same restrictions; separate hosted macOS VM | Revalidates original bundle; XCTest/UI/simulator checks |
| `publish` | Contents/PR write; fresh trusted VM | Revalidates original bundle; unique `acci/agent-<run>-<attempt>` branch and PR |

Publish depends on **both** validations and does not execute generated source.
All jobs use the same immutable event commit. Validation machines do not supply
replacement source bundles to the publisher. This reduces credential exposure,
not a proof of source safety: review the PR. Hosted runners still have
artifact/runtime infrastructure tokens.

### Owner activation (not performed in this update)

1. Review/merge workflow and policy.
2. Choose `openai` or `anthropic` and an **actual available model identifier**.
   It must support the corresponding API/output format; not every model is tested.
3. Review `context_paths` (data sent outside GitHub) and `write_paths`.
   Defaults only cover bundled Python/iOS demo sources. For another project,
   adapt the fixed validation jobs/tests as well, not just paths.
4. Choose token ceilings and provider-account spending limits. Token ceilings
   are **not a guaranteed currency budget**; pricing/billing are provider-specific.
5. Add `ACCI_MODEL_KEY` in GitHub's private Actions-secret controls, never chat,
   `.env`, source, issues, logs or policy.
6. Allow GitHub Actions to create PRs and use contents/PR write permission.
   Runtime repository administration permission is unnecessary.
7. Commit `enabled: true`; set repository variable `ACCI_AGENT_ENABLED=true`.
8. Dispatch **Bounded agent task** on the default branch or personally label a
   reviewed issue `acci:run`.

Only the personal repository owner triggers it. Organization repositories need
an owner-reviewed actor policy; this template does not admit all members.
Owner labelling approves sending issue title/body and selected source to the
chosen provider. Other issue authors, comments, fork PRs and non-default branches
do not trigger calls. No schedule. Re-labelling/manually re-running can cost again.
Concurrency is serialized, not a spending budget.

`GITHUB_TOKEN` normally does not trigger new workflows for its own commits,
so this executor validates **before** publishing. For independent post-PR checks,
configure a scoped GitHub App in a separately reviewed change, not a casual broad
PAT substitution. If branch push succeeds but PR creation fails, inspect remote
branch/PR/run before retrying: write outcomes can be ambiguous.

### Local offline preview

```bash
printf '%s\n' 'Clarify arithmetic without changing behavior' > /tmp/task.txt
# Clean tracked tree required. NEVER calls a provider:
acci agent preview --root . --task-file /tmp/task.txt --out /tmp/acci-context.json
```

The preview contains selected **source content**; review it privately. It is
not an executable patch. For another repository, start with disabled policy:

```bash
acci template agent.example.json --out .acci/agent.json
```

`acci agent propose` is the deliberately different, potentially paid command.
`apply`/`publish` are trusted workflow operations, not bypasses for validation.
Adapters/failure paths are tested with offline mock HTTP; no live paid-provider
end-to-end execution is claimed.

References: [OpenAI Responses](https://developers.openai.com/api/reference/resources/responses/methods/create),
[Anthropic Messages](https://docs.anthropic.com/ja/api/messages).