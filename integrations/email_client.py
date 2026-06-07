import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("dex.integrations.email")


class EmailClient:
    def __init__(self, thunderbird_path: str | None = None) -> None:
        self._tb_path = thunderbird_path or self._find_thunderbird()

    def _find_thunderbird(self) -> str | None:
        import shutil
        candidates = [
            "C:\\Program Files\\Mozilla Thunderbird\\thunderbird.exe",
            "C:\\Program Files (x86)\\Mozilla Thunderbird\\thunderbird.exe",
        ]
        for c in candidates:
            if Path(c).exists():
                return c
        return shutil.which("thunderbird")

    @property
    def available(self) -> bool:
        return self._tb_path is not None and Path(self._tb_path).exists()

    def open_compose(self, to: str = "", subject: str = "", body: str = ""):
        if not self.available:
            logger.warning("Thunderbird not found")
            return False
        try:
            args = [self._tb_path, "-compose", f"to='{to}',subject='{subject}',body='{body}'"]
            subprocess.Popen(args, shell=False)
            logger.info(f"Opened compose: to={to}, subject={subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to open compose: {e}")
            return False

    def open_mailto(self, address: str):
        if not self.available:
            return False
        try:
            subprocess.Popen([self._tb_path, f"mailto:{address}"], shell=False)
            return True
        except Exception as e:
            logger.error(f"Mailto failed: {e}")
            return False
