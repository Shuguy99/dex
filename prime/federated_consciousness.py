import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.prime.federated")


class FederatedConsciousness:
    def __init__(self, llm_client=None, mesh_privacy=None) -> None:
        self._llm = llm_client
        self._mesh_privacy = mesh_privacy
        self._data_dir = Path("data/prime")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._pool_path = self._data_dir / "federated_pool.json"
        self._pool: list[dict[str, Any]] = []
        self._sessions: list[dict[str, Any]] = []
        self._isolation_guaranteed = True

    def propose_collaboration(self, topic: str, participants: list[str]) -> dict[str, Any]:
        session = {
            "id": f"fed_{int(time.time())}",
            "topic": topic,
            "participants": participants,
            "status": "proposed",
            "created": datetime.now().isoformat(),
            "contributions": [],
            "synthesis": None,
            "private_data_isolated": True
        }
        self._sessions.append(session)
        self._save_sessions()
        logger.info(f"Federated session proposed: {topic} with {len(participants)} participants")
        return session

    def contribute(self, session_id: str, participant: str,
                    data: dict[str, Any]) -> dict[str, Any]:
        session = next((s for s in self._sessions if s["id"] == session_id), None)
        if not session:
            return {"success": False, "reason": "Session not found"}

        # Filter private data
        filtered = {}
        for key, value in data.items():
            if self._is_private(key, value):
                logger.info(f"Filtered private data from {participant}: {key}")
                continue
            filtered[key] = value

        contribution = {
            "participant": participant,
            "data": filtered,
            "timestamp": datetime.now().isoformat()
        }
        session["contributions"].append(contribution)
        self._save_sessions()
        return {"success": True, "contribution_size": len(filtered)}

    def _is_private(self, key: str, value: Any) -> bool:
        private_indicators = ["password", "token", "secret", "key", "credential",
                               "private", "biometric", "health", "location",
                               "пароль", "токен", "секрет", "биометрия"]
        key_lower = key.lower()
        val_str = str(value).lower() if value else ""

        for indicator in private_indicators:
            if indicator in key_lower or indicator in val_str:
                return True
        return False

    def synthesize(self, session_id: str) -> dict[str, Any]:
        session = next((s for s in self._sessions if s["id"] == session_id), None)
        if not session:
            return {"success": False, "reason": "Session not found"}

        contributions = session.get("contributions", [])
        if len(contributions) < 2:
            return {"success": False, "reason": "Need at least 2 contributions"}

        if self._llm:
            prompt = (
                f"Topic: {session['topic']}\n"
                f"Contributions from {len(contributions)} participants:\n"
                f"{json.dumps(contributions, ensure_ascii=False)[:2000]}\n\n"
                f"Synthesize a collective intelligence output as JSON:\n"
                f"{{\"summary\": str, \"key_insights\": [str], "
                f"\"consensus_points\": [str], \"divergent_views\": [str]}}"
            )
            synthesis = self._llm.generate_structured(prompt, {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "key_insights": {"type": "array", "items": {"type": "string"}},
                    "consensus_points": {"type": "array", "items": {"type": "string"}},
                    "divergent_views": {"type": "array", "items": {"type": "string"}}
                }
            })
            if synthesis:
                session["synthesis"] = synthesis
                session["status"] = "completed"
                self._save_sessions()
                return {"success": True, "synthesis": synthesis}

        return {"success": False, "reason": "LLM unavailable"}

    def _save_sessions(self) -> None:
        with open(self._pool_path, "w", encoding="utf-8") as f:
            json.dump(self._sessions, f, ensure_ascii=False, indent=2)

    def get_federated_summary(self) -> str:
        if not self._sessions:
            return "Нет федеративных сессий."
        lines = ["── Federated Consciousness ──"]
        for s in self._sessions[-5:]:
            icon = {"completed": "✓", "proposed": "⏳", "active": "🔄"}
            lines.append(f"  {icon.get(s.get('status', ''), '?')} {s.get('topic', '')[:60]}")
            lines.append(f"     participants: {len(s.get('participants', []))}, "
                         f"contributions: {len(s.get('contributions', []))}")
        lines.append(f"\n  Privacy isolation: {'✓ ON' if self._isolation_guaranteed else '⚠️'}")
        return "\n".join(lines)
