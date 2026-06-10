import json
import logging
import socket
import threading
import time
from collections import deque
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.mesh.swarm")


class AgentSwarm:
    def __init__(self, local_server_port: int = 5555) -> None:
        self._port = local_server_port
        self._peers: dict[str, dict[str, Any]] = {}
        self._messages: deque[dict] = deque(maxlen=500)
        self._running = False
        self._server_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._data_dir = Path("data/mesh")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._peer_path = self._data_dir / "peers.json"
        self._command_handler: Callable | None = None

    def start(self, command_handler: Callable | None = None) -> None:
        self._command_handler = command_handler
        self._running = True
        self._server_thread = threading.Thread(target=self._serve, daemon=True)
        self._server_thread.start()
        logger.info(f"Mesh server started on port {self._port}")

    def stop(self) -> None:
        self._running = False
        logger.info("Mesh server stopped")

    def _serve(self) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(("0.0.0.0", self._port))
            server.listen(5)
            server.settimeout(1.0)
        except OSError as e:
            logger.warning(f"Mesh bind failed (port {self._port}): {e}")
            return

        while self._running:
            try:
                conn, addr = server.accept()
                threading.Thread(target=self._handle_peer,
                                 args=(conn, addr), daemon=True).start()
            except TimeoutError:
                continue
            except Exception as e:
                logger.warning(f"Mesh accept error: {e}")
        server.close()

    def _handle_peer(self, conn: socket.socket, addr: tuple) -> None:
        try:
            data = conn.recv(4096)
            if not data:
                return
            message = json.loads(data.decode("utf-8"))
            with self._lock:
                self._messages.append({
                    "from": addr[0],
                    "message": message,
                    "timestamp": time.time()
                })

            response = {"status": "ok", "server_time": time.time()}
            if message.get("type") == "command" and self._command_handler:
                result = self._command_handler(message.get("text", ""))
                response["result"] = result
            elif message.get("type") == "ping":
                response["peers"] = len(self._peers)

            conn.send(json.dumps(response).encode("utf-8"))
        except Exception as e:
            logger.warning(f"Peer handler error: {e}")
        finally:
            conn.close()

    def register_peer(self, peer_id: str, host: str, port: int,
                      capabilities: list[str] | None = None) -> None:
        with self._lock:
            self._peers[peer_id] = {
                "host": host,
                "port": port,
                "capabilities": capabilities or [],
                "last_seen": time.time(),
                "registered": datetime.now().isoformat()
            }
        self._save_peers()
        logger.info(f"Peer registered: {peer_id} @ {host}:{port}")

    def _save_peers(self) -> None:
        with open(self._peer_path, "w", encoding="utf-8") as f:
            data = {k: {**v, "last_seen": v["last_seen"]}
                    for k, v in self._peers.items()}
            json.dump(data, f, ensure_ascii=False, indent=2)

    def send_command(self, peer_id: str, command_text: str) -> dict[str, Any]:
        with self._lock:
            peer = self._peers.get(peer_id)
        if not peer:
            return {"success": False, "error": f"Peer {peer_id} not found"}

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((peer["host"], peer["port"]))
                payload = json.dumps({"type": "command", "text": command_text})
                sock.send(payload.encode("utf-8"))
                response = sock.recv(4096)
                result = json.loads(response.decode("utf-8"))
            return {"success": True, "result": result.get("result", ""),
                    "peer": peer_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def broadcast_command(self, command_text: str) -> list[dict[str, Any]]:
        results = []
        with self._lock:
            peer_ids = list(self._peers.keys())
        for peer_id in peer_ids:
            result = self.send_command(peer_id, command_text)
            results.append(result)
        return results

    def discover_peers(self) -> list[dict[str, Any]]:
        found = []
        for port_offset in range(1, 10):
            target_port = self._port + port_offset
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.5)
                    sock.connect(("127.0.0.1", target_port))
                    payload = json.dumps({"type": "ping"})
                    sock.send(payload.encode("utf-8"))
                    response = sock.recv(4096)
                    data = json.loads(response.decode("utf-8"))
                peer_id = f"peer_{target_port}"
                self.register_peer(peer_id, "127.0.0.1", target_port)
                found.append({"peer_id": peer_id, "port": target_port,
                              "status": data.get("status")})
            except (TimeoutError, ConnectionRefusedError, json.JSONDecodeError):
                continue
        return found

    def get_swarm_summary(self) -> str:
        lines = ["── Dex Mesh ──"]
        lines.append(f"Server port: {self._port}")
        lines.append(f"Peers: {len(self._peers)}")
        for pid, info in self._peers.items():
            caps = ", ".join(info.get("capabilities", [])) or "none"
            lines.append(f"  {pid}: {info['host']}:{info['port']} [{caps}]")
        lines.append(f"Messages relayed: {len(self._messages)}")
        return "\n".join(lines)
