import logging
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("dex.async_engine")


@dataclass
class Command:
    text: str
    callback: Callable[[str], None] | None = None
    error_callback: Callable[[str], None] | None = None
    id: int = field(default_factory=lambda: id(object()))


class AsyncCommandQueue:
    def __init__(self) -> None:
        self._queue: queue.Queue[Command] = queue.Queue()
        self._cancel_event = threading.Event()
        self._busy = threading.Event()
        self._thread: threading.Thread | None = None
        self._running = False
        self._pending: Command | None = None
        self._lock = threading.Lock()

    def start(self, processor: Callable[[str], str]) -> None:
        self._running = True
        self._cancel_event.clear()
        self._thread = threading.Thread(
            target=self._loop, args=(processor,), daemon=True, name="cmd-queue"
        )
        self._thread.start()
        logger.info("AsyncCommandQueue started")

    def stop(self, timeout: float = 3.0) -> None:
        self._running = False
        self._cancel_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def post(self, cmd: Command) -> None:
        self._queue.put(cmd)

    def cancel_current(self) -> None:
        self._cancel_event.set()
        with self._lock:
            self._pending = None

    def is_busy(self) -> bool:
        return self._busy.is_set()

    def pending_count(self) -> int:
        return self._queue.qsize()

    def _loop(self, processor: Callable[[str], str]) -> None:
        while self._running:
            try:
                cmd = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if not self._running:
                break
            with self._lock:
                self._pending = cmd
            self._busy.set()
            self._cancel_event.clear()
            try:
                result = processor(cmd.text)
                if cmd.callback and not self._cancel_event.is_set():
                    cmd.callback(result)
            except Exception as e:
                logger.error(f"Command error: {e}")
                if cmd.error_callback:
                    cmd.error_callback(str(e))
            finally:
                self._busy.clear()
                with self._lock:
                    self._pending = None
                self._queue.task_done()


class TimeoutWrapper:
    def __init__(self, default_timeout: float = 10.0) -> None:
        self.default_timeout = default_timeout

    def call(self, fn: Callable, timeout: float | None = None, *args, **kwargs) -> Any:
        result: list[Any] = [None]
        error: list[Exception | None] = [None]
        done = threading.Event()

        def worker() -> None:
            try:
                result[0] = fn(*args, **kwargs)
            except Exception as e:
                error[0] = e
            finally:
                done.set()

        t = threading.Thread(target=worker, daemon=True, name="timeout-wrap")
        t.start()
        ok = done.wait(timeout=(timeout or self.default_timeout))
        if not ok:
            raise TimeoutError(f"Operation timed out after {timeout or self.default_timeout}s")
        if error[0]:
            raise error[0]
        return result[0]


class GUIScheduler:
    def __init__(self) -> None:
        self._callbacks: queue.Queue[Callable] = queue.Queue()

    def schedule(self, fn: Callable) -> None:
        self._callbacks.put(fn)

    def process_pending(self) -> None:
        while not self._callbacks.empty():
            try:
                fn = self._callbacks.get_nowait()
                fn()
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"GUIScheduler error: {e}")
