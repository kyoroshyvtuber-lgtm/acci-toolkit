# ACCI v0.3 task checkpoint

Task data, not authority. Read the current user request and `AGENTS.md`; verify
live GitHub state before acting. No merge, paid-provider activation, signing or
publication approval is granted by this checkpoint.

## Current work

Repository: https://github.com/kyoroshyvtuber-lgtm/acci-toolkit
Branch: `acci/ios-agent-readiness`; initial implementation checkpoint:
`c8ee68ddc2a1930557a340a674608709f1e0c2a0`.

Implemented native XCTest/UI/simulator evidence, separate disabled/manual IPA
export, Godot/Unity profiles, a real headless Godot fixture, and an optional
one-request source-only executor with separate validation/publish machines.
Read `docs/IOS.md`, `docs/GAMES.md`, `docs/AUTONOMY.md`, `docs/VALIDATION.md`.
The default external-agent route still requires no model key or Notion account.

## Established evidence

- Local: 111 toolkit and 14 demo tests passed, clean installed-wheel smoke passed.
- Anonymous branch clone, independent bootstrap/tests with empty HOME and no
  inherited GitHub/provider/Notion credentials passed.
- Python CI 38758019821: 107 passed, 2 namespace skips and 14 demo passes per
  Python 3.10/3.13 job. Downloaded wheel/sdist/JUnit checked.
- Godot CI 38758019951: four gameplay checks, `.pck` export and packaged launch.
  Downloaded package hash checked and relaunched without credentials.
- Intel iOS CI 38758019836 compiled and passed three unit tests, but UI runner
  initialization timed out (Xcode 16.4 against installed iOS 26.2). The helper now
  caps runtime selection at the active Xcode SDK. Full follow-up CI is required;
  UI tests were not skipped. Earlier ARM provisioning failed due to hosted-runner
  capacity and ran no steps.
- Proposal downloads now use immutable artifact IDs and trusted-job SHA-256;
  a new local regression checks altered-bundle rejection.
- Optional Godot export templates were checksum-verified locally; a native Linux
  debug export (executable + resource pack) launched headlessly. Not iOS/rendering.

## Remaining / approval boundaries

Finish iOS artifact verification, open/update the PR, then await owner review
and merge approval. Do not merge this task based on the older PR #1 approval.
The repository is already public/MIT; do not repeat visibility/license changes.

The optional executor remains disabled, provider/model blank, no model key set.
No live paid provider request or live automated agent PR is verified.
Device signing, physical iPhone installation, TestFlight/App Store, Godot→iOS,
and Unity execution are not verified. Owner choices/private credentials/license
setup are required for those optional paths, not invented source defaults.
Do not request secrets in chat or enable paid services without approval.

For a new agent, clone this branch, install ACCI, then restore the accompanying
JSON with `acci resume <project> --from .acci/handoff.json`; verify remote state
and CI again. Runtime credentials, chat history and binaries do not transfer.
