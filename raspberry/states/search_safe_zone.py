from ..state_machine import StateResult


class SearchSafeZoneState:
    def execute(self, context, frame, detectors) -> StateResult:
        return StateResult(command="MOVE,12,0,1", next_state="SEARCH_SAFE_ZONE", log_message="Procurando zona segura")
