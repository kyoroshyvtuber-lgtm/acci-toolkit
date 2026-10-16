#!/usr/bin/env python3
"""Prepare audited build inputs. No Apple firmware, signing or account patches."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile


def replace_once(path, old, new):
    path = Path(path)
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError(f"unexpected upstream content: {path.name}: {old[:65]!r}")
    path.write_text(text.replace(old, new, 1))


def extract(archive, destination):
    """Pinned sources only; reject archive escapes and device entries too."""
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive) as t:
        members = t.getmembers()
        if len(members) > 150000 or sum(m.size for m in members) > 512 * 1024**2:
            raise ValueError("source archive limits exceeded")
        roots, paths, links = set(), set(), set()
        for m in members:
            name = Path(m.name)
            target = (destination / name).resolve()
            if not name.parts or name.is_absolute() or ".." in name.parts or not target.is_relative_to(destination):
                raise ValueError("unsafe archive path")
            if not (m.isfile() or m.isdir() or m.issym() or m.islnk()):
                raise ValueError("special archive entry")
            if str(name) in paths:
                raise ValueError("duplicate source path")
            paths.add(str(name))
            roots.add(name.parts[0])
            if m.issym():
                links.add(str(name))
                link = (target.parent / m.linkname).resolve()
                if Path(m.linkname).is_absolute() or not link.is_relative_to(destination):
                    raise ValueError("unsafe source symlink")
            if m.islnk():
                links.add(str(name))
                link = (destination / m.linkname).resolve()
                if Path(m.linkname).is_absolute() or not link.is_relative_to(destination):
                    raise ValueError("unsafe source hardlink")
        if len(roots) != 1:
            raise ValueError("expected one source root")
        for m in members:
            if any(str(p) in links for p in Path(m.name).parents):
                raise ValueError("archive member under a source link")
        # Write ordinary files first and links last. No ownership restoration,
        # special entries, overwrites, or writes through archive-created links.
        # This also avoids differing tarfile data-filter backports on Python
        # 3.10/3.13 interpreting valid relative source links differently.
        for m in members:
            target = destination / m.name
            if m.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif m.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with t.extractfile(m) as source, target.open("xb") as dest:
                    shutil.copyfileobj(source, dest)
                target.chmod(0o755 if m.mode & 0o100 else 0o644)
        for m in members:
            target = destination / m.name
            if m.issym():
                target.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(m.linkname, target)
            elif m.islnk():
                source = (destination / m.linkname).resolve()
                if not source.is_relative_to(destination) or not source.is_file():
                    raise ValueError("unsafe source hardlink target")
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open("rb") as src, target.open("xb") as dest:
                    shutil.copyfileobj(src, dest)
                target.chmod(source.stat().st_mode & 0o755)
    return destination / next(iter(roots))


def patch_qemu(q, android):
    # Use QEMU's existing AES implementation, rather than linking OpenSSL into
    # the GPL emulator. These are API substitutions, not verification bypasses.
    for relative in (
        "hw/arm/ipod_touch.c",
        "include/hw/arm/ipod_touch_aes.h",
        "include/hw/arm/ipod_touch_8900_engine.h",
    ):
        replace_once(q / relative, "#include <openssl/aes.h>", '#include "crypto/aes.h"')
    replace_once(q / "include/hw/arm/ipod_touch_sha1.h", "#include <openssl/sha.h>", "#include <glib.h>")
    replace_once(q / "include/hw/arm/ipod_touch_sha1.h", "    SHA_CTX ctx;", "    /* Digest state is local to each request. */")
    replace_once(q / "hw/arm/ipod_touch_sha1.c",
                 "static uint64_t swapLong(void *X) {\n    uint64_t x = (uint64_t) X;",
                 "static uint64_t swapLong(uint64_t x) {")
    replace_once(q / "hw/arm/ipod_touch_sha1.c",
                 "                uint64_t data_length = swapLong(",
                 "                if (s->buffer_ind < 8 || s->buffer_ind > sizeof(s->buffer)) {\n"
                 "                    return 0;\n"
                 "                }\n"
                 "                uint64_t data_length = swapLong(")
    replace_once(q / "hw/arm/ipod_touch.c",
                 "nand_state->nand_path = &nms->nand_path;",
                 "nand_state->nand_path = nms->nand_path;")
    replace_once(
        q / "hw/arm/ipod_touch_sha1.c",
        "                SHA_CTX ctx;\n                SHA1_Init(&ctx);\n                SHA1_Update(&ctx, s->buffer, data_length);\n                SHA1_Final(s->hashout, &ctx);",
        """                if (data_length > sizeof(s->buffer)) {
                    memset(s->hashout, 0, sizeof(s->hashout));
                    return 0;
                }
                GChecksum *checksum = g_checksum_new(G_CHECKSUM_SHA1);
                gsize digest_size = sizeof(s->hashout);
                g_checksum_update(checksum, s->buffer, data_length);
                g_checksum_get_digest(checksum, s->hashout, &digest_size);
                g_checksum_free(checksum);""",
    )
    # The product intentionally contains only the test board and legacy iPod
    # board, not a collection of unrelated emulators or host-sharing devices.
    (q / "configs/devices/arm-softmmu/default.mak").write_text("CONFIG_VERSATILE=y\nCONFIG_IPOD_TOUCH=y\n")
    # Upstream relied on unrelated default-enabled boards to pull in these
    # device dependencies. Declare them explicitly without adding more boards.
    replace_once(q / "hw/arm/Kconfig", "config EXYNOS4\n    bool\n",
                 "config EXYNOS4\n    bool\n    select EXYNOS4210_UART\n")
    replace_once(q / "hw/arm/Kconfig", "config IPOD_TOUCH\n    bool\n    select IPOD_TOUCH\n    select PL192",
                 "config IPOD_TOUCH\n    bool\n    select EXYNOS4210_UART\n    select PFLASH_CFI02\n    select SSI\n    select PL192")
    with (q / "hw/char/Kconfig").open("a") as out:
        out.write("\nconfig EXYNOS4210_UART\n    bool\n")
    replace_once(q / "hw/char/meson.build",
                 "softmmu_ss.add(when: 'CONFIG_EXYNOS4', if_true: files('exynos4210_uart.c'))",
                 "softmmu_ss.add(when: 'CONFIG_EXYNOS4210_UART', if_true: files('exynos4210_uart.c'))")
    if android:
        # Like Termux's Android port, omit ivshmem (Android has no SysV SHM).
        # No guest access to a host directory, KVM, network or shared memory.
        p = q / "meson.build"
        old = "have_ivshmem = config_host_data.get('CONFIG_EVENTFD')"
        if old in p.read_text():
            replace_once(p, old, "have_ivshmem = false")


def prepare(lock, downloads, output, android=False):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    roots = {}
    for source in json.loads(Path(lock).read_text())["sources"]:
        archive = Path(downloads) / source["filename"]
        if hashlib.sha256(archive.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError("source checksum mismatch: " + source["name"])
        roots[source["name"]] = extract(archive, output / source["name"])
    q = roots["qemu"]
    (q / "ui/keycodemapdb").rmdir()
    shutil.copytree(roots["keycodemapdb"], q / "ui/keycodemapdb")
    for source in ("softfloat", "testfloat"):
        target = q / "tests/fp" / ("berkeley-" + source + "-3")
        target.rmdir()
        shutil.copytree(roots[source], target)
    shutil.copytree(roots["proxy-libintl"], roots["glib"] / "subprojects/proxy-libintl")
    patch_qemu(q, android)
    result = {k: str(v) for k, v in roots.items()}
    (output / "roots.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("lock")
    p.add_argument("downloads")
    p.add_argument("output")
    p.add_argument("--android", action="store_true")
    a = p.parse_args()
    prepare(a.lock, a.downloads, a.output, a.android)