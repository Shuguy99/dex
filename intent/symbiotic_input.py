import logging
import time
from collections import deque
from pathlib import Path

logger = logging.getLogger("dex.intent.symbiotic")


COMPLETION_PATTERNS: dict[str, list[str]] = {
    "команда": ["открой", "запусти", "напомни", "найди", "спроси",
                 "исследуй", "дебаты"],
    "файл": ["открой файл", "сохрани", "удали", "переименуй"],
    "python": ["import", "from", "def ", "class ", "print("],
    "git": ["git add", "git commit", "git push", "git pull", "git status"],
}


class SymbioticInput:
    def __init__(self, llm_client=None) -> None:
        self._llm = llm_client
        self._prediction_history: deque[dict] = deque(maxlen=100)
        self._data_dir = Path("data/intent")
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def predict_completion(self, partial: str) -> list[str]:
        if not partial or len(partial) < 2:
            return []

        partial_lower = partial.lower().strip()
        predictions = []

        for trigger, completions in COMPLETION_PATTERNS.items():
            if trigger in partial_lower or any(
                p.startswith(partial_lower.split()[-1]) for p in completions
            ):
                matched = [c for c in completions if c.startswith(partial_lower.split()[-1])]
                predictions.extend(matched)

        if self._llm and not predictions:
            prompt = (
                f"Complete this input: '{partial}'\n"
                f"Suggest 2-3 most likely continuations as JSON array of strings."
            )
            llm_preds = self._llm.generate_structured(prompt, {
                "type": "array",
                "items": {"type": "string"}
            })
            if llm_preds:
                predictions.extend(llm_preds[:3])

        self._prediction_history.append({
            "partial": partial,
            "predictions": predictions,
            "timestamp": time.time()
        })

        return predictions[:3]

    def predict_next_object(self, current_command: str) -> list[str]:
        current_lower = current_command.lower().strip()
        context_map = {
            "открой": ["файл", "папку", "сайт", "браузер", "проект"],
            "запусти": ["приложение", "программу", "браузер", "редактор"],
            "напомни": ["встречу", "задачу", "дедлайн"],
            "найди": ["файл", "документ", "информацию", "письмо"],
            "исследуй": ["тему", "проект", "технологию", "вопрос"],
            "дебаты": ["тему", "идею", "решение", "проблему"],
        }
        for prefix, options in context_map.items():
            if current_lower.startswith(prefix):
                return options
        return []

    def get_symbiotic_summary(self) -> str:
        lines = ["── Symbiotic Input ──"]
        lines.append(f"  Predictions made: {len(self._prediction_history)}")
        if self._prediction_history:
            recent = list(self._prediction_history)[-5:]
            avg_hits = sum(1 for p in recent if p.get("predictions")) / max(len(recent), 1)
            lines.append(f"  Recent hit rate: {avg_hits:.0%}")
        return "\n".join(lines)
