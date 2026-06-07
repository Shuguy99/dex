import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.temporal.life_planner")


GOAL_CATEGORIES = ["health", "learning", "career", "finance", "relationships", "creative"]


class LifePlanner:
    def __init__(self, llm_client=None) -> None:
        self._llm = llm_client
        self._data_dir = Path("data/temporal")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._goals_path = self._data_dir / "life_goals.json"
        self._goals: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if self._goals_path.exists():
            try:
                with open(self._goals_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save(self):
        with open(self._goals_path, "w", encoding="utf-8") as f:
            json.dump(self._goals, f, ensure_ascii=False, indent=2)

    def add_goal(self, description: str, category: str = "learning",
                  deadline: str | None = None, priority: str = "medium"):
        goal = {
            "id": f"goal_{len(self._goals)}",
            "description": description,
            "category": category if category in GOAL_CATEGORIES else "learning",
            "deadline": deadline or (datetime.now() + timedelta(days=90)).isoformat(),
            "priority": priority,
            "status": "active",
            "created": datetime.now().isoformat(),
            "steps": [],
            "progress": 0.0,
            "last_reminder": None,
            "check_ins": 0
        }
        self._goals.append(goal)
        self._save()
        return goal["id"]

    def add_step(self, goal_id: str, step_desc: str):
        goal = next((g for g in self._goals if g["id"] == goal_id), None)
        if not goal:
            return False
        goal["steps"].append({
            "description": step_desc,
            "completed": False,
            "created": datetime.now().isoformat()
        })
        self._save()
        return True

    def _update_progress(self, goal: dict):
        steps = goal.get("steps", [])
        if steps:
            completed = sum(1 for s in steps if s.get("completed"))
            goal["progress"] = completed / len(steps)
        self._save()

    def complete_step(self, goal_id: str, step_index: int):
        goal = next((g for g in self._goals if g["id"] == goal_id), None)
        if not goal or step_index >= len(goal.get("steps", [])):
            return False
        goal["steps"][step_index]["completed"] = True
        self._update_progress(goal)
        return True

    def get_overdue_goals(self) -> list[dict[str, Any]]:
        now = datetime.now()
        return [
            g for g in self._goals
            if g.get("status") == "active"
            and datetime.fromisoformat(g["deadline"]) < now
        ]

    def get_suggestions(self, user_context: str = "") -> list[str]:
        active = [g for g in self._goals if g.get("status") == "active"]
        suggestions = []

        for goal in active:
            if goal["progress"] < 0.3 and goal.get("check_ins", 0) < 3:
                suggestions.append(
                    f"Goal '{goal['description'][:40]}' needs attention. "
                    f"Try breaking it into smaller steps."
                )

        overdue = self.get_overdue_goals()
        for g in overdue[:2]:
            suggestions.append(
                f"Deadline passed for: {g['description'][:50]}. "
                f"Consider reprioritizing."
            )

        return suggestions[:5]

    def check_in(self, daily_log: str = ""):
        for goal in self._goals:
            if goal.get("status") == "active":
                goal["check_ins"] = goal.get("check_ins", 0) + 1
                goal["last_reminder"] = datetime.now().isoformat()
        self._save()

    def get_life_summary(self) -> str:
        if not self._goals:
            return "Нет жизненных целей. Добавьте через команду: цель <описание>"
        active = [g for g in self._goals if g.get("status") == "active"]
        completed = [g for g in self._goals if g.get("status") == "completed"]
        lines = ["── Life Planner ──"]
        lines.append(f"  Active: {len(active)}, Completed: {len(completed)}")
        lines.append("")
        for g in active:
            bar = "█" * int(g["progress"] * 10) + "░" * (10 - int(g["progress"] * 10))
            lines.append(f"  {bar} {g['description'][:50]}")
            lines.append(f"     [{g['category']}] deadline: {g['deadline'][:10]}")
        suggestions = self.get_suggestions()
        if suggestions:
            lines.append("\n  Suggestions:")
            for s in suggestions[:3]:
                lines.append(f"    ▸ {s}")
        return "\n".join(lines)
