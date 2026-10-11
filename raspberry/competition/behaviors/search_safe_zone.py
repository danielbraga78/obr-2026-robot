from .base import Behavior


class SearchSafeZoneBehavior(Behavior):
    def __init__(self, name: str = "SEARCH_SAFE_ZONE") -> None:
        super().__init__(name)

    def execute(self) -> str:
        return "MOVE,10,0,0"
