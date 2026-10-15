# Security model and limits

- Use a dedicated workspace outside the source checkout. Never commit
  `$ACCI_HOME/secrets`, OAuth configuration, environment files, signing
  certificates, runtime logs, or unrelated user files.
- `acci run` clears inherited environment variables, limits resources/time,
  confines its working directory, redacts known token patterns, and can use
  Linux network/mount namespaces when the host permits them.
- `--no-net` fails if network isolation is unavailable. A nonempty configured
  credentials directory also causes execution to fail if it cannot be hidden.
  Do not disable this guard to make a build run.
- **This is not a complete sandbox for hostile code.** Working-directory
  confinement is not filesystem confinement. Mount hiding covers only the
  configured secrets directory; same-user processes, `/proc`, other credential
  locations, and host permissions need a stronger security boundary.
  Run unknown projects in a separate disposable, credential-free container/VM.
- Redaction and scanning are best-effort detectors, not proof that a file or
  history contains no secret. Review code, git history, handoffs, artifacts,
  workflow permissions, dependencies, and reports before public sharing.
- Tests contain deliberately synthetic token/key examples. Review any findings
  in those fixtures; never ignore a whole test tree or disable checks.
- Fork PRs are untrusted. Do not grant them signing secrets or use
  `pull_request_target` to check out and execute their code with write tokens.
- CI templates use third-party Actions version tags. Review/pin dependency
  versions and runner images for a production deployment.
- Handoffs deliberately omit environment/log/artifact dumps. Task text, links,
  and notes can still be confidential; inspect generated files before commit.

Report a vulnerability privately to the repository owner through an available
private channel. Do not post an unredacted secret in an issue. Revoke/rotate
exposed credentials before discussing remediation publicly.

## Optional proposal workflow

The committed agent policy is disabled and has no provider/model. A separate
repository-variable gate, owner actor and default-branch checks are required.
Provider-key, generated-code validation and PR-write jobs run on separate
ephemeral machines. The model returns bounded source-only JSON, never shell
commands. Tests, policy, CI, dependencies and signing are not writable.
See [the complete boundaries](AUTONOMY.md). Secret scanning and passing tests do
not prove generated code is harmless; humans must review the diff.

The publisher rechecks the original proposal/base/policy, not an artifact
produced by a machine that executed generated source. Checkout authentication
is not persisted. Validation still runs on hosted infrastructure with runtime/
artifact tokens; it is not a claim of perfect hostile-code isolation.

## Signing

Signing is separate, manual, disabled and limited to reviewed default-branch
source. Use the `apple-signing` environment and disposable hosted runners.
Check profile/certificate identity and expiry; never print private material.
Cleanup is best effort under hard process termination; the helper fails when
it detects cleanup errors. Never reuse a host with incomplete cleanup.
Signed artifacts can contain profile/device identifiers; visibility requires
explicit owner acknowledgement. See [iOS signing](IOS.md).