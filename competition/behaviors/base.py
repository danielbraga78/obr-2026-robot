from __future__ import annotations

from abc import ABC, abstractmethod


class Behavior(ABC):
    def __init__(self, name: str) -> None:
        self.name = name

    def enter(self) -> None:
        pass

    @abstractmethod
    def execute(self) -> str:
        raise NotImplementedError

    def exit(self) -> None:
        pass

    def finished(self) -> bool:
        return False
