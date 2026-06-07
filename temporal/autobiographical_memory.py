import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.temporal.autobio")

EMOTION_KEYWORDS = {
    "positive": ["рад", "счасть", "отлично", "здорово", "класс", "ура",
                  "круто", "успех", "победа", "+"],
    "negative": ["груст", "плохо", "ужас", "провал", "ошибк", "жаль",
                  "неудач", "проблем", "-"],
    "surprise": ["ого", "вау", "неожидан", "вот это да", "невероят"],
    "gratitude": ["спасибо", "благодар", "ценю", "признателен"]
}


class AutobiographicalMemory:
    def __init__(self, llm_client=None, vector_memory=None) -> None:
        self._llm = llm_client
        self._vector_memory = vector_memory
        self._data_dir = Path("data/temporal")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._mem_path = self._data_dir / "autobiography.json"
        self._memories: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if self._mem_path.exists():
            try:
                with open(self._mem_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save(self):
        with open(self._mem_path, "w", encoding="utf-8") as f:
            json.dump(self._memories[-500:], f, ensure_ascii=False, indent=2)

    def _detect_emotion(self, text: str) -> dict[str, Any]:
        text_lower = text.lower()
        scores = defaultdict(int)
        for emotion, words in EMOTION_KEYWORDS.items():
            for word in words:
                if word in text_lower:
                    scores[emotion] += 1
        primary = max(scores, key=scores.get) if scores else "neutral"
        return {"primary": primary, "scores": dict(scores), "intensity": sum(scores.values())}

    def record_interaction(self, text: str, response: str, command: str = ""):
        emotion = self._detect_emotion(text)
        memory = {
            "id": f"mem_{len(self._memories)}",
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "user_input": text[:200],
            "dex_response": response[:200],
            "command": command[:50],
            "emotion": emotion,
            "significance": self._calculate_significance(emotion, text)
        }
        self._memories.append(memory)
        self._save()

        if emotion["primary"] in ("positive", "negative") and emotion["intensity"] > 2:
            if self._vector_memory:
                narrative = f"[{emotion['primary']}] {text[:150]} → {response[:150]}"
                self._vector_memory.add(narrative, {"type": "autobiographical", "emotion": emotion["primary"]})

    def _calculate_significance(self, emotion: dict, text: str) -> float:
        base = 0.3
        base += emotion["intensity"] * 0.1
        if emotion["primary"] in ("positive", "negative"):
            base += 0.2
        significant_words = ["project", "работа", "запуск", "релиз", "встреч",
                              "собеседова", "решение", "важный"]
        text_lower = text.lower()
        for w in significant_words:
            if w in text_lower:
                base += 0.1
        return min(1.0, base)

    def recall(self, query: str) -> list[dict[str, Any]]:
        query_lower = query.lower()
        results = []

        for mem in self._memories:
            score = 0
            if query_lower in mem.get("user_input", "").lower():
                score += 2
            if query_lower in mem.get("dex_response", "").lower():
                score += 1
            if query_lower in mem.get("emotion", {}).get("primary", ""):
                score += 1.5
            if any(em in query_lower for em in ["год", "месяц", "недел"]):
                mem_date = datetime.fromisoformat(mem["timestamp"])
                if "year" in query_lower:
                    try:
                        target = int(query_lower.split("year")[-1].strip())
                        if mem_date.year == target:
                            score += 3
                    except ValueError:
                        pass
            if score > 0:
                results.append({**mem, "relevance": score})

        results.sort(key=lambda x: -x.get("relevance", 0) * x.get("significance", 0.5))
        return results[:5]

    def get_timeline(self, days: int = 30) -> list[dict[str, Any]]:
        cutoff = datetime.now() - timedelta(days=days)
        recent = [
            m for m in self._memories
            if datetime.fromisoformat(m["timestamp"]) > cutoff
        ]
        return sorted(recent, key=lambda x: x["timestamp"])

    def get_autobio_summary(self) -> str:
        total = len(self._memories)
        if not total:
            return "Нет автобиографических воспоминаний."
        emotions = defaultdict(int)
        for m in self._memories:
            emotions[m.get("emotion", {}).get("primary", "neutral")] += 1
        recent = self.get_timeline(7)
        lines = ["── Autobiographical Memory ──"]
        lines.append(f"  Total memories: {total}")
        lines.append(f"  Last 7 days: {len(recent)}")
        lines.append("  Emotional distribution:")
        for em, count in sorted(emotions.items(), key=lambda x: -x[1]):
            bar = "█" * min(count, 10)
            lines.append(f"    {bar} {em}: {count}")
        return "\n".join(lines)
