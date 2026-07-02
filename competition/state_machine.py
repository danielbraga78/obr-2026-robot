from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class StateMachine:
    states: List[str]
    current_state: str = "BOOT"

    def __post_init__(self) -> None:
        if not self.states:
            self.states = [
                "BOOT",
                "CALIBRATION",
                "FOLLOW_LINE",
                "SEARCH_LINE",
                "AVOID_OBSTACLE",
                "FOLLOW_LINE",
                "ENTER_RESCUE",
                "SEARCH_BALL",
                "ALIGN_BALL",
                "CAPTURE_BALL",
                "SEARCH_SAFE_ZONE",
                "DROP_BALL",
                "SEARCH_BALL",
                "EXIT_RESCUE",
                "FOLLOW_LINE",
                "FINISH",
            ]

    def transition(self, next_state: str) -> None:
        if next_state in self.states:
            self.current_state = next_state
