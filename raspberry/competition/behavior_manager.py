from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .behaviors.follow_line import FollowLineBehavior
from .behaviors.search_line import SearchLineBehavior
from .behaviors.gap import GapBehavior
from .behaviors.intersection import IntersectionBehavior
from .behaviors.obstacle import ObstacleBehavior
from .behaviors.ramp import RampBehavior
from .behaviors.rescue import RescueBehavior
from .behaviors.search_ball import SearchBallBehavior
from .behaviors.align_ball import AlignBallBehavior
from .behaviors.capture_ball import CaptureBallBehavior
from .behaviors.search_safe_zone import SearchSafeZoneBehavior
from .behaviors.drop_ball import DropBallBehavior
from .behaviors.return_to_line import ReturnToLineBehavior
from .behaviors.finish import FinishBehavior


@dataclass
class BehaviorManager:
    behaviors: List[object] | None = None
    current_behavior: Optional[object] = None

    def __post_init__(self) -> None:
        if self.behaviors is None:
            self.behaviors = [
                FollowLineBehavior("FOLLOW_LINE"),
                SearchLineBehavior("SEARCH_LINE"),
                GapBehavior("GAP"),
                IntersectionBehavior("INTERSECTION"),
                ObstacleBehavior("OBSTACLE"),
                RampBehavior("RAMP"),
                RescueBehavior("RESCUE"),
                SearchBallBehavior("SEARCH_BALL"),
                AlignBallBehavior("ALIGN_BALL"),
                CaptureBallBehavior("CAPTURE_BALL"),
                SearchSafeZoneBehavior("SEARCH_SAFE_ZONE"),
                DropBallBehavior("DROP_BALL"),
                ReturnToLineBehavior("RETURN_TO_LINE"),
                FinishBehavior("FINISH"),
            ]
        self.current_behavior = self.behaviors[0]

    def change_to(self, behavior_name: str) -> None:
        for behavior in self.behaviors:
            if getattr(behavior, "name", None) == behavior_name:
                self.current_behavior = behavior
                break
