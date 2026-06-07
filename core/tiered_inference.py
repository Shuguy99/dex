import logging
import re

logger = logging.getLogger("dex.resource.tiered_inference")

SIMPLE_PATTERNS = re.compile(
    r"^(статус|помощь|время|дата|привет|пока|спасибо|"
    r"(открой|закрой|открыть|закрыть)\s+\w+|"
    r"(включи|выключи|вкл|выкл)\s+\w+|"
    r"таймер\s+\d+|стоп)$",
    re.IGNORECASE,
)

MEDIUM_PATTERNS = re.compile(
    r"^(напомни|запомни|найди|поиск|переведи|"
    r"(напиши|создай)\s+(файл|заметку|письмо)|"
    r"погода|курс|калькулятор|конвертируй)",
    re.IGNORECASE,
)


def classify_command(command: str) -> int:
    if not command or len(command) < 2:
        return 0
    if SIMPLE_PATTERNS.match(command):
        return 0
    if MEDIUM_PATTERNS.match(command):
        return 1
    return 2


TIER_NAMES = {0: "rule/nano-LLM", 1: "small-LLM", 2: "full-LLM"}

SIMPLE_RESPONSES = {
    "привет": "Здравствуйте",
    "пока": "До свидания",
    "спасибо": "Пожалуйста",
    "время": None,
    "дата": None,
    "статус": None,
    "помощь": None,
}


def get_simple_response(command: str) -> str | None:
    cmd = command.strip().lower()
    if cmd in SIMPLE_RESPONSES:
        return SIMPLE_RESPONSES[cmd]
    if cmd in ("стоп", "стоп код"):
        return None
    if cmd.startswith("время"):
        from datetime import datetime
        return f"Сейчас {datetime.now().strftime('%H:%M')}"
    if cmd.startswith("дата"):
        from datetime import datetime
        return f"Сегодня {datetime.now().strftime('%d.%m.%Y')}"
    return None


def route_command(command: str, use_small_model: bool = False) -> dict:
    tier = classify_command(command)
    simple = get_simple_response(command) if tier == 0 else None
    return {
        "tier": tier,
        "tier_name": TIER_NAMES.get(tier, "full-LLM"),
        "simple_response": simple,
        "needs_llm": tier > 0 or simple is None,
        "use_small_model": tier == 1 or use_small_model,
    }
