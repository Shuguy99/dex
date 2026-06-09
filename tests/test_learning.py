import os
import sys
import unittest
from pathlib import Path

os.environ["DEX_SKIP_LLM"] = "1"
sys.path.insert(0, str(Path(__file__).parent.parent))

from learning.constitution import ConstitutionalChecker
from learning.digital_twin import DigitalTwin
from learning.meta_learner import MetaLearner
from learning.research import ResearchAgent


class FakeLLM:
    ready = True
    def generate(self, prompt, **kw): return "result"
    def generate_structured(self, prompt, schema, **kw):
        if schema and "properties" in schema:
            if "strategy" in schema["properties"]: return {"strategy":"rule","confidence":0.8}
            if "plan" in schema["properties"]: return {"plan":["step1"],"confidence":0.7}
        return {}

class TestMetaLearner(unittest.TestCase):
    def setUp(self): self.ml = MetaLearner(llm_client=FakeLLM())
    def test_select_strategy(self): r = self.ml.select_strategy("hello"); self.assertIsInstance(r, dict)
    def test_select_strategy_empty(self): r = self.ml.select_strategy(""); self.assertIsInstance(r, dict)

class TestResearchAgent(unittest.TestCase):
    def setUp(self): self.ra = ResearchAgent(llm_client=FakeLLM())
    def test_investigate(self): r = self.ra.investigate("AI safety"); self.assertIsInstance(r, dict)
    def test_investigate_empty(self): r = self.ra.investigate(""); self.assertIsInstance(r, dict)
    def test_fact_check(self): r = self.ra.fact_check("claim"); self.assertIsInstance(r, dict)

class TestDigitalTwin(unittest.TestCase):
    def setUp(self): self.dt = DigitalTwin(llm_client=FakeLLM())
    def test_learn_from_message(self):
        self.dt.learn_from_message("user text", "dex response"); self.assertTrue(True)
    def test_generate_reply(self): r = self.dt.generate_reply("hello"); self.assertIsInstance(r, str)

class TestConstitutionalChecker(unittest.TestCase):
    def setUp(self): self.cc = ConstitutionalChecker()
    def test_can_proceed(self):
        can, reasons = self.cc.can_proceed("открой", {"args":"test"}); self.assertIsInstance(can, bool)
    def test_get_articles(self): r = self.cc.get_articles(); self.assertIsInstance(r, list)
    def test_explain(self): r = self.cc.explain("privacy_1"); self.assertIsInstance(r, str)
