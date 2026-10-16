"""Synthetic ELF metadata tests; these are not runtime/emulation evidence."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "android/elf_check.py"
SPEC = importlib.util.spec_from_file_location("legacy_elf", SCRIPT)
elf = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(elf)


def image(libraries=("libc.so",), *, shared=False, alignment=16384,
          interpreter="/system/bin/linker64"):
    data = bytearray(2048)
    data[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<HH", data, 16, 3, 183)
    struct.pack_into("<Q", data, 32, 64)
    struct.pack_into("<HH", data, 54, 56, 2 if shared else 3)
    struct.pack_into("<IIQQQQQQ", data, 64, 1, 5, 0, 0, 0, len(data), len(data), alignment)
    strings = b"\0"
    entries = []
    for name in libraries:
        entries.append((1, len(strings)))
        strings += name.encode("ascii") + b"\0"
    entries += [(5, 0x400), (0, 0)]
    struct.pack_into("<IIQQQQQQ", data, 120, 2, 4, 0x200, 0x200, 0,
                     len(entries) * 16, len(entries) * 16, 8)
    for i, entry in enumerate(entries):
        struct.pack_into("<QQ", data, 0x200 + i * 16, *entry)
    data[0x400:0x400 + len(strings)] = strings
    if not shared:
        encoded = interpreter.encode("ascii") + b"\0"
        struct.pack_into("<IIQQQQQQ", data, 176, 3, 4, 0x300, 0x300, 0,
                         len(encoded), len(encoded), 1)
        data[0x300:0x300 + len(encoded)] = encoded
    return bytes(data)


class ElfTests(unittest.TestCase):
    def audit(self, content, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic.elf"
            path.write_bytes(content)
            return elf.inspect(path, 183, **kwargs)

    def test_system_only_pie(self):
        self.assertEqual(self.audit(image())["needed"], ["libc.so"])

    def test_unbundled_runtime_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unbundled"):
            self.audit(image(("libc.so", "libc++_shared.so")))

    def test_explicit_runtime_dependency(self):
        result = self.audit(image(("libc.so", "libc++_shared.so")),
                            bundled={"libc++_shared.so"})
        self.assertIn("libc++_shared.so", result["needed"])

    def test_unrelated_library_still_rejected(self):
        with self.assertRaisesRegex(ValueError, "unbundled"):
            self.audit(image(("libunavailable.so",)), bundled={"libc++_shared.so"})

    def test_four_kib_load_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "16KB"):
            self.audit(image(alignment=4096))

    def test_wrong_interpreter_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "expected Android"):
            self.audit(image(interpreter="/lib64/ld-linux-aarch64.so.1"))

    def test_shared_runtime_has_no_interpreter(self):
        self.assertIsNone(self.audit(image(shared=True), shared=True)["interpreter"])

    def test_shared_mode_rejects_executable(self):
        with self.assertRaisesRegex(ValueError, "expected Android"):
            self.audit(image(), shared=True)


if __name__ == "__main__":
    unittest.main()