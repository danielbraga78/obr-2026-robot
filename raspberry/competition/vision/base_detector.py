from __future__ import annotations

from abc import ABC, abstractmethod

from ..world_model import WorldModel


class Detector(ABC):
    def __init__(self, world_model: WorldModel) -> None:
        self.world_model = world_model

    @abstractmethod
    def update(self, frame) -> None:
        raise NotImplementedError
