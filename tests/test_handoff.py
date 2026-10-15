import json

import pytest

from acci import handoff, workspace


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, "HOME", tmp_path)
    return tmp_path


def test_export_and_resume_without_original_environment(home):
    workspace.init("first", repo="owner/project", branch="acci/task")
    workspace.set_task("first", "Build the demo", ["test", "verify"])
    workspace.step("first", "test")
    workspace.link("first", "pr", "https://github.com/owner/project/pull/1")
    original = workspace.load_state("first")
    original["credentials"] = "not-for-export"
    workspace.save_state("first", original)
    result = handoff.export("first")
    exported = json.loads((home / "projects/first/src/.acci/handoff.json").read_text())
    assert exported["schema_version"] == 1
    assert "credentials" not in exported["state"]
    assert str(home) not in json.dumps(exported)
    assert result["review_before_commit"]
    handoff.resume("second", result["files"][0])
    restored = workspace.load_state("second")
    assert restored["project"] == "second"
    assert restored["task"] == "Build the demo"
    assert restored["remaining"] == ["verify"]
    assert restored["links"]["pr"].endswith("/pull/1")


def test_resume_wont_overwrite_a_live_task(home):
    workspace.init("first")
    workspace.set_task("first", "First task", [])
    source = handoff.export("first")["files"][0]
    workspace.init("second")
    workspace.set_task("second", "Keep me", ["test"])
    with pytest.raises(ValueError, match="already has a task"):
        handoff.resume("second", source)
    assert workspace.load_state("second")["task"] == "Keep me"
    handoff.resume("second", source, replace=True)
    assert workspace.load_state("second")["task"] == "First task"


def test_secret_blocks_handoff(home):
    workspace.init("demo")
    workspace.set_task("demo", "token=" + "ghp_" + "Ab12Cd34Ef56" * 4, [])
    with pytest.raises(ValueError, match="possible secret"):
        handoff.export("demo")
    assert not (home / "projects/demo/src/.acci/handoff.json").exists()


@pytest.mark.parametrize("payload", [
    [],
    {"schema_version": 2, "state": {}},
    {"schema_version": 1, "state": None},
    {"schema_version": 1, "state": {"plan": "not-a-list"}},
    {"schema_version": 1, "state": {"steps": [{"step": "test", "status": "invented"}]}},
    {"schema_version": 1, "state": {"attempts": {"test": -1}}},
])
def test_invalid_handoff_is_rejected_without_creating_project(home, payload):
    source = home / "input.json"
    source.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        handoff.resume("demo", source)
    assert not (home / "projects/demo/state.json").exists()


def test_export_rejects_symlink_destination(home):
    workspace.init("demo")
    outside = home / "outside"
    outside.mkdir()
    (home / "projects/demo/src/.acci").symlink_to(outside, target_is_directory=True)
    with pytest.raises(PermissionError):
        handoff.export("demo")
    assert not list(outside.iterdir())