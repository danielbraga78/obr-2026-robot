from .base import Behavior


class DropBallBehavior(Behavior):
    def __init__(self, name: str = "DROP_BALL") -> None:
        super().__init__(name)

    def execute(self) -> str:
        return "RELEASE"
