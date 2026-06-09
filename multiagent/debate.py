import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.multiagent.debate")

DEBATER_PROMPTS = {
    "conservative": (
        "You are a CONSERVATIVE agent. You prioritize stability, safety, and proven approaches. "
        "Argue AGAINST risky or untested changes. Point out potential failures, edge cases, and costs."
    ),
    "innovator": (
        "You are an INNOVATOR agent. You prioritize progress, new approaches, and ambitious solutions. "
        "Argue FOR bold changes and improvements. Point out opportunities and future benefits."
    ),
    "critic": (
        "You are a CRITIC agent. Your ONLY job is to find flaws, vulnerabilities, and weaknesses "
        "in any proposed solution. Be thorough, skeptical, and specific. "
        "Every solution has a vulnerability — find it."
    ),
    "pragmatist": (
        "You are a PRAGMATIST agent. You focus on feasibility, resources, and real-world constraints. "
        "Evaluate proposals based on practicality: time, effort, existing tools, and ROI. "
        "Reject what's impractical, endorse what works."
    )
}


class AgentDebate:
    def __init__(self, llm_client=None) -> None:
        self._llm = llm_client
        self._debate_log: list[dict[str, Any]] = []

    def debate(self, topic: str,
               participants: list[str] | None = None,
               rounds: int = 3) -> dict[str, Any]:
        if participants is None:
            participants = ["conservative", "innovator"]

        if not self._llm or not self._llm.ready:
            return self._simulate_debate(topic, participants, rounds)

        logger.info(f"Debate started: {topic} ({participants}) {rounds} rounds")
        statements = {p: [] for p in participants}
        history = []

        for rnd in range(rounds):
            for speaker in participants:
                prompt_parts = [DEBATER_PROMPTS[speaker]]
                prompt_parts.append(f"\nDebate topic: {topic}")

                if history:
                    prompt_parts.append("\nPrevious arguments:")
                    for h in history[-4:]:
                        prompt_parts.append(f"  {h['speaker']}: {h['argument'][:200]}")

                prompt_parts.append("\n\nPresent your argument concisely (2-3 sentences):")
                full_prompt = "\n".join(prompt_parts)

                argument = self._llm.generate(
                    full_prompt,
                    temperature=0.7 + random.uniform(-0.1, 0.1)
                )

                entry = {"speaker": speaker, "argument": argument, "round": rnd}
                history.append(entry)
                statements[speaker].append(argument)
                logger.debug(f"Debate round {rnd}, {speaker}: {argument[:100]}...")

        synthesis = self._synthesize(topic, history)
        result = {
            "topic": topic,
            "rounds": rounds,
            "participants": participants,
            "statements": statements,
            "history": history,
            "synthesis": synthesis,
            "timestamp": datetime.now().isoformat()
        }

        self._debate_log.append(result)
        self._save_debate(result)
        return result

    def _simulate_debate(self, topic: str, participants: list[str],
                         rounds: int) -> dict[str, Any]:
        history = []
        statements = {p: [] for p in participants}
        stances = {"conservative": "Против", "innovator": "За",
                    "critic": "Критикует", "pragmatist": "Оценивает"}

        for rnd in range(rounds):
            for speaker in participants:
                arg = f"[{stances.get(speaker, '?')}] Аргумент {rnd+1} по теме «{topic}»: "
                if speaker == "conservative":
                    arg += "Нужно быть осторожнее, проверить стабильность."
                elif speaker == "innovator":
                    arg += "Пора двигаться вперёд, использовать новые технологии."
                elif speaker == "critic":
                    arg += "Уязвимость: недостаточное тестирование."
                else:
                    arg += "Оценим ресурсы и сроки."

                entry = {"speaker": speaker, "argument": arg, "round": rnd}
                history.append(entry)
                statements[speaker].append(arg)

        return {
            "topic": topic,
            "rounds": rounds,
            "participants": participants,
            "statements": statements,
            "history": history,
            "synthesis": self._simple_synthesis(topic, history),
            "timestamp": datetime.now().isoformat()
        }

    def _synthesize(self, topic: str, history: list[dict[str, Any]]) -> str:
        if not self._llm or not self._llm.ready:
            return self._simple_synthesis(topic, history)

        transcript = "\n".join([
            f"{h['speaker']}: {h['argument']}" for h in history
        ])
        prompt = (
            f"Act as a debate moderator. Synthesize the following debate on '{topic}'.\n"
            f"Identify: key agreements, key disagreements, the strongest arguments, "
            f"and a balanced conclusion.\n\n"
            f"DEBATE:\n{transcript}\n\n"
            f"SYNTHESIS (in Russian, 3-5 paragraphs):"
        )
        return self._llm.generate(prompt, temperature=0.3)

    def _simple_synthesis(self, topic: str, history: list[dict[str, Any]]) -> str:
        lines = [f"По итогам дебатов по теме «{topic}»:", ""]
        for h in history:
            lines.append(f"  {h['speaker']}: {h['argument'][:200]}")
        return "\n".join(lines)

    def _save_debate(self, result: dict[str, Any]) -> None:
        path = Path("data/debates")
        path.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in result["topic"][:20])
        file_path = path / f"debate_{safe}_{int(time.time())}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    def get_critic_review(self, proposal: str) -> dict[str, Any]:
        if not self._llm or not self._llm.ready:
            return {"proposal": proposal, "flaws": ["LLM not available for review"],
                    "verdict": "unreviewed"}

        prompt = (
            f"{DEBATER_PROMPTS['critic']}\n\n"
            f"Proposal to critique: {proposal}\n\n"
            f"List specific vulnerabilities, risks, and weaknesses. "
            f"Respond as JSON:\n"
            f"{{\"flaws\": [str], \"severity\": \"low\"|\"medium\"|\"high\"|\"critical\", "
            f"\"verdict\": \"approved\"|\"rejected\"|\"needs_changes\"}}"
        )
        result = self._llm.generate_structured(prompt, {
            "type": "object",
            "properties": {
                "flaws": {"type": "array", "items": {"type": "string"}},
                "severity": {"type": "string"},
                "verdict": {"type": "string"}
            }
        })
        return result or {"proposal": proposal, "flaws": [], "verdict": "unreviewed"}

    def get_recent_debates(self, n: int = 5) -> list[dict[str, Any]]:
        return self._debate_log[-n:]
