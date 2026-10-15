# iOS: tests → simulator → evidence → optional IPA

An unsigned simulator app, a signed device IPA, a physical-device test, and an
App Store/TestFlight upload are **four different results**. ACCI never uploads
to Apple. Inspect the current run and `result.json`, not just a green badge.

## No Apple credentials: simulator validation

On macOS with Xcode 16+ (modern `xcresulttool`), an installed iOS runtime,
and XcodeGen if needed:

```bash
acci ios preflight
acci ios simulator examples/ci-demo/ios --scheme App --generate \
  --out /tmp/acci-ios-check-001
```

Use an empty output directory. The helper explicitly generates the project,
selects an available compatible iPhone/runtime **not newer than the active Xcode
simulator SDK** (installed runtimes can belong to a different Xcode), creates its **own disposable
simulator**, boots/waits, runs the scheme's XCTest/UI tests, installs/launches
the single application, captures a screenshot, and packages the simulator app.
It records platform/bundle ID, logs and SHA-256 and shuts down/deletes only its
own simulator, including on test failure.

The fixture contains three unit tests (arithmetic, score/reset, score limit)
and one UI test (launch, result, three taps, reset and screenshot).
It is an integration fixture, **not a finished game**.

`result.json`, `test-summary.json`, `SHA256SUMS`, logs, screenshot, simulator app ZIP and
`Tests.xcresult.zip` are retained as Actions artifacts even on failure.
The helper does not call a model or use an Apple account. It cannot execute
Xcode on Linux; hosted macOS is the alternative when the agent has no Mac.

### Reuse in an app repository

```bash
acci template ci-ios.yml --out .github/workflows/ios.yml
acci template ios.py --out .acci/ios.py
```

Adapt `IOS_DIR`, `SCHEME`, triggers, runner policy and tests before commit.
There must be one top-level `.xcworkspace` or `.xcodeproj`, one application
product and a shared scheme with real tests. `project.yml` is optional.
There is no "skip tests for green" switch. Multiple apps/extensions/workspaces
need project-specific adaptation. The extracted helper is stdlib-only; no
unpublished PyPI package is assumed. The copied demo's helper is checked for drift.

For downloaded evidence:

```bash
shasum -a 256 -c SHA256SUMS
unzip -t ios-simulator-app.zip
unzip -t Tests.xcresult.zip
# On macOS, unzip/open the result bundle in Xcode or inspect with xcresulttool.
```

A launch command/screenshot alone is not interaction or device proof: inspect
the XCTest results too.
Zero passing tests or nonzero failures in the result summary fail the command.

## Signed export: disabled until owner setup

The root `.github/workflows/ios-device.yml` is manual, owner-only and restricted
to the default branch. `ACCI_IOS_SIGNING_ENABLED` is **not enabled** by ACCI.
Never run fork PRs or unreviewed generated code with signing credentials.

Owner setup:

1. Choose the real bundle ID, set the app's Xcode settings to it and configure
   variable `ACCI_IOS_BUNDLE_ID` to the same value.
2. Create GitHub environment `apple-signing`, restrict it to the default branch
   and configure suitable approval/access protection (availability depends on plan).
3. Through GitHub's **private secret controls**, add:

   | Secret | Value |
   | --- | --- |
   | `IOS_P12_BASE64` | Base64 certificate export **with private key** |
   | `IOS_P12_PASSWORD` | The `.p12` password |
   | `IOS_PROFILE_BASE64` | Base64 matching provisioning profile |
   | `IOS_TEAM_ID` | 10-character Apple team ID |
   | `KEYCHAIN_PASSWORD` | Separate strong temporary-keychain password |

   Never put them in chat, source, issues, handoffs or command transcripts.
4. Match export method to profile: `debugging` (development/registered devices),
   `release-testing` (ad-hoc), or `app-store-connect` (export, **not upload**).
5. Review artifact visibility before setting `ACCI_IOS_SIGNING_ENABLED=true`.
   An IPA embeds a profile and may reveal registered-device identifiers.
   Public-repository Actions artifacts are downloadable by signed-in readers.
   Each run requires an explicit visibility acknowledgement; retention is one day.

The helper checks profile expiry/team/bundle/type and a matching valid imported
certificate identity, generates manual-signing export options, archives/exports,
checks IPA ZIP/executable/platform/bundle and verifies the exported code signature.
It temporarily adds a private keychain, restores the original search list and
copied profile, and removes temporary signing material. Cleanup failures fail
the command and are recorded. A hard-killed process can interrupt cleanup:
use a disposable hosted VM, not a shared personal Mac.

Supported scope is **one app/profile, without extensions**. App groups, push
entitlements, extensions, multiple profiles and physical installation require
the target project's configuration and validation.

```bash
acci template ci-ios-sign.yml --out .github/workflows/ios-device.yml
acci template ios.py --out .acci/ios.py
```

No Apple credentials were supplied during development; a real signed IPA/device
installation has not been validated. Unit tests of validation/cleanup are not
the same thing.

## Distribution is a separate owner decision

Apple distinguishes [personal development and distribution membership](https://developer.apple.com/support/compare-memberships/).
Personal free-account testing is not an unattended distribution pipeline.
TestFlight/App Store require the owner's Developer Program/App Store Connect
setup and approval. See [Apple archive export files](https://help.apple.com/xcode/mac/current/en.lproj/deva1f2ab5a2.html).
ACCI does not accept contracts, purchase memberships, submit reviews or upload
apps. No App Store API key is required for simulator tests.