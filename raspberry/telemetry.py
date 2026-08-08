from __future__ import annotations

from typing import Any


def format_arduino_payload(context: Any, command: str | None) -> str:
    """Cria um resumo legível do estado visual e do comando enviado ao Arduino."""
    if not command:
        command = "<none>"

    detections = getattr(context, "last_detections", {}) or {}
    line_detection = detections.get("line")
    ball_detection = detections.get("ball")

    parts = [
        f"state={getattr(context, 'current_state', 'UNKNOWN')}",
        f"command={command}",
        f"ball_detected={bool(getattr(context, 'ball_detected', False))}",
        f"ball_distance={getattr(context, 'ball_distance', None)}",
        f"obstacle={bool(getattr(context, 'obstacle_detected', False))}",
        f"rescue={bool(getattr(context, 'rescue_detected', False))}",
        f"safe_zone={bool(getattr(context, 'safe_zone_detected', False))}",
        f"line_error={getattr(line_detection, 'error', None)}",
        f"line_conf={getattr(line_detection, 'confidence', None)}",
        f"ball_error={getattr(ball_detection, 'error', None)}",
        f"ball_conf={getattr(ball_detection, 'confidence', None)}",
    ]
    return " | ".join(parts)
