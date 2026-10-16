"""The archive guard remains enforced on Python 3.10 and 3.13."""
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "native/prepare_sources.py"
SPEC = importlib.util.spec_from_file_location("legacy_prepare", SCRIPT)
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)


class ArchiveTests(unittest.TestCase):
    def extract(self, entries):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "source.tar"
            with tarfile.open(archive, "w") as t:
                for name, content, kind in entries:
                    m = tarfile.TarInfo(name)
                    if kind == "file":
                        m.size = len(content)
                        t.addfile(m, io.BytesIO(content))
                    else:
                        m.type = tarfile.SYMTYPE if kind == "link" else tarfile.FIFOTYPE
                        m.linkname = content
                        t.addfile(m)
            root = prepare.extract(archive, Path(tmp) / "out")
            return (root / "sub/a").read_bytes()

    def test_regular_source(self):
        self.assertEqual(self.extract([("root/sub/a", b"source", "file")]), b"source")

    def test_internal_relative_link(self):
        self.assertEqual(self.extract([
            ("root/a", b"source", "file"), ("root/sub/a", "../a", "link")
        ]), b"source")

    def test_reject_traversal(self):
        with self.assertRaises(ValueError):
            self.extract([("../escape", b"bad", "file")])

    def test_reject_external_link(self):
        with self.assertRaises(ValueError):
            self.extract([("root/sub/a", "../../../outside", "link")])

    def test_reject_absolute_link(self):
        with self.assertRaises(ValueError):
            self.extract([("root/sub/a", "/tmp/outside", "link")])

    def test_reject_write_through_link(self):
        with self.assertRaises(ValueError):
            self.extract([("root/sub", ".", "link"), ("root/sub/a", b"bad", "file")])

    def test_reject_duplicate(self):
        with self.assertRaises(ValueError):
            self.extract([("root/sub/a", b"a", "file"), ("root/sub/a", b"b", "file")])

    def test_reject_special_file(self):
        with self.assertRaises(ValueError):
            self.extract([("root/sub/a", "", "fifo")])


if __name__ == "__main__":
    unittest.main()