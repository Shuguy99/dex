import os
import sys
import unittest
from pathlib import Path

os.environ["DEX_SKIP_LLM"] = "1"
sys.path.insert(0, str(Path(__file__).parent.parent))

from intent.mental_fuse import MentalFuse
from intent.symbiotic_input import SymbioticInput


class FakeLLM:
    ready = True
    def generate(self, prompt, **kw): return "completion"
    def generate_structured(self, prompt, schema, **kw):
        if schema and "properties" in schema:
            if "completions" in schema["properties"]: return {"completions": ["opt 1"]}
            if "blocked" in schema["properties"]: return {"blocked": False, "severity": "low", "reason": "", "messages": []}
        return {}

class TestMentalFuse(unittest.TestCase):
    def setUp(self): self.mf = MentalFuse()
    def test_check_safe(self): r = self.mf.check("hello"); self.assertIsInstance(r, dict)
    def test_check_empty(self): r = self.mf.check(""); self.assertIsInstance(r, dict)
    def test_get_summary(self): r = self.mf.get_mental_fuse_summary(); self.assertIsInstance(r, str)

class TestSymbioticInput(unittest.TestCase):
    def setUp(self): self.si = SymbioticInput(llm_client=FakeLLM())
    def test_predict_completion(self): r = self.si.predict_completion("hello"); self.assertIsInstance(r, list)
    def test_get_summary(self): r = self.si.get_symbiotic_summary(); self.assertIsInstance(r, str)
