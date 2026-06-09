import json
import logging
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.psych.cognitive_load")


class CognitiveLoadAnalyzer:
    def __init__(self) -> None:
        self._data_dir = Path("data/psych")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._data_dir / "cognitive_load.json"
        self._typing_speed: deque[float] = deque(maxlen=100)
        self._command_complexity: deque[dict] = deque(maxlen=50)
        self._error_rate: deque[bool] = deque(maxlen=50)
        self._interaction_log: deque[dict] = deque(maxlen=200)
        self._load_state()

    def _load_state(self) -> None:
        if self._path.exists():
            try:
                with open(self._path, encoding="utf-8") as f:
                    data = json.load(f)
                    self._typing_speed.extend(data.get("typing_speed", []))
                    self._error_rate.extend(data.get("error_rate", []))
            except Exception:
                pass

    def _save_state(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump({
                    "typing_speed": list(self._typing_speed),
                    "error_rate": list(self._error_rate)
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def record_typing(self, text: str, elapsed_seconds: float) -> None:
        words = len(text.split())
        if words > 0 and elapsed_seconds > 0:
            speed = words / elapsed_seconds
            self._typing_speed.append(speed)

    def record_command(self, command: str, args: str = "", success: bool = True) -> None:
        complexity = self._estimate_complexity(command, args)
        self._command_complexity.append({
            "command": command,
            "complexity": complexity,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
        self._error_rate.append(not success)
        self._interaction_log.append({
            "type": "command",
            "complexity": complexity,
            "success": success,
            "time": time.time()
        })

    def _estimate_complexity(self, command: str, args: str = "") -> float:
        base = 1.0
        if args:
            base += len(args.split()) * 0.1
        if any(c in command for c in ["исследуй", "дебаты", "спланируй"]):
            base += 1.0
        if any(c in command for c in ["открой", "запусти"]):
            base -= 0.3
        return max(0.5, min(5.0, base))

    def get_load_score(self) -> dict[str, Any]:
        recent_commands = list(self._command_complexity)[-20:]
        if not recent_commands:
            return {"load": "low", "score": 0.0, "recommendation": "",
                    "commands_analyzed": 0, "avg_complexity": 0.0, "error_rate": 0.0}

        avg_complexity = sum(c["complexity"] for c in recent_commands) / len(recent_commands)
        error_rate = sum(1 for c in recent_commands if not c["success"]) / max(len(recent_commands), 1)

        recent_errors = list(self._error_rate)[-10:]
        recent_error_rate = sum(recent_errors) / max(len(recent_errors), 1)

        load_score = (avg_complexity / 5.0) * 0.5 + (error_rate * 0.3) + (recent_error_rate * 0.2)

        if load_score > 0.7:
            load_level = "high"
            recommendation = "Высокая когнитивная нагрузка. Рекомендуется отдых. "
            "Несрочные уведомления отложены."
        elif load_score > 0.4:
            load_level = "medium"
            recommendation = "Умеренная нагрузка. Сохраняйте текущий темп."
        else:
            load_level = "low"
            recommendation = "Низкая нагрузка. Хорошее время для сложных задач."

        return {
            "load": load_level,
            "score": round(load_score, 2),
            "avg_complexity": round(avg_complexity, 1),
            "error_rate": round(error_rate, 2),
            "recommendation": recommendation,
            "commands_analyzed": len(recent_commands)
        }

    def get_load_summary(self) -> str:
        score = self.get_load_score()
        icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        lines = ["── Cognitive Load ──"]
        lines.append(f"  {icons.get(score['load'], '⚪')} Load: {score['load'].upper()} "
                     f"({score['score']:.2f})")
        lines.append(f"  Commands analyzed: {score['commands_analyzed']}")
        lines.append(f"  Avg complexity: {score['avg_complexity']}")
        lines.append(f"  Error rate: {score['error_rate']:.0%}")
        lines.append(f"\n{score['recommendation']}")
        return "\n".join(lines)
