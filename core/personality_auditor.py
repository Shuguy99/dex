import json
import logging
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("dex.stability.personality_auditor")

DRIFT_METRICS = [
    "avg_response_length",
    "avg_sentence_length",
    "positivity_ratio",
    "command_complexity",
    "refusal_rate",
    "error_rate",
    "helpful_rate",
    "avg_confidence",
]


class PersonalityAuditor:
    def __init__(self, data_dir: str = "data/temporal") -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._history_path = self._data_dir / "personality_drift.json"
        self._history = self._load_history()
        self._current_week: list[dict] = []
        self._last_audit = self._history.get("last_audit", 0)

    def _load_history(self) -> dict:
        if self._history_path.exists():
            try:
                return json.loads(self._history_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"audits": [], "last_audit": 0, "baseline": {}}

    def _save_history(self) -> None:
        self._history["last_audit"] = time.time()
        self._history_path.write_text(json.dumps(self._history, ensure_ascii=False, indent=2), encoding="utf-8")

    def record_interaction(self, command: str, response: str, error: bool = False) -> None:
        self._current_week.append({
            "ts": time.time(),
            "cmd_len": len(command),
            "resp_len": len(response),
            "error": error,
            "cmd_type": self._classify_command(command),
        })

    def _classify_command(self, command: str) -> str:
        cmd = command.strip().lower()
        if any(w in cmd for w in ["статус", "помощь", "время", "дата"]):
            return "info"
        if any(w in cmd for w in ["открой", "закрой", "открыть", "закрыть", "включи", "выключи"]):
            return "action"
        if any(w in cmd for w in ["напиши", "создай", "сгенерируй", "придумай"]):
            return "creative"
        if any(w in cmd for w in ["найди", "поиск", "напомни", "запомни"]):
            return "memory"
        if any(w in cmd for w in ["анализ", "исследуй", "сравни", "оцени"]):
            return "analysis"
        return "other"

    def _compute_metrics(self, interactions: list[dict]) -> dict:
        if not interactions:
            return {m: 0.0 for m in DRIFT_METRICS}
        n = len(interactions)
        return {
            "avg_response_length": sum(i["resp_len"] for i in interactions) / n,
            "avg_sentence_length": sum(i["resp_len"] for i in interactions) / max(n, 1) / 10,
            "positivity_ratio": 0.6,
            "command_complexity": sum(len(i["cmd_type"]) for i in interactions) / n,
            "refusal_rate": sum(1 for i in interactions if i["error"]) / n,
            "error_rate": sum(1 for i in interactions if i["error"]) / n,
            "helpful_rate": 1.0 - sum(1 for i in interactions if i["error"]) / max(n, 1),
            "avg_confidence": 0.8,
            "sample_size": n,
            "period_days": 7,
        }

    def _drift_score(self, current: dict, baseline: dict) -> dict:
        if not baseline:
            return {"score": 0.0, "details": "first audit"}
        deltas = {}
        for metric in DRIFT_METRICS:
            b = baseline.get(metric, 0)
            c = current.get(metric, 0)
            if b > 0:
                deltas[metric] = abs(c - b) / b
            else:
                deltas[metric] = abs(c - b) / max(c, 0.01)
        score = sum(deltas.values()) / max(len(deltas), 1)
        return {"score": round(score, 4), "deltas": deltas}

    def audit(self, force: bool = False) -> dict | None:
        now = time.time()
        if not force and now - self._last_audit < 604800:
            return None
        if len(self._current_week) < 5:
            return None
        metrics = self._compute_metrics(self._current_week)
        baseline = self._history.get("baseline", {})
        drift = self._drift_score(metrics, baseline)
        audit = {
            "ts": now,
            "date": datetime.now().isoformat(),
            "sample_size": metrics.pop("sample_size", 0),
            "period_days": metrics.pop("period_days", 7),
            "metrics": metrics,
            "drift": drift,
            "alert": drift["score"] > 0.3,
        }
        if not baseline:
            self._history["baseline"] = metrics
            audit["note"] = "baseline established"
        self._history["audits"].append(audit)
        self._current_week = []
        self._save_history()
        if audit["alert"]:
            logger.warning(f"Personality drift detected: {drift['score']:.2%}")
        return audit

    def report(self) -> str:
        audits = self._history.get("audits", [])
        if not audits:
            return "No audits yet"
        last = audits[-1]
        drift = last.get("drift", {})
        lines = [
            "=== Personality Audit Report ===",
            f"Date: {last.get('date', '?')}",
            f"Drift score: {drift.get('score', '?'):.2%}",
        ]
        if drift.get("deltas"):
            lines.append("Deltas:")
            for metric, delta in sorted(drift["deltas"].items()):
                lines.append(f"  {metric}: {delta:+.2%}")
        if last.get("alert"):
            lines.append("[ALERT] Significant drift detected")
        return "\n".join(lines)

    def status(self) -> dict:
        return {
            "audits_count": len(self._history.get("audits", [])),
            "last_audit_ts": self._history.get("last_audit", 0),
            "current_sample": len(self._current_week),
            "has_baseline": bool(self._history.get("baseline")),
        }
