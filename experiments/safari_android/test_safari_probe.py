"""Synthetic format fixtures, NOT Apple application binaries."""
import io
from pathlib import Path
import plistlib
import struct
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

import safari_probe as probe


def thin(*commands, cpu=12, subtype=9, bits=32, endian="<"):
    size = 32 if bits == 64 else 28
    magic = 0xFEEDFACF if bits == 64 else 0xFEEDFACE
    header = struct.pack(endian + "7I", magic, cpu, subtype, 2, len(commands),
                         sum(map(len, commands)), 0)
    return header + (b"\0" * (size - len(header))) + b"".join(commands)


def dylib(name):
    text = name.encode() + b"\0"
    size = (24 + len(text) + 3) & ~3
    return struct.pack("<6I", 0xC, size, 24, 0, 0, 0) + text.ljust(size - 24, b"\0")


def archive(path, binary, executable="Example", duplicate=False):
    plist = plistlib.dumps({"CFBundleExecutable": executable,
                           "CFBundleIdentifier": "example.research.fixture"})
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("Payload/Example.app/Info.plist", plist)
        z.writestr("Payload/Example.app/Example", binary)
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                z.writestr("Payload/Example.app/Info.plist", plist)


class FormatTests(unittest.TestCase):
    def test_arm32_imports_and_legacy_ios(self):
        data = thin(dylib("/System/Library/Frameworks/UIKit.framework/UIKit"),
                    struct.pack("<4I", 0x25, 16, 0x030000, 0x040000))
        result = probe.parse_macho(data)[0]
        self.assertEqual(result["architecture"], "arm")
        self.assertEqual(result["platform_records"][0]["minimum_os"], "3.0.0")
        self.assertEqual(result["direct_libraries"],
                         ["/System/Library/Frameworks/UIKit.framework/UIKit"])

    def test_arm64e_and_ios_platform(self):
        command = struct.pack("<6I", 0x32, 24, 2, 0x100000, 0x120500, 0)
        item = probe.parse_macho(thin(command, bits=64, cpu=0x0100000C, subtype=2))[0]
        self.assertEqual(item["architecture"], "arm64e")
        self.assertEqual(item["platform_records"][0]["platform"], "ios-device")

    def test_big_endian_thin(self):
        self.assertEqual(probe.parse_macho(thin(endian=">"))[0]["bits"], 32)

    def test_encryption_is_reported_not_bypassed(self):
        command = struct.pack("<5I", 0x21, 20, 48, 4, 1)
        item = probe.parse_macho(thin(command) + b"abcd")[0]
        self.assertEqual(item["encryption_status"], "declares-encrypted")

    def test_universal_two_architectures(self):
        arm = thin()
        arm64 = thin(cpu=0x0100000C, subtype=0, bits=64)
        table = (struct.pack(">2I", 0xCAFEBABE, 2)
                 + struct.pack(">5I", 12, 9, 48, len(arm), 0)
                 + struct.pack(">5I", 0x0100000C, 0, 48 + len(arm), len(arm64), 0))
        self.assertEqual([x["bits"] for x in probe.parse_macho(table + arm + arm64)], [32, 64])

    def test_universal64_table(self):
        data = thin(cpu=0x0100000C, subtype=0, bits=64)
        container = (struct.pack(">2I", 0xCAFEBABF, 1)
                     + struct.pack(">2I2Q2I", 0x0100000C, 0, 40, len(data), 0, 0) + data)
        self.assertEqual(probe.parse_macho(container)[0]["bits"], 64)

    def test_overlapping_universal_slices_rejected(self):
        data = thin()
        container = (struct.pack(">2I", 0xCAFEBABE, 2)
                     + struct.pack(">5I", 12, 9, 48, len(data), 0) * 2 + data)
        with self.assertRaisesRegex(ValueError, "Overlapping"):
            probe.parse_macho(container)

    def test_bad_load_sizes_rejected(self):
        for command in (struct.pack("<2I", 0xC, 0), struct.pack("<2I", 0xC, 1024)):
            with self.subTest(command=command), self.assertRaises(ValueError):
                probe.parse_macho(thin(command))

    def test_truncated_or_non_macho_rejected(self):
        for data in (b"", b"hello", thin()[:20], thin(dylib("UIKit"))[:-1]):
            with self.subTest(data=data), self.assertRaises(ValueError):
                probe.parse_macho(data)

    def test_unterminated_library_rejected(self):
        command = struct.pack("<6I", 0xC, 28, 24, 0, 0, 0) + b"ABCD"
        with self.assertRaisesRegex(ValueError, "Unterminated"):
            probe.parse_macho(thin(command))

    def test_ipa_report_does_not_claim_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "example.ipa"
            archive(path, thin())
            result = probe.inspect(path)
            self.assertFalse(result["executes_application"])
            self.assertFalse(result["runtime_compatibility_verified"])
            self.assertEqual(result["declared_bundle_id"], "example.research.fixture")

    def test_duplicate_info_plist_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "example.ipa"
            archive(path, thin(), duplicate=True)
            with self.assertRaises(ValueError):
                probe.inspect(path)

    def test_executable_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "example.ipa"
            archive(path, thin(), executable="../../outside")
            with self.assertRaisesRegex(ValueError, "CFBundleExecutable"):
                probe.inspect(path)

    def test_bundle_directory_and_symlink_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = root / "Example.app"
            app.mkdir()
            (app / "Info.plist").write_bytes(plistlib.dumps({"CFBundleExecutable": "Example"}))
            (app / "Example").write_bytes(thin())
            self.assertEqual(probe.inspect(app)["source_kind"], "app-directory")
            (app / "Example").unlink()
            (root / "outside").write_bytes(thin())
            (app / "Example").symlink_to(root / "outside")
            with self.assertRaisesRegex(ValueError, "non-symlink"):
                probe.inspect(app)

    def test_cli_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input"
            source.write_bytes(thin())
            dest = root / "existing.json"
            dest.write_text("keep")
            with patch("sys.stderr", new_callable=io.StringIO):
                self.assertEqual(probe.main([str(source), "--out", str(dest)]), 2)
            self.assertEqual(dest.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()