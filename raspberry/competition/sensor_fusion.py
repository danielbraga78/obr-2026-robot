from __future__ import annotations

from .world_model import WorldModel


class SensorFusion:
    def __init__(self, world_model: WorldModel | None = None) -> None:
        self.world_model = world_model or WorldModel()

    def update(self, *, line_visible: bool = False, line_offset: float = 0.0, obstacle_detected: bool = False, obstacle_distance: float = 0.0, camera_connected: bool = True, serial_connected: bool = True) -> None:
        self.world_model.line_visible = line_visible
        self.world_model.line_offset = line_offset
        self.world_model.obstacle_detected = obstacle_detected
        self.world_model.obstacle_distance = obstacle_distance
        self.world_model.camera_connected = camera_connected
        self.world_model.serial_connected = serial_connected
