from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass
class WorldModel:
    line_visible: bool = False
    line_angle: float = 0.0
    line_offset: float = 0.0
    line_width: float = 0.0
    intersection_detected: bool = False
    gap_detected: bool = False
    silver_line_detected: bool = False
    black_line_detected: bool = False
    obstacle_distance: float = 0.0
    obstacle_detected: bool = False
    ramp_detected: bool = False
    victim_visible: bool = False
    victim_position: Optional[Tuple[float, float]] = None
    victim_type: Optional[str] = None
    victim_distance: float = 0.0
    safe_zone_visible: bool = False
    checkpoint_detected: bool = False
    rescue_room_detected: bool = False
    robot_pose: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    robot_heading: float = 0.0
    robot_velocity: float = 0.0
    serial_connected: bool = False
    camera_connected: bool = False
    last_error: str = ""
    mission_phase: str = "BOOT"
    active_behavior: str = "FOLLOW_LINE"
    events: list[str] = field(default_factory=list)
