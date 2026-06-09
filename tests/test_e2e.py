import os
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ["DEX_SKIP_LLM"] = "1"
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.assistant import DexAssistant
from core.async_engine import Command


class TestDexE2E(unittest.TestCase):
    def setUp(self):
        self.assistant = DexAssistant()
        self.assistant.initialize()

    def tearDown(self):
        self.assistant.shutdown()

    def test_unknown_command_does_not_crash(self):
        result = self.assistant.process_command("тест")
        self.assertIn("не понимаю", result)

    def test_status_returns_system_info(self):
        result = self.assistant.process_command("статус")
        self.assertIn("Статус системы", result)
        self.assertIn("Версия", result)

    def test_help_returns_command_list(self):
        result = self.assistant.process_command("помощь")
        self.assertIn("открой", result)
        self.assertIn("запусти", result)

    @patch("core.app_launcher.AppLauncher.launch", return_value=True)
    def test_open_notepad_attempts_launch(self, mock_launch):
        result = self.assistant.process_command("запусти блокнот")
        mock_launch.assert_called_once_with("блокнот")
        self.assertIn("Запускаю", result)
        self.assertIn("блокнот", result)

    def test_async_queue_posts_and_fires_callback(self):
        results = []
        event = threading.Event()

        def cb(r):
            results.append(r)
            event.set()

        cmd = Command(text="статус", callback=cb)
        self.assistant.cmd_queue.post(cmd)
        ok = event.wait(timeout=3.0)
        self.assertTrue(ok, "Command was not processed in time")
        self.assertEqual(len(results), 1)
        self.assertIn("Статус системы", results[0])

    def test_audit_returns_auditor_info(self):
        for _ in range(6):
            self.assistant.personality_auditor.record_interaction(
                "команда", "ответ", error=False
            )
        result = self.assistant.process_command("аудит")
        self.assertIn("Drift", result)

    def test_debate_returns_debate_result(self):
        result = self.assistant.process_command("дебаты тест")
        self.assertIn("Дебаты", result)

    def test_invalid_special_chars_does_not_crash(self):
        result = self.assistant.process_command("!@#$%^&*()_+={}[]|\\:;\"'<>,.?/~`")
        self.assertIn("не понимаю", result)

    def test_kill_switch_triggers(self):
        result = self.assistant.process_command("стоп код")
        self.assertIn("Стоп-код", result)
        self.assertTrue(self.assistant.kill_switch.is_triggered)

    def test_history_via_logger_returns_recent_commands(self):
        self.assistant.process_command("статус")
        self.assistant.process_command("помощь")
        self.assistant.process_command("статус")
        recent = self.assistant.dex_logger.get_recent_commands(3)
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[0]["command"], "статус")
        self.assertEqual(recent[1]["command"], "помощь")
        self.assertEqual(recent[2]["command"], "статус")

    def test_clear_does_not_crash(self):
        result = self.assistant.process_command("/clear")
        self.assertIsNotNone(result)

    def test_export_history_does_not_crash(self):
        result = self.assistant.process_command("/export history")
        self.assertIsNotNone(result)

    def test_history_command_does_not_crash(self):
        result = self.assistant.process_command("история 3")
        self.assertIsNotNone(result)

    def test_privacy_mode_toggle(self):
        result = self.assistant.process_command("приватный режим")
        self.assertIn("включён", result)

    def test_resource_status_returns_cache_info(self):
        result = self.assistant.process_command("ресурсы")
        self.assertIn("Resource Status", result)
        self.assertIn("Model cache", result)

    def test_cognitive_load_returns_load_summary(self):
        result = self.assistant.process_command("нагрузка")
        self.assertIsNotNone(result)

    def test_constitutional_check_returns_articles(self):
        result = self.assistant.process_command("конституция")
        self.assertIn("Конституция", result)

    def test_empty_command_returns_fallback(self):
        result = self.assistant.process_command("")
        self.assertIsNotNone(result)

    def test_mocked_ollama_initialization(self):
        with patch("core.assistant.OllamaClient") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.ready = False
            mock_inst.generate.return_value = "mocked"
            mock_inst.models = []
            mock_cls.return_value = mock_inst
            a = DexAssistant()
            a.initialize()
            r = a.process_command("статус")
            self.assertIn("Статус системы", r)
            a.shutdown()

    def test_multiagent_orchestrator_health(self):
        health = self.assistant.orchestrator.check_health()
        self.assertIn("active_agents", health)
        self.assertIn("total_agents", health)


if __name__ == "__main__":
    unittest.main()
