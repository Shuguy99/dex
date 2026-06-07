import json
import logging
import os
import subprocess
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("dex.watchdog")


class WatchdogMonitor:
    def __init__(self, pid: int | None = None, interval: int = 5,
                 log_dir: str | None = None, restart_command: list[str] | None = None) -> None:
        self._target_pid = pid or os.getpid()
        self._interval = interval
        self._log_dir = Path(log_dir) if log_dir else Path("data/logs")
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._restart_cmd = restart_command
        self._active = False
        self._thread: threading.Thread | None = None
        self._start_time = datetime.now()

        self._error_log: deque[dict] = deque(maxlen=1000)
        self._latency_log: deque[float] = deque(maxlen=500)
        self._confirmation_log: deque[dict] = deque(maxlen=200)
        self._crash_count = 0
        self._anomaly_flag = False

    def start(self):
        self._active = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"Watchdog started monitoring PID {self._target_pid}")

    def stop(self):
        self._active = False
        logger.info("Watchdog stopped")

    def log_error(self, source: str, message: str, details: str = ""):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "message": message,
            "details": details
        }
        self._error_log.append(entry)
        self._dump_recent()

    def log_latency(self, ms: float):
        self._latency_log.append(ms)

    def log_confirmation(self, action: str, approved: bool):
        self._confirmation_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "approved": approved
        })

    def check_anomaly(self) -> list[str]:
        issues = []

        if len(self._error_log) >= 10:
            recent = list(self._error_log)[-10:]
            error_rate = sum(1 for e in recent if e["timestamp"]) / 10
            if error_rate > 0.3:
                issues.append(f"High error rate: {error_rate:.0%}")
                self._anomaly_flag = True

        if len(self._latency_log) >= 10:
            avg_latency = sum(self._latency_log) / len(self._latency_log)
            if avg_latency > 5000:
                issues.append(f"High latency: {avg_latency:.0f}ms")
                self._anomaly_flag = True

        return issues

    def _run(self):
        import psutil
        while self._active:
            try:
                if not psutil.pid_exists(self._target_pid):
                    self._crash_count += 1
                    self._dump_crash()
                    logger.critical(f"Process {self._target_pid} crashed!")
                    if self._restart_cmd:
                        subprocess.Popen(self._restart_cmd)
                    break

                proc = psutil.Process(self._target_pid)
                cpu = proc.cpu_percent(interval=0)
                mem = proc.memory_percent()
                logger.debug(f"PID {self._target_pid} - CPU: {cpu:.1f}%, Mem: {mem:.1f}%")

                issues = self.check_anomaly()
                if issues:
                    logger.warning(f"Anomalies detected: {issues}")
                    self._write_anomaly_report(issues)

            except psutil.NoSuchProcess:
                continue
            except Exception as e:
                logger.error(f"Watchdog error: {e}")

            time.sleep(self._interval)

    def _dump_crash(self):
        dump = {
            "timestamp": datetime.now().isoformat(),
            "pid": self._target_pid,
            "uptime_seconds": (datetime.now() - self._start_time).total_seconds(),
            "crash_count": self._crash_count,
            "recent_errors": list(self._error_log)[-20:],
            "recent_confirmations": list(self._confirmation_log)[-10:]
        }
        path = self._log_dir / f"crash_dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dump, f, ensure_ascii=False, indent=2)
        logger.critical(f"Crash dump written: {path}")

    def _dump_recent(self):
        dump = {
            "timestamp": datetime.now().isoformat(),
            "recent_errors": list(self._error_log)[-10:]
        }
        path = self._log_dir / "recent_events.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dump, f, ensure_ascii=False, indent=2)

    def _write_anomaly_report(self, issues: list[str]):
        report = {
            "timestamp": datetime.now().isoformat(),
            "issues": issues,
            "error_count": len(self._error_log),
            "avg_latency_ms": sum(self._latency_log) / len(self._latency_log) if self._latency_log else 0
        }
        path = self._log_dir / f"anomaly_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    @property
    def uptime(self) -> timedelta:
        return datetime.now() - self._start_time

    @property
    def has_anomaly(self) -> bool:
        return self._anomaly_flag

    def clear_anomaly_flag(self):
        self._anomaly_flag = False
