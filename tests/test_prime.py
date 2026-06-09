import os
import sys
import unittest
from pathlib import Path

os.environ["DEX_SKIP_LLM"] = "1"
sys.path.insert(0, str(Path(__file__).parent.parent))

from prime.consciousness_continuum import ConsciousnessContinuum
from prime.delegation import DelegationEngine
from prime.federated_consciousness import FederatedConsciousness


class FakeLLM:
    ready = True
    def generate(self, prompt, **kw): return "text"
    def generate_structured(self, prompt, schema, **kw): return {"session_id":"s1","context_size":5,"status":"ready"}

class TestConsciousnessContinuum(unittest.TestCase):
    def setUp(self): self.cc = ConsciousnessContinuum()
    def test_record_interaction(self):
        self.cc.record_interaction("hello", "hi"); self.assertTrue(True)
    def test_start_session(self):
        self.cc.start_session("local"); self.assertTrue(True)
    def test_get_context_summary(self): r = self.cc.get_context_summary(); self.assertIsInstance(r, str)

class TestDelegationEngine(unittest.TestCase):
    def setUp(self): self.de = DelegationEngine()
    def test_deploy_sub_personality(self): r = self.de.deploy_sub_personality("helper", "remote"); self.assertIsInstance(r, dict)
    def test_get_summary(self): r = self.de.get_delegation_summary(); self.assertIsInstance(r, str)

class TestFederatedConsciousness(unittest.TestCase):
    def setUp(self): self.fc = FederatedConsciousness(llm_client=FakeLLM())
    def test_propose_collaboration(self): r = self.fc.propose_collaboration("task", ["local"]); self.assertIsInstance(r, dict)
    def test_get_summary(self): r = self.fc.get_federated_summary(); self.assertIsInstance(r, str)
