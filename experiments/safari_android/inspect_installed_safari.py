"""Read-only inspection of Safari shipped in an installed iOS Simulator runtime.

Exports metadata only. Never packages Apple binaries and never claims Android execution.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import platform
import plistlib
import re
import subprocess
import sys

from safari_probe import inspect


def numeric_version(value):
    if not re.fullmatch(r"\d+(?:\.\d+){0,3}", value):
        raise ValueError("Unrecognized runtime version")
    return tuple(map(int, value.split(".")))


def runtime_candidates(inventory):
    candidates = []
    for runtime in inventory.get("runtimes", []):
        if (runtime.get("isAvailable")
                and ".iOS-" in runtime.get("identifier", "")
                and runtime.get("bundlePath")):
            numeric_version(runtime["version"])
            candidates.append(runtime)
    return sorted(candidates, key=lambda r: numeric_version(r["version"]), reverse=True)


def find_safari(inventory):
    """Choose the newest installed, readable iOS runtime containing MobileSafari."""
    for runtime in runtime_candidates(inventory):
        root = Path(runtime["bundlePath"]) / "Contents/Resources/RuntimeRoot"
        for directory in ("Applications", "System/Applications"):
            for name in ("MobileSafari.app", "Safari.app"):
                app = root / directory / name
                plist = app / "Info.plist"
                if not plist.is_file() or plist.is_symlink():
                    continue
                info = plistlib.loads(plist.read_bytes())
                if info.get("CFBundleIdentifier") == "com.apple.mobilesafari":
                    return runtime, app, info
    raise ValueError("No readable MobileSafari bundle in the installed iOS runtimes")


def capture(arguments):
    result = subprocess.run(arguments, check=True, capture_output=True, text=True, timeout=60)
    return result.stdout.strip()


def collect():
    if sys.platform != "darwin":
        raise RuntimeError("Collection requires the macOS/Xcode runner; parser tests run anywhere")
    xcode = capture(["xcodebuild", "-version"])
    sdk = capture(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-version"])
    inventory = json.loads(capture(["xcrun", "simctl", "list", "runtimes", "--json"]))
    runtime, app, info = find_safari(inventory)
    report = inspect(app)
    report.update({
        "status": "metadata-collected",
        "origin": "Safari already installed in the hosted runner's iOS Simulator runtime",
        "xcode": xcode,
        "simulator_sdk": sdk,
        "host_architecture": platform.machine(),
        "runtime": {
            "name": runtime.get("name"), "identifier": runtime["identifier"],
            "version": runtime["version"], "build": runtime.get("buildversion"),
        },
        "safari_declared_short_version": info.get("CFBundleShortVersionString"),
        "apple_binaries_redistributed": False,
        "android_execution": "not-performed",
        "device_ipa_acquired": False,
        "comparison_target": json.loads(
            Path(__file__).with_name("target-device.json").read_text(encoding="utf-8")),
    })
    report["limitations"] += [
        "This is a simulator application, not an iPhone device IPA.",
        "Identical ARM CPU architecture is not compatibility with Android's OS interfaces.",
        "No simulator was booted and Safari was not launched by this collection.",
        "Only text/JSON metadata may be exported, never the Apple application or libraries.",
    ]
    return report


def save_report(output, report):
    (output / "safari-metadata.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = (
        "# Safari source inspection — not an Android app\n\n"
        f"Status: {report['status']}\n\n"
        "This evidence is static metadata only. Safari was not launched on Android, "
        "and no working APK, iPhone IPA, or Apple runtime is supplied.\n"
    )
    (output / "SUMMARY.md").write_text(summary, encoding="utf-8")
    files = sorted(p for p in output.iterdir() if p.is_file() and p.name != "SHA256SUMS")
    (output / "SHA256SUMS").write_text("".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files),
        encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    output = args.out.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("Output must be empty; existing evidence is never overwritten")
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "failed-before-collection",
        "report_kind": "static-inspection-only",
        "executes_application": False,
        "runtime_compatibility_verified": False,
        "android_execution": "not-performed",
        "apple_binaries_redistributed": False,
        "device_ipa_acquired": False,
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    code = 0
    try:
        report.update(collect())
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError,
            plistlib.InvalidFileException) as error:
        report["status"] = "collection-failed"
        report["error"] = str(error)
        code = 2
    finally:
        save_report(output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())