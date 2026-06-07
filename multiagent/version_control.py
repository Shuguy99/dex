import contextlib
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.multiagent.version_control")


class AgentVersionControl:
    def __init__(self, agents_dir: str | Path) -> None:
        self._agents_dir = Path(agents_dir)
        self._agents_dir.mkdir(parents=True, exist_ok=True)

    def init_repo(self, agent_id: str) -> bool:
        agent_path = self._agents_dir / agent_id
        agent_path.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["git", "init"],
                cwd=agent_path,
                capture_output=True, text=True, check=True, timeout=30
            )
            subprocess.run(
                ["git", "config", "user.name", "Dex Agent System"],
                cwd=agent_path,
                capture_output=True, check=True, timeout=30
            )
            subprocess.run(
                ["git", "config", "user.email", "dex@local"],
                cwd=agent_path,
                capture_output=True, check=True, timeout=30
            )
            logger.info(f"Git repo initialized for agent {agent_id}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(f"Git not available for agent {agent_id}: {e}")
            return False

    def create_branch(self, agent_id: str, branch_name: str) -> bool:
        agent_path = self._agents_dir / agent_id
        if not (agent_path / ".git").exists():
            self.init_repo(agent_id)
        try:
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=agent_path,
                capture_output=True, check=True, timeout=30
            )
            logger.info(f"Branch '{branch_name}' created for {agent_id}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Branch creation failed: {e}")
            return False

    def commit_change(self, agent_id: str, message: str,
                      files: list[str] | None = None) -> bool:
        agent_path = self._agents_dir / agent_id
        try:
            subprocess.run(["git", "add", "."], cwd=agent_path,
                           capture_output=True, check=True, timeout=30)
            if files:
                for f in files:
                    subprocess.run(["git", "add", f], cwd=agent_path,
                                   capture_output=True, check=True, timeout=30)
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=agent_path, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                logger.info(f"Committed: {message}")
                return True
            logger.warning(f"Commit failed: {result.stderr}")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Commit error: {e}")
            return False

    def rollback(self, agent_id: str, commits_back: int = 1) -> bool:
        agent_path = self._agents_dir / agent_id
        try:
            subprocess.run(
                ["git", "checkout", "main"],
                cwd=agent_path, capture_output=True, check=True, timeout=30
            )
            result = subprocess.run(
                ["git", "revert", f"HEAD~{commits_back}..HEAD", "--no-edit"],
                cwd=agent_path, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                logger.info(f"Rolled back {commits_back} commits for {agent_id}")
                return True
            logger.warning(f"Rollback failed: {result.stderr}")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Rollback error: {e}")
            return False

    def get_log(self, agent_id: str, max_count: int = 10) -> list[dict[str, Any]]:
        agent_path = self._agents_dir / agent_id
        try:
            result = subprocess.run(
                ["git", "log", f"--max-count={max_count}",
                 "--format={\"commit\":\"%h\",\"author\":\"%an\",\"date\":\"%ad\",\"message\":\"%s\"}"],
                cwd=agent_path, capture_output=True, text=True, timeout=30
            )
            entries = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    with contextlib.suppress(json.JSONDecodeError):
                        entries.append(json.loads(line))
            return entries
        except subprocess.CalledProcessError:
            return []
