"""Transformações comuns dos comandos de movimento antes da serial."""

from __future__ import annotations

from .config import CAMERA_INVERTED, CURVE_CORRECTION

_MAX_COMMAND_COMPONENT = 255.0
_STOP_COMMANDS = frozenset({"STOP", "EMERGENCY STOP", "EMERGENCY_STOP"})


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _format_component(value: float) -> str:
    rounded = round(value)
    if abs(value - rounded) < 1e-9:
        return str(int(rounded))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def apply_motor_orientation(vx: float, vy: float, wz: float) -> tuple[float, float, float]:
    """Converte movimento relativo à imagem para o referencial do robô."""
    if not CAMERA_INVERTED:
        return vx, vy, wz
    return -vx, -vy, wz


def normalize_motor_command(command: str) -> str:
    """Aplica curva e orientação uma única vez a comandos MOVE.

    Comandos de parada e comandos que não movimentam os motores permanecem
    intactos para que segurança e protocolos existentes não sejam alterados.
    """
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

    wz = _clamp(wz * CURVE_CORRECTION, -_MAX_COMMAND_COMPONENT, _MAX_COMMAND_COMPONENT)
    vx, vy, wz = apply_motor_orientation(vx, vy, wz)
    return f"MOVE,{_format_component(vx)},{_format_component(vy)},{_format_component(wz)}"