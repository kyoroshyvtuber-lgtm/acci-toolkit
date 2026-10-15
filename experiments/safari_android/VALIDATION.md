# Source inspection checkpoint — not Android execution

Code checkpoint: `5bef3848f8405f131aff724476db25a5c3944a4d`.
Later documentation commits do not change the inspected collector.

## An original Safari reference was located

[GitHub run 38780015419](https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38780015419)
read the original MobileSafari bundle already installed in the hosted
`xcode-27-arm64` image. It was not obtained from an IPA mirror.

- Safari declared short version: **27.0**.
- Safari declared build: **8625.1.29.10.29**.
- Bundle identifier: `com.apple.mobilesafari`.
- Source runtime: **iOS Simulator 27.0**, build `24A434`.
- Toolchain: Xcode 27.0, build `27A266a`; simulator SDK 27.0.
- Executable: **ARM64**, with Mach-O platform **iOS Simulator**, minimum OS 27.0.
- Executable SHA-256:
  `9ee37c065aad7bae6294e9d3575a14503c6c81671a370eeff0a01863e96a0a70`.

The main executable directly imports:

```text
/System/Library/Frameworks/Foundation.framework/Foundation
/System/Library/PrivateFrameworks/MobileSafariUI.framework/MobileSafariUI
/usr/lib/libSystem.B.dylib
/usr/lib/libobjc.A.dylib
```

This is only the main executable's direct dependency list, **not** a resolved
framework/API dependency closure. The inspection does not implement or provide
those dependencies on Android.

## What was checked

- 22 format/collector unit tests passed locally and in the Mac job.
  These tests verify the tools, not Safari runtime compatibility.
- The base toolkit's 55 local tests and 14 Python-demo tests passed.
  [Toolkit CI 38780015120](https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38780015120)
  also succeeded.
- The downloaded [metadata artifact](https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38780015419/artifacts/11995256286)
  contained exactly `safari-metadata.json`, `SUMMARY.md` and `SHA256SUMS`.
  Both recorded file hashes matched. No Apple binary was exported.
- Source/history scanning was reviewed: no findings in the research source;
  reachable history retains the existing deliberately synthetic scanner fixture.
  Scanning is not proof of absence of secrets.

## What was NOT done

- No Safari launch on the Mac simulator or Android.
- No iPhone device IPA acquisition.
- No signing/encryption bypass or extraction of protected libraries.
- No implementation of an Android-compatible iOS runtime or MobileSafariUI.
- No working Safari APK, browser substitute, physical-device test or release.

The phone model is owner-reported **realme GT Neo 5 SE**. Its chipset is recorded
from the manufacturer's page; the expected `arm64-v8a` target is not an ADB
readback. The owner's currently installed Android version remains unknown.

The earlier missing reference has therefore been reduced to a concrete,
inspectable simulator build. **It has not established the requested iOS-on-Android
compatibility.** CPU architecture matching does not resolve the Apple runtime,
framework, system-service and device-platform differences.