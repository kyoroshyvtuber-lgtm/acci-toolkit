# acci-test-lab

Test repository for the ACCI autonomous cloud coding pipeline. Safe to delete.

| Part | Path | CI |
|---|---|---|
| Python CLI `acci-calc` (wheel + runnable `.pyz`) | `src/`, `tests/` | `.github/workflows/ci.yml` |
| Android app (debug APK) | `android/` | `.github/workflows/android.yml` |
| iOS app (simulator build, XcodeGen) | `ios/` | `.github/workflows/ios.yml` (manual) |
| Runner availability probe | — | `.github/workflows/platform-probe.yml` (manual) |

Every CI job posts an ACCI report (steps, versions, tests, artifact SHA-256, log tails) to the PR.
