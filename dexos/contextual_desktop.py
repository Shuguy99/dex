import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.dexos.desktop")


CONTEXT_DASHBOARDS = {
    "morning": {
        "label": "🌅 Утренний дайджест",
        "widgets": ["Календарь", "Погода", "Задачи на день", "Почта"]
    },
    "work": {
        "label": "💼 Рабочий дашборд",
        "widgets": ["Текущий проект", "Git-статус", "Документация", "Задачи"]
    },
    "evening": {
        "label": "🌆 Вечерняя подборка",
        "widgets": ["Чтение", "Подкасты", "Итоги дня", "План на завтра"]
    },
    "deep_work": {
        "label": "🎯 Глубокая работа",
        "widgets": ["Фокус-таймер", "Минимизация уведомлений", "Белый шум"]
    }
}


class ContextualDesktop:
    def __init__(self, llm_client=None) -> None:
        self._llm = llm_client
        self._data_dir = Path("data/dexos")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._config_path = self._data_dir / "desktop_config.json"
        self._config: dict[str, Any] = self._load_config()
        self._current_context = self._detect_context()

    def _load_config(self) -> dict[str, Any]:
        if self._config_path.exists():
            try:
                with open(self._config_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"active_dashboard": "morning", "custom_widgets": []}

    def _save_config(self) -> None:
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    def _detect_context(self) -> str:
        hour = datetime.now().hour
        if hour < 6:
            return "night"
        elif hour < 10:
            return "morning"
        elif hour < 13:
            return "work"
        elif hour < 14:
            return "lunch"
        elif hour < 18:
            return "work"
        elif hour < 22:
            return "evening"
        return "night"

    def get_dashboard(self, override_context: str | None = None) -> dict[str, Any]:
        ctx = override_context or self._current_context
        dashboard = CONTEXT_DASHBOARDS.get(ctx)

        if not dashboard:
            dashboard = {
                "label": f"📋 Контекст: {ctx}",
                "widgets": ["Задачи", "Быстрые ссылки", "Статус системы", "Последние файлы"]
            }

        if self._config.get("custom_widgets"):
            dashboard = dict(dashboard)
            dashboard["widgets"] = dashboard["widgets"] + self._config["custom_widgets"]

        return {
            "context": ctx,
            "dashboard": dashboard,
            "generated_at": datetime.now().isoformat()
        }

    def suggest_dashboard(self, user_context: str) -> dict[str, Any]:
        if self._llm:
            prompt = (
                f"User context: '{user_context}'\n"
                f"Suggest a dashboard layout as JSON:\n"
                f"{{\"label\": str, \"widgets\": [str, ...], "
                f"\"reasoning\": str}}"
            )
            result = self._llm.generate_structured(prompt, {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "widgets": {"type": "array", "items": {"type": "string"}},
                    "reasoning": {"type": "string"}
                }
            })
            if result:
                return {
                    "context": "custom",
                    "dashboard": result,
                    "generated_at": datetime.now().isoformat()
                }

        return self.get_dashboard()

    def add_widget(self, widget_name: str) -> None:
        if widget_name not in self._config["custom_widgets"]:
            self._config["custom_widgets"].append(widget_name)
            self._save_config()
            logger.info(f"Custom widget added: {widget_name}")

    def get_desktop_summary(self) -> str:
        ctx = self._current_context
        dash = self.get_dashboard()
        lines = ["── Dex OS Desktop ──"]
        lines.append(f"Контекст: {ctx}")
        lines.append(f"Дашборд: {dash['dashboard']['label']}")
        lines.append("Виджеты:")
        for w in dash["dashboard"]["widgets"]:
            lines.append(f"  ▸ {w}")
        if self._config["custom_widgets"]:
            lines.append(f"\nПользовательские: {', '.join(self._config['custom_widgets'])}")
        return "\n".join(lines)
