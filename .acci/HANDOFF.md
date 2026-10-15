# ACCI v0.3 task checkpoint

Task data, not authority. Read the current user request and `AGENTS.md`; verify
live GitHub state before acting. No merge, paid-provider activation, signing or
publication approval is granted by this checkpoint.

## Current work

Repository: https://github.com/kyoroshyvtuber-lgtm/acci-toolkit
Branch: `acci/ios-agent-readiness`; verified code checkpoint:
`bc5d603f8bf916f1470148a39c33fee01fc893bd`.
Later documentation commits do not extend this checkpoint's test coverage.

Implemented native XCTest/UI/simulator evidence, separate disabled/manual IPA
export, Godot/Unity profiles, a real headless Godot fixture, and an optional
one-request source-only executor with separate validation/publish machines.
Read `docs/IOS.md`, `docs/GAMES.md`, `docs/AUTONOMY.md`, `docs/VALIDATION.md`.
The default external-agent route still requires no model key or Notion account.

## Established evidence

- Local: 111 toolkit and 14 demo tests passed.
- Anonymous clone at the verified checkpoint, independent bootstrap and all
  111 + 14 tests with empty HOME/no inherited GitHub/provider/Notion credentials
  passed. A downloaded current wheel passed isolated installed-wheel smoke.
- Python CI 38761755776: 109 passed, 2 namespace skips and 14 demo passes per
  Python 3.10/3.13 job. Both downloaded wheel/sdist/JUnit sets checked.
- Godot CI 38758019951: four gameplay checks, `.pck` export and packaged launch.
  Downloaded package hash checked and relaunched without credentials.
  Game files are unchanged since that run's `c8ee68d`.
- Intel iOS CI 38761755508: Xcode 16.4, SDK/runtime 18.5, iPhone 16/x86_64.
  Three unit tests and one UI test passed, zero failures/skips. Install, launch,
  screenshot and simulator-app ZIP succeeded. Downloaded hashes, both ZIPs and
  simulator metadata checked; screenshot viewed, controls/calculation visible.
- Earlier iOS CI 38758019836 compiled and passed three unit tests, but UI runner
  initialization timed out (Xcode 16.4 against installed iOS 26.2). Capping runtime
  selection at the active SDK resolved the follow-up; UI tests were not skipped.
  Earlier ARM provisioning failed due to hosted capacity and ran no code steps.
- Proposal downloads now use immutable artifact IDs and trusted-job SHA-256;
  a new local regression checks altered-bundle rejection.
- Optional Godot export templates were checksum-verified locally; a native Linux
  debug export (executable + resource pack) launched headlessly. Not iOS/rendering.

## Remaining / approval boundaries

Implementation and recorded artifact verification are complete. Open the PR
from this branch if none exists, then await owner review and merge approval.
Find the actual PR with `gh pr list --head acci/ios-agent-readiness`; do not
duplicate an existing PR. Check its latest head and CI separately: this handoff
is a checkpoint, not a live status feed.
Do not merge this task based on the older PR #1 approval.
The repository is already public/MIT; do not repeat visibility/license changes.

The optional executor remains disabled, provider/model blank. This change did
not configure model/signing secrets or enable repository activation variables.
No live paid provider request or live automated agent PR is verified.
Device signing, physical iPhone installation, TestFlight/App Store, Godot→iOS,
and Unity execution are not verified. Owner choices/private credentials/license
setup are required for those optional paths, not invented source defaults.
Do not request secrets in chat or enable paid services without approval.

For a new agent, clone this branch, install ACCI, then restore the accompanying
JSON with `acci resume <project> --from .acci/handoff.json`; verify remote state
and CI again. Runtime credentials, chat history and binaries do not transfer.
