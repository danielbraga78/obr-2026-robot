import time

from .config import PID_DERIVATIVE_FILTER_ALPHA, PID_INTEGRAL_LIMIT


class PIDController:
    """Controlador PID simples para ajustar o erro lateral da linha."""

    def __init__(self, kp: float, ki: float, kd: float, max_output: float = 100.0, now_fn=None) -> None:
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_output = max_output
        self.integral = 0.0
        self.previous_error = 0.0
        self.previous_derivative = 0.0
        self._previous_time = None
        self._now = now_fn or time.monotonic

    def update(self, error: float, reset: bool = False, now: float | None = None) -> float:
        """Atualiza o controlador PID e retorna saída.
        
        Args:
            error: Erro atual
            reset: Se True, reseta o termo integral para evitar wind-up
        """
        if reset:
            self.integral = 0.0

            self.previous_derivative = 0.0
            self._previous_time = None

        current_time = now if now is not None else self._now()
        dt = 0.0 if self._previous_time is None else max(current_time - self._previous_time, 0.0)
        if dt > 0.0:
            self.integral += error * dt
            self.integral = max(-PID_INTEGRAL_LIMIT, min(PID_INTEGRAL_LIMIT, self.integral))
            derivative = (error - self.previous_error) / dt
        else:
            derivative = 0.0

        alpha = max(0.0, min(1.0, PID_DERIVATIVE_FILTER_ALPHA))
        if alpha > 0.0:
            derivative = alpha * derivative + (1.0 - alpha) * self.previous_derivative
        self.previous_error = error
        self.previous_derivative = derivative
        self._previous_time = current_time
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        return max(-self.max_output, min(self.max_output, output))

    def reset(self) -> None:
        self.integral = 0.0
        self.previous_error = 0.0
        self.previous_derivative = 0.0
        self._previous_time = None
