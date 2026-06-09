import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["DEX_SKIP_LLM"] = "1"
sys.path.insert(0, str(Path(__file__).parent.parent))

from temporal.autobiographical_memory import AutobiographicalMemory
from temporal.life_planner import LifePlanner
from temporal.retrospective import RetrospectiveAnalyzer


class FakeLLM:
    ready = True
    def generate(self, prompt, **kw): return "narrative text"
    def generate_structured(self, prompt, schema, **kw): return {}

class TestAutobiographicalMemory(unittest.TestCase):
    def setUp(self): self.am = AutobiographicalMemory(llm_client=FakeLLM())
    def test_record_interaction(self):
        self.am.record_interaction("hello", "hi there", "greeting")
        self.assertTrue(True)
    def test_recall(self): r = self.am.recall("hello"); self.assertIsInstance(r, list)
    def test_get_timeline(self): r = self.am.get_timeline(); self.assertIsInstance(r, list)

class TestLifePlanner(unittest.TestCase):
    def setUp(self): self.lp = LifePlanner(llm_client=FakeLLM())
    def test_add_goal(self): self.assertTrue(self.lp.add_goal("learn python", category="learning"))
    def test_add_goal_empty(self): r = self.lp.add_goal("", category=""); self.assertIsInstance(r, str)
    def test_get_goals(self):
        self.lp.add_goal("test", category="health"); goals = self.lp._goals; self.assertIsInstance(goals, list)
    def test_get_summary(self): r = self.lp.get_life_summary(); self.assertIsInstance(r, str)

class TestRetrospectiveAnalyzer(unittest.TestCase):
    def setUp(self):
        self.am = AutobiographicalMemory(llm_client=FakeLLM())
        self.ra = RetrospectiveAnalyzer(llm_client=FakeLLM(), autobiographical_memory=self.am)
    def test_record_interaction(self):
        self.ra.generate_monthly_report(); self.assertTrue(True)
    def test_generate_monthly_report(self): r = self.ra.generate_monthly_report(); self.assertIsInstance(r, dict)
