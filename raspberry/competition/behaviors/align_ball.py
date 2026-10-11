from .base import Behavior


class AlignBallBehavior(Behavior):
    def __init__(self, name: str = "ALIGN_BALL") -> None:
        super().__init__(name)

    def execute(self) -> str:
        return "MOVE,10,0,0"
