import importlib
import logging
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.evolution.hot_swapper")


class HotSwapper:
    def __init__(self) -> None:
        self._versions: dict[str, list[dict[str, Any]]] = {}
        self._active_versions: dict[str, str] = {}
        self._traffic_splits: dict[str, float] = {}
        self._swap_history: deque[dict] = deque(maxlen=100)
        self._data_dir = Path("data/evolution")
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def register_component(self, name: str, version: str, module_path: str,
                            class_name: str, init_args: dict | None = None) -> None:
        if name not in self._versions:
            self._versions[name] = []
        self._versions[name].append({
            "version": version,
            "module_path": module_path,
            "class_name": class_name,
            "init_args": init_args or {},
            "registered": datetime.now().isoformat(),
            "instance": None,
            "error_count": 0
        })
        if not self._active_versions.get(name):
            self._active_versions[name] = version
        logger.info(f"Component registered: {name} v{version}")

    def _load_instance(self, comp: dict) -> Any | None:
        try:
            spec = importlib.util.spec_from_file_location(
                comp["class_name"], comp["module_path"]
            )
            if not spec or not spec.loader:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            cls = getattr(module, comp["class_name"])
            instance = cls(**comp["init_args"])
            comp["instance"] = instance
            return instance
        except Exception as e:
            logger.error(f"Failed to load {comp['class_name']}: {e}")
            return None

    def hot_swap(self, name: str, new_version: str) -> dict[str, Any]:
        versions = self._versions.get(name, [])
        target = next((v for v in versions if v["version"] == new_version), None)
        if not target:
            return {"success": False, "reason": f"Version {new_version} not found"}

        old_version = self._active_versions.get(name)
        new_instance = self._load_instance(target)
        if new_instance is None:
            return {"success": False, "reason": "Failed to instantiate new version"}

        old_comp = next((v for v in versions if v["version"] == old_version), None)
        if old_comp and old_comp.get("instance"):
            try:
                if hasattr(old_comp["instance"], "shutdown"):
                    old_comp["instance"].shutdown()
            except Exception:
                pass

        self._active_versions[name] = new_version
        self._swap_history.append({
            "component": name,
            "from": old_version,
            "to": new_version,
            "timestamp": datetime.now().isoformat(),
            "success": True
        })
        logger.info(f"Hot-swap: {name} {old_version} → {new_version}")
        return {"success": True, "old_version": old_version, "new_version": new_version}

    def start_ab_test(self, name: str, new_version: str,
                       traffic_split: float = 0.2) -> dict[str, Any]:
        versions = self._versions.get(name, [])
        if not any(v["version"] == new_version for v in versions):
            return {"success": False, "reason": "New version not registered"}

        self._traffic_splits[name] = traffic_split
        ab_id = f"ab_{name}_{int(time.time())}"
        self._swap_history.append({
            "event": "ab_test_start",
            "component": name,
            "new_version": new_version,
            "traffic_split": traffic_split,
            "ab_id": ab_id,
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"A/B test started: {name} v{new_version} @ {traffic_split:.0%}")
        return {"success": True, "ab_id": ab_id, "traffic_split": traffic_split}

    def end_ab_test(self, name: str, promote: bool = False) -> dict[str, Any]:
        split = self._traffic_splits.pop(name, None)
        if split is None:
            return {"success": False, "reason": "No active A/B test"}

        self._swap_history.append({
            "event": "ab_test_end",
            "component": name,
            "promoted": promote,
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"A/B test ended: {name} promoted={promote}")
        return {"success": True, "promoted": promote}

    def get_instance(self, name: str) -> Any | None:
        version = self._active_versions.get(name)
        if not version:
            return None
        comp = next((v for v in self._versions.get(name, [])
                      if v["version"] == version), None)
        if comp and comp.get("instance"):
            return comp["instance"]
        if comp:
            return self._load_instance(comp)
        return None

    def get_swap_summary(self) -> str:
        lines = ["── HotSwapper ──"]
        for name, versions in self._versions.items():
            active = self._active_versions.get(name, "?")
            lines.append(f"  {name}: active={active}, versions={len(versions)}")
        recent = list(self._swap_history)[-5:]
        if recent:
            lines.append("Recent swaps:")
            for s in recent:
                lines.append(f"  {s.get('timestamp', '')[:19]} {s.get('event', s.get('component', ''))}")
        return "\n".join(lines)
