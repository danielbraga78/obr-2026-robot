from __future__ import annotations

import time
from typing import Callable, Optional

from .config import CONTROL_LOOP_HZ, MAX_FRAME_AGE


class ExecutionLoopController:
    """Controla a taxa principal do ciclo de execução e mede latência."""

    def __init__(self, target_hz: float = CONTROL_LOOP_HZ, max_frame_age: float = MAX_FRAME_AGE, now_fn: Optional[Callable[[], float]] = None) -> None:
        self.target_hz = max(target_hz, 1.0)
        self.period_seconds = 1.0 / self.target_hz
        self.max_frame_age = max_frame_age
        self._now = now_fn or time.monotonic
        self._last_cycle_start = 0.0
        self._latency_history: list[float] = []
        self._dropped_frames = 0

    def begin_cycle(self) -> float:
        self._last_cycle_start = self._now()
        return self._last_cycle_start

    def wait_for_next_cycle(self, cycle_start: float) -> float:
        elapsed = self._now() - cycle_start
        remaining = self.period_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)
        return self._now()

    def record_latency(self, loop_latency_ms: float) -> float:
        self._latency_history.append(loop_latency_ms)
        if len(self._latency_history) > 10:
            self._latency_history.pop(0)
        return self.average_latency_ms

    @property
    def average_latency_ms(self) -> float:
        if not self._latency_history:
            return 0.0
        return sum(self._latency_history) / len(self._latency_history)

    def is_result_stale(self, result_timestamp: Optional[float], now: Optional[float] = None) -> bool:
        if result_timestamp is None:
            return True
        current_time = now if now is not None else self._now()
        age = current_time - result_timestamp
        if age > self.max_frame_age:
            self._dropped_frames += 1
            return True
        return False

    @property
    def dropped_frames(self) -> int:
        return self._dropped_frames
