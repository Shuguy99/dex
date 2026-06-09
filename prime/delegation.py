import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.prime.delegation")


class DelegationEngine:
    def __init__(self, mesh_swarm=None) -> None:
        self._mesh = mesh_swarm
        self._data_dir = Path("data/prime")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._deployments_path = self._data_dir / "delegations.json"
        self._delegations: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if self._deployments_path.exists():
            try:
                with open(self._deployments_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save(self) -> None:
        with open(self._deployments_path, "w", encoding="utf-8") as f:
            json.dump(self._delegations[-50:], f, ensure_ascii=False, indent=2)

    def deploy_sub_personality(self, name: str, target_device: str,
                                 capabilities: list[str] | None = None,
                                 instructions: str = "") -> dict[str, Any]:
        deployment = {
            "id": f"dep_{int(time.time())}",
            "name": name,
            "target_device": target_device,
            "capabilities": capabilities or [],
            "instructions": instructions[:500],
            "status": "deployed",
            "deployed_at": datetime.now().isoformat(),
            "experience_log": [],
            "returned": False
        }

        if self._mesh:
            result = self._mesh.register_peer(
                f"sub_{name}", target_device, 5556, capabilities
            )
            deployment["mesh_result"] = str(result)

        self._delegations.append(deployment)
        self._save()
        logger.info(f"Sub-personality '{name}' deployed to {target_device}")
        return deployment

    def log_experience(self, dep_id: str, entry: str) -> None:
        dep = next((d for d in self._delegations if d["id"] == dep_id), None)
        if not dep:
            return False
        dep["experience_log"].append({
            "timestamp": datetime.now().isoformat(),
            "entry": entry[:300]
        })
        self._save()
        return True

    def recall_sub_personality(self, dep_id: str) -> dict[str, Any]:
        dep = next((d for d in self._delegations if d["id"] == dep_id), None)
        if not dep:
            return {"success": False, "reason": "Delegation not found"}

        dep["status"] = "returned"
        dep["returned_at"] = datetime.now().isoformat()
        dep["returned"] = True

        summary = {
            "name": dep["name"],
            "duration": f"{(datetime.fromisoformat(dep['returned_at']) - datetime.fromisoformat(dep['deployed_at'])).days} days",
            "experiences": len(dep.get("experience_log", [])),
            "log": dep.get("experience_log", [])
        }
        dep["return_summary"] = summary
        self._save()
        logger.info(f"Sub-personality '{dep['name']}' recalled")
        return {"success": True, "summary": summary}

    def reintegrate(self, dep_id: str) -> dict[str, Any]:
        dep = next((d for d in self._delegations if d["id"] == dep_id), None)
        if not dep:
            return {"success": False, "reason": "Not found"}
        if dep.get("status") != "returned":
            return {"success": False, "reason": "Sub-personality not yet returned"}

        experiences = dep.get("experience_log", [])
        dep["reintegrated"] = True
        self._save()
        return {
            "success": True,
            "name": dep["name"],
            "experiences_absorbed": len(experiences),
            "insights": [e["entry"] for e in experiences[-5:]]
        }

    def get_delegation_summary(self) -> str:
        if not self._delegations:
            return "Нет активных делегаций."
        lines = ["── Delegation Engine ──"]
        for d in self._delegations[-5:]:
            icon = "✓" if d.get("returned") else "🚀"
            lines.append(f"  {icon} {d.get('name', '?')} → {d.get('target_device', '?')}")
            lines.append(f"     status: {d.get('status', '?')}, "
                         f"experiences: {len(d.get('experience_log', []))}")
        return "\n".join(lines)
