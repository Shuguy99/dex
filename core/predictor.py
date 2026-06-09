import json
import logging
import os
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.predictor")


class PersonalPredictor:
    def __init__(self, llm_client=None) -> None:
        self._llm = llm_client
        self._data_dir = Path("data/predictor")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._data_dir / "usage_patterns.json"

        self._launch_log: deque[dict] = deque(maxlen=1000)
        self._file_log: deque[dict] = deque(maxlen=1000)
        self._patterns: dict[str, Any] = self._load_patterns()
        self._last_predictions: list[dict[str, Any]] = []

    def _load_patterns(self) -> dict[str, Any]:
        if self._path.exists():
            try:
                with open(self._path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"app_frequency": {}, "file_frequency": {}, "time_patterns": {}}

    def _save_patterns(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._patterns, f, ensure_ascii=False, indent=2)

    def record_launch(self, app_name: str) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "app": app_name,
            "hour": datetime.now().hour,
            "weekday": datetime.now().weekday()
        }
        self._launch_log.append(entry)

        key = f"{app_name}"
        self._patterns["app_frequency"][key] = \
            self._patterns["app_frequency"].get(key, 0) + 1

        time_key = f"{datetime.now().weekday()}_{datetime.now().hour}"
        if time_key not in self._patterns["time_patterns"]:
            self._patterns["time_patterns"][time_key] = {}
        self._patterns["time_patterns"][time_key][app_name] = \
            self._patterns["time_patterns"][time_key].get(app_name, 0) + 1

        self._save_patterns()

    def record_file_open(self, file_path: str) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "file": file_path,
            "hour": datetime.now().hour
        }
        self._file_log.append(entry)

        ext = os.path.splitext(file_path)[1]
        self._patterns["file_frequency"][ext] = \
            self._patterns["file_frequency"].get(ext, 0) + 1
        self._save_patterns()

    def record_command(self, command_name: str) -> None:
        if "command_frequency" not in self._patterns:
            self._patterns["command_frequency"] = {}
        self._patterns["command_frequency"][command_name] = \
            self._patterns["command_frequency"].get(command_name, 0) + 1

    def analyze_patterns(self) -> None:
        freq = self._patterns.get("command_frequency", {})
        if not freq:
            return
        top = sorted(freq.items(), key=lambda x: -x[1])[:3]
        logger.debug(f"Top commands: {[c for c, _ in top]}")

    def predict_next(self, minutes_ahead: int = 30) -> list[dict[str, Any]]:
        now = datetime.now()
        time_key = f"{now.weekday()}_{now.hour}"

        predictions = []

        time_patterns = self._patterns.get("time_patterns", {}).get(time_key, {})
        sorted_apps = sorted(time_patterns.items(), key=lambda x: -x[1])

        for app, count in sorted_apps[:3]:
            predictions.append({
                "type": "app",
                "name": app,
                "confidence": min(count / 5, 1.0),
                "reason": f"usually used at this time ({count}x recorded)"
            })

        if self._llm and self._llm.ready and len(predictions) >= 2:
            prompt = (
                f"Based on these usage patterns, predict what the user will need "
                f"in the next {minutes_ahead} minutes. Current time: {now.hour}:{now.minute}.\n"
                f"Recent apps: {[p['name'] for p in predictions]}\n"
                f"Respond as JSON list: [{{\"app\": str, \"reason\": str, \"action\": str}}]"
            )
            llm_pred = self._llm.generate_structured(prompt, {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "app": {"type": "string"},
                        "reason": {"type": "string"},
                        "action": {"type": "string"}
                    }
                }
            })
            if llm_pred:
                for p in llm_pred:
                    predictions.append({
                        "type": "app",
                        "name": p.get("app", ""),
                        "confidence": 0.5,
                        "reason": p.get("reason", ""),
                        "action": p.get("action", "launch")
                    })

        self._last_predictions = predictions
        return predictions

    def prepare_for_prediction(self, executor) -> list[str]:
        predictions = self.predict_next()
        results = []
        for pred in predictions:
            if pred.get("confidence", 0) > 0.7:
                action = pred.get("action", "launch")
                if action == "launch":
                    try:
                        executor("launch_app", {"name": pred["name"]})
                        results.append(f"Prepared: {pred['name']}")
                    except Exception as e:
                        logger.debug(f"Prep failed: {e}")
        return results

    def simulate_consequence(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        sim_path = self._data_dir / "simulations"
        sim_path.mkdir(exist_ok=True)

        risks = []
        if action in ("delete_file", "remove", "del"):
            target = params.get("path", params.get("name", ""))
            if any(p in target.lower() for p in ["system32", "windows", "boot"]):
                risks.append("CRITICAL: System file — may break OS")
            elif any(p in target.lower() for p in ["project", "documents", "work"]):
                risks.append("HIGH: Project file — may lose work")
            else:
                risks.append("LOW: Non-critical file")

        elif action in ("run_command", "shell"):
            cmd = params.get("cmd", "")
            if any(p in cmd for p in ["rm -rf", "format", "del /f", "rd /s"]):
                risks.append("CRITICAL: Destructive command")
            elif any(p in cmd for p in ["pip uninstall", "npm uninstall"]):
                risks.append("MEDIUM: May remove dependencies")

        if self._llm and self._llm.ready:
            prompt = (
                f"Simulate the consequences of: {action}({json.dumps(params, ensure_ascii=False)})\n"
                f"List potential risks and suggest safer alternatives. Be concise."
            )
            llm_analysis = self._llm.generate(prompt, temperature=0.2)
            if llm_analysis:
                risks.append(f"LLM analysis: {llm_analysis[:300]}")

        report = {
            "action": action,
            "params": params,
            "risks": risks,
            "safe": len([r for r in risks if "CRITICAL" in r or "HIGH" in r]) == 0,
            "timestamp": datetime.now().isoformat()
        }

        safe_name = "".join(c if c.isalnum() else "_" for c in action)
        with open(sim_path / f"sim_{safe_name}_{int(time.time())}.json", "w") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return report

    def get_pattern_summary(self) -> str:
        apps = self._patterns.get("app_frequency", {})
        files = self._patterns.get("file_frequency", {})
        top_apps = sorted(apps.items(), key=lambda x: -x[1])[:5]
        top_exts = sorted(files.items(), key=lambda x: -x[1])[:5]

        lines = ["── Паттерны использования ──"]
        lines.append("Чаще всего запускаете:")
        for app, count in top_apps:
            lines.append(f"  {app}: {count} раз")
        lines.append("Чаще всего открываете файлы:")
        for ext, count in top_exts:
            lines.append(f"  {ext}: {count} раз")
        lines.append(f"Записей в логах: {len(self._launch_log) + len(self._file_log)}")
        return "\n".join(lines)
