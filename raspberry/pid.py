class PIDController:
    """Controlador PID simples para ajustar o erro lateral da linha."""

    def __init__(self, kp: float, ki: float, kd: float, max_output: float = 100.0) -> None:
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_output = max_output
        self.integral = 0.0
        self.previous_error = 0.0

    def update(self, error: float, reset: bool = False) -> float:
        """Atualiza o controlador PID e retorna saída.
        
        Args:
            error: Erro atual
            reset: Se True, reseta o termo integral para evitar wind-up
        """
        if reset:
            self.integral = 0.0
        
        self.integral += error
        # Clampar integral para evitar wind-up (crescimento indefinido)
        self.integral = max(-100.0, min(100.0, self.integral))
        
        derivative = error - self.previous_error
        self.previous_error = error
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        return max(-self.max_output, min(self.max_output, output))

    def reset(self) -> None:
        self.integral = 0.0
        self.previous_error = 0.0
