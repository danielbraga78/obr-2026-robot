from .base import Behavior


class ObstacleBehavior(Behavior):
    def __init__(self, name: str = "OBSTACLE") -> None:
        super().__init__(name)

    def execute(self) -> str:
        return "MOVE,10,1,0"
