import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["DEX_SKIP_LLM"] = "1"
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.model_evaluator import ModelEvaluator


class FakeEvalLLM:
    ready = True

    def generate(self, prompt, model=None, **kwargs):
        return "Вот ответ на ваш вопрос. Надеюсь, это поможет."


class TestModelEvaluator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.evaluator = ModelEvaluator(data_dir=self.tmp)
        self.llm = FakeEvalLLM()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_initial_state(self):
        self.assertEqual(self.evaluator.history(), [])

    def test_evaluate_model(self):
        result = self.evaluator.evaluate_model("test-model", self.llm, purposes=["chat"])
        self.assertEqual(result["model"], "test-model")
        self.assertIn("chat", result["purposes"])
        self.assertGreaterEqual(result["overall_score"], 0)
        self.assertGreater(result["overall_score_pct"], 0)

    def test_evaluate_model_saves_history(self):
        self.evaluator.evaluate_model("m1", self.llm, purposes=["chat"])
        self.evaluator.evaluate_model("m2", self.llm, purposes=["chat"])
        self.assertEqual(len(self.evaluator.history()), 2)

    def test_get_best_model(self):
        self.evaluator.evaluate_model("slow-model", self.llm, purposes=["chat"])
        best = self.evaluator.get_best_model("chat")
        self.assertEqual(best, "slow-model")

    def test_model_summary(self):
        self.evaluator.evaluate_model("test-model", self.llm, purposes=["chat"])
        summary = self.evaluator.model_summary("test-model")
        self.assertIsNotNone(summary)
        self.assertEqual(summary["model"], "test-model")

    def test_clear(self):
        self.evaluator.evaluate_model("m1", self.llm, purposes=["chat"])
        self.evaluator.clear()
        self.assertEqual(self.evaluator.history(), [])

    def test_score_response(self):
        score_good = self.evaluator._score_response("q", "Вот развёрнутый ответ. Надеюсь, это полезно.")
        self.assertGreater(score_good, 0.5)
        score_bad = self.evaluator._score_response("q", "не знаю")
        self.assertLess(score_bad, 0.5)


if __name__ == "__main__":
    unittest.main()
