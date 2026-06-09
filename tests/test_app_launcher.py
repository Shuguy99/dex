import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.app_launcher import AppLauncher


class TestAppLauncher(unittest.TestCase):
    def setUp(self):
        self.launcher = AppLauncher()

    @patch("core.app_launcher.shutil.which")
    def test_find_executable_found_by_which(self, mock_which):
        mock_which.return_value = "C:\\windows\\notepad.exe"
        result = self.launcher.find_executable("notepad.exe")
        self.assertEqual(result, "C:\\windows\\notepad.exe")

    @patch("core.app_launcher.shutil.which")
    def test_find_executable_adds_exe(self, mock_which):
        mock_which.return_value = "C:\\windows\\calc.exe"
        result = self.launcher.find_executable("calc")
        self.assertEqual(result, "C:\\windows\\calc.exe")

    @patch("core.app_launcher.shutil.which", return_value=None)
    @patch("core.app_launcher.os.path.isfile")
    @patch.dict("os.environ", {"PATH": "C:\\windows;C:\\windows\\system32"})
    def test_find_executable_in_path_dirs(self, mock_isfile, mock_which):
        mock_isfile.return_value = True
        result = self.launcher.find_executable("notepad.exe")
        self.assertIsNotNone(result)

    @patch("core.app_launcher.shutil.which", return_value=None)
    @patch("core.app_launcher.os.path.isfile", return_value=False)
    def test_find_executable_not_found(self, mock_isfile, mock_which):
        result = self.launcher.find_executable("nonexistent.exe")
        self.assertIsNone(result)

    @patch("core.app_launcher.AppLauncher._launch_path")
    def test_launch_by_alias(self, mock_launch):
        mock_launch.return_value = True
        result = self.launcher.launch("блокнот")
        self.assertTrue(result)

    @patch("core.app_launcher.AppLauncher._launch_path")
    def test_launch_by_alias_not_found(self, mock_launch):
        mock_launch.return_value = False
        result = self.launcher.launch("браузер")
        self.assertFalse(result)

    @patch("core.app_launcher.AppLauncher.find_executable")
    @patch("core.app_launcher.AppLauncher._launch_path")
    def test_launch_by_name(self, mock_launch, mock_find):
        mock_find.return_value = "C:\\test.exe"
        mock_launch.return_value = True
        result = self.launcher.launch("test.exe")
        self.assertTrue(result)

    @patch("core.app_launcher.AppLauncher.find_executable", return_value=None)
    @patch("core.app_launcher.os.startfile")
    def test_launch_startfile_fallback(self, mock_startfile, mock_find):
        mock_startfile.return_value = None
        result = self.launcher.launch("test.doc")
        self.assertTrue(result)

    @patch("core.app_launcher.AppLauncher.find_executable", return_value=None)
    @patch("core.app_launcher.os.startfile", side_effect=Exception("fail"))
    def test_launch_startfile_fails(self, mock_startfile, mock_find):
        result = self.launcher.launch("test.doc")
        self.assertFalse(result)

    @patch("core.app_launcher.AppLauncher._launch_path")
    def test_launch_blacklisted(self, mock_launch):
        self.launcher.blacklist("calc.exe")
        result = self.launcher.launch("calc.exe")
        self.assertFalse(result)
        mock_launch.assert_not_called()

    @patch("core.app_launcher.AppLauncher._launch_path")
    def test_launch_isfile_path(self, mock_launch):
        mock_launch.return_value = True
        with patch("core.app_launcher.os.path.isfile", return_value=True):
            result = self.launcher.launch("C:\\existing.exe")
        self.assertTrue(result)

    @patch("core.app_launcher.subprocess.Popen")
    def test_launch_path_success(self, mock_popen):
        mock_popen.return_value = MagicMock()
        result = self.launcher._launch_path("C:\\test.exe")
        self.assertTrue(result)

    @patch("core.app_launcher.subprocess.Popen", side_effect=Exception("fail"))
    def test_launch_path_failure(self, mock_popen):
        result = self.launcher._launch_path("C:\\test.exe")
        self.assertFalse(result)

    def test_blacklist_whitelist(self):
        self.launcher.blacklist("Calc.exe")
        self.assertIn("calc.exe", self.launcher._blacklisted)
        self.launcher.whitelist("Calc.exe")
        self.assertNotIn("calc.exe", self.launcher._blacklisted)

    def test_blacklist_case_insensitive(self):
        self.launcher.blacklist("NOTEPAD.EXE")
        self.assertIn("notepad.exe", self.launcher._blacklisted)


if __name__ == "__main__":
    unittest.main()
