#!/usr/bin/env bash
# Runs INSIDE the credential-free, offline build container.
set -euo pipefail
abi="${1:?linux|arm64-v8a|x86_64}"
case "$abi" in linux|arm64-v8a|x86_64) ;; *) echo "unsupported ABI" >&2; exit 2 ;; esac
project=/project
work="/work/$abi"
mkdir -p "$work" /work/dist
preserve_logs() {
  result=$?
  mkdir -p "/work/dist/$abi"
  for relative in qemu-build/config.log qemu-build/meson-logs/meson-log.txt glib-build/meson-logs/meson-log.txt; do
    if [[ -f "$work/$relative" ]]; then
      cp "$work/$relative" "/work/dist/$abi/$(echo "$relative" | tr / _)"
    fi
  done
  return "$result"
}
trap preserve_logs EXIT
export HOME="$work/home"
mkdir -p "$HOME"
android=()
if [[ "$abi" != linux ]]; then android=(--android); fi
python3 "$project/native/prepare_sources.py" "$project/sources.lock.json" /downloads "$work/src" "${android[@]}"
root() { python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$work/src/roots.json" "$1"; }
qemu="$(root qemu)"
jobs="${BUILD_JOBS:-3}"
extra=()
if [[ "$abi" != linux ]]; then
  tool=/ndk/toolchains/llvm/prebuilt/linux-x86_64/bin
  case "$abi" in
    arm64-v8a) triple=aarch64-linux-android; cpu=aarch64; meson_cpu=aarch64 ;;
    x86_64) triple=x86_64-linux-android; cpu=x86_64; meson_cpu=x86_64 ;;
    *) echo "unsupported ABI" >&2; exit 2 ;;
  esac
  export PATH="$tool:$PATH"
  export CC="$tool/${triple}28-clang"
  real_cxx="$tool/${triple}28-clang++"
  cat > "$work/cxx-static" <<EOF
#!/bin/bash
# Only C++ link commands get this driver flag. Passing it to C/PIE
# configuration probes produces an unused-argument error under -Werror.
for arg do
  case "\$arg" in
    -c|-S|-E|-fsyntax-only|--version|-v|-dumpmachine|-dumpversion|--print-*|-print-*)
      exec "$real_cxx" "\$@" ;;
  esac
done
exec "$real_cxx" -static-libstdc++ "\$@"
EOF
  chmod +x "$work/cxx-static"
  export CXX="$work/cxx-static"
  export AR="$tool/llvm-ar" RANLIB="$tool/llvm-ranlib" STRIP="$tool/llvm-strip"
  export NM="$tool/llvm-nm" OBJCOPY="$tool/llvm-objcopy" LD="$tool/ld.lld"
  prefix="$work/prefix"
  mkdir -p "$prefix/lib/pkgconfig" "$prefix/include"
  export CFLAGS="-O2 -fPIC"
  export LDFLAGS="-Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384"
  export PKG_CONFIG_LIBDIR="$prefix/lib/pkgconfig"
  export PKG_CONFIG_PATH="$PKG_CONFIG_LIBDIR"
  cat > "$work/pkg-config-static" <<'EOF'
#!/bin/sh
exec /usr/bin/pkg-config --static "$@"
EOF
  chmod +x "$work/pkg-config-static"
  export PKG_CONFIG="$work/pkg-config-static"
  cat > "$prefix/lib/pkgconfig/zlib.pc" <<EOF
Name: zlib
Description: Android system zlib
Version: 1.2.8
Libs: -lz
EOF
  cat > "$work/cross.ini" <<EOF
[binaries]
c = '$CC'
cpp = '$CXX'
ar = '$AR'
strip = '$STRIP'
pkgconfig = '$PKG_CONFIG'
[host_machine]
system = 'android'
cpu_family = '$meson_cpu'
cpu = '$meson_cpu'
endian = 'little'
[properties]
needs_exe_wrapper = true
EOF
  ffi="$(root libffi)"
  mkdir -p "$work/ffi-build"
  (cd "$work/ffi-build"; "$ffi/configure" --host="$triple" --prefix="$prefix" --libdir="$prefix/lib" --disable-shared --enable-static --disable-docs; make -j"$jobs"; make install)
  glib="$(root glib)"
  meson setup "$work/glib-build" "$glib" --cross-file "$work/cross.ini" --prefix "$prefix" --libdir lib \
    --default-library static --buildtype release --wrap-mode nodownload -Dinternal_pcre=true -Diconv=libc \
    -Dlibmount=disabled -Dselinux=disabled -Dxattr=false -Dman=false -Dgtk_doc=false \
    -Dinstalled_tests=false -Dnls=disabled -Dsysprof=disabled
  ninja -C "$work/glib-build" -j"$jobs"
  ninja -C "$work/glib-build" install
  pixman="$(root pixman)"
  meson setup "$work/pixman-build" "$pixman" --cross-file "$work/cross.ini" --prefix "$prefix" --libdir lib \
    --default-library static --buildtype release -Dtests=disabled -Ddemos=disabled \
    -Dgtk=disabled -Dlibpng=disabled -Dopenmp=disabled -Darm-simd=disabled -Da64-neon=disabled
  ninja -C "$work/pixman-build" -j"$jobs"
  ninja -C "$work/pixman-build" install
  dtc="$(root dtc)"
  (cd "$dtc"; make -j"$jobs" CC="$CC" AR="$AR" NO_PYTHON=1 NO_YAML=1 CFLAGS="$CFLAGS" libfdt/libfdt.a)
  cp "$dtc/libfdt/libfdt.a" "$prefix/lib/"
  cp "$dtc/libfdt/"{fdt.h,libfdt.h,libfdt_env.h} "$prefix/include/"
  cat > "$prefix/lib/pkgconfig/libfdt.pc" <<EOF
Name: libfdt
Description: static device tree library
Version: 1.7.0
Libs: -L$prefix/lib -lfdt
Cflags: -I$prefix/include
EOF
  extra=(--cpu="$cpu" --cross-prefix="$tool/$triple-" --cc="$CC" --cxx="$CXX" \
    --extra-cflags="-I$prefix/include" --extra-ldflags="-L$prefix/lib $LDFLAGS" \
    --with-coroutine=sigaltstack)
fi
mkdir -p "$work/qemu-build"
(
  cd "$work/qemu-build"
  "$qemu/configure" --target-list=arm-softmmu --without-default-features \
    --enable-system --disable-user --enable-tcg --enable-vnc --enable-fdt \
    --disable-tools --disable-docs --disable-blobs --disable-werror --enable-pie \
    --with-git-submodules=ignore --audio-drv-list= --meson=meson "${extra[@]}"
  ninja -j"$jobs" qemu-system-arm
)
mkdir -p "/work/dist/$abi"
cp "$work/qemu-build/qemu-system-arm" "/work/dist/$abi/libacci_qemu.so"
if [[ "$abi" != linux ]]; then
  "$STRIP" --strip-unneeded "/work/dist/$abi/libacci_qemu.so"
  "$tool/llvm-readelf" -h -l -d "/work/dist/$abi/libacci_qemu.so" > "/work/dist/$abi/elf.txt"
  cp /ndk/source.properties "/work/dist/$abi/ndk-source.properties"
  "$CXX" --version > "/work/dist/$abi/compiler-version.txt"
  test -s /ndk/NOTICE.toolchain
  cp /ndk/NOTICE.toolchain "/work/dist/$abi/NDK-NOTICE.toolchain"
  if [[ -f /ndk/NOTICE ]]; then cp /ndk/NOTICE "/work/dist/$abi/NDK-NOTICE"; fi
fi
cp "$qemu/COPYING" "/work/dist/$abi/QEMU-COPYING"
mkdir -p "/work/dist/$abi/keymaps"
cp "$qemu/pc-bios/keymaps/en-us" "/work/dist/$abi/keymaps/en-us"
(cd "/work/dist/$abi"; sha256sum libacci_qemu.so keymaps/en-us > SHA256SUMS)