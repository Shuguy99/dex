import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.counsel.counterfactual")


class CounterfactualAnalyzer:
    def __init__(self, llm_client=None) -> None:
        self._llm = llm_client
        self._data_dir = Path("data/counsel")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._forks_path = self._data_dir / "forks.json"
        self._forks: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if self._forks_path.exists():
            try:
                with open(self._forks_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save(self):
        with open(self._forks_path, "w", encoding="utf-8") as f:
            json.dump(self._forks[-200:], f, ensure_ascii=False, indent=2)

    def save_fork(self, decision: str, chosen: str, alternative: str,
                   context: dict[str, Any] | None = None):
        fork = {
            "id": f"fork_{len(self._forks)}",
            "decision": decision,
            "chosen_action": chosen,
            "alternative_action": alternative,
            "context": context or {},
            "created": datetime.now().isoformat(),
            "reviewed": False,
            "actual_outcome": None,
            "counterfactual_outcome": None
        }
        self._forks.append(fork)
        self._save()
        return fork["id"]

    def review_fork(self, fork_id: str, actual_outcome: str) -> dict[str, Any]:
        fork = next((f for f in self._forks if f.get("id") == fork_id), None)
        if not fork:
            return {"found": False}

        fork["actual_outcome"] = actual_outcome
        fork["reviewed"] = True

        if self._llm:
            prompt = (
                f"Decision: '{fork['decision']}'\n"
                f"Chosen: '{fork['chosen_action']}' → outcome: '{actual_outcome}'\n"
                f"Alternative: '{fork['alternative_action']}'\n\n"
                f"Analyze what would likely have happened if the alternative was chosen. "
                f"Respond as JSON:\n"
                f"{{\"counterfactual\": str, \"key_difference\": str, "
                f"\"lesson\": str, \"pattern\": str}}"
            )
            result = self._llm.generate_structured(prompt, {
                "type": "object",
                "properties": {
                    "counterfactual": {"type": "string"},
                    "key_difference": {"type": "string"},
                    "lesson": {"type": "string"},
                    "pattern": {"type": "string"}
                }
            })
            if result:
                fork["counterfactual_outcome"] = result
                self._save()
                return {"found": True, "analysis": result}

        return {"found": True, "analysis": {"counterfactual": "LLM unavailable"}}

    def get_pending_forks(self) -> list[dict[str, Any]]:
        week_ago = datetime.now() - timedelta(days=7)
        return [
            f for f in self._forks
            if not f.get("reviewed")
            and datetime.fromisoformat(f["created"]) < week_ago
        ]

    def get_counterfactual_summary(self) -> str:
        total = len(self._forks)
        reviewed = sum(1 for f in self._forks if f.get("reviewed"))
        pending = sum(1 for f in self._forks if not f.get("reviewed"))
        lines = ["── Counterfactual Analysis ──"]
        lines.append(f"  Total forks: {total}")
        lines.append(f"  Reviewed: {reviewed}")
        lines.append(f"  Pending: {pending}")
        if self._forks:
            patterns = [f.get("counterfactual_outcome", {}).get("pattern", "")
                        for f in self._forks if f.get("counterfactual_outcome")]
            if patterns:
                from collections import Counter
                common = Counter(patterns).most_common(3)
                lines.append("  Common patterns:")
                for p, c in common:
                    lines.append(f"    • {p} ({c}x)")
        return "\n".join(lines)
