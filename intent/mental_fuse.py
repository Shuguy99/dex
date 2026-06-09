import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.intent.mental_fuse")


DESTRUCTIVE_PATTERNS = [
    (r"\brm\s+-rf\b", "Shell: dangerous recursive delete"),
    (r"\bformat\s+\w:", "OS: disk format"),
    (r"\bdel\s+/[fs]", "Shell: force delete"),
    (r"\brd\s+/[sq]", "Shell: recursive directory delete"),
    (r"\bDROP\s+TABLE", "Database: table deletion"),
    (r"\bDELETE\s+FROM\s+\w+\s+(?!WHERE)", "Database: unconditional delete"),
]

SENSITIVE_FILE_PATTERNS = [
    r"system32", r"windows\\system", r"boot\.ini",
    r"config\.json.*password", r"\.env",
    r"id_rsa", r"\.pem", r"credentials",
]

ANGER_KEYWORDS = [
    "ненавижу", "бесит", "удалить всё", "к чёрту",
    "пошло всё", "достало", "ненавижу это"
]


class MentalFuse:
    def __init__(self) -> None:
        self._data_dir = Path("data/intent")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self._data_dir / "mental_fuse_log.json"
        self._blocks: list[dict[str, Any]] = []

    def check(self, command: str, args: str = "",
              context: dict[str, Any] | None = None) -> dict[str, Any]:
        full = f"{command} {args}"
        triggers = []
        blocks = []

        for pattern, desc in DESTRUCTIVE_PATTERNS:
            if re.search(pattern, full, re.IGNORECASE):
                triggers.append({"type": "destructive_command", "detail": desc})
                blocks.append(f"⛔ {desc}")

        for pattern in SENSITIVE_FILE_PATTERNS:
            if re.search(pattern, full, re.IGNORECASE):
                triggers.append({"type": "sensitive_file", "detail": f"Target: {pattern}"})
                blocks.append(f"⚠️ Действие затрагивает критический файл: {pattern}")

        if context and context.get("emotion") == "high":
            triggers.append({"type": "emotional_state", "detail": "High emotional arousal detected"})
            blocks.append("💬 Вы кажетесь взволнованным. Подтвердите действие.")

        blocked = len(blocks) > 0
        if blocked:
            entry = {
                "command": command[:100],
                "args": args[:100],
                "triggers": triggers,
                "timestamp": datetime.now().isoformat(),
                "user_confirmed": False
            }
            self._blocks.append(entry)
            self._save_log(entry)

        return {
            "blocked": blocked,
            "triggers": triggers,
            "messages": blocks,
            "requires_confirmation": blocked
        }

    def _save_log(self, entry: dict) -> None:
        import json
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def get_mental_fuse_summary(self) -> str:
        total = len(self._blocks)
        if not total:
            return "── Mental Fuse: no blocks triggered ──"
        lines = ["── Mental Fuse ──"]
        lines.append(f"  Blocks triggered: {total}")
        for b in self._blocks[-5:]:
            types = ", ".join(t["type"] for t in b.get("triggers", []))
            lines.append(f"  ⛔ {b.get('command', '')[:40]} → {types}")
        return "\n".join(lines)
