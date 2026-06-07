import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.learning.ab_testing")


class ABTester:
    def __init__(self, backup_dir: str | Path) -> None:
        self._backup_dir = Path(backup_dir)
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def run_ab_test(self, test_cases: list[dict[str, Any]],
                    old_model, new_model) -> dict[str, Any]:
        logger.info(f"Running A/B test with {len(test_cases)} cases")

        old_scores = []
        new_scores = []

        for _i, case in enumerate(test_cases):
            old_result = old_model.predict(case["input"])
            new_result = new_model.predict(case["input"])

            expected = case.get("expected_output", "")
            old_ok = self._compare(old_result, expected)
            new_ok = self._compare(new_result, expected)

            old_scores.append(1 if old_ok else 0)
            new_scores.append(1 if new_ok else 0)

        old_accuracy = sum(old_scores) / len(old_scores) if old_scores else 0
        new_accuracy = sum(new_scores) / len(new_scores) if new_scores else 0

        report = {
            "timestamp": datetime.now().isoformat(),
            "test_cases": len(test_cases),
            "old_accuracy": old_accuracy,
            "new_accuracy": new_accuracy,
            "delta": new_accuracy - old_accuracy,
            "passed": (new_accuracy - old_accuracy) >= -0.05,
            "degraded": (new_accuracy - old_accuracy) < -0.05
        }

        report_path = self._backup_dir / f"ab_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"A/B test result: old={old_accuracy:.2f}, new={new_accuracy:.2f}, "
                    f"delta={report['delta']:.2f}, passed={report['passed']}")
        return report

    def _compare(self, result: Any, expected: Any) -> bool:
        if isinstance(expected, str) and isinstance(result, str):
            return expected.lower().strip() in result.lower().strip()
        return result == expected
