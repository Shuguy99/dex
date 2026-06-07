import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.integrations.wearable")


class WearableMonitor:
    def __init__(self) -> None:
        self._data_dir = Path("data/wearable")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._heart_rate: list[dict[str, Any]] = []
        self._steps: list[dict[str, Any]] = []
        self._connected = False

    @property
    def available(self) -> bool:
        try:
            import requests
            return False
        except ImportError:
            return False

    def connect_fitbit(self, token: str = "", client_id: str = "") -> bool:
        try:
            import requests
            self._connected = True
            logger.info("Fitness tracker connected")
            return True
        except ImportError:
            logger.warning("requests not installed")
            return False

    def connect_garmin(self, email: str = "", password: str = "") -> bool:
        try:
            import garminconnect
            self._connected = True
            logger.info("Garmin connected")
            return True
        except ImportError:
            logger.debug("garminconnect not available")
            return False

    def get_heart_rate(self) -> dict[str, Any] | None:
        if not self._connected:
            return None

        mock_data = {
            "current_bpm": 72,
            "resting_bpm": 62,
            "zone": "normal",
            "timestamp": datetime.now().isoformat()
        }

        if mock_data["current_bpm"] > 100:
            mock_data["zone"] = "elevated"
        elif mock_data["current_bpm"] < 50:
            mock_data["zone"] = "low"

        self._heart_rate.append(mock_data)
        return mock_data

    def get_steps(self) -> dict[str, Any]:
        mock = {
            "today_steps": 8432,
            "goal": 10000,
            "progress_pct": 84.3,
            "timestamp": datetime.now().isoformat()
        }
        self._steps.append(mock)
        return mock

    def check_health_alert(self) -> str | None:
        hr = self.get_heart_rate()
        if not hr:
            return None

        if hr.get("current_bpm", 0) > 120:
            return "Ваш пульс повышен. Рекомендую сделать паузу и выпить воды."
        if hr.get("current_bpm", 0) < 45:
            return "Ваш пульс ниже нормы. Всё в порядке, сэр?"

        steps = self.get_steps()
        if steps.get("progress_pct", 100) < 20 and datetime.now().hour > 14:
            return "Вы сегодня мало двигались. Может, прогулка?"

        return None

    def log_custom_metric(self, name: str, value: float, unit: str = ""):
        entry = {
            "name": name,
            "value": value,
            "unit": unit,
            "timestamp": datetime.now().isoformat()
        }
        path = self._data_dir / "custom_metrics.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info(f"Metric logged: {name}={value}{unit}")
