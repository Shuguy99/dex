import json
import logging
from datetime import datetime, time
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.psych.circadian")


class CircadianAdapter:
    def __init__(self) -> None:
        self._data_dir = Path("data/psych")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._config_path = self._data_dir / "circadian_config.json"
        self._config: dict[str, Any] = self._load_config()
        self._schedule = self._build_schedule()

    def _load_config(self) -> dict[str, Any]:
        if self._config_path.exists():
            try:
                with open(self._config_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "wake_time": "07:00",
            "bed_time": "23:00",
            "peak_start": "09:00",
            "peak_end": "12:00",
            "sleep_data_source": "manual",
            "color_temperature": 6500
        }

    def _save_config(self) -> None:
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    def _build_schedule(self) -> dict[str, dict[str, Any]]:
        wake = self._parse_time(self._config["wake_time"], 7)
        bed = self._parse_time(self._config["bed_time"], 23)
        peak_start = self._parse_time(self._config["peak_start"], 9)
        peak_end = self._parse_time(self._config["peak_end"], 12)

        return {
            "sleep": {
                "start": bed,
                "end": wake,
                "label": "Сон",
                "color_temp": 2700,
                "volume": 0.3,
                "notification_mode": "silent"
            },
            "morning_routine": {
                "start": wake,
                "end": peak_start,
                "label": "Утренняя рутина",
                "color_temp": 5000,
                "volume": 0.6,
                "notification_mode": "normal"
            },
            "peak": {
                "start": peak_start,
                "end": peak_end,
                "label": "Пик продуктивности",
                "color_temp": 6500,
                "volume": 0.5,
                "notification_mode": "minimal"
            },
            "afternoon": {
                "start": peak_end,
                "end": time(17, 0),
                "label": "Послеобеденный спад",
                "color_temp": 5000,
                "volume": 0.7,
                "notification_mode": "normal"
            },
            "evening": {
                "start": time(17, 0),
                "end": bed,
                "label": "Вечер",
                "color_temp": 3500,
                "volume": 0.5,
                "notification_mode": "reduced"
            }
        }

    def _parse_time(self, t_str: str, default_hour: int) -> time:
        try:
            parts = t_str.split(":")
            return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
        except (ValueError, IndexError):
            return time(default_hour, 0)

    def get_current_phase(self) -> dict[str, Any]:
        now = datetime.now().time()

        for phase_name, phase in self._schedule.items():
            start = phase["start"]
            end = phase["end"]

            if start <= end:
                if start <= now <= end:
                    return {**phase, "name": phase_name}
            else:
                if now >= start or now <= end:
                    return {**phase, "name": phase_name}

        return {"name": "unknown", "label": "Неизвестно",
                "color_temp": 5000, "volume": 0.5,
                "notification_mode": "normal"}

    def is_peak_time(self) -> bool:
        phase = self.get_current_phase()
        return phase.get("name") == "peak"

    def is_sleep_time(self) -> bool:
        phase = self.get_current_phase()
        return phase.get("name") == "sleep"

    def should_suppress_notifications(self) -> bool:
        phase = self.get_current_phase()
        return phase.get("notification_mode") in ("silent", "reduced")

    def update_sleep_schedule(self, wake_time: str | None = None,
                               bed_time: str | None = None) -> None:
        if wake_time:
            self._config["wake_time"] = wake_time
        if bed_time:
            self._config["bed_time"] = bed_time
        self._save_config()
        self._schedule = self._build_schedule()

    def get_temperature(self) -> int:
        phase = self.get_current_phase()
        return phase.get("color_temp", 5000)

    def get_volume_multiplier(self) -> float:
        phase = self.get_current_phase()
        return phase.get("volume", 0.5)

    def get_circadian_summary(self) -> str:
        phase = self.get_current_phase()
        lines = ["── Circadian Adaptation ──"]
        lines.append(f"  Текущая фаза: {phase['label']}")
        lines.append(f"  Цветовая температура: {phase.get('color_temp', 5000)}K")
        lines.append(f"  Громкость: {phase.get('volume', 0.5):.0%}")
        lines.append(f"  Уведомления: {phase.get('notification_mode', 'normal')}")
        if phase["name"] == "peak":
            lines.append("\n  Пик продуктивности — лучшее время для сложных задач!")
        elif phase["name"] == "sleep":
            lines.append("\n  Время отдыха — несрочные задачи будут отложены.")
        return "\n".join(lines)
