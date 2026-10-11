from .base import Behavior


class SearchLineBehavior(Behavior):
    def __init__(self, name: str = "SEARCH_LINE") -> None:
        super().__init__(name)

    def execute(self) -> str:
        return "MOVE,10,0,1"
