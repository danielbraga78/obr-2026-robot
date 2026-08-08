from dataclasses import dataclass, field
from typing import Optional

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
    "ultrasonic": False,  # Não disponível atualmente
    "tof": False,  # Não disponível atualmente
    "imu": False,  # Não disponível atualmente
    "encoder": False,  # Não disponível atualmente
    "lidar": False,  # Não disponível atualmente
}


@dataclass
class RobotContext:
    current_state: str = BOOT
    last_command: Optional[str] = None
    obstacle_detected: bool = False
    line_center: Optional[float] = None
    rescue_detected: bool = False
    safe_zone_detected: bool = False
    ball_detected: bool = False
    ball_distance: Optional[float] = None
    last_event: Optional[str] = None
    camera_ready: bool = False
    serial_ready: bool = False
    last_detections: dict = field(default_factory=dict)
