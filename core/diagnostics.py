import logging
import sys
import threading
import time

logger = logging.getLogger("dex.diagnostics")


class ThreadDiagnostics:
    def __init__(self) -> None:
        self._snapshots: list[dict] = []
        self._lock = threading.Lock()

    def snapshot(self) -> dict:
        threads = {}
        main_busy = False
        for t in threading.enumerate():
            name = t.name or t.__class__.__name__
            try:
                for frame in sys._current_frames().values():
                    if frame.f_globals.get("__name__") == t.name:
                        pass
            except Exception:
                pass
            threads[name] = {
                "alive": t.is_alive(),
                "daemon": t.daemon,
                "ident": t.ident,
            }
            if name == "MainThread" and t.is_alive():
                import traceback
                try:
                    frames = sys._current_frames().get(t.ident, None)
                    if frames:
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
            if len(self._snapshots) > 100:
                self._snapshots.pop(0)
        return result

    def get_blocked_threads(self, threshold: float = 2.0) -> list[str]:
        blocked = []
        time.time()
        for t in threading.enumerate():
            if t.is_alive() and t.ident:
                try:
                    frames = sys._current_frames().get(t.ident)
                    if frames:
                        stack = "\n".join(
                            f"{f.f_code.co_filename}:{f.f_lineno} {f.f_code.co_name}"
                            for f in frames.f_back
                        ) if frames.f_back else ""
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
