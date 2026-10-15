import os
import subprocess
from pathlib import Path

from acci import cli, workspace

ROOT = Path(__file__).resolve().parents[1]


def test_cli_handoff_commands():
    parser = cli.build_parser()
    assert parser.parse_args(["handoff", "demo"]).project == "demo"
    args = parser.parse_args(["resume", "demo", "--from", "handoff.json"])
    assert args.source == "handoff.json" and not args.replace
    assert parser.parse_args(["doctor", "--offline"]).offline
    assert parser.parse_args(["ios", "preflight"]).ios_command == "preflight"
    assert parser.parse_args(["game", "plan", "."]).game_command == "plan"
    assert parser.parse_args(["agent", "preview", "--task-file", "task.txt", "--out", "context.json"]).agent_command == "preview"


def test_extractable_helpers_and_new_templates(tmp_path):
    for name in ("ios.py", "games.py", "install-godot.sh", "AcciBuild.cs",
                 "ci-ios-sign.yml", "ci-godot.yml", "ci-unity.yml"):
        dest = tmp_path / name
        assert cli.main(["template", name, "--out", str(dest)]) == 0
        assert dest.is_file() and dest.stat().st_size > 100
    assert cli.main(["template", "../cli.py"]) == 2


def test_source_launcher_works_outside_checkout(tmp_path):
    env = dict(os.environ, ACCI_HOME=str(tmp_path / "work"))
    result = subprocess.run(["bash", str(ROOT / "bin/acci"), "init", "portable"],
                            cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "work/projects/portable/state.json").is_file()


def test_custom_home_expands_tilde(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("ACCI_HOME", "~/private-acci")
    assert workspace.default_home() == tmp_path / "private-acci"


def test_github_wrapper_uses_path_and_preserves_failure(tmp_path):
    fake = tmp_path / "gh"
    fake.write_text("#!/bin/sh\nprintf 'fake gh\\n'\nexit 7\n")
    fake.chmod(0o755)
    env = dict(os.environ, ACCI_HOME=str(tmp_path / "home"),
               PATH=f"{tmp_path}:{os.environ['PATH']}")
    env.pop("ACCI_GH", None)
    result = subprocess.run(["bash", str(ROOT / "bin/acci-gh"), "--version"],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 7
    assert "fake gh" in result.stdout