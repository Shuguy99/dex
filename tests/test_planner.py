import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.planner import Plan, Step, TaskPlanner


class TestStep(unittest.TestCase):
    def test_init_defaults(self):
        s = Step("open_file")
        self.assertEqual(s.action, "open_file")
        self.assertEqual(s.params, {})
        self.assertEqual(s.description, "")
        self.assertEqual(s.depends_on, [])
        self.assertEqual(s.status, "pending")
        self.assertIsNone(s.result)
        self.assertIsNone(s.error)
        self.assertEqual(s.duration_ms, 0)

    def test_init_with_params(self):
        s = Step("launch_app", {"name": "calc"}, "Open calc", depends_on=[0, 1])
        self.assertEqual(s.action, "launch_app")
        self.assertEqual(s.params, {"name": "calc"})
        self.assertEqual(s.description, "Open calc")
        self.assertEqual(s.depends_on, [0, 1])

    def test_to_dict(self):
        s = Step("write_file", {"name": "test.txt"}, "Write file", depends_on=[0])
        s.status = "completed"
        s.result = "done"
        s.duration_ms = 100.5
        d = s.to_dict()
        self.assertEqual(d["action"], "write_file")
        self.assertEqual(d["params"], {"name": "test.txt"})
        self.assertEqual(d["status"], "completed")
        self.assertIn("done", d["result"])
        self.assertEqual(d["duration_ms"], 100.5)

    def test_to_dict_no_result(self):
        s = Step("search_memory")
        d = s.to_dict()
        self.assertIsNone(d["result"])


class TestPlan(unittest.TestCase):
    def test_init(self):
        steps = [Step("a"), Step("b")]
        plan = Plan("test goal", steps)
        self.assertEqual(plan.goal, "test goal")
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(plan.status, "created")
        self.assertIsNotNone(plan.created_at)
        self.assertIsNone(plan.completed_at)

    def test_to_dict(self):
        steps = [Step("open_file", description="Open")]
        plan = Plan("goal", steps)
        d = plan.to_dict()
        self.assertEqual(d["goal"], "goal")
        self.assertEqual(d["status"], "created")
        self.assertEqual(len(d["steps"]), 1)
        self.assertEqual(d["steps"][0]["action"], "open_file")


class TestTaskPlanner(unittest.TestCase):
    def setUp(self):
        self.planner = TaskPlanner()

    def test_create_plan_rule_based_web(self):
        plan = self.planner.create_plan("создать веб проект")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.status, "created")
        self.assertEqual(len(plan.steps), 4)
        self.assertEqual(plan.steps[0].action, "create_folder")
        self.assertIn("project", str(plan.steps[0].params["name"]))

    def test_create_plan_rule_based_doc(self):
        plan = self.planner.create_plan("создать документацию")
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(plan.steps[0].action, "create_folder")
        self.assertEqual(plan.steps[1].action, "write_file")

    def test_create_plan_rule_based_fallback(self):
        plan = self.planner.create_plan("random unknown task")
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(plan.steps[0].action, "search_memory")
        self.assertEqual(plan.steps[1].action, "send_notification")

    def test_create_plan_with_llm_ready(self):
        mock_llm = MagicMock()
        mock_llm.ready = True
        mock_llm.generate_structured.return_value = {
            "steps": [
                {"action": "open_file", "params": {"path": "/tmp"}, "description": "Open", "depends_on": []},
            ]
        }
        planner = TaskPlanner(llm_client=mock_llm)
        plan = planner.create_plan("open file")
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].action, "open_file")
        mock_llm.generate_structured.assert_called_once()

    def test_create_plan_with_llm_returns_none(self):
        mock_llm = MagicMock()
        mock_llm.ready = True
        mock_llm.generate_structured.return_value = None
        planner = TaskPlanner(llm_client=mock_llm)
        plan = planner.create_plan("do something")
        self.assertIsNone(plan)

    def test_execute_plan_success(self):
        step = Step("open_file", description="Open file")
        plan = Plan("test", [step])
        executor = MagicMock(return_value="success")
        result = self.planner.execute_plan(plan, executor=executor)
        self.assertEqual(result.status, "completed")
        self.assertEqual(step.status, "completed")
        self.assertEqual(step.result, "success")
        self.assertGreaterEqual(step.duration_ms, 0)

    def test_execute_plan_failure(self):
        step = Step("open_file", description="Open file")
        plan = Plan("test", [step])
        executor = MagicMock(side_effect=Exception("fail"))
        result = self.planner.execute_plan(plan, executor=executor)
        self.assertEqual(result.status, "partial")
        self.assertEqual(step.status, "failed")
        self.assertEqual(step.error, "fail")

    def test_execute_plan_blocked_deps(self):
        step0 = Step("first", description="First")
        step1 = Step("second", description="Second", depends_on=[0])
        plan = Plan("test", [step0, step1])
        executor = MagicMock(return_value="ok")
        result = self.planner.execute_plan(plan, executor=executor)
        self.assertEqual(step0.status, "completed")
        self.assertEqual(step1.status, "completed")
        self.assertEqual(result.status, "completed")

    def test_execute_plan_blocked_deps_not_met(self):
        step1 = Step("second", description="Second", depends_on=[0])
        plan = Plan("test", [step1])
        executor = MagicMock(return_value="ok")
        result = self.planner.execute_plan(plan, executor=executor)
        self.assertEqual(step1.status, "blocked")
        self.assertEqual(step1.error, "Dependencies not met")
        self.assertEqual(result.status, "partial")

    def test_execute_plan_skip_completed(self):
        step = Step("done_step", description="Already done")
        step.status = "completed"
        plan = Plan("test", [step])
        executor = MagicMock()
        self.planner.execute_plan(plan, executor=executor)
        executor.assert_not_called()

    def test_execute_plan_no_executor(self):
        step = Step("test", description="Test")
        plan = Plan("test", [step])
        result = self.planner.execute_plan(plan, executor=None)
        self.assertEqual(result.status, "failed")

    def test_get_plan_empty(self):
        self.assertIsNone(self.planner.get_plan())
        self.assertIsNone(self.planner.get_plan(0))

    def test_get_plan_with_plan(self):
        plan = self.planner.create_plan("hello")
        self.assertIs(self.planner.get_plan(), plan)
        self.assertIs(self.planner.get_plan(0), plan)

    def test_summarize_plan(self):
        plan = self.planner.create_plan("тест")
        summary = self.planner.summarize_plan(plan)
        self.assertIn("тест", summary)
        self.assertIn("Статус", summary)
        self.assertIn("○", summary)

    def test_summarize_plan_with_error(self):
        step = Step("fail", description="Failing step")
        step.status = "failed"
        step.error = "something broke"
        plan = Plan("test", [step])
        summary = self.planner.summarize_plan(plan)
        self.assertIn("something broke", summary)
        self.assertIn("✗", summary)


if __name__ == "__main__":
    unittest.main()
