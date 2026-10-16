#!/usr/bin/env python3
"""Verify native artifacts, stage APK inputs and package corresponding source."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import tarfile
import zipfile
from elf_check import inspect


def checked(path, checksum_file, name=None):
    name = name or path.name
    entries = {}
    for line in checksum_file.read_text().splitlines():
        digest, filename = line.split(maxsplit=1)
        entries[filename.lstrip("*")] = digest
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if entries.get(name) != actual:
        raise ValueError("native artifact checksum mismatch: " + name)
    return actual


def main(repo, artifacts, downloads, out, commit, run_url, ndk):
    project = repo / "experiments/legacy_vm"
    out.mkdir(parents=True, exist_ok=True)
    assets = project / "app/src/main/assets/generated"
    assets.mkdir(parents=True, exist_ok=True)
    identity = {"schema": 1, "app_source_commit": commit, "run_url": run_url,
                "qemu_commit": json.loads((project/"sources.lock.json").read_text())["qemu_commit"],
                "ios_boot_verified": False, "safari_verified": False, "native": {}}
    def revision(path):
        match = re.search(r"^Pkg\.Revision\s*=\s*(\S+)", path.read_text(), re.M)
        if not match: raise ValueError("missing NDK revision")
        return match[1]
    ndk_revision = revision(ndk/"source.properties")
    if ndk_revision != "29.0.14206865":
        raise ValueError("this build pins NDK 29.0.14206865")
    for abi, machine in [("arm64-v8a",183),("x86_64",62)]:
        source = artifacts / ("legacy-native-" + abi)
        binary = source / abi / "libacci_qemu.so"
        checked(binary, source/abi/"SHA256SUMS")
        # Satisfy the actual ELF dependency, rather than relaxing the check for
        # an absent runtime or assuming a compiler flag produced a static link.
        triple = "aarch64-linux-android" if abi == "arm64-v8a" else "x86_64-linux-android"
        runtime = ndk/"toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/lib"/triple/"libc++_shared.so"
        runtime_audit = inspect(runtime,machine,shared=True)
        if revision(source/abi/"ndk-source.properties") != ndk_revision:
            raise ValueError("native engine and C++ runtime use different NDK revisions")
        audit = inspect(binary,machine,bundled={"libc++_shared.so"})
        audit["bundled_libraries"] = {"libc++_shared.so": runtime_audit}
        audit["ndk_revision"] = ndk_revision
        audit["native_build_commit"] = (source/"source-commit.txt").read_text().strip()
        identity["native"][abi] = audit
        target = project / "app/src/main/jniLibs" / abi
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(binary, target/binary.name)
        shutil.copy2(runtime, target/runtime.name)
    guest = artifacts/"legacy-native-linux/guest/smoke.elf"
    identity["guest_sha256"] = checked(guest,guest.parent/"SHA256SUMS")
    linux_evidence = json.loads((artifacts/"legacy-native-linux/smoke/evidence.json").read_text())
    if (linux_evidence.get("ios") is not False or not linux_evidence.get("uart_input") or
        not linux_evidence.get("frame_changed_after_key") or not linux_evidence.get("framebuffer_pixels_verified") or
        linux_evidence.get("guest_sha256") != identity["guest_sha256"]):
        raise ValueError("missing actual Linux guest evidence")
    shutil.copy2(guest,assets/"smoke.elf")
    keymap = artifacts/"legacy-native-linux/linux/keymaps/en-us"
    identity["keymap_sha256"] = checked(keymap,keymap.parent.parent/"SHA256SUMS","keymaps/en-us")
    (assets/"keymaps").mkdir(exist_ok=True)
    shutil.copy2(keymap,assets/"keymaps/en-us")
    identity["linux_smoke"] = linux_evidence
    (assets/"build-identity.json").write_text(json.dumps(identity,indent=2)+"\n")
    (out/"BUILD-IDENTITY.json").write_text(json.dumps(identity,indent=2)+"\n")
    lock = json.loads((project/"sources.lock.json").read_text())
    notices = ["ACCI Legacy VM", "Wrapper and guest: MIT (see repository LICENSE).",
               "Emulator executable: GPL-2.0. Complete corresponding source accompanies this APK.",
               "No Apple code or firmware is included.", ""]
    toolchain_notices = []
    notice_assets = assets/"notices"
    notice_assets.mkdir(exist_ok=True)
    for filename in ("NDK-NOTICE.toolchain","NDK-NOTICE","ndk-source.properties","compiler-version.txt"):
        path = artifacts/"legacy-native-arm64-v8a/arm64-v8a"/filename
        if path.exists():
            shutil.copy2(path,notice_assets/filename)
            toolchain_notices.append(path)
    if not any(p.name=="NDK-NOTICE.toolchain" for p in toolchain_notices):
        raise ValueError("missing NDK runtime license notices")
    notices.extend(["NDK r29 standard C/C++ runtime and compiler support libraries.",
        "See the complete NDK notices bundled in assets/generated/notices/ and in the source ZIP.",
        "NDK toolchain: https://developer.android.com/ndk/downloads",""])
    archive_paths = []
    for source in lock["sources"]:
        archive = downloads/source["filename"]
        if hashlib.sha256(archive.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError("upstream source checksum mismatch")
        archive_paths.append(archive)
        notices.extend([source["name"]+" "+source["version"],source["url"],source["license"],""])
        with tarfile.open(archive) as t:
            for member in t.getmembers():
                parts = Path(member.name).parts
                if member.isfile() and len(parts) == 2 and (
                    parts[-1].startswith(("COPYING","LICENSE","COPYRIGHT"))):
                    if member.size > 200000: raise ValueError("oversized license")
                    notices.extend([member.name,t.extractfile(member).read().decode("utf-8",errors="replace"),""])
                if source["name"] == "dtc" and member.isfile() and member.name.endswith("libfdt/README.license"):
                    notices.extend([member.name,t.extractfile(member).read().decode(),""])
    (assets/"licenses.txt").write_text("\n".join(notices))
    if (repo/".git").exists():
        files = [f.decode() for f in subprocess.check_output(["git","ls-files","-z","experiments/legacy_vm",
            ".github/workflows/legacy-vm.yml","LICENSE"],cwd=repo).split(b"\0") if f]
    else:
        files = (repo/"SOURCE-FILES.txt").read_text().splitlines()
    bundle = out/"acci-legacy-vm-corresponding-source.zip"
    with zipfile.ZipFile(bundle,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for relative in files:
            if not relative.startswith(("experiments/legacy_vm/",".github/workflows/legacy-vm.yml","LICENSE")) or ".." in Path(relative).parts:
                raise ValueError("unexpected corresponding-source path")
            z.write(repo/relative,"source/"+relative)
        z.writestr("source/SOURCE-FILES.txt","\n".join(files)+"\n")
        for archive in archive_paths:
            z.write(archive,"upstream/"+archive.name,compress_type=zipfile.ZIP_STORED)
        for notice in toolchain_notices:
            z.write(notice,"toolchain-notices/"+notice.name)
        z.writestr("BUILD-IDENTITY.json",json.dumps(identity,indent=2)+"\n")
        z.writestr("README.txt","Complete corresponding source for this prototype APK.\n"
            "ACCI-authored source and build recipes: source/experiments/legacy_vm/\n"
            "Original, checksum-pinned upstream archives (including licenses): upstream/\n"
            "Follow source/experiments/legacy_vm/BUILDING.md.\n"
            "No Apple runtime, apps or firmware are included. iOS/Safari boot is NOT verified.\n")
    print(json.dumps(identity))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ("repo","artifacts","downloads","out"): p.add_argument(name,type=Path)
    p.add_argument("commit"); p.add_argument("run_url")
    p.add_argument("ndk",type=Path)
    a = p.parse_args(); main(a.repo,a.artifacts,a.downloads,a.out,a.commit,a.run_url,a.ndk)