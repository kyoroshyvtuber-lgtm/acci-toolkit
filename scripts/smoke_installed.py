"""Run with a freshly wheel-installed Python, from outside the source checkout."""
import json
from importlib import metadata
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    with tempfile.TemporaryDirectory(prefix="acci-installed-") as folder:
        root = Path(folder)
        home = root / "empty-home"
        home.mkdir()
        clean = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(home),
                 "LANG": "C.UTF-8"}

        def call(state, *args):
            env = dict(clean, ACCI_HOME=str(root / state))
            result = subprocess.run([sys.executable, "-m", "acci", *args],
                                    cwd=root, env=env, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(f"acci {args[0]} failed: {result.stderr}")
            return result.stdout

        call("first", "init", "original", "--repo", "owner/example", "--branch", "acci/task")
        call("first", "state", "original", "--task", "Portable smoke task", "--plan", "test,verify")
        call("first", "state", "original", "--step", "test")
        call("first", "template", "ci-ios.yml", "--out", str(root / "ios.yml"))
        exported = json.loads(call("first", "handoff", "original"))
        call("second", "resume", "next", "--from", exported["files"][0])
        restored = json.loads((root / "second/projects/next/state.json").read_text())
        assert restored["project"] == "next"
        assert restored["task"] == "Portable smoke task"
        assert restored["remaining"] == ["verify"]
        assert "iphonesimulator" in (root / "ios.yml").read_text()
        package = subprocess.check_output(
            [sys.executable, "-c", "import acci; print(acci.__file__)"],
            cwd=root, env=clean, text=True).strip()
        assert "site-packages" in package, f"Not a wheel install: {package}"
        distribution = metadata.distribution("acci-toolkit")
        assert distribution.metadata["License-Expression"] == "MIT"
        license_file = next(path for path in distribution.files
                            if str(path).endswith(".dist-info/licenses/LICENSE"))
        assert "Permission is hereby granted" in distribution.locate_file(license_file).read_text()
        print("Installed wheel: init → state → template → handoff → resume OK")
        print("Isolated environments: no inherited provider, GitHub, or Notion configuration")
        print("Installed wheel license: MIT, license text included")


if __name__ == "__main__":
    main()