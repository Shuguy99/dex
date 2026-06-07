import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.learning.backup")


class BackupManager:
    def __init__(self, backup_dir: str | Path) -> None:
        self._backup_dir = Path(backup_dir)
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, name: str, data: dict[str, Any],
                      files: list[str] | None = None) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() else "_" for c in name)
        backup_path = self._backup_dir / f"{safe_name}_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)

        meta_path = backup_path / "backup_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "name": name,
                "timestamp": timestamp,
                "data_keys": list(data.keys())
            }, f, ensure_ascii=False, indent=2)

        data_path = backup_path / "data.json"
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if files:
            files_dir = backup_path / "files"
            files_dir.mkdir(exist_ok=True)
            for src in files:
                src_path = Path(src)
                if src_path.exists():
                    shutil.copy2(src_path, files_dir / src_path.name)

        logger.info(f"Backup created: {backup_path}")
        return str(backup_path)

    def list_backups(self, name_filter: str | None = None) -> list[dict[str, Any]]:
        backups = []
        for entry in sorted(self._backup_dir.iterdir(), reverse=True):
            if entry.is_dir() and (name_filter is None or name_filter in entry.name):
                meta = entry / "backup_meta.json"
                if meta.exists():
                    with open(meta, encoding="utf-8") as f:
                        backups.append(json.load(f))
        return backups

    def restore_backup(self, backup_path: str) -> dict[str, Any] | None:
        data_path = Path(backup_path) / "data.json"
        if not data_path.exists():
            logger.error(f"Backup data not found: {data_path}")
            return None

        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)

        files_dir = Path(backup_path) / "files"
        if files_dir.exists():
            for f_path in files_dir.iterdir():
                if f_path.is_file():
                    dest = Path.cwd() / f_path.name
                    shutil.copy2(f_path, dest)
                    logger.info(f"Restored file: {dest}")

        logger.info(f"Restored from: {backup_path}")
        return data
