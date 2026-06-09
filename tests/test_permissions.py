import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.permissions import PermissionManager


class TestPermissionManager(unittest.TestCase):
    def setUp(self):
        self.pm = PermissionManager()

    def test_init_no_voice(self):
        pm = PermissionManager()
        self.assertIsNone(pm._voice)
        self.assertIsNone(pm._password_hash)

    def test_init_with_voice(self):
        voice = MagicMock()
        pm = PermissionManager(voice_engine=voice)
        self.assertIs(pm._voice, voice)

    @patch("getpass.getpass", return_value="anything")
    def test_confirm_dangerous_action_voice_confirmed(self, mock_getpass):
        voice = MagicMock()
        voice.listen.return_value = "да сэр"
        pm = PermissionManager(voice_engine=voice)
        result = pm.confirm_dangerous_action("delete file")
        self.assertTrue(result)
        voice.say.assert_called_once()

    @patch("getpass.getpass", return_value="anything")
    def test_confirm_dangerous_action_voice_no(self, mock_getpass):
        voice = MagicMock()
        voice.listen.return_value = "нет"
        pm = PermissionManager(voice_engine=voice)
        pm._verify_password = MagicMock(return_value=False)
        result = pm.confirm_dangerous_action("delete file")
        self.assertFalse(result)

    @patch("getpass.getpass", return_value="correct")
    def test_confirm_dangerous_action_voice_none_then_password_correct(self, mock_getpass):
        voice = MagicMock()
        voice.listen.return_value = "something else"
        pm = PermissionManager(voice_engine=voice)
        pm._verify_password = MagicMock(return_value=True)
        result = pm.confirm_dangerous_action("delete file")
        self.assertTrue(result)

    @patch("getpass.getpass", return_value="correct")
    def test_confirm_dangerous_action_no_voice_password_correct(self, mock_getpass):
        pm = PermissionManager()
        pm._verify_password = MagicMock(return_value=True)
        result = pm.confirm_dangerous_action("delete file")
        self.assertTrue(result)

    @patch("getpass.getpass", return_value="wrong")
    def test_confirm_dangerous_action_no_voice_password_wrong(self, mock_getpass):
        pm = PermissionManager()
        pm._verify_password = MagicMock(return_value=False)
        result = pm.confirm_dangerous_action("delete file")
        self.assertFalse(result)

    @patch("getpass.getpass", return_value="anything")
    def test_confirm_dangerous_action_voice_listen_none(self, mock_getpass):
        voice = MagicMock()
        voice.listen.return_value = None
        pm = PermissionManager(voice_engine=voice)
        pm._verify_password = MagicMock(return_value=False)
        result = pm.confirm_dangerous_action("delete file")
        self.assertFalse(result)

    def test_set_password(self):
        self.pm.set_password("mypass")
        self.assertIsNotNone(self.pm._password_hash)

    def test_verify_password_no_hash(self):
        self.assertTrue(self.pm._verify_password("anything"))

    def test_verify_password_with_hash(self):
        self.pm.set_password("correct")
        self.assertTrue(self.pm._verify_password("correct"))
        self.assertFalse(self.pm._verify_password("wrong"))

    def test_is_admin_true(self):
        with patch("ctypes.windll.shell32.IsUserAnAdmin", return_value=True):
            self.assertTrue(self.pm.is_admin())

    def test_is_admin_false(self):
        with patch("ctypes.windll.shell32.IsUserAnAdmin", return_value=False):
            self.assertFalse(self.pm.is_admin())

    def test_is_admin_exception(self):
        with patch("ctypes.windll.shell32.IsUserAnAdmin", side_effect=Exception("no ctypes")):
            self.assertFalse(self.pm.is_admin())

    def test_ensure_non_admin(self):
        voice = MagicMock()
        pm = PermissionManager(voice_engine=voice)
        with patch.object(pm, "is_admin", return_value=True):
            pm.ensure_non_admin()
            voice.say.assert_called_once()

    def test_ensure_non_admin_already_non_admin(self):
        voice = MagicMock()
        pm = PermissionManager(voice_engine=voice)
        with patch.object(pm, "is_admin", return_value=False):
            pm.ensure_non_admin()
            voice.say.assert_not_called()

    @patch("core.permissions.subprocess.run")
    def test_run_restricted(self, mock_run):
        mock_run.return_value = MagicMock()
        result = PermissionManager.run_restricted(["echo", "test"])
        mock_run.assert_called_once()
        self.assertIsNotNone(result)

    @patch("core.permissions.subprocess.run", side_effect=OSError("fail"))
    def test_run_restricted_exception(self, mock_run):
        with self.assertRaises(OSError):
            PermissionManager.run_restricted(["bad"])


if __name__ == "__main__":
    unittest.main()
