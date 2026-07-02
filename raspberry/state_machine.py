from dataclasses import dataclass
from typing import Optional

from .config import STATE_SEQUENCE


@dataclass
class StateResult:
    command: Optional[str] = None
    next_state: Optional[str] = None
    log_message: Optional[str] = None


class RobotStateMachine:
    """Máquina de estados simples para o robô."""

    def __init__(self, states: dict) -> None:
        self.states = states
        self.current_state = STATE_SEQUENCE[0]

    def transition_to(self, state_name: str) -> None:
        if state_name in self.states:
            self.current_state = state_name

    def run_once(self, context, frame, detectors) -> StateResult:
        if self.current_state not in self.states:
            # Fallback para BOOT se estado é inválido
            self.current_state = STATE_SEQUENCE[0]
            return StateResult(command="STOP", next_state=STATE_SEQUENCE[0], log_message="Estado inválido, resetando para BOOT")
        
        state = self.states[self.current_state]
        result = state.execute(context, frame, detectors)
        if result.next_state and result.next_state in self.states:
            self.transition_to(result.next_state)
        return result
