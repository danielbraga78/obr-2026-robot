from .base import Behavior


class IntersectionBehavior(Behavior):
    def __init__(self, name: str = "INTERSECTION") -> None:
        super().__init__(name)

    def execute(self) -> str:
        return "MOVE,12,0,0"
