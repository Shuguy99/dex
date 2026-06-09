import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


class DexLogger:
    def __init__(self, log_dir: str | Path, level: int = logging.INFO) -> None:
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._setup_root_logger(level)
        self._command_log: list[dict] = []
        self._command_log_path = self._log_dir / "commands.jsonl"

    def _setup_root_logger(self, level: int) -> None:
        root = logging.getLogger()
        if root.handlers:
            return
        fmt = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler = RotatingFileHandler(
            self._log_dir / "dex.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        handler.setFormatter(fmt)
        console = logging.StreamHandler()
        console.setFormatter(fmt)

        root = logging.getLogger()
        root.setLevel(level)
        root.addHandler(handler)
        root.addHandler(console)

    def log_command(self, command: str, response: str | None = None,
                    duration_ms: float | None = None, success: bool = True) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "response": response,
            "duration_ms": duration_ms,
            "success": success
        }
        self._command_log.append(entry)
        with open(self._command_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_recent_commands(self, n: int = 10) -> list[dict]:
        return self._command_log[-n:]

    def get_commands_since(self, timestamp: datetime) -> list[dict]:
        return [
            e for e in self._command_log
            if datetime.fromisoformat(e["timestamp"]) >= timestamp
        ]
