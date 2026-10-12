import json
import subprocess
from pathlib import Path

from acci import detect, ghsync


def test_detect_multi_stack(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "settings.gradle").write_text("include ':app'\n")
    (tmp_path / "app/build.gradle").write_text("plugins { id 'com.android.application' }\n")
    (tmp_path / "package.json").write_text('{"scripts": {"test": "jest", "build": "tsc"}}')
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_x.py").write_text("")
    (tmp_path / "README.md").write_text("# x")
    d = detect.detect(tmp_path)
    kinds = {s["stack"] for s in d["stacks"]}
    assert {"android", "node", "python"} <= kinds
    assert "README.md" in d["docs"] and "tests/test_x.py" in d["tests"]
    assert next(s for s in d["stacks"] if s["stack"] == "android")["build"] == "gradle assembleDebug"


def test_detect_ios(tmp_path):
    (tmp_path / "App.xcodeproj").mkdir()
    (tmp_path / "App.xcodeproj/project.pbxproj").write_text("// pbx")
    s = detect.detect(tmp_path)["stacks"][0]
    assert s["stack"] == "ios" and s["runner"] == "macos-latest"


def _repo(tmp_path):
    r = tmp_path / "r"
    r.mkdir()
    for args in (["init", "-q", "-b", "main"], ["config", "user.email", "t@example.invalid"], ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(r), *args], check=True)
    (r / "README.md").write_text("hi\n")
    subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(r), "commit", "-qm", "base"], check=True)
    ghsync.mark_synced(r, "main")
    return r


def _commit(r, msg):
    subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(r), "commit", "-qm", msg], check=True)


def test_blob_sha_matches_git():
    assert ghsync.blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_payload_ok(tmp_path):
    r = _repo(tmp_path)
    (r / "src").mkdir()
    (r / "src/app.py").write_text("print('x')\n")
    (r / "README.md").write_text("hi2\n")
    _commit(r, "change")
    res = ghsync.build_payload(r, "refs/acci/synced/main", "o", "n", "feat", "msg", tmp_path / "out")
    assert not res["problems"] and sorted(res["files"]) == ["README.md", "src/app.py"]
    data = json.loads(Path(res["parts"][0]).read_text())
    assert data["branch"] == "feat" and {f["path"] for f in data["files"]} == {"README.md", "src/app.py"}


def test_payload_blocks_binary_secret_and_unapproved_delete(tmp_path):
    r = _repo(tmp_path)
    (r / "bin.dat").write_bytes(b"\0\1\2")
    (r / "conf.py").write_text("T = '" + "ghp_" + "Z9y8X7w6V5" * 4 + "'\n")
    (r / "README.md").unlink()
    _commit(r, "bad")
    res = ghsync.build_payload(r, "refs/acci/synced/main", "o", "n", "feat", "msg", tmp_path / "out")
    text = " ".join(res["problems"])
    assert "binary" in text and "secret" in text and "deletions" in text and not res["parts"]


def test_compare_trees(tmp_path):
    r = _repo(tmp_path)
    listing = tmp_path / "l.json"
    listing.write_text(json.dumps([{"type": "file", "path": "README.md", "sha": ghsync.blob_sha(b"hi\n")}]))
    files, dirs = ghsync.remote_tree([listing])
    assert ghsync.compare(ghsync.local_tree(r), files, dirs)["identical"]
    (r / "README.md").write_text("changed\n")
    assert ghsync.compare(ghsync.local_tree(r), files, dirs)["changed"] == ["README.md"]
