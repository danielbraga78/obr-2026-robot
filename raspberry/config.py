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
CAMERA_BACKEND_PREFERENCE = ("opencv", "picamera2", "libcamera", "rpicam")

# ============================================================================
# Configuração Processamento de Visão
# ============================================================================
VISION_PROCESS_WIDTH = 320
VISION_PROCESS_HEIGHT = 240
VISION_ROI = (0.0, 0.0, 1.0, 1.0)
VISION_FRAME_TIMEOUT = 0.2

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
PID_KP = 0.35
PID_KI = 0.01
PID_KD = 0.05
MAX_STEER = 80

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
