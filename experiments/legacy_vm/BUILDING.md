# Build and test without the original chat

This is a prototype, not a finished iOS compatibility product.
Never infer Safari execution from the ARM smoke guest.

## Recommended: the checked-in GitHub workflow

1. Clone the repository, check out `acci/safari-investigation`, and inspect
   `AGENTS.md`, this directory and `.github/workflows/legacy-vm.yml`.
2. Use standard `ubuntu-24.04` runners only. Push an approved feature-branch
   change or run the **ACCI Legacy VM prototype** workflow on that branch.
   In a fork, adjust its push branch filter deliberately.
3. Inspect all native build logs, Linux framebuffer/input smoke evidence,
   Android unit/lint results and Android 16 AVD evidence.
4. Download the APK **and corresponding-source ZIP** together. Verify their
   SHA-256 hashes and APK signing certificate. A debug build uses an ephemeral
   development certificate; do not uninstall an existing user app to work
   around a signature mismatch without asking.
5. AVD execution is x86_64. ARM64 compilation/ELF inspection is not a physical
   realme GT Neo 5 SE test.

No secrets or Apple account are required. Network access is used only to fetch
checksum-pinned source/toolchain/build dependencies. Native upstream configure
and build commands execute later in an offline container without credentials.

## Local recipe

Linux x86_64 host with Docker, Python 3.10+, JDK 17, Android SDK 36/build-tools 36,
NDK **29.0.14206865**, and Gradle **8.13**. SDK/toolchain licenses must be accepted
through their normal setup. No paid service is required.

From the repository root:

```bash
P="$PWD/experiments/legacy_vm"
W="${TMPDIR:-/tmp}/acci-legacy-build-$(date +%s)"
NDK="$ANDROID_HOME/ndk/29.0.14206865"
mkdir -p "$W/downloads" "$W/work"
python3 "$P/native/fetch_sources.py" "$P/sources.lock.json" "$W/downloads"
python3 -m unittest discover -s "$P/tests" -v
docker build -t acci-legacy-builder "$P/native"
for ABI in linux arm64-v8a x86_64; do
  docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges \
    --user "$(id -u):$(id -g)" \
    -v "$P:/project:ro" -v "$W/downloads:/downloads:ro" \
    -v "$NDK:/ndk:ro" -v "$W/work:/work" \
    acci-legacy-builder bash /project/native/build.sh "$ABI"
done
docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" \
  -v "$P:/project:ro" -v "$NDK:/ndk:ro" -v "$W/work:/work" \
  acci-legacy-builder bash -c \
  'bash /project/native/build_guest.sh /ndk /work/dist/guest &&
   python3 /project/native/smoke.py /work/dist/linux/libacci_qemu.so \
     /work/dist/guest/smoke.elf /work/dist/smoke'
for ABI in linux arm64-v8a x86_64; do
  DEST="$W/artifacts/legacy-native-$ABI"
  mkdir -p "$DEST"
  cp -a "$W/work/dist/$ABI" "$DEST/"
  git rev-parse HEAD > "$DEST/source-commit.txt"
done
cp -a "$W/work/dist/guest" "$W/work/dist/smoke" "$W/artifacts/legacy-native-linux/"
python3 "$P/android/stage.py" "$PWD" "$W/artifacts" "$W/downloads" "$W/output" \
  "$(git rev-parse HEAD)" "local-build" "$NDK"
cd "$P"
gradle --no-daemon :app:testDebugUnitTest :app:lintDebug :app:assembleDebug
```

Use a new writable work directory for each native source build: extraction
intentionally refuses to overwrite an existing tree. Do not run it against the
operator's credential directory. Generated JNI binaries and assets are ignored
by Git; never commit proprietary firmware.

The APK also bundles the same NDK's `libc++_shared.so` for each ABI. Its bytes,
dependencies and 16 KiB LOAD alignment are audited, not silently assumed to be
part of Android. QEMU searches only the installer-owned native library
directory. Toolchain revision, runtime SHA-256 values and complete NDK notices
are included in the build identity / source bundle. No runtime download is
needed on the phone.

The resulting debug APK is `app/build/outputs/apk/debug/app-debug.apk`.
Inspect it with SDK `apksigner verify --verbose --print-certs` and `aapt dump
badging`. Run `android/avd_smoke.py APK OUTPUT` only against an explicitly
selected, disposable API 36 x86_64 AVD. It changes that AVD's screen settings
and installs this debug app, not a real user's phone.

## User-supplied legacy profile format

Only for trusted files that the user is entitled to use. This is a structural
contract copied from the selected device model, not an extractor or a method
to obtain/decrypt/activate Apple software.

```text
manifest.json
bootrom.bin                 # 1..65536 bytes
iboot.bin                   # 1..4194304 bytes
nor.bin                     # exactly 1048576 bytes
nand/bank0/0.page            # each page: 2048 data + 64 spare bytes
nand/bank0/1.page
...                         # bank0..bank7, numeric page names
```

The manifest has exactly these three fields (order is flexible):

```json
{"schema":1,"machine":"ipod-touch-1g","engineCommit":"501c85c4f8a3503965e38d5d4f30a02c4bc9171c"}
```

At least one NAND page is required. At most 150,000 entries / 384 MiB unpacked;
unknown files, duplicate paths, traversal, oversized files and directory
payloads are rejected. Imported data is written as ordinary files, never
followed as archive-created symlinks. Replacement is staged; validation errors
do not overwrite the previous profile.

Runtime uses a private copy of the profile and a snapshot NOR drive. Guest
changes are disposable: the old upstream NAND model does not provide reliable
persistence. There is no host sharing, network, Apple ID, IPA installer,
activation service, signing/encryption bypass or background execution.
The run stops on leaving the Activity and at 10 minutes. A structurally accepted
profile can still fail to boot. No such iOS boot is claimed here.