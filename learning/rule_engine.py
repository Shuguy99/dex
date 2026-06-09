import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.learning.rule_engine")


class RuleEngine:
    def __init__(self, rules_dir: str | Path, max_per_hour: int = 1) -> None:
        self._rules_dir = Path(rules_dir)
        self._rules_dir.mkdir(parents=True, exist_ok=True)
        self._max_per_hour = max_per_hour
        self._rules: list[dict[str, Any]] = []
        self._rule_timestamps: list[float] = []
        self._harmful_rules: set[str] = set()
        self._load_rules()

    def _load_rules(self) -> None:
        path = self._rules_dir / "rules.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                self._rules = data.get("rules", [])
                self._harmful_rules = set(data.get("harmful", []))
            logger.info(f"Loaded {len(self._rules)} rules, {len(self._harmful_rules)} harmful")

    def _save_rules(self) -> None:
        path = self._rules_dir / "rules.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "rules": self._rules,
                "harmful": list(self._harmful_rules)
            }, f, ensure_ascii=False, indent=2)

    def can_add_rule(self) -> tuple[bool, str]:
        now = time.time()
        self._rule_timestamps = [t for t in self._rule_timestamps if now - t < 3600]
        if self._max_per_hour <= 0:
            return False, "Rule addition is disabled (max_per_hour <= 0)"
        if len(self._rule_timestamps) >= self._max_per_hour:
            wait = 3600 - (now - self._rule_timestamps[0])
            return False, f"Rate limit: wait {wait:.0f}s before adding a new rule"
        return True, ""

    def add_rule(self, rule: dict[str, Any]) -> bool:
        can, msg = self.can_add_rule()
        if not can:
            logger.warning(f"Rule rejected: {msg}")
            return False

        rule["id"] = f"rule_{len(self._rules)}_{int(time.time())}"
        rule["created_at"] = datetime.now().isoformat()
        rule["active"] = True
        rule["metrics"] = {"success_count": 0, "fail_count": 0, "test_score": None}

        self._rules.append(rule)
        self._rule_timestamps.append(time.time())
        self._save_rules()
        logger.info(f"Rule added: {rule['id']}")
        return True

    def evaluate_rule(self, rule_id: str, test_cases: list[dict[str, Any]]) -> float:
        rule = self._get_rule(rule_id)
        if not rule:
            return 0.0

        passed = 0
        for case in test_cases:
            if self._test_rule(rule, case):
                passed += 1

        score = passed / len(test_cases) if test_cases else 1.0
        rule["metrics"]["test_score"] = score
        self._save_rules()
        logger.info(f"Rule {rule_id} test score: {score:.2f}")
        return score

    def _test_rule(self, rule: dict[str, Any], case: dict[str, Any]) -> bool:
        pattern = rule.get("pattern", "")
        expected = rule.get("expected_action", "")
        actual = case.get("input", "")

        if re.search(pattern, actual, re.IGNORECASE):
            return case.get("expected_output") == expected
        return True

    def mark_harmful(self, rule_id: str) -> None:
        self._harmful_rules.add(rule_id)
        rule = self._get_rule(rule_id)
        if rule:
            rule["active"] = False
        self._save_rules()
        logger.warning(f"Rule {rule_id} marked as harmful and disabled")

    def get_active_rules(self) -> list[dict[str, Any]]:
        return [r for r in self._rules
                if r["active"] and r["id"] not in self._harmful_rules]

    def rollback_last_rule(self) -> bool:
        if self._rules:
            last = self._rules[-1]
            last["active"] = False
            self._harmful_rules.add(last["id"])
            self._save_rules()
            logger.info(f"Rolled back rule: {last['id']}")
            return True
        return False

    def _get_rule(self, rule_id: str) -> dict[str, Any] | None:
        for r in self._rules:
            if r["id"] == rule_id:
                return r
        return None

    def generate_rule_from_logs(self, log_entries: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not log_entries:
            return None

        failures = [e for e in log_entries if not e.get("success", True)]
        if not failures:
            return None

        common_commands = {}
        for f in failures:
            cmd = f.get("command", "")
            common_commands[cmd] = common_commands.get(cmd, 0) + 1

        worst = max(common_commands, key=common_commands.get)
        if common_commands[worst] < 2:
            return None

        rule = {
            "pattern": re.escape(worst),
            "condition": f"command == '{worst}'",
            "expected_action": "request_clarification",
            "description": f"Auto-generated: clarify '{worst}' due to repeated failures"
        }
        logger.info(f"Generated rule from logs: {rule['description']}")
        return rule
