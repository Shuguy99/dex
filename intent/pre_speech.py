import logging
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.intent.pre_speech")


class PreSpeechInterface:
    def __init__(self, camera=None) -> None:
        self._camera = camera
        self._data_dir = Path("data/intent")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._gaze_history: deque[dict] = deque(maxlen=50)
        self._micropattern_history: deque[dict] = deque(maxlen=50)
        self._active = False

    def start_monitoring(self):
        self._active = True
        logger.info("Pre-speech monitoring started")

    def stop_monitoring(self):
        self._active = False
        logger.info("Pre-speech monitoring stopped")

    def analyze_gaze(self, frame) -> dict[str, Any]:
        if not self._active:
            return {"focus": "unknown"}

        result = {
            "timestamp": time.time(),
            "focus": "screen",
            "duration": 0.0,
            "movement": "stable"
        }

        if self._camera and hasattr(self._camera, 'get_frame'):
            try:
                gaze_data = self._camera.detect_gaze(frame)
                if gaze_data:
                    result["focus"] = gaze_data.get("target", "screen")
                    result["movement"] = gaze_data.get("movement", "stable")
            except Exception:
                pass

        self._gaze_history.append(result)
        return result

    def detect_intention(self, typing_text: str = "",
                          hand_position: str = "") -> dict[str, Any]:
        signals = []
        confidence = 0.0

        if typing_text:
            if len(typing_text) > 20:
                signals.append("active_typing")
                confidence += 0.2
            if any(w in typing_text.lower() for w in ["delete", "remove", "удали"]):
                signals.append("destructive_intent")
                confidence += 0.4

        if hand_position == "mouse":
            signals.append("reaching_mouse")
            confidence += 0.1

        recent_gaze = list(self._gaze_history)[-10:]
        if recent_gaze:
            screen_focus = sum(1 for g in recent_gaze if g.get("focus") == "screen")
            if screen_focus < len(recent_gaze) * 0.3:
                signals.append("distracted")
                confidence -= 0.1

        return {
            "signals": signals,
            "confidence": min(1.0, confidence),
            "intention": "typing" if "active_typing" in signals else
                         "destructive" if "destructive_intent" in signals else
                         "unknown",
            "timestamp": datetime.now().isoformat()
        }

    def get_pre_speech_summary(self) -> str:
        lines = ["── Pre-Speech Interface ──"]
        lines.append(f"  Active: {self._active}")
        lines.append(f"  Gaze samples: {len(self._gaze_history)}")
        lines.append(f"  Micro-patterns: {len(self._micropattern_history)}")
        recent = list(self._gaze_history)[-5:]
        if recent:
            avg_focus = sum(1 for g in recent if g.get("focus") == "screen") / len(recent)
            lines.append(f"  Recent focus: {avg_focus:.0%}")
        return "\n".join(lines)
