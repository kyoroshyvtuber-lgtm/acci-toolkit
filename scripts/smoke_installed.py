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
        for name in ("ios.py", "games.py", "install-godot.sh", "AcciBuild.cs",
                     "ci-ios-sign.yml", "ci-godot.yml", "ci-unity.yml", "agent.example.json"):
            call("first", "template", name, "--out", str(root / name))
        exported = json.loads(call("first", "handoff", "original"))
        call("second", "resume", "next", "--from", exported["files"][0])
        restored = json.loads((root / "second/projects/next/state.json").read_text())
        assert restored["project"] == "next"
        assert restored["task"] == "Portable smoke task"
        assert restored["remaining"] == ["verify"]
        assert ".acci/ios.py simulator" in (root / "ios.yml").read_text()
        assert "CODE_SIGNING_ALLOWED=NO" in (root / "ios.py").read_text()
        game = root / "game"
        game.mkdir()
        (game / "project.godot").write_text("config_version=5\n")
        planned = json.loads(call("first", "game", "plan", str(game)))
        assert planned["engine"] == "godot" and not planned["publication"]
        # Offline agent preview from the installed wheel, with no API credentials.
        project = root / "agent-project"
        (project / "src").mkdir(parents=True)
        (project / "tests").mkdir()
        (project / ".acci").mkdir()
        (project / "src/app.py").write_text("def answer():\n    return 42\n")
        (project / "tests/test_app.py").write_text("assert 6 * 7 == 42\n")
        (project / ".acci/agent.json").write_bytes((root / "agent.example.json").read_bytes())
        for args in (("init", "-q", "-b", "main"), ("config", "user.name", "smoke"),
                     ("config", "user.email", "smoke@example.invalid"),
                     ("add", "."), ("commit", "-qm", "offline preview fixture")):
            subprocess.run(["git", "-C", str(project), *args], env=clean, check=True,
                           capture_output=True, timeout=60)
        task = root / "task.txt"
        task.write_text("Clarify the arithmetic without changing behavior")
        call("first", "agent", "preview", "--root", str(project), "--task-file", str(task),
             "--out", str(root / "preview.json"))
        preview = json.loads((root / "preview.json").read_text())
        assert preview["provider_called"] is False and len(preview["files"]) == 2
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
        print("Installed wheel: iOS/engine helpers and offline agent preview OK")


if __name__ == "__main__":
    main()