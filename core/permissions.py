import contextlib
import getpass
import logging
import subprocess

logger = logging.getLogger("dex.permissions")


class PermissionManager:
    def __init__(self, voice_engine=None) -> None:
        self._voice = voice_engine
        self._password_hash: str | None = None

    def confirm_dangerous_action(self, action_desc: str) -> bool:
        logger.warning(f"Dangerous action requested: {action_desc}")
        if self._voice:
            self._voice.say(
                f"Внимание, сэр. Требуется подтверждение: {action_desc}. "
                f"Скажите «Да, сэр» для подтверждения или введите пароль."
            )
            if self._voice.listen(timeout=5):
                response = self._voice.listen(timeout=5)
                if response and "да сэр" in response.lower():
                    logger.info("Confirmed via voice: 'Да, сэр'")
                    return True

        pwd = getpass.getpass(f"Confirm '{action_desc}': ")
        if self._verify_password(pwd):
            logger.info("Confirmed via password")
            return True

        logger.warning("Action denied by user")
        return False

    def set_password(self, password: str):
        self._password_hash = str(hash(password))

    def _verify_password(self, password: str) -> bool:
        if self._password_hash is None:
            return True
        return str(hash(password)) == self._password_hash

    def is_admin(self) -> bool:
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def ensure_non_admin(self):
        if self.is_admin():
            logger.warning("Running as admin - this is not recommended")
            self._voice.say("Предупреждение: ассистент запущен с правами администратора")

    @staticmethod
    def run_restricted(command: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
        creation_flags = 0
        with contextlib.suppress(AttributeError):
            creation_flags = subprocess.CREATE_NO_WINDOW

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=creation_flags
        )
