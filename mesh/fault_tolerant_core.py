import json
import logging
from collections import deque
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.mesh.fault_tolerance")

PRESERVED_STATE_KEYS = ["config", "memory_index", "feedback_stats",
                         "rules", "personality_mode"]


class FaultTolerantCore:
    def __init__(self, state_provider: Callable | None = None) -> None:
        self._data_dir = Path("data/mesh")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._state_path = self._data_dir / "recovery_state.json"
        self._state: dict[str, Any] = self._load_state()
        self._state_provider = state_provider
        self._health_log: deque[dict] = deque(maxlen=100)
        self._reduced_mode = False

    def _load_state(self) -> dict[str, Any]:
        if self._state_path.exists():
            try:
                with open(self._state_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"last_active": None, "recovery_count": 0, "state_snapshot": {}}

    def _save_state(self):
        with open(self._state_path, "w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)

    def save_snapshot(self, custom_state: dict[str, Any] | None = None):
        snapshot = custom_state or {}
        if self._state_provider:
            try:
                provided = self._state_provider()
                if isinstance(provided, dict):
                    snapshot.update(provided)
            except Exception as e:
                logger.warning(f"State provider failed: {e}")

        self._state["state_snapshot"] = {
            "timestamp": datetime.now().isoformat(),
            "data": snapshot
        }
        self._state["last_active"] = datetime.now().isoformat()
        self._save_state()
        logger.debug("State snapshot saved")

    def recover(self) -> dict[str, Any]:
        if not self._state.get("state_snapshot"):
            return {"recovered": False, "reason": "No state snapshot available"}

        self._state["recovery_count"] += 1
        self._state["last_recovery"] = datetime.now().isoformat()
        self._save_state()

        logger.info(f"Recovery #{self._state['recovery_count']} from "
                     f"{self._state['state_snapshot']['timestamp']}")
        return {
            "recovered": True,
            "snapshot_time": self._state["state_snapshot"]["timestamp"],
            "data": self._state["state_snapshot"]["data"],
            "recovery_count": self._state["recovery_count"]
        }

    def enter_reduced_mode(self, reason: str = "Primary unavailable"):
        self._reduced_mode = True
        entry = {
            "event": "reduced_mode",
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        self._health_log.append(entry)
        logger.warning(f"Entering reduced mode: {reason}")

    def exit_reduced_mode(self):
        self._reduced_mode = False
        entry = {
            "event": "full_mode",
            "timestamp": datetime.now().isoformat()
        }
        self._health_log.append(entry)
        logger.info("Exited reduced mode, full functionality restored")

    def record_health(self, status: str, details: str = ""):
        entry = {
            "status": status,
            "details": details[:200],
            "timestamp": datetime.now().isoformat()
        }
        self._health_log.append(entry)

    def get_last_health(self, n: int = 5) -> list[dict[str, Any]]:
        return list(self._health_log)[-n:]

    def get_fault_summary(self) -> str:
        lines = ["── Fault-Tolerant Core ──"]
        lines.append(f"State: {'reduced' if self._reduced_mode else 'full'}")
        lines.append(f"Recoveries: {self._state.get('recovery_count', 0)}")
        lines.append(f"Last active: {self._state.get('last_active', 'never')[:19]}")
        recent = self.get_last_health(3)
        if recent:
            lines.append("Recent health:")
            for h in recent:
                lines.append(f"  {h['timestamp'][:19]} [{h['status']}] {h.get('details', '')[:50]}")
        return "\n".join(lines)
