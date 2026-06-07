import logging
import threading
import time
from collections import OrderedDict

logger = logging.getLogger("dex.resource.model_cache")


class ModelCache:
    def __init__(self, max_loaded: int = 2, ttl: int = 300) -> None:
        self._max_loaded = max_loaded
        self._ttl = ttl
        self._lock = threading.Lock()
        self._models = OrderedDict()
        self._last_use = {}

    def acquire(self, model_name: str) -> bool:
        with self._lock:
            now = time.time()
            if model_name in self._models:
                self._models.move_to_end(model_name)
                self._last_use[model_name] = now
                return True
            if len(self._models) >= self._max_loaded:
                self._evict_one()
            self._models[model_name] = None
            self._last_use[model_name] = now
            logger.info(f"Model loaded: {model_name} ({len(self._models)}/{self._max_loaded})")
            return False

    def release(self, model_name: str):
        with self._lock:
            if model_name in self._models:
                del self._models[model_name]
                self._last_use.pop(model_name, None)
                logger.info(f"Model unloaded: {model_name} ({len(self._models)}/{self._max_loaded})")

    def mark_loaded(self, model_name: str, handle: object):
        with self._lock:
            self._models[model_name] = handle
            self._last_use[model_name] = time.time()

    def get_handle(self, model_name: str) -> object | None:
        with self._lock:
            handle = self._models.get(model_name)
            if handle is not None:
                self._last_use[model_name] = time.time()
            return handle

    def _evict_one(self):
        oldest = None
        oldest_time = float("inf")
        now = time.time()
        for name in list(self._models.keys()):
            last = self._last_use.get(name, 0)
            if now - last > self._ttl:
                oldest = name
                break
            if last < oldest_time:
                oldest_time = last
                oldest = name
        if oldest:
            logger.info(f"Evicting model: {oldest} (idle {now - self._last_use.get(oldest, 0):.0f}s)")
            del self._models[oldest]
            self._last_use.pop(oldest, None)

    def loaded_count(self) -> int:
        return len(self._models)

    def loaded_models(self) -> list[str]:
        return list(self._models.keys())

    def unload_all(self):
        with self._lock:
            self._models.clear()
            self._last_use.clear()
            logger.info("All models unloaded")

    def status(self) -> dict:
        return {
            "loaded": list(self._models.keys()),
            "count": len(self._models),
            "max": self._max_loaded,
            "ttl": self._ttl,
        }
