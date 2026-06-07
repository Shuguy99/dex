import hashlib
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.learning.federated")

FEDERATED_DIR = "data/federated"
TRUSTED_PEERS = "data/federated/peers.json"


class FederatedLearning:
    def __init__(self, data_dir: str | Path = FEDERATED_DIR,
                 node_id: str | None = None) -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._node_id = node_id or self._generate_node_id()
        self._peers: list[dict[str, Any]] = []
        self._load_peers()

    def _generate_node_id(self) -> str:
        import socket
        base = socket.gethostname() + str(random.randint(1000, 9999))
        return hashlib.sha256(base.encode()).hexdigest()[:16]

    def _load_peers(self):
        path = self._data_dir / "peers.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                self._peers = json.load(f)

    def _save_peers(self):
        with open(self._data_dir / "peers.json", "w", encoding="utf-8") as f:
            json.dump(self._peers, f, ensure_ascii=False, indent=2)

    def share_lesson(self, lesson: dict[str, Any]) -> str:
        lesson_id = hashlib.sha256(
            json.dumps(lesson, sort_keys=True).encode()
        ).hexdigest()[:16]

        anonymized = {
            "lesson_id": lesson_id,
            "rule_pattern": lesson.get("pattern", ""),
            "action": lesson.get("expected_action", ""),
            "success_rate": lesson.get("metrics", {}).get("test_score", 0),
            "context": lesson.get("description", "")[:100],
            "severity": lesson.get("severity", "info"),
            "node_id": self._node_id,
            "timestamp": datetime.now().isoformat()
        }
        anonymized.pop("node_id", None)

        out_path = self._data_dir / f"lesson_{lesson_id[:8]}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(anonymized, f, ensure_ascii=False, indent=2)
        logger.info(f"Lesson shared: {lesson_id[:8]}")
        return lesson_id

    def receive_lessons(self) -> list[dict[str, Any]]:
        lessons = []
        for f_path in self._data_dir.glob("lesson_*.json"):
            try:
                with open(f_path, encoding="utf-8") as f:
                    lessons.append(json.load(f))
            except (json.JSONDecodeError, Exception) as e:
                logger.error(f"Failed to read lesson {f_path}: {e}")
        return lessons

    def add_peer(self, address: str, public_key: str | None = None):
        peer = {
            "address": address,
            "added": datetime.now().isoformat(),
            "trusted": True
        }
        if public_key:
            peer["public_key"] = public_key
        self._peers.append(peer)
        self._save_peers()
        logger.info(f"Peer added: {address}")

    def sync_with_peers(self) -> int:
        total = 0
        for peer in self._peers:
            if not peer.get("trusted", True):
                continue
            try:
                import urllib.request
                url = f"{peer['address']}/lessons"
                req = urllib.request.Request(url, timeout=10)
                with urllib.request.urlopen(req) as resp:
                    data = json.loads(resp.read())
                    for lesson in data:
                        out = self._data_dir / f"peer_{hashlib.md5(peer['address'].encode()).hexdigest()[:8]}_{lesson.get('lesson_id', 'unknown')[:8]}.json"
                        if not out.exists():
                            with open(out, "w", encoding="utf-8") as f:
                                json.dump(lesson, f, ensure_ascii=False, indent=2)
                            total += 1
            except Exception as e:
                logger.warning(f"Sync with {peer['address']} failed: {e}")
        return total
