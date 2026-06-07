import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.mesh.privacy")


class MeshPrivacyController:
    def __init__(self) -> None:
        self._data_dir = Path("data/mesh")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._policy_path = self._data_dir / "privacy_policy.json"
        self._policies: dict[str, dict[str, Any]] = self._load_policies()

    def _load_policies(self) -> dict[str, Any]:
        if self._policy_path.exists():
            try:
                with open(self._policy_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"devices": {}, "default_level": "local_process"}

    def _save_policies(self):
        with open(self._policy_path, "w", encoding="utf-8") as f:
            json.dump(self._policies, f, ensure_ascii=False, indent=2)

    DATA_LEVELS = {
        "local_sensor": {
            "label": "Обработка на сенсоре",
            "description": "Данные не покидают устройство сбора. На сервер передаётся только вывод"
        },
        "local_process": {
            "label": "Обработка на устройстве",
            "description": "Данные обрабатываются на устройстве, передаются только результаты"
        },
        "encrypted_relay": {
            "label": "Шифрованная передача",
            "description": "Данные шифруются перед отправкой на сервер"
        },
        "full_access": {
            "label": "Полный доступ",
            "description": "Данные могут передаваться и обрабатываться на любом узле сети"
        }
    }

    def set_device_policy(self, device_id: str, data_type: str, level: str):
        if level not in self.DATA_LEVELS:
            return False
        if device_id not in self._policies["devices"]:
            self._policies["devices"][device_id] = {}
        self._policies["devices"][device_id][data_type] = {
            "level": level,
            "label": self.DATA_LEVELS[level]["label"],
            "updated": datetime.now().isoformat()
        }
        self._save_policies()
        return True

    def get_device_policy(self, device_id: str, data_type: str) -> dict[str, Any]:
        device_policies = self._policies["devices"].get(device_id, {})
        policy = device_policies.get(data_type)
        if policy:
            return policy
        default_level = self._policies["default_level"]
        return {
            "level": default_level,
            "label": self.DATA_LEVELS[default_level]["label"],
            "source": "default"
        }

    def can_transmit(self, device_id: str, data_type: str) -> bool:
        policy = self.get_device_policy(device_id, data_type)
        level = policy.get("level", "local_process")
        return level in ("encrypted_relay", "full_access")

    def needs_encryption(self, device_id: str, data_type: str) -> bool:
        policy = self.get_device_policy(device_id, data_type)
        return policy.get("level") == "encrypted_relay"

    def get_privacy_summary(self) -> str:
        lines = ["── Mesh Privacy Controller ──"]
        lines.append(f"Default level: {self._policies['default_level']}")
        lines.append("Device policies:")
        for device_id, policies in self._policies.get("devices", {}).items():
            lines.append(f"  {device_id}:")
            for dtype, pol in policies.items():
                lines.append(f"    {dtype} → {pol['label']}")
        return "\n".join(lines)
