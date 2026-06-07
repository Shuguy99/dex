import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.multiagent.sandbox")


class AgentSandbox:
    def __init__(self, docker_image: str = "dex-agent-sandbox:latest") -> None:
        self._image = docker_image
        self._has_docker = self._check_docker()

    def _check_docker(self) -> bool:
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @property
    def available(self) -> bool:
        return self._has_docker

    def test_agent_code(self, code: str, test_cases: list[dict[str, Any]],
                        timeout: int = 60) -> dict[str, Any]:
        if not self._has_docker:
            logger.warning("Docker not available, running test locally")
            return self._test_locally(code, test_cases)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            code_path = tmp_path / "agent_code.py"
            code_path.write_text(code, encoding="utf-8")

            manifest = {
                "entry_point": "agent_code.py",
                "test_cases": test_cases
            }
            manifest_path = tmp_path / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            try:
                result = subprocess.run(
                    ["docker", "run", "--rm",
                     "-v", f"{tmpdir}:/workspace",
                     self._image,
                     "python", "/workspace/agent_code.py"],
                    capture_output=True, text=True, timeout=timeout
                )
                success = result.returncode == 0
                report = {
                    "success": success,
                    "stdout": result.stdout[-1000:],
                    "stderr": result.stderr[-1000:],
                    "return_code": result.returncode
                }
            except subprocess.TimeoutExpired:
                report = {
                    "success": False,
                    "error": "Timeout",
                    "stdout": "",
                    "stderr": ""
                }
            except Exception as e:
                report = {
                    "success": False,
                    "error": str(e),
                    "stdout": "",
                    "stderr": ""
                }

        return report

    def _test_locally(self, code: str, test_cases: list[dict[str, Any]]) -> dict[str, Any]:
        results = []
        for case in test_cases:
            try:
                exec_globals = {}
                exec(code, exec_globals)
                input_data = case.get("input", "")
                expected = case.get("expected_output", "")

                if "process" in exec_globals:
                    output = exec_globals["process"](input_data)
                    passed = str(expected).lower() in str(output).lower()
                else:
                    output = None
                    passed = False

                results.append({
                    "input": input_data,
                    "expected": expected,
                    "output": str(output),
                    "passed": passed
                })
            except Exception as e:
                results.append({
                    "input": case.get("input", ""),
                    "expected": case.get("expected_output", ""),
                    "output": f"ERROR: {e}",
                    "passed": False
                })

        passed_count = sum(1 for r in results if r["passed"])
        return {
            "success": passed_count == len(test_cases),
            "passed": passed_count,
            "total": len(test_cases),
            "results": results,
            "accuracy": passed_count / len(test_cases) if test_cases else 1.0
        }
