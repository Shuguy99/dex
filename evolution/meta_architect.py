import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.evolution.architect")


class MetaArchitect:
    def __init__(self, llm_client=None) -> None:
        self._llm = llm_client
        self._data_dir = Path("data/evolution")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._data_dir / "architecture_proposals.json"
        self._proposals: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if self._path.exists():
            try:
                with open(self._path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._proposals[-50:], f, ensure_ascii=False, indent=2)

    TOPOLOGIES = {
        "flat": {"agents": 3, "latency": "low", "scalability": "medium"},
        "layered": {"agents": 5, "latency": "medium", "scalability": "high"},
        "mesh": {"agents": 7, "latency": "high", "scalability": "very_high"},
        "hub": {"agents": 4, "latency": "low", "scalability": "medium"}
    }

    def analyze_bottlenecks(self, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
        metrics = metrics or {}
        bottlenecks = []

        agent_latencies = metrics.get("agent_latencies", {})
        for agent, lat in agent_latencies.items():
            if isinstance(lat, (int, float)) and lat > 500:
                bottlenecks.append({
                    "type": "latency",
                    "agent": agent,
                    "value": lat,
                    "severity": "high" if lat > 1000 else "medium"
                })

        error_rates = metrics.get("error_rates", {})
        for agent, rate in error_rates.items():
            if isinstance(rate, (int, float)) and rate > 0.2:
                bottlenecks.append({
                    "type": "error_rate",
                    "agent": agent,
                    "value": rate,
                    "severity": "high" if rate > 0.5 else "medium"
                })

        inter_agent_comm = metrics.get("communication_delays", {})
        for pair, delay in inter_agent_comm.items():
            if isinstance(delay, (int, float)) and delay > 300:
                bottlenecks.append({
                    "type": "communication_delay",
                    "agents": pair,
                    "value": delay,
                    "severity": "medium"
                })

        return {
            "bottlenecks": bottlenecks,
            "total_bottlenecks": len(bottlenecks),
            "topology_recommendation": self._recommend_topology(bottlenecks)
        }

    def _recommend_topology(self, bottlenecks: list[dict]) -> str:
        high_severity = sum(1 for b in bottlenecks if b.get("severity") == "high")
        if high_severity > 3:
            return "mesh"
        elif high_severity > 1:
            return "layered"
        return "flat"

    def propose_architecture_change(self, current_topology: str = "flat",
                                     metrics: dict[str, Any] | None = None) -> dict[str, Any]:
        analysis = self.analyze_bottlenecks(metrics)
        recommended = analysis.get("topology_recommendation", current_topology)

        if self._llm:
            prompt = (
                f"Current topology: {current_topology}\n"
                f"Bottlenecks: {json.dumps(analysis['bottlenecks'][:5], ensure_ascii=False)}\n"
                f"Recommended: {recommended}\n\n"
                f"Propose a specific architecture change as JSON:\n"
                f"{{\"title\": str, \"description\": str, "
                f"\"new_topology\": str, \"benefits\": [str], "
                f"\"risks\": [str], \"estimated_improvement\": float (0-1), "
                f"\"changes\": [{{\"action\": str, \"target\": str}}]}}"
            )
            proposal = self._llm.generate_structured(prompt, {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "new_topology": {"type": "string"},
                    "benefits": {"type": "array", "items": {"type": "string"}},
                    "risks": {"type": "array", "items": {"type": "string"}},
                    "estimated_improvement": {"type": "number"},
                    "changes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string"},
                                "target": {"type": "string"}
                            }
                        }
                    }
                }
            })
            if proposal:
                proposal["id"] = f"arch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                proposal["status"] = "proposed"
                proposal["created"] = datetime.now().isoformat()
                self._proposals.append(proposal)
                self._save()
                return {"success": True, "analysis": analysis, "proposal": proposal}

        return {"success": False, "analysis": analysis, "reason": "LLM unavailable"}

    def get_arch_summary(self) -> str:
        lines = ["── Meta-Architect ──"]
        lines.append(f"Proposals: {len(self._proposals)}")
        for p in self._proposals[-5:]:
            icon = {"applied": "✓", "proposed": "⏳", "rejected": "✗"}
            lines.append(f"  {icon.get(p.get('status', ''), '?')} {p.get('title', '')[:60]}")
            lines.append(f"     → {p.get('new_topology', '?')} (Δ{p.get('estimated_improvement', 0)})")
        return "\n".join(lines)
