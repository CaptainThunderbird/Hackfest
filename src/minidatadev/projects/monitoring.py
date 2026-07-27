"""Small local-first guardrails and operational health reporting."""

from __future__ import annotations

import json
from collections import deque
from datetime import UTC, datetime, timedelta
from pathlib import Path


class RateLimiter:
    def __init__(self, limit: int, window_minutes: int = 60) -> None:
        self.limit = limit
        self.window = timedelta(minutes=window_minutes)
        self._events: deque[datetime] = deque()

    def allow(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        while self._events and now - self._events[0] >= self.window:
            self._events.popleft()
        if len(self._events) >= self.limit:
            return False
        self._events.append(now)
        return True

    @property
    def remaining(self) -> int:
        return max(0, self.limit - len(self._events))


def record_event(log_path: Path, event: str, **details: object) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": event,
        **details,
    }
    with log_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, default=str) + "\n")


def health_snapshot(database_path: Path, data_dir: Path) -> dict[str, object]:
    return {
        "status": "healthy",
        "database_ready": database_path.parent.exists(),
        "storage_ready": data_dir.exists(),
        "checked_at": datetime.now(UTC).isoformat(),
    }
