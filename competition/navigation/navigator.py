from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Navigator:
    linear_speed: int = 20
    lateral_speed: int = 0
    angular_speed: int = 0

    def build_command(self, behavior: str, linear: float, angular: float) -> str:
        speed = self.linear_speed
        turn = int(max(-1, min(1, angular)))
        return f"MOVE,{speed},{self.lateral_speed},{turn}"
