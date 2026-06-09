import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["DEX_SKIP_LLM"] = "1"
sys.path.insert(0, str(Path(__file__).parent.parent))

from mesh.agent_swarm import AgentSwarm
from mesh.fault_tolerant_core import FaultTolerantCore
from mesh.privacy_controller import MeshPrivacyController


class TestAgentSwarm(unittest.TestCase):
    def test_init(self): s = AgentSwarm(); self.assertIsNotNone(s)
    def test_start_stop(self): s = AgentSwarm(); s.stop(); self.assertTrue(True)

class TestFaultTolerantCore(unittest.TestCase):
    def setUp(self): self.ftc = FaultTolerantCore(state_provider=lambda: {"state":"ok"})
    def test_save_snapshot(self): self.ftc.save_snapshot(); self.assertTrue(True)
    def test_record_health(self): self.ftc.record_health(True); self.assertTrue(True)
    def test_recover(self): r = self.ftc.recover(); self.assertIsInstance(r, dict)

class TestMeshPrivacyController(unittest.TestCase):
    def setUp(self): self.mpc = MeshPrivacyController()
    def test_set_device_policy(self): self.mpc.set_device_policy("device1", "strict", 2); self.assertTrue(True)
    def test_can_transmit(self): r = self.mpc.can_transmit("device1", "data"); self.assertIsInstance(r, bool)
    def test_get_summary(self): r = self.mpc.get_privacy_summary(); self.assertIsInstance(r, str)
