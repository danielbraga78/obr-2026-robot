from .base import Behavior


class ReturnToLineBehavior(Behavior):
    def __init__(self, name: str = "RETURN_TO_LINE") -> None:
        super().__init__(name)

    def execute(self) -> str:
        return "MOVE,12,0,0"
