from ..state_machine import StateResult
from ..config import SEARCH_SAFE_ZONE_SPEED


class SearchSafeZoneState:
    def execute(self, context, frame, detectors) -> StateResult:
        return StateResult(command=f"MOVE,{SEARCH_SAFE_ZONE_SPEED},0,1", next_state="SEARCH_SAFE_ZONE", log_message="Procurando zona segura")
