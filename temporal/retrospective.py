import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.temporal.retrospective")


class RetrospectiveAnalyzer:
    def __init__(self, llm_client=None, feedback_collector=None,
                 autobiographical_memory=None) -> None:
        self._llm = llm_client
        self._feedback = feedback_collector
        self._autobio = autobiographical_memory
        self._data_dir = Path("data/temporal")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._reports_path = self._data_dir / "retrospectives.json"
        self._reports: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if self._reports_path.exists():
            try:
                with open(self._reports_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save(self):
        with open(self._reports_path, "w", encoding="utf-8") as f:
            json.dump(self._reports[-50:], f, ensure_ascii=False, indent=2)

    def generate_monthly_report(self) -> dict[str, Any]:
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 1:
            last_month_start = month_start.replace(year=month_start.year - 1, month=12)
        else:
            last_month_start = month_start.replace(month=month_start.month - 1)

        stats = self._compute_stats(last_month_start, now)
        narrative = self._build_narrative(stats)

        report = {
            "period": f"{last_month_start.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}",
            "generated": now.isoformat(),
            "stats": stats,
            "narrative": narrative,
            "promises_kept": stats.get("promises_kept", 0),
            "patterns_changed": stats.get("new_patterns", [])
        }
        self._reports.append(report)
        self._save()
        return report

    def _compute_stats(self, since: datetime, to: datetime) -> dict[str, Any]:
        stats = {
            "total_interactions": 0,
            "avg_feedback": 0.0,
            "top_commands": [],
            "emotion_trend": {},
            "productivity_score": 0.0,
            "promises_kept": 0,
            "new_patterns": []
        }

        if self._autobio:
            memories = self._autobio._memories if hasattr(self._autobio, '_memories') else []
            period_memories = [
                m for m in memories
                if datetime.fromisoformat(m["timestamp"]) > since
            ]
            stats["total_interactions"] = len(period_memories)

            emotions = defaultdict(int)
            for m in period_memories:
                emotions[m.get("emotion", {}).get("primary", "neutral")] += 1
            stats["emotion_trend"] = dict(emotions)

            if period_memories:
                positive = emotions.get("positive", 0)
                stats["productivity_score"] = min(1.0, positive / max(len(period_memories), 1) * 2)

        if self._feedback:
            try:
                fb_stats = self._feedback.get_stats(30)
                stats["avg_feedback"] = fb_stats.get("avg", 0.0)
            except Exception:
                pass

        return stats

    def _build_narrative(self, stats: dict) -> str:
        if self._llm:
            prompt = (
                f"Monthly retrospective data:\n"
                f"Interactions: {stats.get('total_interactions')}\n"
                f"Avg feedback: {stats.get('avg_feedback')}\n"
                f"Emotions: {json.dumps(stats.get('emotion_trend', {}), ensure_ascii=False)}\n"
                f"Productivity: {stats.get('productivity_score')}\n\n"
                f"Generate a personal growth narrative in Russian (3-5 sentences). "
                f"Highlight changes in thinking patterns and personal development."
            )
            narrative = self._llm.generate(prompt, temperature=0.6)
            if narrative:
                return narrative

        interactions = stats.get("total_interactions", 0)
        avg = stats.get("avg_feedback", 0)
        return (
            f"За период было {interactions} взаимодействий. "
            f"Средняя оценка: {avg:.1f}/5. "
            f"Продолжайте расти!"
        )

    def compare_with_year_ago(self) -> dict[str, Any]:
        now = datetime.now()
        year_ago_start = now.replace(year=now.year - 1) - timedelta(days=30)
        year_ago_end = now.replace(year=now.year - 1)

        current_stats = self._compute_stats(now - timedelta(days=30), now)
        past_stats = self._compute_stats(year_ago_start, year_ago_end)

        comparison = {
            "current_period": "last 30 days",
            "past_period": f"{year_ago_start.strftime('%Y-%m-%d')} to {year_ago_end.strftime('%Y-%m-%d')}",
            "current": current_stats,
            "past": past_stats,
            "interaction_change": current_stats.get("total_interactions", 0) -
                                  past_stats.get("total_interactions", 0),
            "feedback_change": current_stats.get("avg_feedback", 0) -
                               past_stats.get("avg_feedback", 0)
        }

        if self._llm:
            prompt = (
                f"Year-over-year comparison:\n"
                f"Current: {json.dumps(current_stats, ensure_ascii=False)}\n"
                f"Past: {json.dumps(past_stats, ensure_ascii=False)}\n\n"
                f"Write a brief analysis of how the user has changed. "
                f"2-3 sentences in Russian."
            )
            narrative = self._llm.generate(prompt, temperature=0.5)
            if narrative:
                comparison["narrative"] = narrative

        return comparison

    def get_retro_summary(self) -> str:
        lines = ["── Retrospective Analysis ──"]
        if not self._reports:
            lines.append("  No reports yet. Generate one when enough data exists.")
            return "\n".join(lines)
        last = self._reports[-1]
        lines.append(f"  Last report: {last.get('period', '?')}")
        lines.append(f"  Interactions: {last.get('stats', {}).get('total_interactions', 0)}")
        lines.append(f"  Avg feedback: {last.get('stats', {}).get('avg_feedback', 0):.1f}/5")
        lines.append(f"  Productivity: {last.get('stats', {}).get('productivity_score', 0):.0%}")
        if last.get("narrative"):
            lines.append(f"\n  {last['narrative'][:200]}")
        return "\n".join(lines)
