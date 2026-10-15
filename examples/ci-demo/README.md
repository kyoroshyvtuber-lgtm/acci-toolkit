# acci-test-lab

Test repository for the ACCI autonomous cloud coding pipeline. Safe to delete.

| Part | Path | CI |
|---|---|---|
| Python CLI `acci-calc` (wheel + runnable `.pyz`) | `src/`, `tests/` | `.github/workflows/ci.yml` |
| Android app (debug APK) | `android/` | `.github/workflows/android.yml` |
| iOS app (unit/UI tests, simulator install/launch, XcodeGen) | `ios/` | `.github/workflows/ios.yml` |
| Runner availability probe | — | `.github/workflows/platform-probe.yml` (manual) |

Python/Android use the original ACCI PR-report helper. iOS retains `.xcresult`,
logs, screenshot, simulator app and SHA-256 without a PR-write token.
The iOS helper is self-contained in `.acci/ios.py`; the scheme includes real
unit/UI tests. Its tiny score interaction is an integration fixture, not a
finished game. Signing/store publication are deliberately separate.
