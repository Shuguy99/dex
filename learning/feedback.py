import contextlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.learning.feedback")


class FeedbackCollector:
    def __init__(self, data_dir: str | Path) -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._data_dir / "feedback.jsonl"
        self._ratings: list[dict[str, Any]] = []

    def ask(self, action: str, context: str = "") -> int | None:
        logger.info(f"Feedback requested for: {action}")
        print(f"\n[Dex] {context}")
        print("Оцени результат от 1 до 5 (0 — пропустить): ")
        try:
            rating = int(input("> ").strip())
            if 1 <= rating <= 5:
                self._record(action, rating)
                return rating
            elif rating == 0:
                return None
        except (ValueError, EOFError):
            pass
        return None

    def _record(self, action: str, rating: int) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "rating": rating
        }
        self._ratings.append(entry)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info(f"Feedback recorded: {action} -> {rating}/5")

    def get_stats(self, days: int = 7) -> dict[str, Any]:
        cutoff = datetime.now() - timedelta(days=days)
        recent = [r for r in self._ratings
                  if datetime.fromisoformat(r["timestamp"]) >= cutoff]
        if not recent:
            return {"count": 0, "avg": 0, "days": days}

        return {
            "count": len(recent),
            "avg": sum(r["rating"] for r in recent) / len(recent),
            "min": min(r["rating"] for r in recent),
            "max": max(r["rating"] for r in recent),
            "days": days
        }

    def low_rated_actions(self, threshold: int = 2) -> list[dict[str, Any]]:
        return [r for r in self._ratings if r["rating"] <= threshold]

    def load_history(self) -> list[dict[str, Any]]:
        if self._path.exists():
            with open(self._path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        with contextlib.suppress(json.JSONDecodeError):
                            self._ratings.append(json.loads(line))
