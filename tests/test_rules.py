import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from learning.rule_engine import RuleEngine


class TestRuleEngine(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.engine = RuleEngine(self.tmpdir, max_per_hour=10)

    def test_add_rule(self):
        rule = {
            "pattern": "удали",
            "condition": "command == 'удали'",
            "expected_action": "request_confirmation",
            "description": "Always confirm deletions"
        }
        result = self.engine.add_rule(rule)
        self.assertTrue(result)
        self.assertEqual(len(self.engine.get_active_rules()), 1)

    def test_rate_limit(self):
        self.engine._max_per_hour = 0
        can, msg = self.engine.can_add_rule()
        self.assertFalse(can)

    def test_get_active_rules(self):
        rule_active = {
            "pattern": "test",
            "expected_action": "pass",
            "description": "active test"
        }
        rule_inactive = {
            "pattern": "test2",
            "expected_action": "pass",
            "description": "inactive test"
        }
        self.engine.add_rule(rule_active)
        self.engine.add_rule(rule_inactive)
        self.engine.mark_harmful(self.engine._rules[-1]["id"])

        active = self.engine.get_active_rules()
        self.assertEqual(len(active), 1)

    def test_evaluate_rule(self):
        rule = {
            "pattern": "привет",
            "expected_action": "greet",
            "description": "Greeting rule"
        }
        self.engine.add_rule(rule)
        rule_id = self.engine._rules[-1]["id"]

        test_cases = [
            {"input": "привет мир", "expected_output": "greet"},
            {"input": "как дела", "expected_output": None},
        ]
        score = self.engine.evaluate_rule(rule_id, test_cases)
        self.assertEqual(score, 1.0)

    def test_rollback(self):
        rule = {"pattern": "bad", "expected_action": "bad", "description": "bad rule"}
        self.engine.add_rule(rule)
        self.engine.rollback_last_rule()
        self.assertEqual(len(self.engine.get_active_rules()), 0)


if __name__ == "__main__":
    unittest.main()
