import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.generative.self_expander")


IMPROVEMENT_DOMAINS = [
    {
        "name": "orchestrator",
        "path_hint": "multiagent/orchestrator.py",
        "description": "Multi-agent orchestrator improvements"
    },
    {
        "name": "memory",
        "path_hint": "memory/vector_store.py",
        "description": "Vector memory optimizations"
    },
    {
        "name": "tts",
        "path_hint": "voice.py",
        "description": "TTS engine replacement or enhancement"
    },
    {
        "name": "rag",
        "path_hint": "rag/engine.py",
        "description": "RAG retrieval improvements"
    }
]


class SelfExpander:
    def __init__(self, llm_client=None, git_repo_path: str | None = None) -> None:
        self._llm = llm_client
        self._repo_path = git_repo_path or os.getcwd()
        self._data_dir = Path("data/self_expansion")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._proposals_path = self._data_dir / "proposals.json"
        self._proposals: list[dict[str, Any]] = self._load_proposals()

    def _load_proposals(self) -> list[dict[str, Any]]:
        if self._proposals_path.exists():
            try:
                with open(self._proposals_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_proposals(self) -> None:
        with open(self._proposals_path, "w", encoding="utf-8") as f:
            json.dump(self._proposals[-100:], f, ensure_ascii=False, indent=2)

    def propose_improvement(self, domain: str | None = None) -> dict[str, Any]:
        if not self._llm:
            return {"success": False, "reason": "LLM not available"}

        if domain is None:
            domain_info = IMPROVEMENT_DOMAINS[int(time.time()) % len(IMPROVEMENT_DOMAINS)]
        else:
            matches = [d for d in IMPROVEMENT_DOMAINS if d["name"] == domain]
            domain_info = matches[0] if matches else IMPROVEMENT_DOMAINS[0]

        current_code = ""
        path = Path(self._repo_path) / domain_info["path_hint"]
        if path.exists():
            current_code = path.read_text(encoding="utf-8")[:2000]

        prompt = (
            f"Analyze this module and propose a specific, implementable improvement:\n"
            f"Module: {domain_info['name']} ({domain_info['description']})\n\n"
            f"Current code (excerpt):\n{current_code or '(new module)'}\n\n"
            f"Respond as JSON with:\n"
            f"{{'title': str, 'description': str, 'benefits': [str], "
            f"'complexity': 'low'/'medium'/'high', "
            f"'code_snippet': str (the actual code change or new code), "
            f"'file_path': str (relative path to create/modify), "
            f"'risks': [str]}}"
        )
        proposal = self._llm.generate_structured(prompt, {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "benefits": {"type": "array", "items": {"type": "string"}},
                "complexity": {"type": "string", "enum": ["low", "medium", "high"]},
                "code_snippet": {"type": "string"},
                "file_path": {"type": "string"},
                "risks": {"type": "array", "items": {"type": "string"}}
            }
        })
        if not proposal:
            return {"success": False, "reason": "Failed to generate proposal"}

        proposal["id"] = f"prop_{int(time.time())}"
        proposal["domain"] = domain_info["name"]
        proposal["status"] = "pending"
        proposal["created"] = datetime.now().isoformat()
        self._proposals.append(proposal)
        self._save_proposals()
        return {"success": True, "proposal": proposal}

    def apply_proposal(self, proposal_id: str, dry_run: bool = True) -> dict[str, Any]:
        proposal = next((p for p in self._proposals if p.get("id") == proposal_id), None)
        if not proposal:
            return {"success": False, "reason": "Proposal not found"}

        file_path = Path(self._repo_path) / proposal["file_path"]
        code = proposal.get("code_snippet", "")

        if not code:
            return {"success": False, "reason": "No code in proposal"}

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "file_path": str(file_path),
                "code_preview": code[:500],
                "message": "Dry-run: file would be created/modified"
            }

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(code, encoding="utf-8")
            proposal["status"] = "applied"
            proposal["applied"] = datetime.now().isoformat()
            self._save_proposals()

            if self._is_git_repo():
                self._git_commit(proposal)

            return {
                "success": True,
                "dry_run": False,
                "file_path": str(file_path),
                "message": f"Proposal applied to {file_path}"
            }
        except Exception as e:
            logger.exception("Failed to apply proposal")
            return {"success": False, "reason": str(e)}

    def _is_git_repo(self) -> bool:
        git_dir = Path(self._repo_path) / ".git"
        return git_dir.is_dir()

    def _git_commit(self, proposal: dict) -> bool:
        try:
            subprocess.run(
                ["git", "add", proposal["file_path"]],
                cwd=self._repo_path, capture_output=True, timeout=10
            )
            subprocess.run(
                ["git", "commit", "-m",
                 f"auto: {proposal.get('title', 'self-expansion')}"],
                cwd=self._repo_path, capture_output=True, timeout=10
            )
        except Exception as e:
            logger.warning(f"Git commit failed: {e}")

    def get_proposals_summary(self) -> str:
        if not self._proposals:
            return "Нет предложений по улучшению."

        lines = ["── Self-Expansion Proposals ──"]
        for p in self._proposals[-10:]:
            status_icon = {"pending": "⏳", "applied": "✓", "rejected": "✗"}
            icon = status_icon.get(p.get("status", ""), "?")
            complexity_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}
            comp = complexity_icon.get(p.get("complexity", ""), "⚪")
            lines.append(f"  {icon} {comp} {p.get('id', '?')[:12]}: {p.get('title', '')[:60]}")
            lines.append(f"     {p.get('description', '')[:100]}")
        return "\n".join(lines)
