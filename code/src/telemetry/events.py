"""
Request-level telemetry event logger.
Records latency, token usage, model, caching, and escalation per call.
Writes events to a local JSON log file for each run.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class TelemetryEvent:
    """One telemetry event representing a single model call or pipeline step."""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    user_id: str = ""
    model: str = ""
    stage: str = ""          # e.g. "claim_parser", "image_reviewer", "holistic"
    latency_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cached: bool = False
    escalated: bool = False
    error: Optional[str] = None


class EventLogger:
    """Collects TelemetryEvent objects and writes them to a JSON log file."""

    def __init__(self, log_path: Optional[Path] = None):
        self._events: list[TelemetryEvent] = []
        self._log_path = log_path
        self._run_start = datetime.utcnow().isoformat() + "Z"

    @property
    def events(self) -> list[TelemetryEvent]:
        return self._events

    def record(self, event: TelemetryEvent) -> None:
        """Append an event to the in-memory log."""
        self._events.append(event)

    def start_timer(self) -> float:
        """Return a monotonic start time for latency measurement."""
        return time.monotonic()

    def elapsed(self, start: float) -> float:
        """Return seconds elapsed since `start`."""
        return round(time.monotonic() - start, 4)

    def flush(self, path: Optional[Path] = None) -> Path:
        """Write all collected events to a JSON file.

        Returns the path written to.
        """
        target = path or self._log_path
        if target is None:
            target = Path("telemetry_log.json")

        target.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "run_start": self._run_start,
            "run_end": datetime.utcnow().isoformat() + "Z",
            "total_events": len(self._events),
            "events": [asdict(e) for e in self._events],
        }

        with open(target, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return target

    def summary(self) -> dict:
        """Return aggregate statistics over all recorded events."""
        total_latency = sum(e.latency_seconds for e in self._events)
        total_input = sum(e.input_tokens for e in self._events)
        total_output = sum(e.output_tokens for e in self._events)
        cached_count = sum(1 for e in self._events if e.cached)
        escalated_count = sum(1 for e in self._events if e.escalated)
        error_count = sum(1 for e in self._events if e.error)

        return {
            "total_events": len(self._events),
            "total_latency_seconds": round(total_latency, 4),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "cached_calls": cached_count,
            "escalated_calls": escalated_count,
            "error_calls": error_count,
        }
