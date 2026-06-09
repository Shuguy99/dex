import logging
from typing import Any

logger = logging.getLogger("dex.personality")

MODES = {
    "рабочий": {
        "name": "working",
        "style": "professional, concise, precise",
        "greeting": "Сэр, к вашим услугам.",
        "tts_rate": 170,
        "formality": 0.9
    },
    "расслабленный": {
        "name": "relaxed",
        "style": "casual, warm, friendly with occasional humor",
        "greeting": "Привет, сэр. Чем займёмся?",
        "tts_rate": 190,
        "formality": 0.3
    },
    "креативный": {
        "name": "creative",
        "style": "enthusiastic, imaginative, uses metaphors",
        "greeting": "О, сэр! У меня есть идея!",
        "tts_rate": 200,
        "formality": 0.2
    },
    "джарвис": {
        "name": "jarvis",
        "style": "calm, witty, slightly ironic, loyal butler",
        "greeting": "Здравствуйте, сэр. Чем могу быть полезен?",
        "tts_rate": 180,
        "formality": 0.6
    }
}

POSITIVE_WORDS = {"спасибо", "отлично", "класс", "хорошо", "да", "+",
                   "прекрасно", "замечательно", "молодец", "умница"}
NEGATIVE_WORDS = {"плохо", "ужасно", "медленно", "нет", "-",
                   "отвратительно", "грустно", "недоволен", "разочарован"}
QUESTION_WORDS = {"как", "что", "почему", "зачем", "где", "когда",
                   "кто", "сколько", "можешь", "есть ли"}


class PersonalityEngine:
    def __init__(self, default_mode: str = "джарвис") -> None:
        self._mode: dict[str, Any] = MODES.get(default_mode, MODES["джарвис"])
        self._mode_name = default_mode
        self._history: list[dict[str, Any]] = []
        self._user_tone_history: list[str] = []
        self._custom_instructions: list[str] = []
        self._greeted = False

    @property
    def current_mode(self) -> str:
        return self._mode_name

    @property
    def system_prompt(self) -> str:
        base = (
            f"You are Dex, an AI assistant. Your style: {self._mode['style']}. "
            f"You speak Russian. Be helpful, loyal, and efficient. "
        )
        if self._custom_instructions:
            base += " Additional instructions:\n" + "\n".join(f"- {i}" for i in self._custom_instructions)
        return base

    def set_mode(self, mode_name: str) -> bool:
        if mode_name in MODES:
            self._mode = MODES[mode_name]
            self._mode_name = mode_name
            logger.info(f"Personality mode: {mode_name}")
            return True
        return False

    def analyze_tone(self, text: str) -> dict[str, Any]:
        words = set(text.lower().split())
        pos = len(words & POSITIVE_WORDS)
        neg = len(words & NEGATIVE_WORDS)
        has_question = any(w in text.lower() for w in QUESTION_WORDS)
        has_exclamation = "!" in text
        word_count = len(text.split())

        compound = pos - neg
        if compound > 0:
            tone = "positive"
        elif compound < 0:
            tone = "negative"
        elif has_question:
            tone = "questioning"
        else:
            tone = "neutral"

        urgency = "high" if has_exclamation and word_count < 5 else \
                  "medium" if has_exclamation else \
                  "low"

        self._user_tone_history.append(tone)
        return {
            "tone": tone,
            "urgency": urgency,
            "positive_score": pos,
            "negative_score": neg,
            "compound": compound
        }

    def adapt_response(self, text: str, response: str) -> str:
        tone = self.analyze_tone(text)

        if tone["urgency"] == "high":
            response = f"Сэр! {response}" if not response.startswith("Сэр") else response
        elif tone["tone"] == "negative" and self._mode["formality"] < 0.5:
            response += "\n\nВсё в порядке, сэр? Может, принести кофе? :)"
        elif tone["tone"] == "positive":
            response += "\n\nРад стараться, сэр!"

        return response

    def get_greeting(self) -> str:
        if not self._greeted:
            self._greeted = True
            return self._mode["greeting"]
        return ""

    def add_instruction(self, instruction: str) -> None:
        self._custom_instructions.append(instruction)
        logger.info(f"Personality instruction added: {instruction}")

    def record_interaction(self, user_text: str, dex_response: str) -> None:
        self._history.append({
            "user": user_text,
            "dex": dex_response,
            "tone": self.analyze_tone(user_text),
            "timestamp": __import__('datetime').datetime.now().isoformat()
        })

    def get_mode_list(self) -> list[str]:
        return list(MODES.keys())

    def tts_rate(self) -> int:
        return int(self._mode.get("tts_rate", 180))
