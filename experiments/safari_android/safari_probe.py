"""Offline bundle/Mach-O inspection. NOT an emulator or a Safari launcher."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import struct
import sys
import zipfile

MAX_BINARY = 256 * 1024 * 1024
MAX_ARCHIVE = 512 * 1024 * 1024
MAX_PLIST = 2 * 1024 * 1024
THIN = {
    b"\xce\xfa\xed\xfe": ("<", 32), b"\xfe\xed\xfa\xce": (">", 32),
    b"\xcf\xfa\xed\xfe": ("<", 64), b"\xfe\xed\xfa\xcf": (">", 64),
}
FAT = {
    b"\xca\xfe\xba\xbe": (">", False), b"\xbe\xba\xfe\xca": ("<", False),
    b"\xca\xfe\xba\xbf": (">", True), b"\xbf\xba\xfe\xca": ("<", True),
}
CPUS = {7: "x86", 0x01000007: "x86_64", 12: "arm", 0x0100000C: "arm64"}
PLATFORMS = {1: "macos", 2: "ios-device", 6: "mac-catalyst", 7: "ios-simulator"}
DYLIB_COMMANDS = {0xC, 0x80000018, 0x8000001F, 0x20, 0x80000023}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def version(value):
    return f"{value >> 16}.{(value >> 8) & 255}.{value & 255}"


def parse_thin(data):
    require(data[:4] in THIN, "Not a supported thin Mach-O header")
    endian, bits = THIN[data[:4]]
    header_size = 32 if bits == 64 else 28
    require(len(data) >= header_size, "Truncated Mach-O header")
    _, cpu, subtype, filetype, ncmds, sizeofcmds, _ = struct.unpack_from(endian + "7I", data)
    require(ncmds <= 16384, "Too many load commands")
    end = header_size + sizeofcmds
    require(end <= len(data), "Load command area exceeds binary")
    offset, libraries, platforms, encryption = header_size, [], [], []
    for _ in range(ncmds):
        require(offset + 8 <= end, "Truncated load command")
        cmd, size = struct.unpack_from(endian + "2I", data, offset)
        require(size >= 8 and size % 4 == 0 and offset + size <= end,
                "Invalid load command size")
        block = data[offset:offset + size]
        if cmd in DYLIB_COMMANDS:
            require(size >= 24, "Truncated dylib command")
            name_offset = struct.unpack_from(endian + "I", block, 8)[0]
            require(24 <= name_offset < size, "Invalid dylib name offset")
            terminator = block.find(b"\0", name_offset)
            require(terminator != -1, "Unterminated dylib name")
            libraries.append(block[name_offset:terminator].decode("utf-8"))
        elif cmd in (0x21, 0x2C):
            require(size >= (24 if cmd == 0x2C else 20), "Truncated encryption command")
            crypt_offset, crypt_size, crypt_id = struct.unpack_from(endian + "3I", block, 8)
            require(crypt_offset + crypt_size <= len(data), "Encryption range exceeds binary")
            encryption.append({"cryptid": crypt_id, "bytes": crypt_size})
        elif cmd == 0x25:
            require(size >= 16, "Truncated iOS version command")
            minimum, sdk = struct.unpack_from(endian + "2I", block, 8)
            platforms.append({"platform": "ios-device-or-simulator-legacy",
                              "minimum_os": version(minimum), "sdk": version(sdk)})
        elif cmd == 0x32:
            require(size >= 24, "Truncated build version command")
            platform, minimum, sdk, ntools = struct.unpack_from(endian + "4I", block, 8)
            require(24 + 8 * ntools <= size, "Truncated build tool records")
            platforms.append({"platform": PLATFORMS.get(platform, f"unknown-{platform}"),
                              "minimum_os": version(minimum), "sdk": version(sdk)})
        offset += size
    require(offset == end, "Load command count does not match declared area")
    architecture = CPUS.get(cpu, f"unknown-{cpu:#x}")
    if cpu == 0x0100000C and subtype & 0x00FFFFFF == 2:
        architecture = "arm64e"
    return {
        "architecture": architecture, "bits": bits, "cpu_type": cpu,
        "cpu_subtype": subtype, "file_type": filetype,
        "platform_records": platforms, "direct_libraries": sorted(set(libraries)),
        "encryption": encryption,
        "encryption_status": ("declares-encrypted" if any(x["cryptid"] for x in encryption)
                              else "no-encryption-declared"),
    }


def parse_macho(data):
    require(len(data) <= MAX_BINARY, "Binary exceeds inspection limit")
    if data[:4] in THIN:
        return [parse_thin(data)]
    require(data[:4] in FAT, "Not a supported Mach-O or universal binary")
    require(len(data) >= 8, "Truncated universal header")
    endian, fat64 = FAT[data[:4]]
    count = struct.unpack_from(endian + "I", data, 4)[0]
    entry_size = 32 if fat64 else 20
    table_end = 8 + count * entry_size
    require(0 < count <= 64 and table_end <= len(data), "Invalid universal architecture table")
    slices, ranges = [], []
    for i in range(count):
        position = 8 + i * entry_size
        if fat64:
            cpu, subtype, start, length, alignment, _ = struct.unpack_from(
                endian + "2I2Q2I", data, position)
        else:
            cpu, subtype, start, length, alignment = struct.unpack_from(
                endian + "5I", data, position)
        require(alignment <= 31 and start % (1 << alignment) == 0,
                "Invalid universal slice alignment")
        require(start >= table_end and length > 0 and start + length <= len(data),
                "Universal slice exceeds binary")
        require(all(start + length <= a or start >= b for a, b in ranges),
                "Overlapping universal slices")
        item = parse_thin(data[start:start + length])
        require(item["cpu_type"] == cpu and item["cpu_subtype"] == subtype,
                "Universal table disagrees with slice header")
        ranges.append((start, start + length))
        slices.append(item)
    return slices


def executable_name(info):
    value = info.get("CFBundleExecutable")
    require(isinstance(value, str) and value not in ("", ".", "..")
            and not any(c in value for c in "/\\\0"), "Invalid CFBundleExecutable")
    return value


def read_limited(path, limit):
    require(not path.is_symlink() and path.is_file(), "Expected a regular, non-symlink file")
    require(path.stat().st_size <= limit, "Input exceeds inspection limit")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    require(len(data) <= limit, "Input exceeds inspection limit")
    return data


def archive_member(archive, name, limit):
    items = [x for x in archive.infolist() if x.filename == name]
    require(len(items) == 1, "Missing or duplicate selected archive member")
    item = items[0]
    require(not item.flag_bits & 1, "ZIP-level encrypted input is not supported")
    require(item.file_size <= limit, "Selected archive member exceeds inspection limit")
    with archive.open(item) as stream:
        data = stream.read(limit + 1)
    require(len(data) <= limit and len(data) == item.file_size, "Invalid archive member size")
    return data


def inspect(path):
    path = Path(path)
    require(not path.is_symlink(), "Input itself must not be a symlink")
    info = {}
    if path.is_dir():
        require(path.name.endswith(".app"), "Directory input must be an .app bundle")
        info = plistlib.loads(read_limited(path / "Info.plist", MAX_PLIST))
        require(isinstance(info, dict), "Info.plist must be a dictionary")
        name = executable_name(info)
        binary = read_limited(path / name, MAX_BINARY)
        source = "app-directory"
    else:
        require(path.is_file() and path.stat().st_size <= MAX_ARCHIVE,
                "Expected an existing input within the size limit")
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                require(len(names) <= 50000, "Too many archive entries")
                candidates = [x for x in names if re.fullmatch(
                    r"(?:Payload/)?[^/]+\.app/Info\.plist", x)]
                require(len(candidates) == 1, "Expected one top-level application bundle")
                plist_name = candidates[0]
                info = plistlib.loads(archive_member(archive, plist_name, MAX_PLIST))
                require(isinstance(info, dict), "Info.plist must be a dictionary")
                name = executable_name(info)
                binary = archive_member(
                    archive, plist_name.removesuffix("Info.plist") + name, MAX_BINARY)
            source = "app-archive"
        else:
            binary = read_limited(path, MAX_BINARY)
            source = "raw-mach-o"
    return {
        "report_kind": "static-inspection-only",
        "executes_application": False,
        "runtime_compatibility_verified": False,
        "source_kind": source,
        "declared_bundle_id": info.get("CFBundleIdentifier"),
        "declared_bundle_version": info.get("CFBundleVersion"),
        "executable_sha256": hashlib.sha256(binary).hexdigest(),
        "slices": parse_macho(binary),
        "limitations": [
            "No app or library is executed.",
            "Bundle identifiers and metadata are declarations, not proof of authenticity.",
            "Direct imports only; dependencies are not recursively resolved.",
            "No decryption, signing bypass, account access or entitlement validation.",
            "A successful inspection is NOT proof that Safari or any app runs on Android.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, help="New JSON file; existing files are not overwritten")
    args = parser.parse_args(argv)
    try:
        report = inspect(args.input)
        text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.out:
            with args.out.open("x", encoding="utf-8") as stream:
                stream.write(text)
        else:
            print(text, end="")
        return 0
    except (ValueError, OSError, struct.error, plistlib.InvalidFileException,
            zipfile.BadZipFile, RuntimeError) as error:
        print(f"static probe: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())