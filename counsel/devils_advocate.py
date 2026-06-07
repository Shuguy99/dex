import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.counsel.devils_advocate")


CRITICAL_DOMAINS = [
    "delete", "remove", "удали", "сотри", "удалить",
    "send", "отправ", "послать",
    "invest", "купи", "продай", "инвестируй",
    "commit", "push", "deploy", "merge",
    "format", "wipe", "очисти"
]


class DevilsAdvocate:
    def __init__(self, llm_client=None) -> None:
        self._llm = llm_client
        self._data_dir = Path("data/counsel")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self._data_dir / "devils_advocate_log.json"
        self._history: list[dict[str, Any]] = []

    def analyze(self, intention: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        is_critical = any(d in intention.lower() for d in CRITICAL_DOMAINS)

        counterarguments = self._generate_counterarguments(intention, is_critical)

        entry = {
            "intention": intention,
            "context": context or {},
            "counterarguments": counterarguments,
            "is_critical": is_critical,
            "timestamp": datetime.now().isoformat()
        }
        self._history.append(entry)
        self._save_log(entry)

        return entry

    def _generate_counterarguments(self, intention: str, critical: bool) -> list[dict[str, Any]]:

        if self._llm:
            prompt = (
                f"Intention: '{intention}'\n"
                f"Critical: {critical}\n\n"
                f"Act as a devil's advocate. Generate 3-5 strong counterarguments "
                f"against this intention. Be critical, thorough, and provocative.\n"
                f"Respond as JSON array:\n"
                f"[{{\"argument\": str, \"severity\": \"low\"/\"medium\"/\"high\", "
                f"\"dimension\": \"ethical\"/\"practical\"/\"strategic\"/\"emotional\"}}]"
            )
            result = self._llm.generate_structured(prompt, {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "argument": {"type": "string"},
                        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                        "dimension": {"type": "string", "enum": ["ethical", "practical", "strategic", "emotional"]}
                    }
                }
            })
            if result:
                return result

        default_args = [
            {"argument": "Рассмотрите альтернативы. Возможно, есть более эффективный путь.",
             "severity": "medium", "dimension": "practical"},
            {"argument": "Учитывайте долгосрочные последствия, а не только краткосрочную выгоду.",
             "severity": "medium", "dimension": "strategic"}
        ]
        if critical:
            default_args.insert(0, {
                "argument": "Это действие может иметь необратимые последствия.",
                "severity": "high", "dimension": "ethical"
            })
        return default_args

    def _save_log(self, entry: dict):
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def get_advocate_summary(self) -> str:
        if not self._history:
            return "Нет записей адвоката дьявола."
        total = len(self._history)
        critical = sum(1 for h in self._history if h.get("is_critical"))
        high_severity = sum(
            1 for h in self._history
            for c in h.get("counterarguments", [])
            if c.get("severity") == "high"
        )
        lines = ["── Devil's Advocate ──"]
        lines.append(f"  Analyzed intentions: {total}")
        lines.append(f"  Critical actions: {critical}")
        lines.append(f"  High-severity flags: {high_severity}")
        return "\n".join(lines)
