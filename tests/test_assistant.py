import os
import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
