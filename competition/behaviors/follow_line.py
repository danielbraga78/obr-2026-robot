from .base import Behavior


class FollowLineBehavior(Behavior):
    def __init__(self, name: str = "FOLLOW_LINE") -> None:
        super().__init__(name)

    def execute(self) -> str:
        return "MOVE,20,0,0"
