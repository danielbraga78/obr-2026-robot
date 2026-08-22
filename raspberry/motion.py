"""Transformações comuns dos comandos de movimento antes da serial."""

from __future__ import annotations

from .config import (
    CAMERA_INVERTED,
    CURVE_CORRECTION,
    MOTOR_DEADBAND_PWM,
    MOTOR_MAX_PWM,
    MOTOR_MIN_MEANINGFUL_PWM,
)

_MAX_COMMAND_COMPONENT = 255.0
_ZERO = 0.5
_STOP_COMMANDS = frozenset({"STOP", "EMERGENCY STOP", "EMERGENCY_STOP"})


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _format_component(value: float) -> str:
    rounded = round(value)
    if abs(value - rounded) < 1e-9:
        return str(int(rounded))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _wheel_speeds(vx: float, vy: float, wz: float) -> tuple[float, float, float, float]:
    """Mesma mistura omni do firmware, para prever o que cada roda receberia."""
    front_left = vx + vy + wz
    front_right = -vx + vy + wz
    rear_left = -vx - vy + wz
    rear_right = vx - vy + wz

    largest = max(abs(front_left), abs(front_right), abs(rear_left), abs(rear_right))
    scale = (MOTOR_MAX_PWM / largest) if largest > MOTOR_MAX_PWM else 1.0
    return (front_left * scale, front_right * scale, rear_left * scale, rear_right * scale)


def _is_expressible(vx: float, vy: float, wz: float) -> bool:
    """Nenhuma roda cai na zona morta, onde o comando não pode ser cumprido."""
    return all(abs(speed) < _ZERO for speed in _wheel_speeds(vx, vy, wz)) or all(
        abs(speed) < _ZERO or abs(speed) >= MOTOR_DEADBAND_PWM for speed in _wheel_speeds(vx, vy, wz)
    )


def fit_to_motor_deadband(vx: float, vy: float, wz: float) -> tuple[float, float, float]:
    """Ajusta o comando ao que os motores conseguem executar.

    Abaixo de MOTOR_DEADBAND_PWM a roda não vence o atrito, e o firmware
    arredondava esses valores para o próprio mínimo — pedindo 110 a uma roda que
    deveria estar quase parada. Na prática a taxa de giro parava de responder ao
    PID a partir de wz≈40: a malha ficava aberta justamente na curva fechada, e
    o robô passava reto.

    Duas saídas, nesta ordem:

    1. **Ampliar o comando inteiro.** Se a razão entre a roda mais rápida e a
       mais lenta couber na faixa útil (255/110 = 2,3), basta multiplicar tudo
       pelo mesmo fator. A trajetória é idêntica, só mais rápida. Comandos
       minúsculos não entram aqui: ampliar 22 vezes um pedido de 5 não é a
       mesma trajetória mais rápida, é um solavanco.
    2. **Sacrificar avanço, nunca curva.** Quando a razão não cabe, a translação
       é reduzida até o giro caber. Numa curva de 90 graus isso transforma o
       movimento em pivô — que é o que a curva pede, e o único formato que os
       motores executam com fidelidade.
    """
    speeds = _wheel_speeds(vx, vy, wz)
    moving = [abs(speed) for speed in speeds if abs(speed) >= _ZERO]
    if not moving:
        return vx, vy, wz
    if min(moving) >= MOTOR_DEADBAND_PWM:
        return vx, vy, wz

    # Margem contra arredondamento: sem ela a roda mais lenta pousa em 109,99.
    gain = (MOTOR_DEADBAND_PWM / min(moving)) * 1.001
    if max(moving) >= MOTOR_MIN_MEANINGFUL_PWM and max(moving) * gain <= MOTOR_MAX_PWM:
        return vx * gain, vy * gain, wz * gain

    for step in range(1, 21):
        scale = 1.0 - (step / 20.0)
        if _is_expressible(vx * scale, vy * scale, wz):
            return vx * scale, vy * scale, wz

    # Nenhuma redução resolve: o giro pedido só existe como pivô. Vale a pena
    # quando o comando é de curva de verdade; um ajuste fino de rumo vira um
    # solavanco se for elevado ao mínimo dos motores, então esse vira parada.
    if abs(wz) >= MOTOR_MIN_MEANINGFUL_PWM:
        pivot = MOTOR_DEADBAND_PWM if wz > 0 else -MOTOR_DEADBAND_PWM
        return 0.0, 0.0, pivot if abs(wz) < MOTOR_DEADBAND_PWM else wz

    # Nada coube: devolve o comando original em vez de parar. O firmware zera as
    # rodas que não conseguem girar, o que é uma aproximação ruim do movimento
    # pedido — mas parar o robô é pior que se mover de forma aproximada.
    return vx, vy, wz


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
    vx, vy, wz = fit_to_motor_deadband(vx, vy, wz)
    vx, vy, wz = apply_motor_orientation(vx, vy, wz)
    return f"MOVE,{_format_component(vx)},{_format_component(vy)},{_format_component(wz)}"