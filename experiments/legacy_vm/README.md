# ACCI Legacy VM — bounded emulator prototype

Work in progress. **Not a universal IPA installer, not Safari on Android.**
The first test guest is our own MIT-licensed bare-metal ARM program, not iOS.
An actual CPU emulator must execute that guest, produce its framebuffer and
receive input before an APK can be described as an emulator prototype.

## Intended first milestone

- QEMU CPU/device engine inside an Android app, with local display and input.
- ARM64 APK for the owner's realme GT Neo 5 SE; Android 16 / API 36 target.
- Separate x86_64 Android emulator testing. That does not test a physical realme.
- No server, remote desktop service, Apple account or proprietary system image
  in the APK. The display transport stays on an app-private UNIX socket.
- A separate, explicit legacy iPod Touch 1G profile for lawful, user-supplied
  images. File-format acceptance is not proof of booting iOS or running Safari.

## Reproducible engine inputs

`sources.lock.json` pins six source archives and SHA-256 values. QEMU is
devos50/qemu-ios `ipod_touch_1g`, commit
`501c85c4f8a3503965e38d5d4f30a02c4bc9171c` (QEMU 6.2.50).
`native/prepare_sources.py` applies reviewed source transformations. It does not
patch activation, account authentication, code signing or encrypted apps.
The old experimental device model is not a security boundary: do not feed it
untrusted firmware or use it for sensitive browsing.

The native workflow builds Linux, Android arm64-v8a and Android x86_64.
Untrusted upstream build commands run in a credential-free container without
network access, with read-only source/toolchain mounts and a writable work area.
Use only standard runners. No releases or store submissions are made.

The included ARM test runs on the separate `versatilepb` board, not the iPod
board. Its UART markers and framebuffer changes are checked through real QEMU
execution. They do **not** establish iOS/Safari compatibility.

## Licensing

ACCI-authored wrapper, guest and build scripts: repository MIT license.
The linked emulator is **GPL-2.0**, not MIT; GLib is LGPL-2.1-or-later.
libffi and pixman are permissive; libfdt uses its upstream BSD/GPL dual license.
Preserve upstream notices and provide complete corresponding source/build
recipes alongside any distributed APK. See the source lock and archived
upstream license files. No Apple firmware, apps, logos or account data belong in
this repository or its public artifacts.

## Evidence

Build/run results are recorded in `VALIDATION.md` once actually verified.
An APK that compiles, an emulator that boots our guest, an iOS boot and a Safari
page load are four different milestones. Do not collapse them into one claim.