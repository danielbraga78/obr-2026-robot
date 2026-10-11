from .base import Behavior


class CaptureBallBehavior(Behavior):
    def __init__(self, name: str = "CAPTURE_BALL") -> None:
        super().__init__(name)

    def execute(self) -> str:
        return "GRAB"
