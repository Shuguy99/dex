import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["DEX_SKIP_LLM"] = "1"
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CONFIG
from watchdog.anomaly import AnomalyDetector
from watchdog.logger import DexLogger
from watchdog.monitor import WatchdogMonitor


class TestAnomalyDetector(unittest.TestCase):
    def setUp(self):
        self.ad = AnomalyDetector(error_threshold=0.5, latency_threshold_ms=5000, window_size=10)
    def test_record_latency(self): self.ad.record_latency(100); self.assertTrue(True)
    def test_record_error(self): self.ad.record_error(); self.assertTrue(True)
    def test_check(self): r = self.ad.check(); self.assertIsInstance(r, list)

class TestDexLogger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dl = DexLogger(log_dir=str(self.tmp))
    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)
    def test_log_command(self): self.dl.log_command("test", "response", 50); self.assertTrue(True)
    def test_log_command_error(self): self.dl.log_command("test", "resp", 50, success=False); self.assertTrue(True)
    def test_get_recent(self): r = self.dl.get_recent_commands(5); self.assertIsInstance(r, list)

class TestWatchdogMonitor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.wm = WatchdogMonitor(log_dir=str(self.tmp))
    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)
    def test_start_stop(self):
        self.wm.start(); self.wm.stop(); self.assertTrue(True)
    def test_check_anomaly(self):
        self.wm.start(); r = self.wm.check_anomaly(); self.wm.stop(); self.assertIsInstance(r, list)

if __name__ == "__main__":
    unittest.main()
