import subprocess
import zipfile

from acci import secretscan

FAKE_GH = "ghp_" + "A1b2C3d4E5" * 4  # assembled at runtime: never a literal token in the source


def test_detects_and_masks_github_token():
    found = secretscan.scan_text(f"token = '{FAKE_GH}'")
    assert any(f["rule"] == "github-token" for f in found)
    assert FAKE_GH not in str(found)


def test_redact():
    out = secretscan.redact(f"Authorization: token {FAKE_GH}\npassword = \"hunter2hunter2\"")
    assert FAKE_GH not in out and "[REDACTED:github-token]" in out and "hunter2hunter2" not in out


def test_private_key_header():
    assert secretscan.scan_text("-----BEGIN " + "RSA PRIVATE KEY-----")


def test_placeholders_ignored():
    assert not secretscan.scan_text('password = "${DB_PASSWORD}"')
    assert not secretscan.scan_text('api_key = "your_api_key_here"')
    assert not secretscan.scan_text('secret = "aaaaaaaaaaaa"')  # low entropy


def test_generic_high_entropy_assignment():
    assert secretscan.scan_text('client_secret = "Zq8Lr2vX9pM4tK7w"')


def test_sensitive_files(tmp_path):
    (tmp_path / ".env").write_text("A=1\n")
    (tmp_path / ".env.example").write_text("A=\n")
    (tmp_path / "release.keystore").write_bytes(b"\0\1")
    names = {f["where"] for f in secretscan.scan_path(tmp_path) if f["rule"] == "sensitive-file"}
    assert names == {".env", "release.keystore"}


def test_scans_inside_archives(tmp_path):
    z = tmp_path / "app.whl"
    with zipfile.ZipFile(z, "w") as zz:
        zz.writestr("pkg/conf.py", f"T = '{FAKE_GH}'")
    found = secretscan.scan_path(z)
    assert any(f["rule"] == "github-token" and f["where"].endswith("!pkg/conf.py") for f in found)


def test_scans_git_history_even_after_deletion(tmp_path):
    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.email", "t@example.invalid")
    git("config", "user.name", "t")
    (tmp_path / "c.py").write_text(f"T = '{FAKE_GH}'\n")
    git("add", "-A")
    git("commit", "-qm", "add")
    (tmp_path / "c.py").unlink()
    git("add", "-A")
    git("commit", "-qm", "remove")
    assert any(f["rule"] == "github-token" for f in secretscan.scan_git(tmp_path))
