from .base import Behavior


class RampBehavior(Behavior):
    def __init__(self, name: str = "RAMP") -> None:
        super().__init__(name)

    def execute(self) -> str:
        return "MOVE,15,0,0"
