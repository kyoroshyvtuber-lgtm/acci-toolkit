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