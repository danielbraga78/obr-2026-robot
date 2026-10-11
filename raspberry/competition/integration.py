from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .behavior_manager import BehaviorManager
from .world_model import WorldModel


_STATE_TO_BEHAVIOR = {
    "FOLLOW_LINE": "FOLLOW_LINE",
    "SEARCH_LINE": "SEARCH_LINE",
    "AVOID_OBSTACLE": "OBSTACLE",
    "ENTER_RESCUE": "RESCUE",
    "SEARCH_BALL": "SEARCH_BALL",
    "ALIGN_BALL": "ALIGN_BALL",
    "CAPTURE_BALL": "CAPTURE_BALL",
    "SEARCH_SAFE_ZONE": "SEARCH_SAFE_ZONE",
    "DROP_BALL": "DROP_BALL",
    "RETURN_TO_LINE": "RETURN_TO_LINE",
    "FINISH": "FINISH",
}


@dataclass
class CompetitionRuntimeAdapter:
    behavior_manager: BehaviorManager | None = None
    world_model: WorldModel | None = None

    def __post_init__(self) -> None:
        if self.behavior_manager is None:
            self.behavior_manager = BehaviorManager()
        if self.world_model is None:
            self.world_model = WorldModel()

    def build_command(self, context, state_name: str) -> Optional[str]:
        behavior_name = _STATE_TO_BEHAVIOR.get(state_name)
        if not behavior_name:
            return None

        self.behavior_manager.change_to(behavior_name)
        behavior = self.behavior_manager.current_behavior
        if behavior is None:
            return None

        self.world_model.active_behavior = behavior.name
        self.world_model.mission_phase = state_name
        self.world_model.serial_connected = getattr(context, "serial_ready", False)
        self.world_model.camera_connected = getattr(context, "camera_ready", False)
        self.world_model.obstacle_detected = getattr(context, "obstacle_detected", False)
        self.world_model.safe_zone_visible = getattr(context, "safe_zone_detected", False)
        self.world_model.victim_visible = getattr(context, "rescue_detected", False)
        self.world_model.victim_distance = float(getattr(context, "ball_distance", 0.0) or 0.0)

        last_detections = getattr(context, "last_detections", None) or {}
        self.world_model.line_visible = bool(last_detections.get("line"))

        return behavior.execute()
