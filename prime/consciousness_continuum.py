import json
import logging
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.prime.continuum")


class ConsciousnessContinuum:
    def __init__(self) -> None:
        self._data_dir = Path("data/prime")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._session_path = self._data_dir / "session_continuum.json"
        self._current_session: dict[str, Any] | None = None
        self._session_history: deque[dict] = deque(maxlen=50)
        self._handoff_ready = False

    def start_session(self, device_id: str, context: dict[str, Any] | None = None) -> None:
        self._current_session = {
            "id": f"sess_{int(time.time())}",
            "device_id": device_id,
            "start_time": datetime.now().isoformat(),
            "context": context or {},
            "history": [],
            "emotional_tone": "neutral",
            "pending_tasks": [],
            "intermediate_results": []
        }
        self._session_history.append(self._current_session)
        self._handoff_ready = True
        logger.info(f"Session started on {device_id}")

    def record_interaction(self, text: str, result: str) -> None:
        if not self._current_session:
            return
        self._current_session["history"].append({
            "timestamp": datetime.now().isoformat(),
            "input": text[:200],
            "result": result[:200]
        })

    def set_pending_task(self, task: str) -> None:
        if self._current_session:
            self._current_session["pending_tasks"].append(task)

    def store_intermediate(self, key: str, value: Any) -> None:
        if self._current_session:
            self._current_session["intermediate_results"].append({
                "key": key,
                "value": str(value)[:500],
                "timestamp": datetime.now().isoformat()
            })

    def prepare_handoff(self) -> dict[str, Any] | None:
        if not self._current_session:
            return None
        serialized = json.dumps(self._current_session, ensure_ascii=False, default=str)
        with open(self._session_path, "w", encoding="utf-8") as f:
            f.write(serialized)
        self._handoff_ready = True
        return {
            "session_id": self._current_session["id"],
            "context_size": len(self._current_session["history"]),
            "pending_tasks": self._current_session["pending_tasks"],
            "emotional_tone": self._current_session["emotional_tone"]
        }

    def restore_session(self) -> bool:
        if not self._session_path.exists():
            return False
        try:
            with open(self._session_path, encoding="utf-8") as f:
                data = json.load(f)
            self._current_session = data
            self._current_session["restored_at"] = datetime.now().isoformat()
            self._current_session["restore_count"] = \
                self._current_session.get("restore_count", 0) + 1
            self._session_history.append(self._current_session)
            logger.info(f"Session restored: {data.get('id', '?')}")
            return True
        except Exception as e:
            logger.warning(f"Session restore failed: {e}")
            return False

    def get_context_summary(self) -> str:
        if not self._current_session:
            return "Нет активной сессии."
        s = self._current_session
        lines = ["── Consciousness Continuum ──"]
        lines.append(f"  Session: {s.get('id', '?')}")
        lines.append(f"  Device: {s.get('device_id', '?')}")
        lines.append(f"  History: {len(s.get('history', []))} interactions")
        lines.append(f"  Pending tasks: {len(s.get('pending_tasks', []))}")
        lines.append(f"  Handoff ready: {self._handoff_ready}")
        return "\n".join(lines)
