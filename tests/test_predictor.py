import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.predictor import PersonalPredictor


class TestPersonalPredictor(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.predictor = PersonalPredictor()
        self.predictor._data_dir = self.tmpdir
        self.predictor._path = self.tmpdir / "usage_patterns.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_init_creates_dir(self):
        d = Path(tempfile.mkdtemp())
        p = PersonalPredictor()
        p._data_dir = d / "subdir"
        p._path = d / "subdir" / "usage_patterns.json"
        # accessing path triggers creation
        p._path.parent.mkdir(parents=True, exist_ok=True)
        self.assertTrue(p._path.parent.exists())
        import shutil
        shutil.rmtree(d, ignore_errors=True)

    def test_load_patterns_default(self):
        patterns = self.predictor._load_patterns()
        self.assertEqual(patterns, {"app_frequency": {}, "file_frequency": {}, "time_patterns": {}})

    def test_load_patterns_existing(self):
        data = {"app_frequency": {"calc": 5}, "file_frequency": {}, "time_patterns": {}}
        with open(self.predictor._path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        loaded = self.predictor._load_patterns()
        self.assertEqual(loaded["app_frequency"], {"calc": 5})

    def test_record_launch(self):
        with patch("core.predictor.PersonalPredictor._save_patterns"):
            self.predictor.record_launch("calc.exe")
        self.assertEqual(len(self.predictor._launch_log), 1)
        self.assertEqual(self.predictor._patterns["app_frequency"]["calc.exe"], 1)

    def test_record_launch_multiple(self):
        with patch("core.predictor.PersonalPredictor._save_patterns"):
            self.predictor.record_launch("calc.exe")
            self.predictor.record_launch("calc.exe")
            self.predictor.record_launch("notepad.exe")
        self.assertEqual(self.predictor._patterns["app_frequency"]["calc.exe"], 2)
        self.assertEqual(self.predictor._patterns["app_frequency"]["notepad.exe"], 1)

    def test_record_file_open(self):
        with patch("core.predictor.PersonalPredictor._save_patterns"):
            self.predictor.record_file_open("test.py")
        self.assertEqual(len(self.predictor._file_log), 1)
        self.assertEqual(self.predictor._patterns["file_frequency"][".py"], 1)

    def test_record_command(self):
        self.predictor.record_command("deploy")
        self.assertEqual(self.predictor._patterns["command_frequency"]["deploy"], 1)
        self.predictor.record_command("deploy")
        self.assertEqual(self.predictor._patterns["command_frequency"]["deploy"], 2)

    def test_analyze_patterns_empty(self):
        self.predictor.analyze_patterns()
        # no exception

    def test_analyze_patterns_with_data(self):
        self.predictor._patterns["command_frequency"] = {"a": 5, "b": 3, "c": 1}
        with self.assertLogs("dex.predictor", level="DEBUG") as logs:
            self.predictor.analyze_patterns()
        self.assertTrue(any("Top commands" in l for l in logs.output))

    def test_predict_next_empty(self):
        predictions = self.predictor.predict_next()
        self.assertEqual(predictions, [])

    def test_predict_next_with_data(self):
        import datetime
        now = datetime.datetime.now()
        time_key = f"{now.weekday()}_{now.hour}"
        self.predictor._patterns["time_patterns"][time_key] = {"calc.exe": 10, "notepad.exe": 3}
        predictions = self.predictor.predict_next()
        self.assertGreater(len(predictions), 0)
        self.assertEqual(predictions[0]["name"], "calc.exe")
        self.assertEqual(predictions[0]["confidence"], 1.0)

    def test_predict_next_with_llm(self):
        mock_llm = MagicMock()
        mock_llm.ready = True
        mock_llm.generate_structured.return_value = [
            {"app": "vs code", "reason": "coding time", "action": "launch"}
        ]
        predictor = PersonalPredictor(llm_client=mock_llm)
        predictor._data_dir = self.tmpdir
        predictor._path = self.tmpdir / "usage_patterns.json"
        import datetime
        now = datetime.datetime.now()
        time_key = f"{now.weekday()}_{now.hour}"
        predictor._patterns["time_patterns"][time_key] = {"calc.exe": 10, "notepad.exe": 3}
        predictions = predictor.predict_next()
        self.assertGreater(len(predictions), 2)
        self.assertEqual(predictions[2]["name"], "vs code")

    def test_predict_next_with_llm_no_llm_preds(self):
        mock_llm = MagicMock()
        mock_llm.ready = True
        mock_llm.generate_structured.return_value = None
        predictor = PersonalPredictor(llm_client=mock_llm)
        predictor._data_dir = self.tmpdir
        predictor._path = self.tmpdir / "usage_patterns.json"
        import datetime
        now = datetime.datetime.now()
        time_key = f"{now.weekday()}_{now.hour}"
        predictor._patterns["time_patterns"][time_key] = {"calc.exe": 10}
        predictions = predictor.predict_next()
        self.assertEqual(len(predictions), 1)

    def test_get_pattern_summary(self):
        self.predictor._patterns["app_frequency"] = {"calc.exe": 5, "notepad.exe": 3}
        self.predictor._patterns["file_frequency"] = {".py": 10, ".txt": 2}
        self.predictor._launch_log.append({"app": "test"})
        summary = self.predictor.get_pattern_summary()
        self.assertIn("calc.exe", summary)
        self.assertIn(".py", summary)
        self.assertIn("Записей в логах", summary)

    def test_simulate_consequence_delete_critical(self):
        result = self.predictor.simulate_consequence("delete_file", {"path": "C:\\Windows\\system32\\config"})
        self.assertIn("CRITICAL", str(result["risks"]))
        self.assertFalse(result["safe"])

    def test_simulate_consequence_delete_high(self):
        result = self.predictor.simulate_consequence("delete_file", {"path": "/project/file.txt"})
        self.assertIn("HIGH", str(result["risks"]))
        self.assertFalse(result["safe"])

    def test_simulate_consequence_delete_low(self):
        result = self.predictor.simulate_consequence("delete_file", {"path": "/tmp/file.txt"})
        self.assertIn("LOW", str(result["risks"]))
        self.assertTrue(result["safe"])

    def test_simulate_consequence_critical_command(self):
        result = self.predictor.simulate_consequence("run_command", {"cmd": "rm -rf /"})
        self.assertIn("CRITICAL", str(result["risks"]))

    def test_simulate_consequence_medium_command(self):
        result = self.predictor.simulate_consequence("run_command", {"cmd": "pip uninstall django"})
        self.assertIn("MEDIUM", str(result["risks"]))

    def test_simulate_consequence_with_llm(self):
        mock_llm = MagicMock()
        mock_llm.ready = True
        mock_llm.generate.return_value = "This is dangerous"
        predictor = PersonalPredictor(llm_client=mock_llm)
        predictor._data_dir = self.tmpdir
        predictor._path = self.tmpdir / "usage_patterns.json"
        result = predictor.simulate_consequence("delete_file", {"path": "/tmp/x"})
        self.assertIn("LLM analysis", str(result["risks"]))

    def test_prepare_for_prediction(self):
        import datetime
        now = datetime.datetime.now()
        time_key = f"{now.weekday()}_{now.hour}"
        self.predictor._patterns["time_patterns"][time_key] = {"calc.exe": 100}
        executor = MagicMock()
        results = self.predictor.prepare_for_prediction(executor)
        self.assertGreater(len(results), 0)

    def test_prepare_for_prediction_low_confidence(self):
        import datetime
        now = datetime.datetime.now()
        time_key = f"{now.weekday()}_{now.hour}"
        self.predictor._patterns["time_patterns"][time_key] = {"calc.exe": 1}
        executor = MagicMock()
        results = self.predictor.prepare_for_prediction(executor)
        self.assertEqual(len(results), 0)

    def test_prepare_for_prediction_executor_error(self):
        import datetime
        now = datetime.datetime.now()
        time_key = f"{now.weekday()}_{now.hour}"
        self.predictor._patterns["time_patterns"][time_key] = {"calc.exe": 100}
        executor = MagicMock(side_effect=Exception("fail"))
        results = self.predictor.prepare_for_prediction(executor)
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
