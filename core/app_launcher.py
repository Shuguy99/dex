import logging
import os
import shutil
import subprocess

logger = logging.getLogger("dex.app_launcher")

APP_ALIASES = {
    "браузер": ["chrome.exe", "msedge.exe", "firefox.exe"],
    "калькулятор": ["calc.exe"],
    "блокнот": ["notepad.exe"],
    "терминал": ["powershell.exe", "cmd.exe"],
    "проводник": ["explorer.exe"],
    "диспетчер задач": ["taskmgr.exe"],
    "настройки": ["ms-settings:"],
    "steam": ["steam.exe"],
    "discord": ["discord.exe"],
    "telegram": ["telegram.exe"],
    "vs code": ["Code.exe"],
    "visual studio code": ["Code.exe"],
    "код": ["Code.exe"],
    "word": ["WINWORD.EXE"],
    "excel": ["EXCEL.EXE"],
    "outlook": ["OUTLOOK.EXE"],
    "spotify": ["Spotify.exe"],
    "skype": ["Skype.exe"],
}


class AppLauncher:
    def __init__(self) -> None:
        self._blacklisted = set()

    def find_executable(self, name: str) -> str | None:
        ext = os.path.splitext(name)[1] or ".exe"
        if not name.endswith((".exe", ".com", ".bat", ".cmd")):
            name += ext

        path = shutil.which(name)
        if path:
            return path

        for dir in os.environ.get("PATH", "").split(os.pathsep):
            candidate = os.path.join(dir.strip('"'), name)
            if os.path.isfile(candidate):
                return candidate
        return None

    def launch(self, name: str) -> bool:
        if name in self._blacklisted:
            logger.warning(f"Blacklisted app: {name}")
            return False

        lower = name.lower()
        if lower in APP_ALIASES:
            for exe in APP_ALIASES[lower]:
                path = self.find_executable(exe)
                if path:
                    return self._launch_path(path)
            logger.warning(f"No executable found for alias '{name}'")
            return False

        if os.path.isfile(name):
            return self._launch_path(name)

        path = self.find_executable(name)
        if path:
            return self._launch_path(path)

        try:
            os.startfile(name)
            logger.info(f"Startfile: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to launch '{name}': {e}")
            return False

    def _launch_path(self, path: str) -> bool:
        try:
            subprocess.Popen([path], shell=False)
            logger.info(f"Launched: {path}")
            return True
        except Exception as e:
            logger.error(f"Launch failed: {path}: {e}")
            return False

    def blacklist(self, name: str):
        self._blacklisted.add(name.lower())

    def whitelist(self, name: str):
        self._blacklisted.discard(name.lower())
