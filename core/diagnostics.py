import logging
import sys
import threading
import time
from collections import deque

logger = logging.getLogger("dex.diagnostics")


class ThreadDiagnostics:
    def __init__(self) -> None:
        self._snapshots: deque[dict] = deque(maxlen=100)
        self._lock = threading.Lock()
        self._recursion_guard = threading.local()

    def snapshot(self) -> dict:
        # Защита от рекурсивных вызовов
        if getattr(self._recursion_guard, 'in_snapshot', False):
            # Возвращаем базовый снапшот без анализа стека
            return {
                "ts": time.time(),
                "thread_count": threading.active_count(),
                "threads": {t.name or t.__class__.__name__: {
                    "alive": t.is_alive(),
                    "daemon": t.daemon,
                    "ident": t.ident,
                } for t in threading.enumerate()},
                "main_thread_blocked": False,
            }

        self._recursion_guard.in_snapshot = True
        try:
            threads = {}
            main_busy = False
            current_thread_ident = threading.current_thread().ident

            for t in threading.enumerate():
                name = t.name or t.__class__.__name__
                threads[name] = {
                    "alive": t.is_alive(),
                    "daemon": t.daemon,
                    "ident": t.ident,
                }
                # Пропускаем анализ стека для текущего потока (он и так в snapshot)
                if name == "MainThread" and t.is_alive() and t.ident is not None and t.ident != current_thread_ident:
                    try:
                        frames = sys._current_frames().get(t.ident, None)
                        if frames:
                            import traceback
                            main_busy = "QEventLoop" not in str(
                                traceback.extract_stack(frames)[-3:]
                            )
                    except Exception:
                        pass

            result = {
                "ts": time.time(),
                "thread_count": threading.active_count(),
                "threads": threads,
                "main_thread_blocked": main_busy,
            }
            with self._lock:
                self._snapshots.append(result)
            return result
        finally:
            self._recursion_guard.in_snapshot = False

    def get_blocked_threads(self, threshold: float = 2.0) -> list[str]:
        blocked = []
        current_ident = threading.current_thread().ident
        for t in threading.enumerate():
            if t.ident == current_ident:
                continue
            if t.is_alive() and t.ident:
                try:
                    frames = sys._current_frames().get(t.ident)
                    if frames:
                        stack_lines = []
                        f = frames.f_back
                        while f:
                            stack_lines.append(f"{f.f_code.co_filename}:{f.f_lineno} {f.f_code.co_name}")
                            f = f.f_back
                        stack = "\n".join(stack_lines) if stack_lines else ""
                        if "time.sleep" not in stack:
                            blocked.append(f"{t.name}: {stack[:200]}")
                except Exception:
                    pass
        return blocked

    def report(self) -> str:
        last = self.snapshot()
        lines = ["=== Thread Diagnostics ==="]
        lines.append(f"Threads: {last['thread_count']}")
        lines.append(f"Main blocked: {last['main_thread_blocked']}")
        for name, info in sorted(last["threads"].items()):
            status = "RUN" if info["alive"] else "STOP"
            lines.append(f"  [{status}] {name}")
        blocked = self.get_blocked_threads()
        if blocked:
            lines.append("")
            lines.append("Potential blockers:")
            for b in blocked[:5]:
                lines.append(f"  {b}")
        return "\n".join(lines)

    def get_recent_snapshots(self, count: int = 5) -> list[dict]:
        with self._lock:
            return list(self._snapshots)[-count:]
