# Original Safari / Android investigation

**Research only. This is not an Android browser, IPA installer, emulator, or
working Safari APK. No Safari-on-Android execution is claimed.**

The owner wants original iOS applications on a realme GT Neo 5 SE, not a browser
reskinned to look like Safari. Do not silently replace that goal with a WebView app.

## Sources and acquisition boundaries

- [Official Safari App Store page](https://apps.apple.com/sc/app/safari/id1146562112).
  Finding this page is not the same as acquiring a standalone device IPA.
- [Apple Safari resources](https://developer.apple.com/safari/resources/).
  Safari Technology Preview downloads target macOS, not Android.
- [GitHub Xcode 27 image inventory](https://github.com/actions/runner-images/blob/main/images/macos/xcode-27-arm64-Readme.md)
  documents an installed iOS 27.0 simulator. The workflow reads the Safari bundle
  already present there. It does **not** download an unlicensed IPA from a mirror,
  bypass encryption/signing, request an Apple password, or redistribute Apple code.
- [Target phone](https://www.realme.com/cn/realme-gt-neo-5-se).
  The manufacturer lists Snapdragon 7+ Gen 2. `target-device.json` keeps the actual
  installed Android version unknown; the shipping OS is not a device readback.

The workflow's `xcode-27` label is a standard ARM preview image, not `-xlarge`.
Preview availability and software can change. Inspect actual run evidence.

## What the experiment does

1. Run format/collector unit tests.
2. Locate original MobileSafari in the newest readable installed iOS runtime.
3. Record its declared version, CPU slices, Mach-O platform, minimum OS,
   direct dynamic-library dependencies and executable digest.
4. Export **only JSON/text metadata and SHA-256**, never Apple executables,
   framework libraries, runtime images, browser data, or a fabricated APK.

The simulator application is **not an iPhone device IPA**. Matching ARM CPU
architecture does not supply Android with iOS frameworks, system services,
entitlements, or a compatible application runtime. Static analysis is not execution.

## Local use

```bash
python3 -m unittest discover -s experiments/safari_android -p 'test_*.py' -v
python3 experiments/safari_android/safari_probe.py /path/to/owned-app.ipa \
  --out /new/metadata.json
# Only on a suitable Mac, read an already installed simulator application:
python3 experiments/safari_android/inspect_installed_safari.py --out /new/evidence
```

The general static probe accepts a raw Mach-O, `.app` directory, or IPA/app ZIP.
It reads selected entries without extracting or executing them. Only direct
imports are listed; it does not resolve a complete framework dependency closure.
Input identifiers are declarations, not signature/authenticity verification.
Unit tests use synthetic fixtures, not redistributed Apple app binaries.

## Separate open-source route — not the original Safari app

[Igalia WPE Android](https://github.com/Igalia/wpe-android/blob/main/README.md)
documents an actual Android WebKit port and MiniBrowser, targeting arm64/x86_64.
Building an application using that port is a different deliverable from executing
the original iOS Safari binary and needs an explicitly agreed scope.

This investigation lives in a source checkout; it is not part of the installed
ACCI CLI package. Do not merge, publish a release, enable a paid service, or
claim a supported Android application based only on a successful metadata job.