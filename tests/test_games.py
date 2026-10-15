import pytest

from acci import detect, games


def test_godot_plan_and_detection(tmp_path):
    (tmp_path / "project.godot").write_text('config_version=5\n')
    value = games.plan(str(tmp_path))
    assert value["engine"] == "godot"
    assert value["missing_files"] == ["export_presets.cfg"]
    assert value["commands"][1][-2] == "iOS"
    assert not value["publication"]
    assert "godot" in {s["stack"] for s in detect.detect(tmp_path)["stacks"]}
    with pytest.raises(ValueError, match="preset"):
        games.plan(str(tmp_path), preset="bad\nshell")


def test_unity_plan_tests_do_not_quit_prematurely(tmp_path):
    (tmp_path / "ProjectSettings").mkdir()
    (tmp_path / "ProjectSettings/ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.30f1\n")
    value = games.plan(str(tmp_path), editor="/Applications/Unity/Editor")
    assert value["editor_version"] == "6000.0.30f1"
    assert "Assets/Editor/AcciBuild.cs" in value["missing_files"]
    assert all("-quit" not in cmd for cmd in value["commands"][:2])
    assert "-executeMethod" in value["commands"][2]
    assert "unity" in {s["stack"] for s in detect.detect(tmp_path)["stacks"]}


def test_unknown_or_ambiguous_engine_requires_choice(tmp_path):
    with pytest.raises(ValueError, match="ambiguous"):
        games.plan(str(tmp_path))
    (tmp_path / "project.godot").touch()
    (tmp_path / "ProjectSettings").mkdir()
    (tmp_path / "ProjectSettings/ProjectVersion.txt").touch()
    with pytest.raises(ValueError, match="ambiguous"):
        games.plan(str(tmp_path))


def test_unity_result_validation_rejects_no_tests_and_failures(tmp_path):
    result = tmp_path / "results.xml"
    result.write_text('<test-run result="Passed" total="3" passed="2" failed="0" skipped="1" />')
    assert games.verify_unity_tests([str(result)])["results"][0]["passed"] == 2
    for value in (
        '<test-run result="Failed" total="3" passed="2" failed="1" />',
        '<test-run result="Passed" total="0" passed="0" failed="0" />',
        '<test-run />', 'not XML',
    ):
        result.write_text(value)
        with pytest.raises(ValueError):
            games.verify_unity_tests([str(result)])