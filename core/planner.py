import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("dex.planner")


class Step:
    def __init__(self, action: str, params: dict[str, Any] | None = None,
                  description: str = "", depends_on: list[int] | None = None) -> None:
        self.action = action
        self.params = params or {}
        self.description = description
        self.depends_on = depends_on or []
        self.status = "pending"
        self.result: Any = None
        self.error: str | None = None
        self.duration_ms: float = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "params": self.params,
            "description": self.description,
            "depends_on": self.depends_on,
            "status": self.status,
            "result": str(self.result)[:200] if self.result else None,
            "error": self.error,
            "duration_ms": self.duration_ms
        }


class Plan:
    def __init__(self, goal: str, steps: list[Step]) -> None:
        self.goal = goal
        self.steps = steps
        self.created_at = time.time()
        self.completed_at: float | None = None
        self.status = "created"

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }


class TaskPlanner:
    def __init__(self, llm_client=None, executor: Callable[[str, dict], str] | None = None) -> None:
        self._llm = llm_client
        self._executor = executor
        self._plans: list[Plan] = []

    def create_plan(self, goal: str) -> Plan | None:
        if self._llm and self._llm.ready:
            return self._plan_with_llm(goal)
        return self._plan_with_rules(goal)

    def _plan_with_llm(self, goal: str) -> Plan | None:
        schema = {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string"},
                            "params": {"type": "object"},
                            "description": {"type": "string"},
                            "depends_on": {
                                "type": "array",
                                "items": {"type": "integer"}
                            }
                        }
                    }
                }
            }
        }
        prompt = (
            f"Break down the following goal into a sequence of executable steps:\n"
            f"Goal: {goal}\n\n"
            f"Available actions: open_file, launch_app, create_folder, write_file, "
            f"run_command, search_memory, send_notification, execute_script, "
            f"install_package, clone_repo\n\n"
            f"Each step must have an action, optional params, description, "
            f"and depends_on (list of step indices it depends on, 0-based)."
        )
        result = self._llm.generate_structured(prompt, schema, model="qwen2.5:14b")
        if result and "steps" in result:
            steps = [Step(**s) for s in result["steps"]]
            plan = Plan(goal, steps)
            self._plans.append(plan)
            logger.info(f"LLM plan created: {goal} ({len(steps)} steps)")
            return plan
        return None

    def _plan_with_rules(self, goal: str) -> Plan:
        steps = []
        lower = goal.lower()

        if any(w in lower for w in ["веб", "web", "сайт", "проект", "project"]):
            steps = [
                Step("create_folder", {"name": "project"}, "Создать папку проекта"),
                Step("launch_app", {"name": "Code.exe"}, "Открыть VS Code", depends_on=[0]),
                Step("run_command", {"cmd": "python -m venv venv"},
                     "Создать виртуальное окружение", depends_on=[0]),
                Step("run_command", {"cmd": "pip install flask"},
                     "Установить flask", depends_on=[2]),
            ]
        elif any(w in lower for w in ["документ", "документация", "doc"]):
            steps = [
                Step("create_folder", {"name": "docs"}, "Создать папку docs"),
                Step("write_file", {"name": "README.md", "content": "# Project"},
                     "Создать README", depends_on=[0]),
            ]
        else:
            steps = [
                Step("search_memory", {"query": goal}, "Поиск в памяти"),
                Step("send_notification", {"message": f"Processing: {goal}"},
                     "Уведомить пользователя", depends_on=[0]),
            ]

        plan = Plan(goal, steps)
        self._plans.append(plan)
        logger.info(f"Rule-based plan created: {goal} ({len(steps)} steps)")
        return plan

    def execute_plan(self, plan: Plan, executor: Callable[[str, dict], str] | None = None) -> Plan:
        exec_fn = executor or self._executor
        if not exec_fn:
            logger.error("No executor available")
            plan.status = "failed"
            return plan

        plan.status = "running"
        logger.info(f"Executing plan: {plan.goal}")

        for i, step in enumerate(plan.steps):
            if step.status == "completed":
                continue

            deps_ok = all(
                plan.steps[d].status == "completed" for d in step.depends_on
            )
            if not deps_ok:
                step.status = "blocked"
                step.error = "Dependencies not met"
                continue

            step.status = "running"
            ts = time.time()
            try:
                result = exec_fn(step.action, step.params)
                step.result = result
                step.status = "completed"
                logger.info(f"Step {i} completed: {step.description}")
            except Exception as e:
                step.error = str(e)
                step.status = "failed"
                logger.error(f"Step {i} failed: {e}")
            step.duration_ms = (time.time() - ts) * 1000

        plan.completed_at = time.time()
        plan.status = "completed" if all(
            s.status == "completed" for s in plan.steps
        ) else "partial"
        return plan

    def get_plan(self, idx: int = -1) -> Plan | None:
        if self._plans:
            return self._plans[idx]
        return None

    def summarize_plan(self, plan: Plan) -> str:
        lines = [f"План: {plan.goal}", f"Статус: {plan.status}", ""]
        for i, step in enumerate(plan.steps):
            icon = {"completed": "✓", "running": "→", "failed": "✗",
                    "blocked": "⊘", "pending": "○"}.get(step.status, "?")
            dep = f" [after {step.depends_on}]" if step.depends_on else ""
            lines.append(f"  {icon} Шаг {i}: {step.description}{dep}")
            if step.error:
                lines.append(f"     Error: {step.error}")
        return "\n".join(lines)
