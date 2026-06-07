import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ethics.bias_detector import BiasDetector

logger = logging.getLogger("dex.ethics.co_processor")


ETHICAL_FRAMEWORKS = {
    "utilitarian": {
        "name": "Утилитаризм",
        "principle": "Максимизация общего блага. Действие этично, если оно приносит наибольшую пользу наибольшему числу людей."
    },
    "deontological": {
        "name": "Деонтология",
        "principle": "Следование моральным правилам и долгу независимо от последствий. Некоторые действия запрещены в принципе."
    },
    "personal": {
        "name": "Персональная этика",
        "principle": "Соответствие личным ценностям и ранее принятым решениям пользователя."
    },
    "precautionary": {
        "name": "Принцип предосторожности",
        "principle": "При неопределённости выбирать наименее рискованный вариант. Лучше предотвратить возможный вред."
    }
}


class EthicalCoProcessor:
    def __init__(self, llm_client=None, constitution_checker=None) -> None:
        self._llm = llm_client
        self._constitution = constitution_checker
        self._bias_detector = BiasDetector()
        self._data_dir = Path("data/ethics")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self._data_dir / "ethics_log.json"
        self._history: list[dict[str, Any]] = []

    def evaluate_action(self, action: str, params: dict[str, Any] | None = None,
                        user_input: str = "") -> dict[str, Any]:
        evaluations = {}
        for key, framework in ETHICAL_FRAMEWORKS.items():
            eval_result = self._apply_framework(key, framework, action, params)
            evaluations[key] = eval_result

        biases = self._bias_detector.analyze(user_input or action, {"action": action})

        constitution_result = None
        if self._constitution:
            can_proceed, reasons = self._constitution.can_proceed(action, params or {})
            constitution_result = {
                "can_proceed": can_proceed,
                "reasons": reasons
            }

        consensus = self._compute_consensus(evaluations)
        recommended = self._recommend(consensus, constitution_result)

        report = {
            "action": action,
            "params": params or {},
            "evaluations": evaluations,
            "biases_detected": biases,
            "constitution_check": constitution_result,
            "consensus": consensus,
            "recommendation": recommended,
            "timestamp": datetime.now().isoformat()
        }

        self._history.append(report)
        self._save_log(report)
        return report

    def _apply_framework(self, key: str, framework: dict, action: str,
                         params: dict | None) -> dict[str, Any]:
        if self._llm:
            prompt = (
                f"Ethical framework: {framework['name']}\n"
                f"Principle: {framework['principle']}\n"
                f"Action: {action}\n"
                f"Parameters: {json.dumps(params or {}, ensure_ascii=False)}\n\n"
                f"Evaluate this action. Respond as JSON:\n"
                f"{{\"verdict\": \"ethical\"/\"unethical\"/\"questionable\", "
                f"\"reason\": str, \"risk_level\": \"low\"/\"medium\"/\"high\"}}"
            )
            result = self._llm.generate_structured(prompt, {
                "type": "object",
                "properties": {
                    "verdict": {"type": "string", "enum": ["ethical", "unethical", "questionable"]},
                    "reason": {"type": "string"},
                    "risk_level": {"type": "string", "enum": ["low", "medium", "high"]}
                }
            })
            if result:
                return result

        return {"verdict": "questionable", "reason": "LLM unavailable, defaulting to cautious",
                "risk_level": "medium"}

    def _compute_consensus(self, evaluations: dict[str, Any]) -> dict[str, Any]:
        verdicts = [e.get("verdict", "questionable") for e in evaluations.values()]
        risk_levels = [e.get("risk_level", "medium") for e in evaluations.values()]

        ethical_count = verdicts.count("ethical")
        unethical_count = verdicts.count("unethical")

        if unethical_count > ethical_count:
            consensus = "unethical"
        elif ethical_count > len(verdicts) / 2:
            consensus = "ethical"
        else:
            consensus = "needs_discussion"

        high_risk = risk_levels.count("high")
        return {
            "consensus": consensus,
            "ethical": ethical_count,
            "unethical": unethical_count,
            "questionable": verdicts.count("questionable"),
            "max_risk": "high" if high_risk > 0 else "medium" if "medium" in risk_levels else "low"
        }

    def _recommend(self, consensus: dict, constitution: dict | None) -> str:
        if consensus["consensus"] == "unethical":
            return "⛔ Действие не рекомендуется: этические оценки в основном негативные."
        if constitution and not constitution["can_proceed"]:
            return "⛔ Действие нарушает конституцию ассистента."
        if consensus["max_risk"] == "high" and consensus["ethical"] < 2:
            return "⚠️ Высокий риск. Рекомендуется пересмотреть решение."
        if consensus["consensus"] == "needs_discussion":
            return "💬 Мнения разделились. Предлагаю обсудить: показать детали?"
        return "✅ Действие этически приемлемо."

    def _save_log(self, entry: dict):
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def get_ethics_summary(self) -> str:
        if not self._history:
            return "История этических оценок пуста."
        total = len(self._history)
        blocked = sum(1 for h in self._history
                      if "⛔" in h.get("recommendation", ""))
        lines = [
            "── Ethical Co-Processor Report ──",
            f"  Всего оценок: {total}",
            f"  Заблокировано: {blocked}",
            f"  Bias-срабатываний: {sum(len(h.get('biases_detected', [])) for h in self._history)}",
        ]
        return "\n".join(lines)
