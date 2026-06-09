import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.multiagent.orchestrator")


class Agent:
    def __init__(self, agent_id: str, agent_type: str,
                 code: str | None = None, config: dict[str, Any] | None = None) -> None:
        self.id = agent_id
        self.type = agent_type
        self.code = code or ""
        self.config = config or {}
        self.active = False
        self.version = 1
        self.last_heartbeat: float | None = None
        self.error_count = 0
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._running = True
        self.active = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"Agent {self.id} started")

    def stop(self) -> None:
        self._running = False
        self.active = False
        logger.info(f"Agent {self.id} stopped")

    def _run_loop(self) -> None:
        while self._running:
            self.last_heartbeat = time.time()
            time.sleep(5)

    @property
    def alive(self) -> bool:
        if not self.last_heartbeat:
            return False
        return (time.time() - self.last_heartbeat) < 15

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "version": self.version,
            "active": self.active,
            "config": self.config,
            "alive": self.alive,
            "error_count": self.error_count
        }


class Orchestrator:
    def __init__(self, agents_dir: str | Path) -> None:
        self._agents_dir = Path(agents_dir)
        self._agents_dir.mkdir(parents=True, exist_ok=True)
        self._agents: dict[str, Agent] = {}
        self._task_queue: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def register_agent(self, agent: Agent) -> None:
        with self._lock:
            self._agents[agent.id] = agent
            self._save_agent_meta(agent)
        logger.info(f"Registered agent: {agent.id} ({agent.type})")

    def unregister_agent(self, agent_id: str) -> None:
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].stop()
                del self._agents[agent_id]

    def start_agent(self, agent_id: str) -> bool:
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].start()
                return True
        return False

    def stop_agent(self, agent_id: str) -> bool:
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].stop()
                return True
        return False

    def dispatch_task(self, task: dict[str, Any]) -> str | None:
        task_type = task.get("type", "")
        task_id = task.get("id", f"task_{int(time.time())}")

        with self._lock:
            suitable = [
                a for a in self._agents.values()
                if a.active and a.alive and a.type == task_type
            ]
            if suitable:
                agent = suitable[0]
                agent.error_count = 0
                logger.info(f"Task {task_id} dispatched to {agent.id}")
                return agent.id

        logger.warning(f"No suitable agent for task type: {task_type}")
        return None

    def check_health(self) -> dict[str, Any]:
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_agents": len(self._agents),
            "active_agents": sum(1 for a in self._agents.values() if a.active),
            "alive_agents": sum(1 for a in self._agents.values() if a.alive),
            "dead_agents": [],
            "failing_agents": []
        }
        for agent_id, agent in self._agents.items():
            if not agent.alive:
                report["dead_agents"].append(agent_id)
            if agent.error_count > 5:
                report["failing_agents"].append(agent_id)
        return report

    def _save_agent_meta(self, agent: Agent) -> None:
        path = self._agents_dir / f"{agent.id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(agent.to_dict(), f, ensure_ascii=False, indent=2)

    def load_agents(self) -> list[dict[str, Any]]:
        for f_path in self._agents_dir.glob("*.json"):
            try:
                with open(f_path, encoding="utf-8") as f:
                    data = json.load(f)
                agent = Agent(
                    agent_id=data["id"],
                    agent_type=data["type"],
                    config=data.get("config", {})
                )
                agent.version = data.get("version", 1)
                self._agents[agent.id] = agent
            except Exception as e:
                logger.error(f"Failed to load agent from {f_path}: {e}")
