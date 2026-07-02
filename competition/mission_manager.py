from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MissionManager:
    current_phase: str = "BOOT"

    def transition(self, next_phase: str) -> None:
        self.current_phase = next_phase
