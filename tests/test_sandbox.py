import os
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.sandbox import FileSandbox, SandboxError


class TestFileSandbox(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.subdir = os.path.join(self.tmpdir, "allowed")
        os.makedirs(self.subdir, exist_ok=True)
        self.system_dir = os.path.join(self.tmpdir, "system")
        os.makedirs(self.system_dir, exist_ok=True)

        self.sandbox = FileSandbox(
            allowed_dirs=[self.subdir],
            system_paths=[self.system_dir]
        )

    def test_allowed_read(self):
        test_file = os.path.join(self.subdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("hello")
        self.sandbox.check_read(test_file)

    def test_blocked_read(self):
        blocked = os.path.join(self.tmpdir, "other", "secret.txt")
        os.makedirs(os.path.dirname(blocked), exist_ok=True)
        with open(blocked, "w") as f:
            f.write("secret")
        with self.assertRaises(SandboxError):
            self.sandbox.check_read(blocked)

    def test_allowed_write(self):
        test_file = os.path.join(self.subdir, "out.txt")
        self.sandbox.check_write(test_file)

    def test_blocked_write(self):
        blocked = os.path.join(self.tmpdir, "out.txt")
        with self.assertRaises(SandboxError):
            self.sandbox.check_write(blocked)

    def test_is_dangerous(self):
        dangerous = os.path.join(self.system_dir, "config.exe")
        self.assertTrue(self.sandbox.is_dangerous(dangerous))
        safe = os.path.join(self.subdir, "notes.txt")
        self.assertFalse(self.sandbox.is_dangerous(safe))

    def test_resolve_path(self):
        test_file = os.path.join(self.subdir, "found.txt")
        with open(test_file, "w") as f:
            f.write("data")
        result = self.sandbox.resolve_path("found.txt")
        self.assertEqual(result, os.path.normcase(os.path.normpath(test_file)))

    def test_resolve_path_not_found(self):
        result = self.sandbox.resolve_path("nonexistent.txt")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# pytest-style tests for uncovered methods
# ---------------------------------------------------------------------------


def test_open_file_calls_startfile(tmp_path, monkeypatch):
    sandbox = FileSandbox(allowed_dirs=[str(tmp_path)], system_paths=[])
    f = tmp_path / "test.txt"
    f.write_text("content")
    calls = []
    monkeypatch.setattr(os, "startfile", lambda p: calls.append(p))
    result = sandbox.open_file(str(f))
    expected = os.path.normcase(os.path.normpath(str(f)))
    assert result == expected
    assert calls == [expected]


def test_open_file_not_found(tmp_path):
    sandbox = FileSandbox(allowed_dirs=[str(tmp_path)], system_paths=[])
    result = sandbox.open_file(str(tmp_path / "nonexistent.txt"))
    assert result is None


def test_read_file(tmp_path):
    sandbox = FileSandbox(allowed_dirs=[str(tmp_path)], system_paths=[])
    f = tmp_path / "readme.txt"
    f.write_text("hello world", encoding="utf-8")
    content = sandbox.read_file(str(f))
    assert content == "hello world"


def test_read_file_not_found(tmp_path):
    sandbox = FileSandbox(allowed_dirs=[str(tmp_path)], system_paths=[])
    with pytest.raises(FileNotFoundError):
        sandbox.read_file(str(tmp_path / "nope.txt"))


def test_write_file(tmp_path):
    sandbox = FileSandbox(allowed_dirs=[str(tmp_path)], system_paths=[])
    dest = tmp_path / "sub" / "out.txt"
    sandbox.write_file(str(dest), "written content")
    assert dest.read_text(encoding="utf-8") == "written content"


def test_delete_file_without_confirmation(tmp_path):
    sandbox = FileSandbox(allowed_dirs=[str(tmp_path)], system_paths=[])
    f = tmp_path / "delete_me.txt"
    f.write_text("to be deleted")
    sandbox.delete_file(str(f))
    assert not f.exists()


def test_delete_file_system_requires_confirmation(tmp_path):
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    sandbox = FileSandbox(allowed_dirs=[str(tmp_path), str(system_dir)], system_paths=[str(system_dir)])
    f = system_dir / "important.exe"
    f.write_text("data")
    with pytest.raises(SandboxError, match="requires confirmation"):
        sandbox.delete_file(str(f))
    assert f.exists()


def test_delete_file_system_with_confirmation(tmp_path):
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    sandbox = FileSandbox(allowed_dirs=[str(tmp_path), str(system_dir)], system_paths=[str(system_dir)])
    f = system_dir / "important.exe"
    f.write_text("data")
    sandbox.delete_file(str(f), confirmed=True)
    assert not f.exists()


def test_move_file_without_confirmation(tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    sandbox = FileSandbox(allowed_dirs=[str(allowed)], system_paths=[])
    src = allowed / "source.txt"
    src.write_text("move me")
    dst = allowed / "dest.txt"
    sandbox.move_file(str(src), str(dst))
    assert not src.exists()
    assert dst.read_text(encoding="utf-8") == "move me"


def test_move_file_system_requires_confirmation(tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    # system_dir must be in allowed_dirs so check_read passes, but also in system_paths for confirmation check
    sandbox = FileSandbox(allowed_dirs=[str(allowed), str(system_dir)], system_paths=[str(system_dir)])
    src = system_dir / "sys.exe"
    src.write_text("data")
    dst = allowed / "sys.exe"
    with pytest.raises(SandboxError, match="requires confirmation"):
        sandbox.move_file(str(src), str(dst))
    assert src.exists()


def test_move_file_system_with_confirmation(tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    sandbox = FileSandbox(allowed_dirs=[str(allowed), str(system_dir)], system_paths=[str(system_dir)])
    src = system_dir / "sys.exe"
    src.write_text("data")
    dst = allowed / "sys.exe"
    sandbox.move_file(str(src), str(dst), confirmed=True)
    assert not src.exists()
    assert dst.read_text(encoding="utf-8") == "data"


def test_list_directory(tmp_path):
    sandbox = FileSandbox(allowed_dirs=[str(tmp_path)], system_paths=[])
    (tmp_path / "a.txt").write_text("")
    (tmp_path / "b.txt").write_text("")
    (tmp_path / "sub").mkdir()
    entries = sandbox.list_directory(str(tmp_path))
    assert sorted(entries) == ["a.txt", "b.txt", "sub"]


def test_resolve_path_existing_direct(tmp_path):
    sandbox = FileSandbox(allowed_dirs=[str(tmp_path)], system_paths=[])
    f = tmp_path / "exact.txt"
    f.write_text("data")
    result = sandbox.resolve_path(str(f))
    assert result == os.path.normcase(os.path.normpath(str(f)))


if __name__ == "__main__":
    unittest.main()
