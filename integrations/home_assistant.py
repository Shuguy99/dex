import json
import logging
import urllib.request
from typing import Any

logger = logging.getLogger("dex.integrations.home_assistant")


class HomeAssistant:
    def __init__(self, url: str = "http://localhost:8123",
                 token: str | None = None) -> None:
        self._url = url.rstrip("/")
        self._token = token or ""
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }

    @property
    def available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self._url}/api/", headers=self._headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _api(self, method: str, path: str, data: dict | None = None) -> dict | list | None:
        try:
            url = f"{self._url}/api/{path.lstrip('/')}"
            body = json.dumps(data).encode() if data else None
            req = urllib.request.Request(url, data=body, headers=self._headers,
                                          method=method)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.error(f"Home Assistant API error: {e}")
            return None

    def get_states(self) -> list[dict[str, Any]]:
        return self._api("GET", "states") or []

    def get_state(self, entity_id: str) -> dict[str, Any] | None:
        return self._api("GET", f"states/{entity_id}")

    def call_service(self, domain: str, service: str,
                     entity_id: str | None = None, **kwargs) -> bool:
        data = {}
        if entity_id:
            data["entity_id"] = entity_id
        data.update(kwargs)
        result = self._api("POST", f"services/{domain}/{service}", data)
        return result is not None

    def turn_on(self, entity_id: str) -> bool:
        domain = entity_id.split(".")[0]
        return self.call_service(domain, "turn_on", entity_id=entity_id)

    def turn_off(self, entity_id: str) -> bool:
        domain = entity_id.split(".")[0]
        return self.call_service(domain, "turn_off", entity_id=entity_id)

    def set_temperature(self, entity_id: str, temperature: float) -> bool:
        return self.call_service("climate", "set_temperature",
                                 entity_id=entity_id, temperature=temperature)

    def get_entities_by_domain(self, domain: str) -> list[dict[str, Any]]:
        states = self.get_states()
        return [s for s in states if s.get("entity_id", "").startswith(f"{domain}.")]
