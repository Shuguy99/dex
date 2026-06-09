import os
import sys
import unittest
from pathlib import Path

import pytest

os.environ["DEX_SKIP_LLM"] = "1"
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from core.assistant import DexAssistant


class TestDexAssistant(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.config.DATA_DIR = Path(__file__).parent.parent / "data"
        self.config.LOG_DIR = self.config.DATA_DIR / "logs"
        self.config.MEMORY_DIR = self.config.DATA_DIR / "memory"
        self.config.RULES_DIR = self.config.DATA_DIR / "rules"
        self.config.AGENTS_DIR = self.config.DATA_DIR / "agents"
        self.config.BACKUP_DIR = self.config.DATA_DIR / "backups"
        self.config.LORA_MODEL_DIR = str(self.config.DATA_DIR / "lora")

    def test_initialization(self):
        assistant = DexAssistant()
        self.assertIsNotNone(assistant)
        self.assertIsNotNone(assistant.voice)
        self.assertIsNotNone(assistant.sandbox)
        self.assertIsNotNone(assistant.vector_memory)
        self.assertIsNotNone(assistant.watchdog)
        self.assertIsNotNone(assistant.kill_switch)

    def test_help_command(self):
        assistant = DexAssistant()
        assistant.initialize()
        result = assistant.process_command("помощь")
        self.assertIn("открой", result)
        self.assertIn("запусти", result)
        self.assertIn("запомни", result)

    def test_status_command(self):
        assistant = DexAssistant()
        assistant.initialize()
        result = assistant.process_command("статус")
        self.assertIn("Версия", result)
        self.assertIn("Агентов", result)

    def test_unknown_command(self):
        assistant = DexAssistant()
        assistant.initialize()
        result = assistant.process_command("asdfgh123")
        self.assertIn("не понимаю", result)

    def test_kill_switch(self):
        assistant = DexAssistant()
        assistant.initialize()
        result = assistant.process_command("стоп код")
        self.assertIn("Стоп-код", result)
        self.assertTrue(assistant.kill_switch.is_triggered)

    def test_privacy_mode(self):
        assistant = DexAssistant()
        assistant.initialize()
        result = assistant.process_command("приватный режим")
        self.assertIn("включён", result)
        result2 = assistant.process_command("открой файл")
        self.assertIn("не выполняются", result2)
        result3 = assistant.process_command("приватный режим")
        self.assertIn("выключен", result3)


# =====================================================================
# pytest-style tests for CRITICAL untested paths
# =====================================================================


def test_empty_text(monkeypatch):
    """Edge case: empty text should not crash, returns fallback."""
    assistant = DexAssistant()
    assistant.initialize()
    result = assistant.process_command("")
    assert isinstance(result, str)
    assert len(result) > 0


def test_whitespace_text(monkeypatch):
    """Edge case: whitespace-only text should not crash."""
    assistant = DexAssistant()
    assistant.initialize()
    result = assistant.process_command("   ")
    assert isinstance(result, str)
    assert len(result) > 0


def test_very_long_text(monkeypatch):
    """Edge case: very long text should not crash."""
    assistant = DexAssistant()
    assistant.initialize()
    result = assistant.process_command("x" * 10000)
    assert isinstance(result, str)


def test_process_command_tiered_inference_intercepts_greeting(monkeypatch):
    """Tiered inference intercepts 'привет' before command matching."""
    assistant = DexAssistant()
    assistant.initialize()
    result = assistant.process_command("привет")
    assert "Здравствуйте" in result


def test_process_command_tiered_inference_intercepts_farewell(monkeypatch):
    """Tiered inference intercepts 'пока' before command matching."""
    assistant = DexAssistant()
    assistant.initialize()
    result = assistant.process_command("пока")
    assert "До свидания" in result


def test_process_command_mental_fuse_blocks_destructive(monkeypatch):
    """Mental fuse blocks destructive shell commands."""
    assistant = DexAssistant()
    assistant.initialize()
    result = assistant.process_command("rm -rf /")
    assert "⛔" in result or "заблокировано" in result or "действие" in result


def test_plugin_list_empty(monkeypatch):
    """Plugin list with no plugins returns 'Нет установленных плагинов'."""
    assistant = DexAssistant()
    assistant.initialize()
    monkeypatch.setattr(assistant.plugins, "list_plugins", lambda: [])
    result = assistant.process_command("плагин list")
    assert "Нет установленных плагинов" in result


def test_plugin_list_with_plugins(monkeypatch):
    """Plugin list with plugins shows them."""
    assistant = DexAssistant()
    assistant.initialize()
    fake_plugins = [
        {"name": "test", "version": "1.0", "description": "Test plugin",
         "enabled": True, "loaded": True}
    ]
    monkeypatch.setattr(assistant.plugins, "list_plugins", lambda: fake_plugins)
    result = assistant.process_command("плагин list")
    assert "test" in result
    assert "1.0" in result


def test_plugin_enable_not_found(monkeypatch):
    """Plugin enable with unknown name returns not found."""
    assistant = DexAssistant()
    assistant.initialize()
    monkeypatch.setattr(assistant.plugins, "enable_plugin", lambda name: False)
    result = assistant.process_command("плагин enable nonexistent")
    assert "не найден" in result


def test_plugin_enable_success(monkeypatch):
    """Plugin enable with known name returns success."""
    assistant = DexAssistant()
    assistant.initialize()
    monkeypatch.setattr(assistant.plugins, "enable_plugin", lambda name: True)
    result = assistant.process_command("плагин enable test")
    assert "включён" in result


def test_plugin_disable_not_found(monkeypatch):
    """Plugin disable with unknown name returns not found."""
    assistant = DexAssistant()
    assistant.initialize()
    monkeypatch.setattr(assistant.plugins, "disable_plugin", lambda name: False)
    result = assistant.process_command("плагин disable nonexistent")
    assert "не найден" in result


def test_plugin_disable_success(monkeypatch):
    """Plugin disable with known name returns success."""
    assistant = DexAssistant()
    assistant.initialize()
    monkeypatch.setattr(assistant.plugins, "disable_plugin", lambda name: True)
    result = assistant.process_command("плагин disable test")
    assert "отключён" in result


def test_plugin_info_not_found(monkeypatch):
    """Plugin info with unknown name returns not found."""
    assistant = DexAssistant()
    assistant.initialize()
    monkeypatch.setattr(assistant.plugins, "get_plugin", lambda name: None)
    result = assistant.process_command("плагин info nonexistent")
    assert "не найден" in result


def test_plugin_help(monkeypatch):
    """Plugin command with unknown subcommand shows help."""
    assistant = DexAssistant()
    assistant.initialize()
    result = assistant.process_command("плагин unknown")
    assert "плагин list" in result
    assert "плагин enable" in result


def test_register_plugin_commands(monkeypatch):
    """Plugin command prefixes are registered as handlers."""
    assistant = DexAssistant()
    assistant.initialize()
    monkeypatch.setattr(assistant.plugins, "get_command_prefixes",
                        lambda: {"myplugin": "myplugin"})
    monkeypatch.setattr(assistant.plugins, "execute", lambda cmd: "plugin executed")
    assistant._register_plugin_commands()
    assert "myplugin" in assistant._command_handlers
    result = assistant._command_handlers["myplugin"]("hello")
    assert "plugin executed" in result


def test_make_plugin_handler_fallback(monkeypatch):
    """Plugin handler returns fallback when execute returns None."""
    assistant = DexAssistant()
    assistant.initialize()
    monkeypatch.setattr(assistant.plugins, "execute", lambda cmd: None)
    handler = assistant._make_plugin_handler("testprefix")
    result = handler("some args")
    assert "не обработал" in result


def test_register_plugin_commands_does_not_overwrite_existing(monkeypatch):
    """Existing command handlers should not be overwritten by plugin commands."""
    assistant = DexAssistant()
    assistant.initialize()
    original = assistant._command_handlers.get("плагин", None)
    monkeypatch.setattr(assistant.plugins, "get_command_prefixes",
                        lambda: {"плагин": "someplugin"})
    assistant._register_plugin_commands()
    assert assistant._command_handlers["плагин"] is original


def test_conversational_respond_llm_ready(monkeypatch):
    """Conversational respond with LLM ready uses llm.chat."""
    assistant = DexAssistant()
    assistant.initialize()
    assistant.llm._available_models = ["test"]
    monkeypatch.setattr(assistant.llm, "chat", lambda **kw: "Mock LLM response")
    monkeypatch.setattr(assistant.vector_memory, "search", lambda query, n_results=3: [])
    result = assistant.process_command("как дела?")
    assert result == "Mock LLM response"


def test_conversational_respond_not_ready(monkeypatch):
    """Conversational respond without LLM falls back to 'не понимаю'."""
    assistant = DexAssistant()
    assistant.initialize()
    result = assistant.process_command("произвольный запрос без llm")
    assert "не понимаю" in result


def test_conversational_respond_llm_error(monkeypatch):
    """Conversational respond when LLM throws returns error message."""
    assistant = DexAssistant()
    assistant.initialize()
    assistant.llm._available_models = ["test"]
    monkeypatch.setattr(assistant.vector_memory, "search", lambda query, n_results=3: [])

    def broken_chat(**kw):
        raise RuntimeError("LLM failure")
    monkeypatch.setattr(assistant.llm, "chat", broken_chat)
    result = assistant.process_command("как дела?")
    assert "ошибка" in result


def test_conversational_respond_stores_history(monkeypatch):
    """Conversational respond stores user message and assistant response."""
    assistant = DexAssistant()
    assistant.initialize()
    assistant.llm._available_models = ["test"]
    monkeypatch.setattr(assistant.llm, "chat", lambda **kw: "Mock reply")
    monkeypatch.setattr(assistant.vector_memory, "search", lambda query, n_results=3: [])
    assistant.process_command("как прошел день")
    assert len(assistant._conversation_history) == 2
    assert assistant._conversation_history[0]["role"] == "user"
    assert assistant._conversation_history[1]["role"] == "assistant"


def test_get_conversation_summary_empty(monkeypatch):
    """Empty conversation history returns empty list."""
    assistant = DexAssistant()
    assistant.initialize()
    summary = assistant.get_conversation_summary()
    assert summary == []


def test_get_conversation_summary_with_data(monkeypatch):
    """Conversation summary returns last N exchanges."""
    assistant = DexAssistant()
    assistant.initialize()
    assistant._conversation_history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "how are you"},
        {"role": "assistant", "content": "fine"},
    ]
    summary = assistant.get_conversation_summary(n=1)
    assert len(summary) == 2
    assert summary == assistant._conversation_history[-2:]


def test_cmd_open_no_args(monkeypatch):
    """_cmd_open with no args returns prompt."""
    assistant = DexAssistant()
    assistant.initialize()
    result = assistant.process_command("открой")
    assert "Что открыть" in result


def test_cmd_launch_no_args(monkeypatch):
    """_cmd_launch with no args returns prompt."""
    assistant = DexAssistant()
    assistant.initialize()
    result = assistant.process_command("запусти")
    assert "Что запустить" in result


def test_cmd_remember_no_args(monkeypatch):
    """_cmd_remember with no args returns prompt."""
    assistant = DexAssistant()
    assistant.initialize()
    result = assistant.process_command("запомни")
    assert "Что запомнить" in result


def test_cmd_predict_no_data(monkeypatch):
    """_cmd_predict with no usage data says not enough data."""
    assistant = DexAssistant()
    assistant.initialize()
    result = assistant.process_command("прогноз")
    assert "Недостаточно данных" in result or "Прогноз" in result


def test_cmd_debate_no_args(monkeypatch):
    """_cmd_debate with no args returns prompt."""
    assistant = DexAssistant()
    assistant.initialize()
    result = assistant.process_command("дебаты")
    assert "Какую тему" in result


def test_cmd_remember_saves_memory(monkeypatch):
    """_cmd_remember saves a new non-sensitive fact to vector memory."""
    assistant = DexAssistant()
    assistant.initialize()
    monkeypatch.setattr(assistant.memory_validator, "validate_new_fact",
                        lambda fact: True)
    monkeypatch.setattr(assistant.vector_memory, "add",
                        lambda text, metadata, doc_id: None)
    result = assistant.process_command("запомни мой любимый цвет синий")
    assert "Запомнил" in result or "сохранена" in result


def test_cmd_open_file_no_args(monkeypatch):
    """_cmd_open_file with no args (just 'открой файл') returns prompt."""
    assistant = DexAssistant()
    assistant.initialize()
    result = assistant.process_command("открой файл")
    assert "Что открыть" in result


def test_cmd_remember_validates_fact(monkeypatch):
    """_cmd_remember calls memory_validator for new facts."""
    assistant = DexAssistant()
    assistant.initialize()
    validated = False

    def mock_validate(fact):
        nonlocal validated
        validated = True
        return True

    monkeypatch.setattr(assistant.memory_validator, "validate_new_fact", mock_validate)
    monkeypatch.setattr(assistant.vector_memory, "add",
                        lambda text, metadata, doc_id: None)
    assistant.process_command("запомни факт о погоде")
    assert validated


if __name__ == "__main__":
    unittest.main()
