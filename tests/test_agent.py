import io
import json
import os
import subprocess
import urllib.error

import pytest

from acci import agent


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    for args in (("init", "-q", "-b", "main"), ("config", "user.name", "test"),
                 ("config", "user.email", "test@example.invalid")):
        agent.git(root, *args)
    (root / "src").mkdir()
    (root / "src/app.py").write_text("def answer():\n    return 42\n")
    (root / "tests").mkdir()
    (root / "tests/test_app.py").write_text("assert 6 * 7 == 42\n")
    (root / ".acci").mkdir()
    policy = {"schema_version": 1, "enabled": False, "provider": "", "model": "",
              "context_paths": ["src/", "tests/"], "write_paths": ["src/"],
              "max_context_bytes": 2000, "max_file_bytes": 1000,
              "max_changed_files": 2, "max_output_tokens": 1024}
    (root / ".acci/agent.json").write_text(json.dumps(policy))
    agent.git(root, "add", ".")
    agent.git(root, "commit", "-qm", "base")
    return root, policy


def response(path="src/app.py", content="def answer():\n    return 6 * 7\n"):
    return {"summary": "Clarify the calculation", "changes": [{"path": path, "content": content}]}


def bundle(root, policy):
    return {"schema_version": 1, "base_sha": agent.clean_base(root),
            "policy_sha256": agent.policy_digest(policy), "summary": response()["summary"],
            "changes": agent.validate_changes(root, policy, response()), "usage": {}}


def test_disabled_offline_preview_never_calls_provider(repo, monkeypatch):
    root, policy = repo
    monkeypatch.setattr(agent, "provider_request", lambda *a: pytest.fail("Unexpected paid API call"))
    preview = agent.propose(root, policy, "Clarify the arithmetic")
    assert not preview["provider_called"]
    assert [f["writable"] for f in preview["files"]] == [True, False]
    with pytest.raises(ValueError, match="Owner must enable"):
        agent.propose(root, policy, "Clarify", call_provider=True)


def test_policy_roundtrip_and_caps(repo):
    root, policy = repo
    assert agent.load_policy(root) == policy
    for change in ({"max_output_tokens": 1000000}, {"write_paths": [".github/"]},
                   {"write_paths": ["tests/"]}, {"write_paths": ["../outside/"]},
                   {"enabled": "true"}, {"provider": "arbitrary-proxy"},
                   {"unknown": "value"}, {"model": "bad\nheader"}):
        (root / ".acci/agent.json").write_text(json.dumps({**policy, **change}))
        with pytest.raises(ValueError):
            agent.load_policy(root)


def test_owner_can_explicitly_configure_live_policy_without_changing_tests(repo):
    root, policy = repo
    enabled = {**policy, "enabled": True, "provider": "openai", "model": "owner-selected-model"}
    (root / ".acci/agent.json").write_text(json.dumps(enabled))
    assert agent.load_policy(root) == enabled


@pytest.mark.parametrize("path", [
    "../outside.py", "/tmp/x.py", "src//a.py", "src/../x.py",
    "src/.github/x.py", "src/test_new.py", "tests/test_app.py", ".acci/agent.json",
    "src/new.py", "src/a.sh", "src/conftest.py",
])
def test_rejects_unsafe_or_untracked_writes(repo, path):
    root, policy = repo
    with pytest.raises(ValueError):
        agent.validate_changes(root, policy, response(path))


def test_existing_tests_protected_even_if_policy_attempts_to_allow_them(repo):
    root, policy = repo
    policy["write_paths"] = ["tests/"]
    with pytest.raises(ValueError, match="Protected"):
        agent.validate_changes(root, policy, response("tests/test_app.py"))


def test_rejects_empty_duplicate_oversized_or_secret_changes(repo):
    root, policy = repo
    bad = [
        {**response(), "changes": []},
        {**response(), "changes": response()["changes"] * 2},
        response(content=""),
        response(content="a" * 1001),
        response(content="VALUE='" + "ghp_" + "Z9y8X7w6V5" * 4 + "'"),
        {**response(), "summary": "bad\nsummary"},
        {**response(), "extra": "not allowed"},
        response(content=(root / "src/app.py").read_text()),
    ]
    for value in bad:
        with pytest.raises(ValueError):
            agent.validate_changes(root, policy, value)


def test_context_rejects_dirty_tree_secret_task_and_budget(repo):
    root, policy = repo
    with pytest.raises(ValueError, match="secret"):
        agent.context(root, policy, "use " + "ghp_" + "Z9y8X7w6V5" * 4)
    with pytest.raises(ValueError, match="8000"):
        agent.context(root, policy, "x" * 8001)
    with pytest.raises(ValueError, match="Context exceeds"):
        agent.context(root, {**policy, "max_context_bytes": 2}, "task")
    (root / "src/app.py").write_text("changed")
    with pytest.raises(ValueError, match="clean"):
        agent.context(root, policy, "task")


def test_symlink_and_hardlink_rejection(repo, tmp_path):
    root, policy = repo
    outside = tmp_path / "outside.py"
    outside.write_text("outside")
    path = root / "src/app.py"
    path.unlink()
    path.symlink_to(outside)
    with pytest.raises(ValueError, match="Symlink"):
        agent.validate_changes(root, policy, response())
    path.unlink()
    os.link(outside, path)
    with pytest.raises(ValueError, match="hard-linked"):
        agent.validate_changes(root, policy, response())


def test_bundle_applies_only_to_exact_clean_base(repo):
    root, policy = repo
    value = bundle(root, policy)
    assert agent.apply_bundle(root, policy, value) == ["src/app.py"]
    assert (root / "src/app.py").read_text() == response()["changes"][0]["content"]
    with pytest.raises(ValueError, match="clean"):
        agent.apply_bundle(root, policy, value)


def test_all_changes_validated_before_any_write(repo):
    root, policy = repo
    value = bundle(root, policy)
    original = (root / "src/app.py").read_text()
    value["changes"].append({"path": ".github/evil.yml", "old_sha256": "x", "content": "bad"})
    with pytest.raises(ValueError):
        agent.apply_bundle(root, policy, value)
    assert (root / "src/app.py").read_text() == original
    value = bundle(root, policy)
    value["changes"][0]["old_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash"):
        agent.apply_bundle(root, policy, value)
    value = bundle(root, policy)
    value["base_sha"] = "0" * 40
    with pytest.raises(ValueError, match="Stale"):
        agent.apply_bundle(root, policy, value)
    value = bundle(root, policy)
    with pytest.raises(ValueError, match="policy mismatch"):
        agent.apply_bundle(root, {**policy, "max_changed_files": 1}, value)


def test_bundle_bytes_are_bound_to_trusted_job_digest(repo, tmp_path):
    root, policy = repo
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle(root, policy)))
    expected = agent.digest(path.read_bytes())
    assert agent.read_bundle(str(path), expected)["base_sha"] == agent.clean_base(root)
    with pytest.raises(ValueError, match="SHA-256"):
        agent.read_bundle(str(path), "0" * 64)
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError, match="SHA-256"):
        agent.read_bundle(str(path), expected)


class FakeHTTP:
    def __init__(self, data):
        self.data, self.requests = data, []
    def open(self, request, timeout):
        self.requests.append((request, timeout))
        return io.BytesIO(json.dumps(self.data).encode())


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_provider_adapters_offline(repo, monkeypatch, provider):
    root, policy = repo
    policy = {**policy, "enabled": True, "provider": provider, "model": "owner-selected-model"}
    data = ({"status": "completed", "output": [{"type": "message", "content": [
        {"type": "output_text", "text": json.dumps(response())}]}]}
        if provider == "openai" else {"stop_reason": "end_turn", "content": [
            {"type": "text", "text": json.dumps(response())}]})
    data["usage"] = {"input_tokens": 30, "output_tokens": 20, "unsafe": "discard"}
    fake = FakeHTTP(data)
    monkeypatch.setattr(agent.urllib.request, "build_opener", lambda *a: fake)
    monkeypatch.setenv("ACCI_MODEL_KEY", "synthetic-test-credential")
    result = agent.propose(root, policy, "Clarify the calculation", call_provider=True)
    assert result["changes"][0]["path"] == "src/app.py"
    assert result["usage"] == {"input_tokens": 30, "output_tokens": 20}
    assert len(fake.requests) == 1
    request, timeout = fake.requests[0]
    payload = json.loads(request.data)
    assert request.full_url == ("https://api.openai.com/v1/responses" if provider == "openai"
                                else "https://api.anthropic.com/v1/messages")
    assert timeout == 180 and "synthetic-test-credential" not in request.data.decode()
    assert payload["model"] == "owner-selected-model"
    assert not payload.get("tools")
    if provider == "openai":
        assert payload["max_output_tokens"] == 1024 and payload["store"] is False
        assert payload["text"]["format"]["strict"]
    else:
        assert payload["max_tokens"] == 1024


@pytest.mark.parametrize("data", [
    {"status": "incomplete"},
    {"status": "completed", "output": []},
    {"status": "completed", "output": [{"type": "message", "content": [
        {"type": "output_text", "text": "```not json```"}]}]},
])
def test_rejects_incomplete_or_malformed_provider_output(repo, monkeypatch, data):
    _, policy = repo
    fake = FakeHTTP(data)
    monkeypatch.setattr(agent.urllib.request, "build_opener", lambda *a: fake)
    with pytest.raises(ValueError):
        agent.provider_request({**policy, "provider": "openai", "model": "owner-model"}, {}, "test-key")
    assert len(fake.requests) == 1


def test_http_error_body_is_not_logged_or_retried(repo, monkeypatch):
    _, policy = repo
    calls = []
    class ErrorHTTP:
        def open(self, request, timeout):
            calls.append(request)
            raise urllib.error.HTTPError(request.full_url, 429, "limit", {},
                                         io.BytesIO(b"private-provider-error-body"))
    monkeypatch.setattr(agent.urllib.request, "build_opener", lambda *a: ErrorHTTP())
    with pytest.raises(RuntimeError) as error:
        agent.provider_request({**policy, "provider": "openai", "model": "chosen"}, {}, "test-key")
    assert len(calls) == 1 and "429" in str(error.value)
    assert "private-provider-error-body" not in str(error.value) and "test-key" not in str(error.value)
    with pytest.raises(ValueError, match="redirects"):
        agent.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.invalid")


def test_publish_creates_only_unique_task_branch_and_pr(repo, monkeypatch):
    root, policy = repo
    value = bundle(root, policy)
    repository = "owner/project"
    agent.git(root, "remote", "add", "origin", f"https://github.com/{repository}")
    real_git = agent.git
    calls = []
    def fake_git(path, *args):
        calls.append(args)
        if "ls-remote" in args or "push" in args:
            return ""
        return real_git(path, *args)
    monkeypatch.setattr(agent, "git", fake_git)
    real_run = subprocess.run
    def fake_run(command, **kwargs):
        if command[0] == "gh":
            assert command[1:3] == ["pr", "create"]
            return subprocess.CompletedProcess(command, 0, "https://github.com/owner/project/pull/1\n", "")
        return real_run(command, **kwargs)
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = agent.publish(root, policy, value, repository, "acci/agent-123-1", "main",
                           "https://github.com/owner/project/actions/runs/123")
    assert result["merged"] is False
    assert real_git(root, "branch", "--show-current") == "acci/agent-123-1"
    assert not any("merge" in args or "--force" in args for args in calls)
    push = next(args for args in calls if "push" in args)
    assert push[-1] == "HEAD:refs/heads/acci/agent-123-1"


def test_publish_rejects_unapproved_targets_before_writing(repo):
    root, policy = repo
    value = bundle(root, policy)
    with pytest.raises(ValueError, match="Only unique"):
        agent.publish(root, policy, value, "owner/project", "main", "main",
                      "https://github.com/owner/project/actions/runs/123")
    assert agent.git(root, "branch", "--show-current") == "main"