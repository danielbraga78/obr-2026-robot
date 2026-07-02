import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def format_command(command: Optional[str]) -> str:
    return command or "NO_OP"
