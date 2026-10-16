#!/usr/bin/env bash
set -euo pipefail
ndk="${1:?NDK root}"
out="${2:?output directory}"
here="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$out"
"$ndk/toolchains/llvm/prebuilt/linux-x86_64/bin/clang" \
  --target=arm-none-eabi -march=armv5te -marm -mfloat-abi=soft \
  -ffreestanding -fno-builtin -fno-stack-protector -nostdlib -O2 \
  -Wl,-T,"$here/guest/link.ld" \
  "$here/guest/start.S" "$here/guest/smoke.c" -o "$out/smoke.elf"
sha256sum "$out/smoke.elf" > "$out/SHA256SUMS"