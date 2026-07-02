from .base import Behavior


class GapBehavior(Behavior):
    def __init__(self, name: str = "GAP") -> None:
        super().__init__(name)

    def execute(self) -> str:
        return "MOVE,15,0,0"
