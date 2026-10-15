# Validation record

## v0.3: iOS, games and optional bounded executor

Verified implementation checkpoint:
`bc5d603f8bf916f1470148a39c33fee01fc893bd` on `acci/ios-agent-readiness`.
This is a task branch, not an approved merge or package/store release.

- Local Linux/Python 3.13: **111 toolkit tests and 14 Python-demo tests passed**.
  Bash syntax, Python compilation, source scan and reachable-history scan checked.
  Only the existing deliberately synthetic `client_secret` fixture was found.
- [Toolkit run 38761755776](https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38761755776):
  Python 3.10/3.13 each recorded **109 passed, 2 skipped**, plus 14 demo tests.
  The skips are the existing user-namespace checks unavailable on hosted Linux;
  they passed locally. Both jobs built wheel/sdist and passed clean-wheel smoke,
  including helper/template extraction, engine plan and offline agent preview.
- Both cloud package sets were downloaded; JUnit totals, ZIP integrity, required
  source-distribution files and SHA-256 were checked. A downloaded Python 3.13
  wheel also passed the installed-wheel smoke outside the checkout. A separate
  anonymous clone at this checkpoint, with empty HOME/no inherited GitHub/
  provider/Notion credentials, passed independent bootstrap, all 111 toolkit
  tests and all 14 Python-demo tests.
- [iOS run 38761755508](https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38761755508):
  Xcode 16.4, SDK/runtime 18.5, iPhone 16 simulator, x86_64. **Three unit tests
  and one UI test passed**, with zero failures or skips. The UI scenario checked
  launch, arithmetic, three score-increment taps and reset. Installation,
  separate launch, screenshot capture and app packaging succeeded.
  Downloaded `result.json`, test summary and every `SHA256SUMS` entry were checked;
  both app and `.xcresult` ZIPs passed integrity checks. App metadata confirms
  `iphonesimulator`, not `iphoneos`. The screenshot was viewed: calculation 42,
  score 0 and both controls visible without clipping. No cleanup warning was
  recorded. [Evidence artifact](https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38761755508/artifacts/11986668320)
  is subject to Actions retention; it is not a permanent release.
- [Godot run 38758019951](https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38758019951):
  pinned, checksum-verified Godot 4.7.2 imported the fixture, passed four gameplay
  checks, exported `.pck` and launched that package. The downloaded cloud package
  passed its SHA-256 check and launched again locally without credentials.
  This run used `c8ee68d`; the game source/profile is unchanged at this checkpoint.
  This is a resource pack, **not an iOS/standalone game build**.

The optional full Godot export-template installer was also run locally with
release SHA-256 verification, followed by native Linux debug export (executable
plus resource pack) and a successful headless launch. This is additional local
engine/export validation, not an iOS, rendering or finished-game claim.

### Investigation history

- [iOS run 38758019836](https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38758019836):
  application compilation and **three unit tests passed**, but the UI runner
  timed out loading Accessibility. Evidence shows active Xcode 16.4 with selected
  iOS 26.2. Runtime selection was capped at the active Xcode SDK; the complete
  follow-up above passed without skipping UI tests. The earlier ARM
  runner never acquired a machine due to GitHub capacity; no code step ran there.
- [Earlier toolkit run 38758019821](https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38758019821)
  at `c8ee68d` passed 107 tests with two namespace skips per Python version.
  The two added regressions cover active-SDK runtime selection and exact
  proposal-bundle digest. Proposal downloads now pin immutable artifact IDs and
  trusted proposal SHA-256, not artifact names.

### Disabled and unverified paths

The optional executor remains disabled in `.acci/agent.json`, with no provider
or model chosen. Provider adapters, scope guards, exact-base apply, separate-job
credential boundaries, unique-branch/PR logic and failure paths are covered by
offline tests. **No live paid provider request or live automated agent PR was
performed.** Neither repository activation variables nor signing secrets were
configured by this change.

Still not verified: real Apple certificate/profile export, physical iPhone
installation, TestFlight/App Store, Godot→iOS export, Unity editor/license/build,
or identical behavior from arbitrary models. Signing checks/cleanup are tested
with fixtures, not a real signed IPA. See [iOS](IOS.md), [games](GAMES.md) and
[autonomy](AUTONOMY.md) for exact owner activation requirements.

## Portable toolkit (v0.2 historical record)

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

Not verified in this historical v0.2 snapshot: iOS device signing or installation, running the iOS app in a
simulator, TestFlight/App Store, Android production signing/store release,
Node build template, Windows/.NET build template, every detected framework,
or identical results from arbitrary models.

## Publication approval and verification

The owner explicitly approved the MIT license, merging PR #1, and making the
repository public. `LICENSE` records the MIT terms; package metadata and the
installed-wheel smoke check verify that the license is included.

The earlier release checkpoint was a snapshot before those approved
administrative operations; `.acci/` now tracks the current task. Check live PR state, repository visibility,
default-branch `LICENSE`, and latest main-branch CI before reporting completion
or repeating any mutation. A checkpoint is not a live status feed.

Before public sharing, review intended files and reachable git history for
secrets/private data and verify CI/clean installation. Scanners are aids, not
guarantees. Never publish credentials, local workspaces, or private Notion data.