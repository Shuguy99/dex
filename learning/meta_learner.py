import json
import logging
import random
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.meta_learner")


class MetaLearner:
    def __init__(self, llm_client=None, sandbox=None, rule_engine=None,
                 lora_trainer=None, rag_engine=None) -> None:
        self._llm = llm_client
        self._sandbox = sandbox
        self._rule_engine = rule_engine
        self._lora_trainer = lora_trainer
        self._rag = rag_engine
        self._data_dir = Path("data/meta_learning")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._data_dir / "meta_knowledge.json"
        self._error_log: deque[dict] = deque(maxlen=500)
        self._strategy_history: deque[dict] = deque(maxlen=200)
        self._synthetic_scenarios: list[dict] = []
        self._meta_knowledge: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if self._path.exists():
            try:
                with open(self._path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "strategy_scores": {}, "error_classes": {},
            "synthetic_scenarios": [], "skill_progress": {}
        }

    def _save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._meta_knowledge, f, ensure_ascii=False, indent=2)

    def record_error(self, error_type: str, context: str, severity: str = "medium") -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "context": context[:200],
            "severity": severity
        }
        self._error_log.append(entry)
        cls = self._meta_knowledge["error_classes"]
        cls[error_type] = cls.get(error_type, 0) + 1
        self._save()

    def select_strategy(self, error_type: str, context: str = "") -> dict[str, Any]:
        scores = self._meta_knowledge["strategy_scores"]
        error_freq = self._meta_knowledge["error_classes"].get(error_type, 0)

        candidates = []
        if self._rule_engine and error_freq > 2:
            candidates.append(("rule", scores.get("rule", 0.5)))
        if self._lora_trainer and error_freq > 5:
            candidates.append(("lora", scores.get("lora", 0.5)))
        if self._rag and error_freq > 1:
            candidates.append(("rag", scores.get("rag", 0.5)))
        if self._llm and not candidates:
            candidates.append(("llm_prompt", scores.get("llm_prompt", 0.3)))

        if not candidates:
            return {"strategy": "none", "reason": "No viable strategies"}

        best = max(candidates, key=lambda x: x[1])
        strategy = best[0]

        if self._llm:
            prompt = (
                f"Error type: {error_type}\nContext: {context}\n"
                f"Error frequency: {error_freq}\n"
                f"Available strategies: rule(scored {scores.get('rule', 0.5)}), "
                f"lora({scores.get('lora', 0.5)}), rag({scores.get('rag', 0.5)})\n"
                f"Recommend the best strategy as one word. Answer only: rule/lora/rag"
            )
            llm_choice = self._llm.generate(prompt, temperature=0.1)
            if llm_choice and llm_choice.strip().lower() in ("rule", "lora", "rag"):
                strategy = llm_choice.strip().lower()

        return {
            "strategy": strategy,
            "reason": f"Best for '{error_type}' (freq={error_freq}, score={scores.get(strategy, 0.5):.2f})"
        }

    def record_strategy_outcome(self, strategy: str, success: bool, improvement: float = 0.0) -> None:
        scores = self._meta_knowledge["strategy_scores"]
        current = scores.get(strategy, 0.5)
        delta = 0.05 if success else -0.05
        scores[strategy] = max(0.0, min(1.0, current + delta + improvement * 0.1))
        self._save()

    def simulate_skill_acquisition(self, task_desc: str) -> dict[str, Any]:
        if not self._sandbox:
            return {"success": False, "reason": "No sandbox available"}

        synthetic_examples = self._generate_training_examples(task_desc)
        if not synthetic_examples:
            return {"success": False, "reason": "Could not synthesize examples"}

        trial_log = []
        for example in synthetic_examples[:3]:
            try:
                code = f"def test_skill():\n    {example.get('solution', 'pass')}"
                exec_result = self._sandbox.run_code(code, timeout=10)
                trial_log.append({
                    "example": example["prompt"][:100],
                    "passed": not exec_result.get("error"),
                    "output": str(exec_result.get("output", ""))[:200]
                })
            except Exception as e:
                trial_log.append({"example": example["prompt"][:100], "passed": False, "error": str(e)})

        passed = sum(1 for t in trial_log if t["passed"])
        report = {
            "task": task_desc[:200],
            "examples_generated": len(synthetic_examples),
            "trials_run": len(trial_log),
            "pass_rate": passed / max(len(trial_log), 1),
            "trial_log": trial_log,
            "success": passed >= len(trial_log) * 0.5
        }

        self._meta_knowledge["skill_progress"][task_desc[:100]] = {
            "pass_rate": report["pass_rate"],
            "timestamp": datetime.now().isoformat()
        }
        self._save()
        return report

    def _generate_training_examples(self, task_desc: str) -> list[dict[str, str]]:
        if self._llm:
            prompt = (
                f"Generate 3 training examples for the task: '{task_desc}'\n"
                f"For each, provide a brief prompt and a Python solution snippet.\n"
                f"Format as JSON array: [{{\"prompt\": str, \"solution\": str}}]"
            )
            result = self._llm.generate_structured(prompt, {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "solution": {"type": "string"}
                    }
                }
            })
            if result:
                return result

        return [
            {"prompt": f"Basic: {task_desc}", "solution": "print('ok')"},
            {"prompt": f"Intermediate: {task_desc}", "solution": "print('ok')"},
            {"prompt": f"Advanced: {task_desc}", "solution": "print('ok')"},
        ]

    def generate_synthetic_scenarios(self, base_topics: list[str]) -> list[dict[str, Any]]:
        if not self._llm:
            return []

        seen = set(s["topic"] for s in self._meta_knowledge["synthetic_scenarios"])
        new_topics = [t for t in base_topics if t not in seen]

        scenarios = []
        for topic in new_topics[:5]:
            difficulty = random.choice(["easy", "medium", "hard"])
            prompt = (
                f"Create a challenging synthetic training scenario on '{topic}' "
                f"(difficulty: {difficulty}). Include: a task description, "
                f"expected output format, and 2 edge cases.\n"
                f"Format as JSON: {{\"topic\": str, \"difficulty\": str, "
                f"\"task\": str, \"expected_output\": str, \"edge_cases\": [str]}}"
            )
            result = self._llm.generate_structured(prompt, {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "difficulty": {"type": "string"},
                    "task": {"type": "string"},
                    "expected_output": {"type": "string"},
                    "edge_cases": {"type": "array", "items": {"type": "string"}}
                }
            })
            if result:
                result["created"] = datetime.now().isoformat()
                scenarios.append(result)
                self._meta_knowledge["synthetic_scenarios"].append(result)

        self._save()
        return scenarios

    def get_meta_report(self) -> str:
        scores = self._meta_knowledge["strategy_scores"]
        errors = self._meta_knowledge["error_classes"]
        skills = self._meta_knowledge["skill_progress"]
        lines = ["── Meta-Learning Report ──"]
        lines.append("\nStrategy scores:")
        for s, score in sorted(scores.items(), key=lambda x: -x[1]):
            bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
            lines.append(f"  {bar} {s}: {score:.2f}")
        lines.append("\nTop error classes:")
        for e, cnt in sorted(errors.items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  {e}: {cnt}x")
        lines.append(f"\nSkills simulated: {len(skills)}")
        if skills:
            best = max(skills.items(), key=lambda x: x[1]["pass_rate"])
            lines.append(f"  Best: {best[0][:50]} ({best[1]['pass_rate']:.0%})")
        return "\n".join(lines)
