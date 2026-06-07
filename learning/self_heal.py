import ast
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.learning.self_heal")


class SelfHealer:
    def __init__(self, llm_client=None, sandbox=None) -> None:
        self._llm = llm_client
        self._sandbox = sandbox

    def analyze_code(self, file_path: str | Path) -> list[dict[str, Any]]:
        path = Path(file_path)
        if not path.exists():
            return []

        issues = []

        issues.extend(self._run_pylint(path))
        issues.extend(self._run_mypy(path))
        issues.extend(self._run_bandit(path))
        issues.extend(self._static_analysis(path))

        return issues

    def _run_pylint(self, path: Path) -> list[dict[str, Any]]:
        try:
            result = subprocess.run(
                ["pylint", str(path), "--output-format", "json"],
                capture_output=True, text=True, timeout=60
            )
            if result.stdout:
                import json as json_mod
                issues = json_mod.loads(result.stdout)
                return [
                    {"tool": "pylint", "line": i.get("line", 0),
                     "message": i.get("message", ""),
                     "severity": i.get("type", "info"),
                     "symbol": i.get("symbol", "")}
                    for i in issues
                ]
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
        return []

    def _run_mypy(self, path: Path) -> list[dict[str, Any]]:
        try:
            result = subprocess.run(
                ["mypy", str(path), "--no-error-summary"],
                capture_output=True, text=True, timeout=60
            )
            issues = []
            for line in result.stdout.strip().split("\n"):
                if "error:" in line or "warning:" in line:
                    parts = line.split(":")
                    issues.append({
                        "tool": "mypy",
                        "line": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0,
                        "message": line.strip(),
                        "severity": "error" if "error:" in line else "warning"
                    })
            return issues
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

    def _run_bandit(self, path: Path) -> list[dict[str, Any]]:
        try:
            result = subprocess.run(
                ["bandit", "-r", str(path), "-f", "json"],
                capture_output=True, text=True, timeout=60
            )
            if result.stdout:
                import json as json_mod
                data = json_mod.loads(result.stdout)
                return [
                    {"tool": "bandit", "line": r.get("line_number", 0),
                     "message": r.get("issue_text", ""),
                     "severity": r.get("issue_severity", "medium"),
                     "confidence": r.get("issue_confidence", "")}
                    for r in data.get("results", [])
                ]
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
        return []

    def _static_analysis(self, path: Path) -> list[dict[str, Any]]:
        issues = []
        try:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.Try):
                    if not node.handlers:
                        continue
                    for handler in node.handlers:
                        if handler.type is None:
                            issues.append({
                                "tool": "static",
                                "line": node.lineno,
                                "message": "Bare except: use specific exception types",
                                "severity": "warning"
                            })
                elif isinstance(node, ast.FunctionDef):
                    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                        issues.append({
                            "tool": "static",
                            "line": node.lineno,
                            "message": f"Empty function: {node.name}",
                            "severity": "info"
                        })
        except SyntaxError as e:
            issues.append({
                "tool": "static",
                "line": e.lineno or 0,
                "message": f"Syntax error: {e}",
                "severity": "error"
            })
        return issues

    def suggest_fix(self, file_path: str | Path, issues: list[dict[str, Any]]) -> str | None:
        if not issues or not self._llm or not self._llm.ready:
            return None

        path = Path(file_path)
        code = path.read_text(encoding="utf-8")

        issues_text = "\n".join([
            f"  Line {i['line']} [{i['severity']}]: {i['message']}"
            for i in issues[:10]
        ])

        prompt = (
            f"Fix the following issues in this Python code.\n"
            f"Return ONLY the corrected code, no explanations.\n\n"
            f"Issues:\n{issues_text}\n\n"
            f"Code:\n{code}\n\n"
            f"Corrected code:"
        )
        return self._llm.generate(
            prompt, system="You fix Python code bugs.", temperature=0.1
        )

    def test_and_apply(self, file_path: str | Path,
                       test_command: list[str] | None = None) -> dict[str, Any]:
        path = Path(file_path)
        path.read_text(encoding="utf-8")

        backup = path.with_suffix(".py.bak")
        path.rename(backup)

        try:
            issues = self.analyze_code(path)
            if not issues:
                backup.unlink(missing_ok=True)
                return {"status": "clean", "issues": 0}

            fixed = self.suggest_fix(path, issues)
            if not fixed:
                backup.replace(path)
                return {"status": "no_fix", "issues": len(issues)}

            path.write_text(fixed, encoding="utf-8")

            if test_command:
                result = subprocess.run(
                    test_command, capture_output=True, text=True, timeout=60
                )
                if result.returncode != 0:
                    backup.replace(path)
                    return {
                        "status": "tests_failed",
                        "issues": len(issues),
                        "test_output": result.stderr[:500]
                    }

            backup.unlink(missing_ok=True)
            return {
                "status": "applied",
                "issues": len(issues),
                "fixes_applied": len(issues)
            }

        except Exception as e:
            if backup.exists():
                backup.replace(path)
            return {"status": "error", "message": str(e)}
