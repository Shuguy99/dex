import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.ethics.bias")


BIAS_PATTERNS = {
    "urgency": {
        "keywords": ["срочно", "быстро", "немедленно", "скорее", "сейчас же",
                      "поторопись", "некогда"],
        "bias": "time_pressure",
        "message": "Похоже, вы торопитесь. Возможно, стоит сделать паузу и перепроверить."
    },
    "fatigue": {
        "keywords": ["устал", "спать хочу", "глаза слипаются", "нет сил",
                      "вымотан", "разбит"],
        "bias": "fatigue",
        "message": "Вы выглядите уставшим. Важные решения лучше отложить до отдыха."
    },
    "anger": {
        "keywords": ["бесит", "ненавижу", "достало", "зол", "разозлён",
                      "ярость", "взбешён"],
        "bias": "anger",
        "message": "Заметно раздражение. Предлагаю сделать паузу, чтобы избежать импульсивных решений."
    },
    "overconfidence": {
        "keywords": ["всегда", "никогда", "точно", "наверняка", "абсолютно",
                      "очевидно же"],
        "bias": "overconfidence",
        "message": "Кажется, вы очень уверены. Возможно, стоит рассмотреть альтернативы."
    },
    "sunk_cost": {
        "keywords": ["уже потратил", "столько времени", "нельзя же бросить",
                      "жаль бросать", "столько усилий"],
        "bias": "sunk_cost",
        "message": "Похоже на ловушку невозвратных затрат. Оцените решение без оглядки на прошлые вложения."
    }
}


class BiasDetector:
    def __init__(self) -> None:
        self._data_dir = Path("data/ethics")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._history_path = self._data_dir / "bias_history.json"
        self._history: list[dict[str, Any]] = []
        self._load_history()

    def _load_history(self):
        if self._history_path.exists():
            try:
                import json
                with open(self._history_path, encoding="utf-8") as f:
                    self._history = json.load(f)
            except Exception:
                pass

    def _save_history(self):
        import json
        with open(self._history_path, "w", encoding="utf-8") as f:
            json.dump(self._history[-200:], f, ensure_ascii=False, indent=2)

    def analyze(self, text: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        detected = []
        text_lower = text.lower()

        for name, pattern in BIAS_PATTERNS.items():
            found = [kw for kw in pattern["keywords"] if kw in text_lower]
            if found:
                entry = {
                    "type": name,
                    "bias": pattern["bias"],
                    "triggers": found,
                    "message": pattern["message"],
                    "timestamp": datetime.now().isoformat(),
                    "context": context or {}
                }
                detected.append(entry)
                self._history.append(entry)

        if detected:
            self._save_history()

        return detected

    def check_command(self, command: str, args: str = "") -> list[dict[str, Any]]:
        full = f"{command} {args}"
        biases = self.analyze(full)

        recent = [
            h for h in self._history
            if datetime.fromisoformat(h["timestamp"]) > datetime.now() - timedelta(minutes=5)
        ]
        if len(recent) >= 3 and len(set(h["type"] for h in recent)) >= 2:
            fatigue_types = set(h["type"] for h in recent)
            if len(fatigue_types) >= 2:
                biases.append({
                    "type": "compound_stress",
                    "bias": "cognitive_overload",
                    "triggers": [f"Multiple bias types detected: {', '.join(fatigue_types)}"],
                    "message": "Обнаружено несколько когнитивных искажений за короткое время. "
                               "Рекомендуется отдых.",
                    "timestamp": datetime.now().isoformat(),
                    "context": {}
                })

        return biases

    def get_bias_summary(self) -> str:
        if not self._history:
            return "История когнитивных искажений пуста."

        bias_counts: dict[str, int] = {}
        for h in self._history:
            bias_counts[h["bias"]] = bias_counts.get(h["bias"], 0) + 1

        lines = ["── Bias Detection Summary ──"]
        for bias, count in sorted(bias_counts.items(), key=lambda x: -x[1]):
            bar = "█" * min(count, 10)
            lines.append(f"  {bar} {bias}: {count}x")
        return "\n".join(lines)
