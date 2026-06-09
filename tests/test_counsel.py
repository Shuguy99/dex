import os
import sys
import unittest
from pathlib import Path

os.environ["DEX_SKIP_LLM"] = "1"
sys.path.insert(0, str(Path(__file__).parent.parent))

from counsel.counterfactual import CounterfactualAnalyzer
from counsel.devils_advocate import DevilsAdvocate
from counsel.scenario_branch import ScenarioTree


class FakeLLM:
    ready = True
    def generate(self, prompt, **kw): return "analysis"
    def generate_structured(self, prompt, schema, **kw):
        if schema and "properties" in schema:
            if "scenarios" in schema["properties"]: return {"scenarios":[{"name":"A","probability":0.6,"impact":"high","risks":[]}]}
            if "counterfactuals" in schema["properties"]: return {"counterfactuals":[{"change":"x","outcome":"y"}]}
            if "critique" in schema["properties"]: return {"critique":"valid","dimension":"logic","severity":"medium"}
        return {}

class TestScenarioTree(unittest.TestCase):
    def setUp(self): self.st = ScenarioTree(llm_client=FakeLLM())
    def test_build_tree(self): r = self.st.build_tree("deploy feature"); self.assertIsInstance(r, dict)
    def test_get_summary(self): r = self.st.get_scenario_summary(); self.assertIsInstance(r, str)

class TestCounterfactualAnalyzer(unittest.TestCase):
    def setUp(self): self.ca = CounterfactualAnalyzer(llm_client=FakeLLM())
    def test_save_fork(self): r = self.ca.save_fork("decision", "chosen", "alternative", {}); self.assertIsInstance(r, str)
    def test_get_summary(self): r = self.ca.get_counterfactual_summary(); self.assertIsInstance(r, str)

class TestDevilsAdvocate(unittest.TestCase):
    def setUp(self): self.da = DevilsAdvocate(llm_client=FakeLLM())
    def test_analyze(self): r = self.da.analyze("perfect plan"); self.assertIsInstance(r, dict)
    def test_analyze_empty(self): r = self.da.analyze(""); self.assertIsInstance(r, dict)
    def test_get_summary(self): r = self.da.get_advocate_summary(); self.assertIsInstance(r, str)
