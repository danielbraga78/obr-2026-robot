from __future__ import annotations

import logging
from typing import Optional

from .config import (
    OBSTACLE_PROXIMITY_THRESHOLD_CM,
    ULTRASONIC_CONFIRM_READINGS,
    ULTRASONIC_MAX_JUMP_CM,
    ULTRASONIC_MAX_VALID_CM,
    ULTRASONIC_MIN_VALID_CM,
)

logger = logging.getLogger(__name__)


class UltrasonicMonitor:
    """Filtra as leituras DIST do Arduino antes de virarem obstáculo.

    Uma leitura sozinha não é suficiente. Com o HC-SR04 desconectado o pino ECHO
    fica flutuando e o `pulseIn` do firmware devolve durações aleatórias que caem
    dentro da faixa válida — obstáculos fantasmas que fariam o robô abandonar a
    linha. Duas defesas: exigir leituras próximas consecutivas e descartar
    saltos grandes entre uma leitura e a seguinte (a 10 Hz, 40 cm equivaleria a
    4 m/s, velocidade que este chassi não atinge).

    Consequência a conhecer: um obstáculo que entra de lado no feixe (de 200 cm
    para 15 cm de uma leitura para a outra) leva três leituras, ~300 ms, para ser
    confirmado — a primeira quebra a coerência e as duas seguintes confirmam.
    """

    def __init__(
        self,
        proximity_cm: float = OBSTACLE_PROXIMITY_THRESHOLD_CM,
        confirm_readings: int = ULTRASONIC_CONFIRM_READINGS,
        max_jump_cm: float = ULTRASONIC_MAX_JUMP_CM,
        min_valid_cm: float = ULTRASONIC_MIN_VALID_CM,
        max_valid_cm: float = ULTRASONIC_MAX_VALID_CM,
    ) -> None:
        self.proximity_cm = proximity_cm
        self.confirm_readings = max(1, confirm_readings)
        self.max_jump_cm = max_jump_cm
        self.min_valid_cm = min_valid_cm
        self.max_valid_cm = max_valid_cm
        self._last_distance: Optional[float] = None
        self._close_streak = 0

    def update(self, context, distance_cm: float) -> None:
        """Processa uma leitura e atualiza a fonte "range" do contexto."""
        if not (self.min_valid_cm <= distance_cm <= self.max_valid_cm):
            logger.debug("Leitura ultrassônica fora de faixa ignorada: %.1f cm", distance_cm)
            self._close_streak = 0
            context.set_obstacle_source("range", False)
            return

        previous = self._last_distance
        self._last_distance = distance_cm
        context.obstacle_distance = distance_cm

        coherent = previous is None or abs(distance_cm - previous) <= self.max_jump_cm
        if distance_cm <= self.proximity_cm and coherent:
            self._close_streak += 1
        else:
            self._close_streak = 0

        context.set_obstacle_source("range", self._close_streak >= self.confirm_readings)

    def reset(self) -> None:
        """Descarta o histórico. Chamado quando o Arduino reinicia."""
        self._last_distance = None
        self._close_streak = 0
