import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["DEX_SKIP_LLM"] = "1"
sys.path.insert(0, str(Path(__file__).parent.parent))

from ethics.bias_detector import BiasDetector
from ethics.co_processor import EthicalCoProcessor


class FakeLLM:
    ready = True
    def generate(self, prompt, **kw): return '{"consensus":"approve","confidence":0.8}'
    def generate_structured(self, prompt, schema, **kw): return {"consensus":"approve","confidence":0.8}

class TestEthicalCoProcessor(unittest.TestCase):
    def setUp(self): self.cp = EthicalCoProcessor(llm_client=FakeLLM())
    def test_evaluate_action(self): r = self.cp.evaluate_action("delete data"); self.assertIsInstance(r, dict)
    def test_evaluate_empty(self): r = self.cp.evaluate_action(""); self.assertIsInstance(r, dict)
    def test_get_summary(self): r = self.cp.get_ethics_summary(); self.assertIsInstance(r, str)

class TestBiasDetector(unittest.TestCase):
    def setUp(self): self.bd = BiasDetector()
    def test_analyze(self): r = self.bd.analyze("All programmers are good"); self.assertIsInstance(r, list)
    def test_analyze_empty(self): r = self.bd.analyze(""); self.assertIsInstance(r, list)
    def test_check_command(self): r = self.bd.check_command("test"); self.assertIsInstance(r, list)
    def test_get_summary(self): r = self.bd.get_bias_summary(); self.assertIsInstance(r, str)
