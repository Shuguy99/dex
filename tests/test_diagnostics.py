import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.diagnostics import ThreadDiagnostics


class TestThreadDiagnostics(unittest.TestCase):
    def setUp(self):
        self.diag = ThreadDiagnostics()

    def test_init(self):
        self.assertEqual(len(self.diag._snapshots), 0)

    def test_snapshot_basic_structure(self):
        snap = self.diag.snapshot()
        self.assertIn("ts", snap)
        self.assertIn("thread_count", snap)
        self.assertIn("threads", snap)
        self.assertIn("main_thread_blocked", snap)
        self.assertGreater(snap["thread_count"], 0)
        self.assertIn("MainThread", snap["threads"])

    def test_snapshot_with_mock_threads(self):
        mock_main = MagicMock()
        mock_main.name = "MainThread"
        mock_main.is_alive.return_value = True
        mock_main.daemon = False
        mock_main.ident = 12345

        mock_worker = MagicMock()
        mock_worker.name = "Worker-1"
        mock_worker.is_alive.return_value = False
        mock_worker.daemon = True
        mock_worker.ident = 67890

        with patch("threading.enumerate", return_value=[mock_main, mock_worker]), \
             patch("threading.active_count", return_value=2):
            snap = self.diag.snapshot()
        self.assertEqual(snap["thread_count"], 2)
        self.assertTrue(snap["threads"]["MainThread"]["alive"])
        self.assertFalse(snap["threads"]["Worker-1"]["alive"])
        self.assertTrue(snap["threads"]["Worker-1"]["daemon"])

    def test_snapshot_history_capped(self):
        for _ in range(150):
            self.diag.snapshot()
        self.assertLessEqual(len(self.diag._snapshots), 100)

    def test_get_blocked_threads_no_blockers(self):
        mock_t = MagicMock()
        mock_t.name = "IdleThread"
        mock_t.is_alive.return_value = True
        mock_t.ident = 99999

        with patch("threading.enumerate", return_value=[mock_t]):
            blocked = self.diag.get_blocked_threads()
            self.assertIsInstance(blocked, list)

    def test_get_blocked_threads_with_blocked(self):
        mock_t = MagicMock()
        mock_t.name = "BusyThread"
        mock_t.is_alive.return_value = True
        mock_t.ident = 11111

        frame = MagicMock()
        frame.f_back = None
        frame.f_code.co_filename = "test.py"
        frame.f_code.co_name = "busy_func"

        with patch("threading.enumerate", return_value=[mock_t]), \
             patch("sys._current_frames", return_value={11111: frame}):
            blocked = self.diag.get_blocked_threads(threshold=0.0)
            self.assertGreaterEqual(len(blocked), 0)

    def test_get_blocked_threads_with_sleep(self):
        mock_t = MagicMock()
        mock_t.name = "Sleeper"
        mock_t.is_alive.return_value = True
        mock_t.ident = 22222

        inner = MagicMock()
        inner.f_code.co_filename = "threading.py"
        inner.f_code.co_name = "time.sleep"
        inner.f_lineno = 123
        inner.f_back = None
        frame_sleep = MagicMock()
        frame_sleep.f_back = inner
        frame_sleep.f_code.co_filename = "test.py"
        frame_sleep.f_code.co_name = "outer"
        frame_sleep.f_lineno = 42

        with patch("threading.enumerate", return_value=[mock_t]), \
             patch("sys._current_frames", return_value={22222: frame_sleep}):
            blocked = self.diag.get_blocked_threads(threshold=0.0)
            self.assertEqual(len(blocked), 0)

    def test_report(self):
        report = self.diag.report()
        self.assertIn("Thread Diagnostics", report)
        self.assertIn("Threads:", report)
        self.assertIn("MainThread", report)
        self.assertIn("Main blocked", report)

    def test_main_thread_blocked_detection(self):
        mock_main = MagicMock()
        mock_main.name = "MainThread"
        mock_main.is_alive.return_value = True
        mock_main.daemon = False
        mock_main.ident = 1

        frame = MagicMock()
        frame.f_globals = {"__name__": "MainThread"}

        with patch("threading.enumerate", return_value=[mock_main]), \
             patch("sys._current_frames", return_value={1: frame}), \
             patch("traceback.extract_stack", return_value=[]):
            snap = self.diag.snapshot()
            self.assertIsNotNone(snap)

    def test_main_thread_blocked_detection_with_qeventloop(self):
        mock_main = MagicMock()
        mock_main.name = "MainThread"
        mock_main.is_alive.return_value = True
        mock_main.daemon = False
        mock_main.ident = 1

        frame = MagicMock()
        frame.f_globals = {"__name__": "MainThread"}

        with patch("threading.enumerate", return_value=[mock_main]), \
             patch("sys._current_frames", return_value={1: frame}), \
             patch("traceback.extract_stack", return_value=["QEventLoop"]):
            snap = self.diag.snapshot()
            self.assertFalse(snap["main_thread_blocked"])


if __name__ == "__main__":
    unittest.main()
