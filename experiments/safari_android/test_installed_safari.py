"""Synthetic directory tests; no Apple application is redistributed."""
import hashlib
import json
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch

import inspect_installed_safari as collector


class CollectionTests(unittest.TestCase):
    def runtime(self, root, version="27.0", available=True, safari=True, identifier=None):
        bundle = root / (version + ".simruntime")
        runtime = {"isAvailable": available, "version": version, "bundlePath": str(bundle),
                   "identifier": identifier or "com.apple.CoreSimulator.SimRuntime.iOS-" + version}
        if safari:
            app = bundle / "Contents/Resources/RuntimeRoot/Applications/MobileSafari.app"
            app.mkdir(parents=True)
            (app / "Info.plist").write_bytes(
                plistlib.dumps({"CFBundleIdentifier": "com.apple.mobilesafari"}))
        return runtime

    def test_newest_runtime_is_selected_numerically(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtimes = [self.runtime(root, "9.0"), self.runtime(root, "27.0")]
            runtime, _, _ = collector.find_safari({"runtimes": runtimes})
            self.assertEqual(runtime["version"], "27.0")

    def test_unavailable_runtime_is_not_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtimes = [self.runtime(root, "27.0"), self.runtime(root, "28.0", available=False)]
            self.assertEqual(collector.find_safari({"runtimes": runtimes})[0]["version"], "27.0")

    def test_newest_without_safari_falls_back_to_readable_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtimes = [self.runtime(root, "26.5"), self.runtime(root, "27.0", safari=False)]
            self.assertEqual(collector.find_safari({"runtimes": runtimes})[0]["version"], "26.5")

    def test_non_ios_runtime_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.runtime(Path(tmp), identifier="com.apple.CoreSimulator.SimRuntime.tvOS-27-0")
            with self.assertRaisesRegex(ValueError, "No readable"):
                collector.find_safari({"runtimes": [r]})

    def test_unrelated_bundle_identifier_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.runtime(Path(tmp))
            plist = Path(r["bundlePath"]) / "Contents/Resources/RuntimeRoot/Applications/MobileSafari.app/Info.plist"
            plist.write_bytes(plistlib.dumps({"CFBundleIdentifier": "example.not-safari"}))
            with self.assertRaisesRegex(ValueError, "No readable"):
                collector.find_safari({"runtimes": [r]})

    def test_failed_collection_never_claims_execution(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
                collector, "collect", side_effect=RuntimeError("fixture failure")), patch("builtins.print"):
            root = Path(tmp)
            self.assertEqual(collector.main(["--out", str(root)]), 2)
            report = json.loads((root / "safari-metadata.json").read_text())
            self.assertFalse(report["executes_application"])
            self.assertFalse(report["runtime_compatibility_verified"])
            self.assertFalse(report["apple_binaries_redistributed"])
            self.assertEqual(report["android_execution"], "not-performed")

    def test_exports_metadata_only_with_valid_hash_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            collector.save_report(root, {"status": "metadata-collected"})
            self.assertEqual({p.name for p in root.iterdir()},
                             {"safari-metadata.json", "SUMMARY.md", "SHA256SUMS"})
            for line in (root / "SHA256SUMS").read_text().splitlines():
                expected, name = line.split("  ", 1)
                self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()