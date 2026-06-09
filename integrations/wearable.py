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
        self._connection_type: str | None = None
        self._fitbit_token: str | None = None
        self._garmin_client: Any = None

    @property
    def available(self) -> bool:
        try:
            import requests  # noqa: F401
            return True
        except ImportError:
            return False

    def connect_fitbit(self, token: str = "", client_id: str = "") -> bool:
        try:
            import requests

            url = "https://api.fitbit.com/1/user/-/profile.json"
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            display_name = data.get("user", {}).get("displayName", "unknown")
            logger.info("Fitbit connected as %s", display_name)
            self._connected = True
            self._connection_type = "fitbit"
            self._fitbit_token = token
            return True
        except Exception:
            logger.exception("Failed to connect Fitbit")
            return False

    def connect_garmin(self, email: str = "", password: str = "") -> bool:
        try:
            from garminconnect import Garmin

            client = Garmin(email, password)
            client.login()
            logger.info("Garmin connected as %s", email)
            self._connected = True
            self._connection_type = "garmin"
            self._garmin_client = client
            return True
        except Exception:
            logger.exception("Failed to connect Garmin")
            return False

    def get_heart_rate(self) -> dict[str, Any] | None:
        if not self._connected or self._connection_type != "fitbit" or not self._fitbit_token:
            return None
        try:
            import requests

            url = "https://api.fitbit.com/1/user/-/activities/heart/date/today/1d.json"
            headers = {"Authorization": f"Bearer {self._fitbit_token}"}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            activities = data.get("activities-heart", [])
            value = activities[0].get("value", {}) if activities else {}
            resting_bpm = value.get("restingHeartRate")

            current_bpm = None
            intraday = data.get("activities-heart-intraday", {})
            dataset = intraday.get("dataset", [])
            if dataset:
                current_bpm = dataset[-1].get("value")

            zones = value.get("heartRateZones", [])
            zone = "normal"
            bpm = current_bpm or resting_bpm
            if bpm is not None:
                for z in zones:
                    zmin = z.get("min", 0)
                    zmax = z.get("max", 999)
                    if zmin <= bpm < zmax:
                        zone = z.get("name", "normal").lower()
                        break

            hr_data: dict[str, Any] = {
                "current_bpm": current_bpm or resting_bpm,
                "resting_bpm": resting_bpm,
                "zone": zone,
                "timestamp": datetime.now().isoformat(),
            }
            self._heart_rate.append(hr_data)
            return hr_data
        except Exception:
            logger.exception("Failed to fetch heart rate")
            return None

    def get_steps(self) -> dict[str, Any] | None:
        if not self._connected or self._connection_type != "fitbit" or not self._fitbit_token:
            return None
        try:
            import requests

            url = "https://api.fitbit.com/1/user/-/activities/steps/date/today/1d.json"
            headers = {"Authorization": f"Bearer {self._fitbit_token}"}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            activities = data.get("activities-steps", [])
            today_steps = int(activities[0].get("value", 0)) if activities else 0

            steps_data: dict[str, Any] = {
                "today_steps": today_steps,
                "goal": None,
                "progress_pct": None,
                "timestamp": datetime.now().isoformat(),
            }
            self._steps.append(steps_data)
            return steps_data
        except Exception:
            logger.exception("Failed to fetch steps")
            return None

    def check_health_alert(self) -> str | None:
        hr = self.get_heart_rate()
        if not hr:
            return None
        if hr.get("current_bpm", 0) > 120:
            return "Ваш пульс повышен. Рекомендую сделать паузу и выпить воды."
        if hr.get("current_bpm", 0) < 45:
            return "Ваш пульс ниже нормы. Всё в порядке, сэр?"
        steps = self.get_steps()
        if steps and steps.get("progress_pct") is not None and steps["progress_pct"] < 20 and datetime.now().hour > 14:
            return "Вы сегодня мало двигались. Может, прогулка?"
        return None

    def log_custom_metric(self, name: str, value: float, unit: str = "") -> None:
        entry = {
            "name": name,
            "value": value,
            "unit": unit,
            "timestamp": datetime.now().isoformat(),
        }
        path = self._data_dir / "custom_metrics.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info("Metric logged: %s=%s%s", name, value, unit)
