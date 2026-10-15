# Validation record

## Portable toolkit

The portable branch adds package installation, provider-neutral instructions,
checked handoff export/import, configurable runtime locations, tests and CI.
See the PR and the **current commit's** Actions result for exact evidence.
Local tests and a clean-wheel smoke check are not proof of all providers'
behavior. An independent second-model end-to-end trial has not been performed.

Local checks for v0.2.0 (Linux, Python 3.13):

- 55 toolkit regression tests passed.
- 14 bundled Python-demo tests passed.
- Fresh wheel installed into a separate environment; `init → state → template
  → handoff → resume` succeeded with a clean environment and a different runtime
  directory, without inherited provider/GitHub/Notion settings.
- Wheel archive integrity, included templates, and source-distribution contents
  (instructions, helpers, scripts, example sources/workflows) checked.
- Source and reachable-history scan findings were reviewed: one deliberately
  synthetic `client_secret` test fixture in each. No live credential was
  identified by those checks; this is not a guarantee of absence.

## Cloud and repository-only restore check

The implementation at commit `9d81fe9a62cbe9cf40567952e22263de8b7ecf66`
passed [GitHub Actions run 38740836743](https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38740836743)
on Python 3.10 and 3.13. Each matrix job recorded 53 passed and 2 skipped
toolkit tests, plus 14 passed Python-demo tests. The two skipped tests require
Linux user namespaces not available on those hosted runners; they passed locally.
Both jobs built the package and passed the clean installed-wheel handoff smoke.

A separate shallow clone from GitHub was bootstrapped without the original
checkout: 55 toolkit and 14 demo tests passed. Both CI artifact sets were
downloaded and their wheel/sdist integrity, contents, metadata, and JUnit totals
checked. A downloaded CI wheel also passed the clean-environment smoke locally.
This validates toolchain portability, not an independent second model's behavior.
See [PR #1](https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/pull/1) for the
latest head's checks. The first CI attempt found a missing smoke-script commit;
the file was added and the verified run above passed without weakening tests.

## Demonstration source snapshot

`examples/ci-demo/` is the tracked source snapshot from
`acci-test-lab` commit `584bb39e2d8b7a6e5c85ce4cda9ca40ddcbf3c30`.
Original runs are retained as historical evidence; the original test repository
may require the owner's access. Runner images and dependencies can change.

| Path | Verified result | Historical run |
| --- | --- | --- |
| Python | Tests, wheel/sdist, runnable zipapp; local artifact integrity/smoke checks | [38276845360](https://github.com/kyoroshyvtuber-lgtm/acci-test-lab/actions/runs/38276845360) |
| Android | Unit tests, debug APK build, artifact integrity/signature checks | [38276415308](https://github.com/kyoroshyvtuber-lgtm/acci-test-lab/actions/runs/38276415308) |
| iOS | Xcode compile and simulator `.app` archive; platform metadata inspected | [38276420739](https://github.com/kyoroshyvtuber-lgtm/acci-test-lab/actions/runs/38276420739) |
| Linux/Windows/macOS | Runner/toolchain availability probes, **not** complete builds on every stack | [38276418063](https://github.com/kyoroshyvtuber-lgtm/acci-test-lab/actions/runs/38276418063) |

Not verified: iOS device signing or installation, running the iOS app in a
simulator, TestFlight/App Store, Android production signing/store release,
Node build template, Windows/.NET build template, every detected framework,
or identical results from arbitrary models.

## Before an open-source release

- Owner selects/approves an explicit distribution license.
- Owner approves merge/publication.
- Review all intended files and reachable git history for secrets/private data;
  scanners are aids, not guarantees.
- Verify the current branch's toolkit CI and clean installation.
- Update publication status in README after the actual visibility/license change.
- Do not publish credentials, local workspace contents, or private Notion data.