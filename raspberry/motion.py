"""Transformações comuns dos comandos de movimento antes da serial."""

from __future__ import annotations

import math

from .config import (
    CAMERA_INVERTED,
    CURVE_CORRECTION,
    MOTOR_MAX_PWM,
    MOTOR_MIN_PWM,
    MOTOR_PWM_GAINS,
)

_STOP_COMMANDS = frozenset({"STOP", "EMERGENCY STOP", "EMERGENCY_STOP"})
_WHEEL_MATRIX = (
    (1.0, 1.0, 1.0),
    (1.0, -1.0, -1.0),
    (1.0, -1.0, 1.0),
    (1.0, 1.0, -1.0),
)
_ZERO_EPSILON = 1e-9


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _format_component(value: float) -> str:
    rounded = round(value)
    if abs(value - rounded) < 1e-9:
        return str(int(rounded))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _wheel_speeds(vx: float, vy: float, wz: float) -> tuple[float, float, float, float]:
    """Mistura omni do firmware, com a mesma saturação global de PWM."""
    speeds = tuple(
        row[0] * vx + row[1] * vy + row[2] * wz
        for row in _WHEEL_MATRIX
    )
    largest = max(abs(speed) for speed in speeds)
    scale = MOTOR_MAX_PWM / largest if largest > MOTOR_MAX_PWM else 1.0
    return tuple(speed * scale for speed in speeds)


def _firmware_wheel_pwms(
    vx: float,
    vy: float,
    wz: float,
    motor_min_pwm: tuple[int, int, int, int] | None = None,
    motor_gains: tuple[float, float, float, float] | None = None,
) -> tuple[int, int, int, int]:
    """Simula truncamento, ganho e corte de PWM usados pelos firmwares atuais."""
    minima = motor_min_pwm or MOTOR_MIN_PWM
    gains = motor_gains or MOTOR_PWM_GAINS
    speeds = _wheel_speeds(vx, vy, wz)
    outputs = []
    for speed, minimum, gain in zip(speeds, minima, gains):
        requested = int(speed)
        duty = int(math.floor(abs(requested) * gain + 0.5))
        duty = min(MOTOR_MAX_PWM, duty)
        if duty < minimum:
            duty = 0
        outputs.append(-duty if requested < 0 else duty)
    return tuple(outputs)


def _body_velocity_from_wheels(wheels: tuple[int, int, int, int]) -> tuple[float, float, float]:
    m1, m2, m3, m4 = wheels
    return (
        (m1 + m2 + m3 + m4) / 4.0,
        (m1 - m2 - m3 + m4) / 4.0,
        (m1 - m2 + m3 - m4) / 4.0,
    )


def _realized_is_within_request(
    realized: tuple[float, float, float],
    target: tuple[float, float, float],
) -> bool:
    for actual, requested in zip(realized, target):
        if abs(requested) <= _ZERO_EPSILON:
            if abs(actual) > 0.51:
                return False
        elif (
            abs(actual) <= 0.51
            or actual * requested < -0.51
            or abs(actual) > abs(requested) + 0.51
        ):
            return False
    return True


def _axis_candidates(
    values: tuple[float, float, float],
    signs: tuple[float, float, float],
    limits: tuple[float, float, float],
    axis: int,
    minima: tuple[int, int, int, int],
    gains: tuple[float, float, float, float],
) -> set[float]:
    """Pontos onde uma roda cruza zero, o mínimo calibrado ou o PWM máximo."""
    candidates = {0.0, limits[axis], values[axis]}
    for motor_index, row in enumerate(_WHEEL_MATRIX):
        coefficient = row[axis] * signs[axis]
        if coefficient == 0:
            continue
        offset = sum(
            row[index] * signs[index] * values[index]
            for index in range(3)
            if index != axis
        )
        minimum_command = max(1, int(math.ceil((minima[motor_index] - 0.5) / gains[motor_index])))
        for boundary in (0.0, float(minimum_command), -float(minimum_command), float(MOTOR_MAX_PWM), -float(MOTOR_MAX_PWM)):
            candidate = (boundary - offset) / coefficient
            if -1e-9 <= candidate <= limits[axis] + 1e-9:
                candidates.add(_clamp(candidate, 0.0, limits[axis]))
    return candidates


def fit_to_motor_deadband(
    vx: float,
    vy: float,
    wz: float,
    motor_min_pwm: tuple[int, int, int, int] | None = None,
) -> tuple[float, float, float]:
    """Projeta um pedido no conjunto de movimentos que o firmware pode aplicar.

    A projeção minimiza o erro quadrático no vetor (vx, vy, wz), mantém os
    sinais e nunca amplia uma componente solicitada. O firmware zera cada roda
    abaixo de seu mínimo; a busca modela esse corte, o truncamento e a saturação
    antes de comparar candidatos. Se não houver movimento útil, o resultado é
    zero em vez de um pivô ou avanço introduzido implicitamente.
    """
    minima = motor_min_pwm or MOTOR_MIN_PWM
    gains = MOTOR_PWM_GAINS
    requested = (vx, vy, wz)
    if any(not math.isfinite(value) for value in requested):
        return 0.0, 0.0, 0.0

    largest = max(abs(speed) for speed in _wheel_speeds(*requested))
    scale = MOTOR_MAX_PWM / largest if largest > MOTOR_MAX_PWM else 1.0
    target = tuple(value * scale for value in requested)
    signs = tuple(1.0 if value > 0 else -1.0 if value < 0 else 0.0 for value in target)
    limits = tuple(abs(value) for value in target)

    target_wheels = _firmware_wheel_pwms(*target, minima, gains)
    raw_wheels = _wheel_speeds(*target)
    if all(
        abs(raw) < 0.5 or abs(actual) >= minimum
        for raw, actual, minimum in zip(raw_wheels, target_wheels, minima)
    ):
        return target

    target_velocity = target

    def evaluate(values: tuple[float, float, float]):
        command = tuple(signs[i] * values[i] for i in range(3))
        output = _firmware_wheel_pwms(*command, minima, gains)
        realized = _body_velocity_from_wheels(output)
        if not _realized_is_within_request(realized, target_velocity):
            return (math.inf, math.inf), command
        error = sum((actual - goal) ** 2 for actual, goal in zip(realized, target_velocity))
        command_delta = sum((command[i] - target_velocity[i]) ** 2 for i in range(3))
        return (error, command_delta), command

    starts = [
        limits,
        (0.0, 0.0, 0.0),
        (0.0, limits[1], limits[2]),
        (limits[0], 0.0, limits[2]),
        (limits[0], limits[1], 0.0),
    ]
    best_score = (math.inf, math.inf)
    best_command = (0.0, 0.0, 0.0)
    for start in starts:
        values = tuple(start)
        for _ in range(6):
            changed = False
            for axis in range(3):
                if limits[axis] <= _ZERO_EPSILON:
                    continue
                axis_best_score, _ = evaluate(values)
                axis_best = values[axis]
                for candidate in _axis_candidates(values, signs, limits, axis, minima, gains):
                    trial = list(values)
                    trial[axis] = candidate
                    score, _ = evaluate(tuple(trial))
                    if score < axis_best_score:
                        axis_best_score = score
                        axis_best = candidate
                if axis_best != values[axis]:
                    updated = list(values)
                    updated[axis] = axis_best
                    values = tuple(updated)
                    changed = True
            if not changed:
                break
        score, command = evaluate(values)
        if score < best_score:
            best_score, best_command = score, command

    if not any(abs(pwm) for pwm in _firmware_wheel_pwms(*best_command, minima, gains)):
        return 0.0, 0.0, 0.0
    return best_command


def apply_motor_orientation(vx: float, vy: float, wz: float) -> tuple[float, float, float]:
    """A câmera já entrega a imagem no referencial usado pelo controlador."""
    return vx, vy, wz


def normalize_motor_command(
    command: str,
    motor_min_pwm: tuple[int, int, int, int] | None = None,
) -> str:
    """Mantém sinais e limita MOVE ao conjunto executável do firmware."""
    normalized = command.strip()
    if not normalized or normalized.upper() in _STOP_COMMANDS:
        return normalized
    parts = normalized.split(",")
    if len(parts) != 4 or parts[0].upper() != "MOVE":
        return normalized
    try:
        vx, vy, wz = (float(value) for value in parts[1:])
    except ValueError:
        return normalized
    if any(not math.isfinite(value) for value in (vx, vy, wz)):
        return "STOP"

    wz = _clamp(wz * CURVE_CORRECTION, -MOTOR_MAX_PWM, MOTOR_MAX_PWM)
    vx, vy, wz = fit_to_motor_deadband(vx, vy, wz, motor_min_pwm)
    vx, vy, wz = apply_motor_orientation(vx, vy, wz)
    if not any(abs(value) >= 0.5 for value in (vx, vy, wz)):
        return "STOP"
    return f"MOVE,{_format_component(vx)},{_format_component(vy)},{_format_component(wz)}"
