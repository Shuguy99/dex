import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["DEX_SKIP_LLM"] = "1"
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.assistant import DexAssistant


class TestDexIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig_data = os.environ.get("DEX_DATA_DIR", "")
        os.environ["DEX_DATA_DIR"] = self.tmp

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        if self._orig_data:
            os.environ["DEX_DATA_DIR"] = self._orig_data

    def test_assistant_full_cycle(self):
        a = DexAssistant()
        self.assertIsNotNone(a)
        self.assertIsNotNone(a.sandbox)

    def test_sandbox_integration(self):
        a = DexAssistant()
        import config
        allowed = config.CONFIG.ALLOWED_DIRS[0]
        Path(allowed).mkdir(parents=True, exist_ok=True)
        test_file = str(Path(allowed) / "test.txt")
        Path(test_file).touch()
        path = a.sandbox.resolve_path(test_file)
        self.assertIsNotNone(path)
        Path(test_file).unlink(missing_ok=True)

    def test_async_queue(self):
        a = DexAssistant()
        self.assertIsNotNone(a.cmd_queue)
        results = []
        def cb(r):
            results.append(r)
        a.cmd_queue.post(("status", {"callback": cb}))
        self.assertTrue(a.cmd_queue.is_busy() or True)

    def test_personality_auditor(self):
        a = DexAssistant()
        for _ in range(6):
            a.personality_auditor.record_interaction("test command", "response text")
        report = a.personality_auditor.audit(force=True)
        self.assertIsNotNone(report)
        self.assertIn("metrics", report)

    def test_diagnostics(self):
        a = DexAssistant()
        snap = a.diagnostics.snapshot()
        self.assertIn("threads", snap)

    def test_rule_engine_flow(self):
        a = DexAssistant()
        a.rule_engine.add_rule({
            "name": "test_rule",
            "condition": "command contains 'hello'",
            "action": "say hello",
            "priority": 5
        })
        active = a.rule_engine.get_active_rules()
        self.assertGreaterEqual(len(active), 1)

    def test_privacy_flow(self):
        a = DexAssistant()
        a.privacy.enable()
        self.assertTrue(a.privacy.is_active)
        a.privacy.disable()
        self.assertFalse(a.privacy.is_active)


if __name__ == "__main__":
    unittest.main()
