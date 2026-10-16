# Original Safari / Android investigation

**Research only. This is not an Android browser, IPA installer, emulator, or
working Safari APK. No Safari-on-Android execution is claimed.**

The owner wants original iOS applications on a realme GT Neo 5 SE, not a browser
reskinned to look like Safari. Do not silently replace that goal with a WebView app.

See [the recorded source inspection](VALIDATION.md) for the actual Safari build,
verified evidence and remaining execution blockers.

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
  The manufacturer lists Snapdragon 7+ Gen 2. `target-device.json` records
  **Android 16 as reported by the owner**, not as an ADB-verified device readback.

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

## Source-checked routes around the framework gap

These are findings from upstream documentation, **not experiments reproduced in
ACCI or on the owner's Android 16 phone**. A source describing a successful
research setup is not a downloadable, verified Android emulator.

### Full-system emulation of an older iOS — relevant research candidate

Instead of replacing MobileSafariUI on Android, run a matching iOS system and
application inside a virtual device. This is an architectural alternative to
reimplementing the application's entire framework dependency closure.

[eShard's iOS 14 / QEMU investigation, part I](https://www.eshard.com/blog/emulating-ios-14-with-qemu)
and [part II](https://www.eshard.com/blog/emulating-ios-14-with-qemu-part2)
describe a research setup with graphical applications, touch input and networking.
The authors also describe important limits: missing hardware facilities,
applications needing newer iOS versions, and applications requiring Metal.
Their setup includes modifications to system components; it must not be treated
as an unmodified, generally available iPhone runtime. This repository does not
provide activation, account, pairing, signature or encryption bypasses.

**Not established here:** a reproducible released set of all needed components,
an Android port, Safari execution on Android, usable performance, or arbitrary
IPA support. The Safari 27.0 **simulator** application inspected above is not an
interchangeable input for an older iOS **device** image.

There is also concrete legacy GUI work:
[QEMU-iOS](https://github.com/devos50/qemu-ios) targets the iPod Touch 1G/2G, and
[its author's iPhoneOS 1.0 account](https://devos50.github.io/blog/2022/ipod-touch-qemu)
describes display rendering and touch input. This establishes a narrow historical
precedent, not compatibility with modern Safari, current games or Android 16.

Conversely, [darwin-vm](https://github.com/jprx/darwin-vm) explicitly says that it
boots a command-line environment, not a full iPhone/Mac with graphics or GUI
applications. Its supported-boot table must not be cited as proof that Safari runs.

### Existing compatibility layers — reusable ideas, different limits

- [touchHLE](https://github.com/touchHLE/touchHLE/blob/trunk/README.md) supports an
  AArch64 Android host, but targets early iPhone OS 2.x/3.x and iOS 4.0.x
  applications; its stated goals explicitly exclude 64-bit iOS. This is a
  candidate for selected older games, not the inspected ARM64 Safari.
- [unidbg](https://github.com/zhkl0228/unidbg/blob/master/README.md) documents
  ARM32/ARM64 and experimental iOS/Objective-C/Swift execution support. It is an
  execution/research building block, not evidence of a complete Safari GUI,
  MobileSafariUI implementation or Android browser product.
- [Darling](https://www.darlinghq.org/) treats iOS support as a long-term goal and
  identifies UIKit implementation as a major missing piece.
  [ipasim](https://github.com/ipasimulator/ipasim) targets Windows and says that
  only simple applications currently work. Neither is a verified drop-in
  solution for the target phone.

### Different deliverables that must not be silently substituted

- **Old Windows Safari under a Windows compatibility environment:** Apple
  [identifies Safari 5.1.7 as the final, outdated Windows version](https://support.apple.com/en-us/102665);
  [Winlator](https://github.com/brunodev85/winlator) runs Windows applications
  through Wine and Box86/Box64 on Android. Combining those facts is only an
  **untested candidate**, not proof of Safari compatibility. The old Apple
  installer URL checked during this investigation returned 404; no installer was
  obtained or run. This is not iOS Safari and is not a safe substitute for a
  maintained browser or a place to enter personal credentials.
- **Remote Apple-hosted execution:** remote iOS devices are an existing service
  category, for example [BrowserStack's device cloud](https://www.browserstack.com/mobile-device-testing).
  An Apple-hosted browser with a remote client is a deployment alternative, not
  local IPA execution or offline use on Android. No remote session, new service,
  account or paid plan has been enabled.
- **Android WebKit application:** see the WPE route below. The engine is real,
  but it does not supply the original Safari application or an iOS runtime.

### Gate before claiming the emulator works

The full-system route is worth a bounded feasibility experiment, not a promise
of universal compatibility. First establish available, lawfully usable inputs
and reproducibility of the required open-source components, without bypassing
account or signing protections. Then test a minimal, self-authored application
and display/input path in an isolated environment before integrating an Android
shell. A Safari milestone would require the matching application/runtime to
render a controlled local test page on the actual Android device, with recorded
launch, input, output and failure evidence. A shell boot, parser test, Mac
simulator run, screenshot from another project or a green CI badge is not that
milestone. No such experiment or Android execution has been performed here.

## Separate open-source route — not the original Safari app

[Igalia WPE Android](https://github.com/Igalia/wpe-android/blob/main/README.md)
documents an actual Android WebKit port and MiniBrowser, targeting arm64/x86_64.
Building an application using that port is a different deliverable from executing
the original iOS Safari binary and needs an explicitly agreed scope.

This investigation lives in a source checkout; it is not part of the installed
ACCI CLI package. Do not merge, publish a release, enable a paid service, or
claim a supported Android application based only on a successful metadata job.

## Task checkpoint for another agent

The research-specific checkpoint is in [.acci/HANDOFF.md](.acci/HANDOFF.md) and
[.acci/handoff.json](.acci/handoff.json), not the repository root's older task
checkpoint. Review the recorded limitations and verify current remote results.
From the repository root, after installing ACCI, it can be restored with:

```bash
acci resume safari-android-research \
  --from experiments/safari_android/.acci/handoff.json
```

This restores task state only, not an Apple runtime, binaries, credentials,
downloaded artifacts or a working Android application.