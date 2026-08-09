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

    def _apply_transition(self, result_next_state: str | None, strategy_next_state: str | None) -> None:
        if strategy_next_state is not None and strategy_next_state in self.states:
            self.transition_to(strategy_next_state)
            return
        if result_next_state is not None and result_next_state in self.states:
            self.transition_to(result_next_state)

    def run_once(self, context, frame, detectors, strategy_next_state: str | None = None) -> StateResult:
        if self.current_state not in self.states:
            # Fallback para BOOT se estado é inválido
            self.current_state = STATE_SEQUENCE[0]
            return StateResult(command="STOP", next_state=STATE_SEQUENCE[0], log_message="Estado inválido, resetando para BOOT")

        state = self.states[self.current_state]
        result = state.execute(context, frame, detectors)
        self._apply_transition(result.next_state, strategy_next_state)
        return result
