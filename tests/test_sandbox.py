import os
import sys
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
