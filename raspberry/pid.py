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
        self.proportional_output = 0.0
        self.integral_output = 0.0
        self.derivative_output = 0.0

    def update(
        self,
        error: float,
        reset: bool = False,
        now: float | None = None,
        derivative_output_limit: float | None = None,
    ) -> float:
        """Atualiza o PID usando ``dt`` real e filtro exponencial na derivada.

        ``PID_DERIVATIVE_FILTER_ALPHA`` é o peso da nova derivada: zero mantém
        totalmente a amostra anterior e um desativa a suavização.
        """
        if reset:
            self.reset()

        current_time = now if now is not None else self._now()
        dt = 0.0 if self._previous_time is None else max(current_time - self._previous_time, 0.0)
        derivative = 0.0
        if dt > 0.0:
            derivative = (error - self.previous_error) / dt

        alpha = max(0.0, min(1.0, PID_DERIVATIVE_FILTER_ALPHA))
        if alpha > 0.0:
            derivative = alpha * derivative + (1.0 - alpha) * self.previous_derivative
        derivative_term = self.kd * derivative
        if derivative_output_limit is not None:
            limit = max(0.0, min(self.max_output, derivative_output_limit))
            derivative_term = max(-limit, min(limit, derivative_term))

        previous_integral = self.integral
        candidate_integral = previous_integral
        if dt > 0.0:
            candidate_integral = max(
                -PID_INTEGRAL_LIMIT,
                min(PID_INTEGRAL_LIMIT, previous_integral + error * dt),
            )

        proportional = self.kp * error
        candidate_output = proportional + self.ki * candidate_integral + derivative_term
        saturated = abs(candidate_output) > self.max_output
        integrates_further_into_saturation = (
            (candidate_output > self.max_output and self.ki * error > 0.0)
            or (candidate_output < -self.max_output and self.ki * error < 0.0)
        )
        if saturated and integrates_further_into_saturation:
            candidate_integral = previous_integral
        self.integral = candidate_integral

        self.previous_error = error
        self.previous_derivative = derivative
        self._previous_time = current_time
        self.proportional_output = proportional
        self.integral_output = self.ki * self.integral
        self.derivative_output = derivative_term
        output = proportional + self.integral_output + derivative_term
        return max(-self.max_output, min(self.max_output, output))

    def reset(self) -> None:
        self.integral = 0.0
        self.previous_error = 0.0
        self.previous_derivative = 0.0
        self._previous_time = None
        self.proportional_output = 0.0
        self.integral_output = 0.0
        self.derivative_output = 0.0
