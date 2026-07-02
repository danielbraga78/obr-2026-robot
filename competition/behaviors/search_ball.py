from .base import Behavior


class SearchBallBehavior(Behavior):
    def __init__(self, name: str = "SEARCH_BALL") -> None:
        super().__init__(name)

    def execute(self) -> str:
        return "MOVE,12,0,1"
