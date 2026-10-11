from .base import Behavior


class RescueBehavior(Behavior):
    def __init__(self, name: str = "RESCUE") -> None:
        super().__init__(name)

    def execute(self) -> str:
        return "STOP"
