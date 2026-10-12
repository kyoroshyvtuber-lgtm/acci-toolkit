import os
import zipfile

import pytest

from acci import safezip


def make_zip(path, entries):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data, mode in entries:
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = (mode or 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    return path


def test_good_archive_strips_root_and_keeps_exec_bit(tmp_path):
    z = make_zip(tmp_path / "ok.zip", [("proj/README.md", b"hi", None), ("proj/run.sh", b"echo 1", 0o100755)])
    rep = safezip.extract(z, tmp_path / "out")
    assert rep["ok"] and rep["stripped_root"] == "proj"
    assert (tmp_path / "out/README.md").read_bytes() == b"hi"
    assert os.stat(tmp_path / "out/run.sh").st_mode & 0o111


@pytest.mark.parametrize("name", ["../evil.txt", "a/../../evil.txt", "/etc/evil", "C:/evil.txt", "..\\evil.txt"])
def test_zip_slip_rejected(tmp_path, name):
    z = make_zip(tmp_path / "bad.zip", [("ok.txt", b"x", None), (name, b"x", None)])
    with pytest.raises(safezip.UnsafeArchive):
        safezip.extract(z, tmp_path / "out")
    assert not (tmp_path / "evil.txt").exists()
    assert not (tmp_path / "out").exists()  # rejected before anything is written


def test_symlink_rejected(tmp_path):
    z = make_zip(tmp_path / "ln.zip", [("link", b"/etc/passwd", 0o120777)])
    rep = safezip.inspect(z)
    assert not rep["ok"] and any("symlink" in p for p in rep["problems"])


def test_special_file_rejected(tmp_path):
    z = make_zip(tmp_path / "fifo.zip", [("pipe", b"", 0o010644)])
    assert any("special file" in p for p in safezip.inspect(z)["problems"])


def test_zip_bomb_ratio(tmp_path):
    z = make_zip(tmp_path / "bomb.zip", [("zeros.bin", b"\0" * (20 * 1024 * 1024), None)])
    rep = safezip.inspect(z)
    assert not rep["ok"] and any("ratio" in p for p in rep["problems"])


def test_limits_total_and_count(tmp_path):
    z = make_zip(tmp_path / "many.zip", [(f"f{i}.txt", os.urandom(300), None) for i in range(5)])
    assert not safezip.inspect(z, dict(safezip.LIMITS, max_total_bytes=1000))["ok"]
    assert not safezip.inspect(z, dict(safezip.LIMITS, max_members=3))["ok"]


def test_crc_corruption_detected(tmp_path):
    z = make_zip(tmp_path / "c.zip", [("a.txt", b"hello world " * 200, None)])
    data = bytearray(z.read_bytes())
    data[40] ^= 0xFF
    z.write_bytes(bytes(data))
    assert not safezip.inspect(z)["ok"]


def test_duplicate_entries_rejected(tmp_path):
    with pytest.warns(UserWarning):
        z = make_zip(tmp_path / "d.zip", [("a.txt", b"1", None), ("a.txt", b"2", None)])
    assert not safezip.inspect(z)["ok"]


def test_not_a_zip_and_missing(tmp_path):
    f = tmp_path / "x.zip"
    f.write_bytes(b"not a zip")
    assert "not a ZIP archive" in safezip.inspect(f)["problems"]
    assert not safezip.inspect(tmp_path / "missing.zip")["ok"]


def test_destination_must_be_empty(tmp_path):
    z = make_zip(tmp_path / "ok.zip", [("a.txt", b"1", None)])
    (tmp_path / "out").mkdir()
    (tmp_path / "out/keep.txt").write_text("user data")
    with pytest.raises(safezip.UnsafeArchive):
        safezip.extract(z, tmp_path / "out")
    assert (tmp_path / "out/keep.txt").read_text() == "user data"
