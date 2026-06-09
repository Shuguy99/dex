import logging
from collections import deque
from datetime import datetime

logger = logging.getLogger("dex.watchdog.anomaly")


class AnomalyDetector:
    def __init__(self, error_threshold: float = 0.3,
                 latency_threshold_ms: int = 5000,
                 window_size: int = 50) -> None:
        self._error_threshold = error_threshold
        self._latency_threshold = latency_threshold_ms
        self._window_size = window_size
        self._error_timestamps: deque[datetime] = deque(maxlen=window_size)
        self._latencies: deque[float] = deque(maxlen=window_size)
        self._confirmations: deque[dict] = deque(maxlen=100)

    def record_error(self) -> None:
        self._error_timestamps.append(datetime.now())

    def record_latency(self, ms: float) -> None:
        self._latencies.append(ms)

    def record_confirmation(self, action: str, approved: bool) -> None:
        self._confirmations.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "approved": approved
        })

    def check(self) -> list[str]:
        issues = []

        if len(self._error_timestamps) >= 10:
            recent = list(self._error_timestamps)[-10:]
            now = datetime.now()
            recent_count = sum(1 for t in recent if (now - t).total_seconds() < 60)
            if recent_count / 10 > self._error_threshold:
                issues.append(f"Error spike: {recent_count}/10 in last 60s")

        if len(self._latencies) >= 5:
            avg = sum(self._latencies) / len(self._latencies)
            if avg > self._latency_threshold:
                issues.append(f"Latency spike: avg {avg:.0f}ms > {self._latency_threshold}ms")

        if len(self._confirmations) >= 10:
            recent_conf = list(self._confirmations)[-10:]
            denial_rate = sum(1 for c in recent_conf if not c["approved"]) / 10
            if denial_rate > 0.7:
                issues.append(f"High confirmation denial rate: {denial_rate:.0%}")

        return issues
