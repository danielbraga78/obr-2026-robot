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

    def _apply_transition(self, result_next_state: str | None, decision_next_state: str | None) -> None:
        if decision_next_state is not None and decision_next_state in self.states:
            self.transition_to(decision_next_state)
            return
        if result_next_state is not None and result_next_state in self.states:
            self.transition_to(result_next_state)

    def run_once(
        self,
        context,
        frame,
        detectors,
        decision=None,
        strategy_next_state: str | None = None,
    ) -> StateResult:
        """Execute exactly one state under one explicit decision authority.

        ``strategy_next_state`` remains as a compatibility argument for older
        callers. New callers should pass the complete StrategyDecision through
        ``decision`` so transition and command priority are applied together.
        """
        if self.current_state not in self.states:
            # Fallback para BOOT se estado é inválido
            self.current_state = STATE_SEQUENCE[0]
            return StateResult(command="STOP", next_state=STATE_SEQUENCE[0], log_message="Estado inválido, resetando para BOOT")

        decision_next_state = getattr(decision, "next_state", None) if decision is not None else None
        decision_command = getattr(decision, "command", None) if decision is not None else None
        override_next_state = decision_next_state if decision is not None else strategy_next_state

        state = self.states[self.current_state]
        state_name_before_execution = self.current_state
        if override_next_state is not None and override_next_state in self.states:
            self.transition_to(override_next_state)
            if self.current_state != state_name_before_execution:
                state = self.states[self.current_state]

        result = state.execute(context, frame, detectors)

        if override_next_state is not None and override_next_state in self.states:
            result = StateResult(
                command=decision_command if decision_command is not None else result.command,
                next_state=None,
                log_message=result.log_message,
            )
            return result

        if result.next_state is not None and result.next_state in self.states:
            self.transition_to(result.next_state)

        return result
