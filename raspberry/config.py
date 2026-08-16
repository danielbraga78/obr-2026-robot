from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# ============================================================================
# Configuração Serial (Comunicação com Arduino)
# ============================================================================
SERIAL_MODE = "auto"  # "auto", "usb", "uart"
SERIAL_PORT = "auto"  # "auto", "/dev/ttyUSB0", "/dev/ttyAMA0", etc.
SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT = 0.1
SERIAL_RECONNECT_DELAY = 1.0
SERIAL_HEARTBEAT_INTERVAL = 1.0
SERIAL_HEARTBEAT_TIMEOUT = 2.5

# ============================================================================
# Configuração Câmera
# ============================================================================
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
CAMERA_BACKEND = "auto"  # "auto", "picamera2", "libcamera", "rpicam", "opencv"
CAMERA_RECONNECT_DELAY = 0.5
# picamera2 primeiro: é o caminho nativo da câmera CSI no Raspberry Pi OS Bookworm.
# Os backends GStreamer só funcionam se o OpenCV foi compilado com GStreamer
# (o wheel do pip não é); opencv fica por último como fallback para webcam USB.
CAMERA_BACKEND_PREFERENCE = ("picamera2", "libcamera", "rpicam", "opencv")
CAMERA_READ_FAILURE_LIMIT = 3  # Falhas seguidas de leitura antes de reabrir o backend
CAMERA_WARMUP_FRAMES = 3  # Frames descartados na abertura (auto-exposição)
CAMERA_MAX_RECONNECT_DELAY = 5.0  # Teto do backoff quando não há câmera presente
CAMERA_DIAGNOSTIC_INTERVAL = 15.0  # Intervalo entre diagnósticos repetidos no log

# ============================================================================
# Configuração do Preview (janela na tela do Raspberry Pi)
# ============================================================================
# "auto" = mostra se houver display (DISPLAY/WAYLAND_DISPLAY definidos)
# "on"   = tenta sempre (útil para forçar via SSH com X11 forwarding)
# "off"  = desliga
# A variável de ambiente ROBOT_PREVIEW sobrepõe este valor.
PREVIEW_MODE = "auto"
PREVIEW_FPS = 15  # Taxa da janela; não afeta o loop de controle
PREVIEW_WINDOW_NAME = "OBR 2026 - Visao do Robo"
PREVIEW_SHOW_OVERLAY = True  # Desenha ROI, linha detectada, estado e comando

# ============================================================================
# Configuração Processamento de Visão
# ============================================================================
VISION_PROCESS_WIDTH = 320
VISION_PROCESS_HEIGHT = 240
# (x0, y0, x1, y1) normalizados. Para seguir linha usamos só a faixa inferior do
# quadro: é a parte da pista logo à frente do robô. Usar o quadro inteiro mistura
# a linha próxima com curvas distantes e distorce o erro do PID.
VISION_ROI = (0.0, 0.55, 1.0, 1.0)
VISION_FRAME_TIMEOUT = 0.2

# Detecção da linha
# "adaptive" usa Otsu no canal V e se ajusta sozinho à iluminação da arena.
# "hsv" usa os limiares fixos LINE_MIN/LINE_MAX abaixo (frágil: fita preta sob
# luz forte costuma ler V entre 90 e 130, acima do limite fixo).
LINE_THRESHOLD_MODE = "adaptive"
LINE_MIN_CONTRAST = 25  # Diferença mínima entre linha e piso para aceitar a máscara
LINE_MAX_COVERAGE = 0.6  # Acima disso a "linha" virou o quadro todo: rejeita
LINE_MIN_AREA = 100  # Área mínima do contorno, em pixels do quadro processado

# Thresholds para detectores de cor (HSV)
LINE_MIN = (0, 0, 0)
LINE_MAX = (180, 150, 80)
BALL_MIN = (20, 80, 80)
BALL_MAX = (40, 255, 255)
RESCUE_MIN = (20, 80, 120)
RESCUE_MAX = (40, 255, 255)
SAFE_ZONE_MIN = (30, 80, 80)
SAFE_ZONE_MAX = (70, 255, 255)

# ============================================================================
# Configuração Detecção de Obstáculos (Vision-based)
# ============================================================================
# O robô agora usa APENAS visão computacional para detectar obstáculos.
# Nenhum sensor ultrassônico, ToF ou LiDAR é obrigatório.
OBSTACLE_DETECTION_ENABLED = True
OBSTACLE_CONFIDENCE_THRESHOLD = 0.3  # 0.0 a 1.0
OBSTACLE_MIN_AREA = 100  # Pixels mínimos para considerar um objeto
OBSTACLE_PROXIMITY_THRESHOLD_CM = 25  # Distância estimada para reagir

# Cada fonte de obstáculo (visão e ultrassônico) mantém a própria flag; a flag
# agregada obstacle_detected é o OU das duas dentro desta janela. Sem isso a
# fonte que reporta "livre" apaga o obstáculo que a outra acabou de ver.
OBSTACLE_SOURCE_TTL = 0.25

# ============================================================================
# Configuração do Sensor Ultrassônico (HC-SR04 no Arduino)
# ============================================================================
# O firmware começa com a medição desligada e só liga ao receber
# "SENSOR,ULTRASONIC,ON". Ligue SENSORS_ENABLED["ultrasonic"] apenas com o
# sensor de fato conectado: com o pino ECHO solto o pulseIn devolve valores
# aleatórios dentro da faixa válida e o robô desvia de obstáculos inexistentes.
ULTRASONIC_MIN_VALID_CM = 2.0  # Abaixo disso o HC-SR04 não mede
ULTRASONIC_MAX_VALID_CM = 400.0  # Acima disso é eco espúrio
ULTRASONIC_MAX_JUMP_CM = 40.0  # Salto máximo entre leituras a 10 Hz
ULTRASONIC_CONFIRM_READINGS = 2  # Leituras próximas seguidas para confirmar
# Reenvia o comando de habilitação enquanto nenhum DIST chegar (o primeiro envio
# se perde no bootloader do Arduino, que reseta quando a porta serial é aberta).
SENSOR_ENABLE_RETRY_INTERVAL = 3.0

# ============================================================================
# Configuração PID (Controle de Navegação)
# ============================================================================
# O erro entregue ao PID é normalizado (-1.0 a 1.0) e a saída é o wz enviado ao
# Arduino, na mesma escala de PWM dos motores (0-255). Ganhos são ponto de
# partida: precisam ser afinados na pista.
PID_KP = 60.0
PID_KI = 0.2
PID_KD = 18.0
MAX_STEER = 80  # Autoridade máxima de giro (PWM)

# Velocidades em unidades de PWM (o Arduino usa 0-255 direto no analogWrite).
# Abaixo de ~60 os motores não vencem o atrito com carga.
BASE_SPEED = 110  # Velocidade em reta
MIN_SPEED = 70  # Velocidade nas curvas fechadas
STEER_SIGN = 1.0  # Use -1.0 se o robô virar para o lado errado

# ============================================================================
# Estados da Máquina de Estados
# ============================================================================
BOOT = "BOOT"
CALIBRATION = "CALIBRATION"
FOLLOW_LINE = "FOLLOW_LINE"
SEARCH_LINE = "SEARCH_LINE"
AVOID_OBSTACLE = "AVOID_OBSTACLE"
ENTER_RESCUE = "ENTER_RESCUE"
SEARCH_BALL = "SEARCH_BALL"
ALIGN_BALL = "ALIGN_BALL"
CAPTURE_BALL = "CAPTURE_BALL"
SEARCH_SAFE_ZONE = "SEARCH_SAFE_ZONE"
DROP_BALL = "DROP_BALL"
FINISH = "FINISH"

STATE_SEQUENCE = [
    BOOT, CALIBRATION, FOLLOW_LINE, SEARCH_LINE, AVOID_OBSTACLE,
    ENTER_RESCUE, SEARCH_BALL, ALIGN_BALL, CAPTURE_BALL,
    SEARCH_SAFE_ZONE, DROP_BALL, FINISH
]

# ============================================================================
# Mapa de Sensores Disponíveis
# ============================================================================
# Sensores atualmente suportados:
# - "camera": Sensor de visão (USB ou CSI) - OBRIGATÓRIO
#
# Sensores opcionais (placeholders para implementação futura):
# - "ultrasonic": Sensor ultrassônico
# - "tof": Sensor Time of Flight
# - "imu": Sensor Inertial Measurement Unit
# - "encoder": Sensores de encoder para odometria
# - "lidar": Sensor LiDAR
#
# Se um sensor não estiver disponível, o sistema funciona sem ele.
# A arquitetura permite adicionar sensores sem modificar o código existente.
SENSORS_ENABLED = {
    "camera": True,  # Obrigatório
    "vision_obstacle_detection": True,  # Detecção de obstáculos por visão
    "ultrasonic": True,  # Sensor ultrassônico do Arduino habilitado quando houver hardware
    "tof": False,  # Não disponível atualmente
    "imu": False,  # Não disponível atualmente
    "encoder": False,  # Não disponível atualmente
    "lidar": False,  # Não disponível atualmente
}


# Nome da flag temporal de cada fonte de obstáculo.
OBSTACLE_SOURCE_FLAGS = {
    "vision": "obstacle_detected_vision",
    "range": "obstacle_detected_range",
}


@dataclass
class RobotContext:
    current_state: str = BOOT
    last_command: Optional[str] = None
    # Agregada: verdadeira quando qualquer fonte viu obstáculo recentemente.
    obstacle_detected: bool = False
    obstacle_detected_vision: bool = False
    obstacle_detected_range: bool = False
    obstacle_distance: Optional[float] = None
    line_center: Optional[float] = None
    rescue_detected: bool = False
    safe_zone_detected: bool = False
    ball_detected: bool = False
    ball_distance: Optional[float] = None
    last_event: Optional[str] = None
    camera_ready: bool = False
    serial_ready: bool = False
    last_detections: dict = field(default_factory=dict)
    _temporal_flags: Dict[str, float] = field(default_factory=dict)
    _event_timestamps: Dict[str, float] = field(default_factory=dict)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"obstacle_detected", "obstacle_detected_vision", "obstacle_detected_range", "rescue_detected", "safe_zone_detected", "ball_detected"} and isinstance(value, bool):
            temporal_flags = getattr(self, "_temporal_flags", None)
            if temporal_flags is None:
                object.__setattr__(self, name, value)
                return
            if value:
                temporal_flags[name] = time.monotonic()
            else:
                temporal_flags.pop(name, None)
        elif name == "last_event":
            event_timestamps = getattr(self, "_event_timestamps", None)
            if event_timestamps is None:
                object.__setattr__(self, name, value)
                return
            if value is None:
                event_timestamps.pop("last_event", None)
            else:
                event_timestamps["last_event"] = time.monotonic()
        object.__setattr__(self, name, value)

    def set_temporal_flag(self, name: str, value: bool, *, now: Optional[float] = None) -> None:
        current_time = time.monotonic() if now is None else now
        if value:
            self._temporal_flags[name] = current_time
        else:
            self._temporal_flags.pop(name, None)
        object.__setattr__(self, name, value)

    def has_recent_temporal_flag(self, name: str, ttl: float, *, now: Optional[float] = None) -> bool:
        current_time = time.monotonic() if now is None else now
        timestamp = self._temporal_flags.get(name)
        if timestamp is None:
            return False
        return (current_time - timestamp) <= ttl

    def set_obstacle_source(self, source: str, value: bool, *, now: Optional[float] = None) -> None:
        """Registra o obstáculo visto por uma fonte específica.

        A flag agregada `obstacle_detected` — a que a Strategy lê — passa a ser o
        OU das fontes recentes. Antes visão e ultrassônico escreviam direto nela
        e se apagavam: o ultrassônico marcava obstáculo a 12 cm e o quadro de
        visão seguinte, sem obstáculo no campo dele, limpava antes de alguém ler.
        """
        flag = OBSTACLE_SOURCE_FLAGS[source]
        self.set_temporal_flag(flag, value, now=now)
        aggregate = any(
            self.has_recent_temporal_flag(name, OBSTACLE_SOURCE_TTL, now=now)
            for name in OBSTACLE_SOURCE_FLAGS.values()
        )
        self.set_temporal_flag("obstacle_detected", aggregate, now=now)

    def clear_obstacle_sources(self, *, now: Optional[float] = None) -> None:
        """Consome o obstáculo: zera as fontes e a agregada.

        Usado pelo estado de desvio. Zerar só a agregada não bastaria — a
        próxima atualização de qualquer fonte a recalcularia como verdadeira a
        partir da fonte antiga, e o robô ficaria desviando do mesmo evento.
        """
        for name in OBSTACLE_SOURCE_FLAGS.values():
            self.set_temporal_flag(name, False, now=now)
        self.set_temporal_flag("obstacle_detected", False, now=now)

    def set_last_event(self, event: Optional[str], *, now: Optional[float] = None) -> None:
        current_time = time.monotonic() if now is None else now
        object.__setattr__(self, "last_event", event)
        if event is None:
            self._event_timestamps.pop("last_event", None)
        else:
            self._event_timestamps["last_event"] = current_time

    def has_recent_event(self, event: str, ttl: float, *, now: Optional[float] = None) -> bool:
        current_time = time.monotonic() if now is None else now
        timestamp = self._event_timestamps.get("last_event")
        if timestamp is None:
            return False
        return self.last_event == event and (current_time - timestamp) <= ttl

    def expire_temporal_signals(self, *, now: Optional[float] = None) -> None:
        current_time = time.monotonic() if now is None else now
        for name, timestamp in list(self._temporal_flags.items()):
            if (current_time - timestamp) > 0.25:
                self._temporal_flags.pop(name, None)
                setattr(self, name, False)

        if self.last_event is not None:
            timestamp = self._event_timestamps.get("last_event")
            if timestamp is not None and (current_time - timestamp) > 1.0:
                self._event_timestamps.pop("last_event", None)
                self.last_event = None

    def refresh_temporal_state(self, *, now: Optional[float] = None) -> None:
        self.expire_temporal_signals(now=now)
