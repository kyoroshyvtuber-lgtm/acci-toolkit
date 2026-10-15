import pytest

from acci import runner, workspace

FAKE = "ghp_" + "Q1w2E3r4T5" * 4


@pytest.fixture
def proj(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, "HOME", tmp_path)
    workspace.init("demo")
    return tmp_path / "projects" / "demo"


def test_ok_and_logged(proj):
    res = runner.run("demo", "echo hello", timeout=30)
    assert res["exit"] == 0 and res["tail"] == ["hello"]
    assert "hello" in (proj / "logs" / res["log"]).read_text()
    assert '"type": "cmd"' in (proj / "logs" / "journal.jsonl").read_text()


def test_parent_env_not_inherited(proj, monkeypatch):
    monkeypatch.setenv("SUPER_SECRET_TOKEN", "do-not-leak")
    res = runner.run("demo", "env", timeout=30)
    assert "do-not-leak" not in (proj / "logs" / res["log"]).read_text()


def test_output_redacted(proj):
    res = runner.run("demo", f"echo token={FAKE}", timeout=30)
    log = (proj / "logs" / res["log"]).read_text()
    assert FAKE not in log and "[REDACTED:github-token]" in log


def test_timeout_kills_process_group(proj):
    res = runner.run("demo", "sleep 60 & sleep 60", timeout=2)
    assert res["timed_out"] and res["exit"] != 0 and res["secs"] < 30


def test_memory_limit(proj):
    res = runner.run("demo", ["python3", "-c", "x = bytearray(800 * 1024 * 1024)"], mem_mb=256, timeout=60)
    assert res["exit"] != 0 and any("MemoryError" in line for line in res["tail"])


def test_cwd_confined_to_project(proj):
    with pytest.raises(PermissionError):
        runner.run("demo", "true", cwd="/tmp")


def test_credentials_fail_closed_without_namespaces(proj, tmp_path, monkeypatch):
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "credential").write_text("private test fixture")
    monkeypatch.setattr(runner, "unshare_ok", lambda: False)
    with pytest.raises(RuntimeError, match="credential directory cannot be hidden"):
        runner.run("demo", "echo must-not-run")
    assert not list((proj / "logs").glob("cmd-*"))


@pytest.mark.skipif(not runner.unshare_ok(), reason="no user namespaces")
def test_no_network_mode(proj):
    res = runner.run("demo", "curl -sS -m 5 -o /dev/null https://github.com", network=False, timeout=30)
    assert res["exit"] != 0


@pytest.mark.skipif(not runner.unshare_ok(), reason="no user namespaces")
def test_orchestrator_secrets_hidden(proj, tmp_path):
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "hosts.yml").write_text("oauth_token: x\n")
    res = runner.run("demo", f"ls -A {tmp_path / 'secrets'} | wc -l; cat {tmp_path / 'secrets' / 'hosts.yml'}", timeout=30)
    assert res["secrets_hidden"] and res["tail"][0].strip() == "0"
    assert "oauth_token" not in (proj / "logs" / res["log"]).read_text()


def test_fix_attempt_budget(proj):
    for _ in range(3):
        assert workspace.attempt("demo", "E1", limit=3)[1] is False
    assert workspace.attempt("demo", "E1", limit=3)[1] is True


def test_trash_requires_confirmation(proj, tmp_path):
    with pytest.raises(PermissionError):
        workspace.trash("demo", "wrong")
    dst = workspace.trash("demo", "demo")
    assert dst.exists() and not proj.exists()
