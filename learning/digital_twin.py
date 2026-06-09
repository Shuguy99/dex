import contextlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.learning.digital_twin")


class DigitalTwin:
    def __init__(self, llm_client=None, vector_memory=None) -> None:
        self._llm = llm_client
        self._vector_memory = vector_memory
        self._data_dir = Path("data/twin")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._style_path = self._data_dir / "style_profile.json"
        self._messages_path = self._data_dir / "messages.jsonl"
        self._profile: dict[str, Any] = self._load_profile()

    def _load_profile(self) -> dict[str, Any]:
        if self._style_path.exists():
            try:
                return json.loads(self._style_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "vocabulary": [],
            "common_phrases": [],
            "formality_level": 0.5,
            "decision_pattern": "analytical",
            "communication_style": "direct",
            "learned_preferences": [],
            "thinking_patterns": []
        }

    def _save_profile(self) -> None:
        self._style_path.write_text(
            json.dumps(self._profile, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def learn_from_message(self, text: str, context: str = "") -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "context": context
        }
        with open(self._messages_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        words = re.findall(r'\b\w+\b', text.lower())
        uncommon = [w for w in words if len(w) > 6 and w not in self._profile["vocabulary"]]
        if uncommon:
            self._profile["vocabulary"].extend(uncommon[:3])
            self._profile["vocabulary"] = list(set(self._profile["vocabulary"]))[:100]

        if context and context not in self._profile["learned_preferences"]:
            self._profile["learned_preferences"].append(context)
            self._profile["learned_preferences"] = self._profile["learned_preferences"][-50:]

        if self._llm and self._llm.ready and len(self._profile["vocabulary"]) % 10 == 0:
            self._update_style_profile()

        self._save_profile()

    def _update_style_profile(self) -> None:
        recent = self._get_recent_messages(20)
        if not recent or not self._llm:
            return

        texts = "\n".join([m["text"] for m in recent])
        prompt = (
            f"Analyze this user's communication style from their messages. "
            f"Respond as JSON:\n"
            f"{{\n"
            f"  \"formality_level\": 0.0-1.0,\n"
            f"  \"communication_style\": \"direct\"|\"detailed\"|\"humorous\"|\"technical\",\n"
            f"  \"decision_pattern\": \"analytical\"|\"intuitive\"|\"decisive\"|\"cautious\",\n"
            f"  \"thinking_patterns\": [\"pattern1\", \"pattern2\"]\n"
            f"}}\n\n"
            f"Messages:\n{texts}"
        )
        result = self._llm.generate_structured(prompt, {
            "type": "object",
            "properties": {
                "formality_level": {"type": "number"},
                "communication_style": {"type": "string"},
                "decision_pattern": {"type": "string"},
                "thinking_patterns": {"type": "array", "items": {"type": "string"}}
            }
        })
        if result:
            for key, value in result.items():
                if value is not None:
                    self._profile[key] = value

    def _get_recent_messages(self, n: int = 10) -> list[dict[str, Any]]:
        if not self._messages_path.exists():
            return []
        messages = []
        with open(self._messages_path, encoding="utf-8") as f:
            for line in f:
                with contextlib.suppress(json.JSONDecodeError, ValueError):
                    messages.append(json.loads(line.strip()))
        return messages[-n:]

    def generate_reply(self, incoming: str, draft: bool = True) -> str:
        if not self._llm or not self._llm.ready:
            return incoming

        style = self._profile
        prompt = (
            f"Generate a reply in the style of the user based on their communication profile.\n\n"
            f"User's communication style: {style.get('communication_style', 'direct')}\n"
            f"Formality level: {style.get('formality_level', 0.5)}\n"
            f"Decision pattern: {style.get('decision_pattern', 'analytical')}\n"
            f"Typical vocabulary: {', '.join(style.get('vocabulary', [])[-5:])}\n\n"
            f"Incoming message: {incoming}\n\n"
            f"Generate a reply that sounds like THEM (not like an AI assistant):"
        )
        reply = self._llm.generate(prompt, temperature=0.7)
        if draft:
            reply = f"[ЧЕРНОВИК]\n{reply}\n\nОтправить? (да/нет)"
        return reply or incoming

    def generate_ideas(self, context: str, count: int = 3) -> list[str]:
        if not self._llm or not self._llm.ready:
            return []

        style = self._profile
        prompt = (
            f"Generate {count} creative ideas/solutions for the following context. "
            f"Match the user's thinking patterns: {', '.join(style.get('thinking_patterns', ['analytical']))}\n\n"
            f"Context: {context}\n\n"
            f"Respond as JSON array of strings."
        )
        result = self._llm.generate_structured(prompt, {
            "type": "array",
            "items": {"type": "string"}
        })
        return result if isinstance(result, list) else []

    def get_profile_summary(self) -> str:
        p = self._profile
        return (
            f"── Цифровой двойник ──\n"
            f"Стиль: {p.get('communication_style', '?')}\n"
            f"Формальность: {p.get('formality_level', 0.5):.0%}\n"
            f"Принятие решений: {p.get('decision_pattern', '?')}\n"
            f"Словарный запас: {len(p.get('vocabulary', []))} уникальных слов\n"
            f"Изученных предпочтений: {len(p.get('learned_preferences', []))}\n"
            f"Всего сообщений: {len(self._get_recent_messages(1000))}"
        )
