import json
import logging
import urllib.request
from typing import Any

logger = logging.getLogger("dex.integrations.matrix")


class MatrixClient:
    def __init__(self, server_url: str = "http://localhost:8008",
                 username: str = "", password: str = "") -> None:
        self._server = server_url.rstrip("/")
        self._username = username
        self._password = password
        self._token: str | None = None
        self._device_id: str | None = None

    @property
    def available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self._server}/_matrix/client/versions")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def login(self) -> bool:
        try:
            payload = {
                "type": "m.login.password",
                "user": self._username,
                "password": self._password
            }
            req = urllib.request.Request(
                f"{self._server}/_matrix/client/v3/login",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                self._token = data.get("access_token")
                self._device_id = data.get("device_id")
                logger.info(f"Matrix logged in as {self._username}")
                return True
        except Exception as e:
            logger.error(f"Matrix login failed: {e}")
            return False

    def _api(self, method: str, path: str, data: dict | None = None) -> dict | list | None:
        if not self._token:
            logger.warning("Matrix: not logged in")
            return None
        try:
            url = f"{self._server}/_matrix/client/v3/{path.lstrip('/')}"
            headers = {
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json"
            }
            body = json.dumps(data).encode() if data else None
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.error(f"Matrix API error: {e}")
            return None

    def send_message(self, room_id: str, message: str) -> bool:
        result = self._api(
            "PUT",
            f"rooms/{room_id}/send/m.room.message/{self._gen_txn_id()}",
            {
                "msgtype": "m.text",
                "body": message
            }
        )
        return result is not None

    def _gen_txn_id(self) -> str:
        import random
        import time
        return f"dex_{int(time.time())}_{random.randint(1000,9999)}"

    def get_rooms(self) -> list[dict[str, Any]]:
        result = self._api("GET", "joined_rooms")
        if result and "joined_rooms" in result:
            return [{"room_id": r} for r in result["joined_rooms"]]
        return []

    def logout(self):
        if self._token:
            self._api("POST", "logout")
            self._token = None
            logger.info("Matrix logged out")
