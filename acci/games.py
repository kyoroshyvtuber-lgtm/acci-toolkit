"""Engine-specific build plans, not a universal game converter."""
from __future__ import annotations

import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def plan(project: str, engine: str = "auto", preset: str = "iOS",
         editor: str | None = None) -> dict:
    root = Path(project).resolve()
    if not root.is_dir():
        raise ValueError("Project directory does not exist")
    godot = (root / "project.godot").is_file()
    unity = (root / "ProjectSettings/ProjectVersion.txt").is_file()
    if engine == "auto":
        if godot == unity:
            raise ValueError("Specify --engine godot|unity; project is ambiguous or undetected")
        engine = "godot" if godot else "unity"
    if engine == "godot":
        if not godot:
            raise ValueError("Godot project.godot is missing")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _.-]{0,80}", preset):
            raise ValueError("Invalid Godot export preset name")
        binary = editor or "godot"
        missing = [] if (root / "export_presets.cfg").is_file() else ["export_presets.cfg"]
        return {"engine": "godot", "project": str(root), "missing_files": missing,
                "requirements": ["Matching Godot editor and export templates",
                                 "For iOS: macOS + Xcode, configured iOS preset, owner team/bundle ID",
                                 "For iOS simulator: Compatibility renderer"],
                "commands": [
                    [binary, "--headless", "--path", str(root), "--import"],
                    [binary, "--headless", "--path", str(root), "--export-debug", preset,
                     str(root / "build/Game.zip")]],
                "test_note": "Add the project's actual headless gameplay tests BEFORE export; import is not a test",
                "next": "Inspect generated Xcode project, add simulator tests/launch checks, then export signed IPA separately",
                "publication": False, "verified": "plan only; no commands executed"}
    if engine == "unity":
        if not unity:
            raise ValueError("Unity ProjectSettings/ProjectVersion.txt is missing")
        text = (root / "ProjectSettings/ProjectVersion.txt").read_text(encoding="utf-8")
        match = re.search(r"^m_EditorVersion:\s*(\S+)", text, re.M)
        binary = editor or "<owner-installed-Unity-editor>"
        method = root / "Assets/Editor/AcciBuild.cs"
        return {"engine": "unity", "project": str(root),
                "editor_version": match.group(1) if match else "unknown",
                "missing_files": [] if method.is_file() else ["Assets/Editor/AcciBuild.cs"],
                "requirements": ["Matching Unity Editor + iOS Build Support + valid owner license",
                                 "macOS + Xcode for iOS; enabled scenes in build settings"],
                "commands": [
                    [binary, "-batchmode", "-projectPath", str(root), "-runTests",
                     "-testPlatform", "EditMode", "-testResults", str(root / "build/editmode.xml"),
                     "-logFile", str(root / "build/editmode.log")],
                    [binary, "-batchmode", "-projectPath", str(root), "-runTests",
                     "-testPlatform", "PlayMode", "-testResults", str(root / "build/playmode.xml"),
                     "-logFile", str(root / "build/playmode.log")],
                    [binary, "-batchmode", "-quit", "-projectPath", str(root),
                     "-buildTarget", "iOS", "-executeMethod", "AcciBuild.BuildIOS",
                     "-logFile", str(root / "build/export.log")]],
                "next": "Set ACCI_UNITY_EXPORT; inspect Xcode export and validate simulator/device separately",
                "publication": False, "verified": "plan only; Unity is not installed/activated by ACCI"}
    raise ValueError("Supported engines: godot, unity")


def add_parsers(parser):
    sub = parser.add_subparsers(dest="game_command", required=True)
    cmd = sub.add_parser("plan", help="print a build plan without running/activating an engine")
    cmd.add_argument("project")
    cmd.add_argument("--engine", choices=("auto", "godot", "unity"), default="auto")
    cmd.add_argument("--preset", default="iOS")
    cmd.add_argument("--editor")
    cmd.set_defaults(fn=lambda a: print(json.dumps(plan(a.project, a.engine, a.preset, a.editor), indent=2)))
    cmd = sub.add_parser("verify-unity-tests", help="fail on missing, empty or failing NUnit test results")
    cmd.add_argument("files", nargs="+")
    cmd.set_defaults(fn=lambda a: print(json.dumps(verify_unity_tests(a.files), indent=2)))


def verify_unity_tests(files: list[str]) -> dict:
    results = []
    for filename in files:
        path = Path(filename)
        if not path.is_file() or path.stat().st_size > 5_000_000:
            raise ValueError(f"Missing/oversized Unity test results: {path.name}")
        try:
            root = ET.fromstring(path.read_bytes())
            total, passed, failed = (int(root.attrib[k]) for k in ("total", "passed", "failed"))
            skipped = int(root.attrib.get("skipped", "0"))
        except (ValueError, KeyError, ET.ParseError):
            raise ValueError(f"Unrecognized NUnit result: {path.name}") from None
        if root.tag != "test-run" or root.get("result") != "Passed" or total <= 0 or passed <= 0 or failed:
            raise ValueError(f"Unity tests did not pass or no tests ran: {path.name}")
        results.append({"file": path.name, "total": total, "passed": passed, "skipped": skipped})
    if not results:
        raise ValueError("At least one test result is required")
    return {"status": "passed", "results": results}


if __name__ == "__main__":
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    add_parsers(parser)
    args = parser.parse_args()
    try:
        sys.exit(args.fn(args) or 0)
    except (ValueError, OSError) as error:
        print(f"acci game: {error}", file=sys.stderr)
        sys.exit(2)