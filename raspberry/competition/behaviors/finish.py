from .base import Behavior


class FinishBehavior(Behavior):
    def __init__(self, name: str = "FINISH") -> None:
        super().__init__(name)

    def execute(self) -> str:
        return "STOP"
