import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.counsel.scenario")


class ScenarioTree:
    def __init__(self, llm_client=None, predictor=None) -> None:
        self._llm = llm_client
        self._predictor = predictor
        self._data_dir = Path("data/counsel")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._data_dir / "scenarios.json"
        self._scenarios: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if self._path.exists():
            try:
                with open(self._path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._scenarios[-100:], f, ensure_ascii=False, indent=2)

    def build_tree(self, situation: str, goals: list[str] | None = None) -> dict[str, Any]:
        if self._llm:
            goals_str = ", ".join(goals or ["general"])
            prompt = (
                f"Situation: '{situation}'\n"
                f"Long-term goals: {goals_str}\n\n"
                f"Build a decision tree as JSON:\n"
                f"{{\"root\": str, \"branches\": [{{\"decision\": str, "
                f"\"outcome\": str, \"probability\": float (0-1), "
                f"\"alignment_with_goals\": float (0-1), "
                f"\"risk_level\": \"low\"/\"medium\"/\"high\", "
                f"\"sub_branches\": [same structure...]}}]}}"
            )
            tree = self._llm.generate_structured(prompt, {
                "type": "object",
                "properties": {
                    "root": {"type": "string"},
                    "branches": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "decision": {"type": "string"},
                                "outcome": {"type": "string"},
                                "probability": {"type": "number"},
                                "alignment_with_goals": {"type": "number"},
                                "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                                "sub_branches": {"type": "array", "items": {"type": "object"}}
                            }
                        }
                    }
                }
            })
            if tree:
                tree["created"] = datetime.now().isoformat()
                tree["situation"] = situation
                tree["id"] = f"tree_{len(self._scenarios)}"
                self._scenarios.append(tree)
                self._save()
                return tree

        return {"root": situation, "branches": [], "reason": "LLM unavailable"}

    def find_best_path(self, tree_id: str) -> dict[str, Any]:
        tree = next((s for s in self._scenarios if s.get("id") == tree_id), None)
        if not tree:
            return {"found": False, "reason": "Tree not found"}

        def _score_branch(branch: dict) -> float:
            score = branch.get("probability", 0) * branch.get("alignment_with_goals", 0.5)
            risk_penalty = {"low": 0, "medium": -0.2, "high": -0.5}
            score += risk_penalty.get(branch.get("risk_level", "medium"), -0.2)
            return score

        all_decisions = []
        def _walk_branches(branches: list[dict], path: list[str]) -> None:
            for b in branches:
                current_path = path + [b.get("decision", "?")]
                score = _score_branch(b)
                all_decisions.append((score, current_path, b.get("outcome", "")))
                if b.get("sub_branches"):
                    _walk_branches(b["sub_branches"], current_path)

        _walk_branches(tree.get("branches", []), [])
        all_decisions.sort(key=lambda x: -x[0])

        if all_decisions:
            return {"found": True, "best_path": all_decisions[0][1],
                    "score": all_decisions[0][0],
                    "expected_outcome": all_decisions[0][2]}
        return {"found": True, "best_path": [], "score": 0, "expected_outcome": "No branches"}

    def get_scenario_summary(self) -> str:
        if not self._scenarios:
            return "Нет сохранённых сценариев."
        lines = ["── Scenario Trees ──"]
        for s in self._scenarios[-5:]:
            branch_count = len(s.get("branches", []))
            lines.append(f"  [{s.get('id', '?')}] {s.get('situation', '')[:70]}")
            lines.append(f"       branches: {branch_count}, created: {s.get('created', '')[:10]}")
        return "\n".join(lines)
