"""
Interfaces abstratas para sensores.

Este módulo fornece interfaces genéricas para diferentes tipos de sensores.
Cada sensor deve implementar as interfaces apropriadas para ser integrado
ao sistema de percepção do robô.

Sensores atualmente suportados:
- Câmera (USB ou CSI): implementado e obrigatório
- Ultrassônico: placeholder para implementação futura
- ToF (Time of Flight): placeholder para implementação futura
- IMU (Inertial Measurement Unit): placeholder para implementação futura
- Encoders: placeholder para implementação futura
- LiDAR: placeholder para implementação futura
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ObstacleDetectionResult:
    """Resultado da detecção de obstáculos."""
    obstacle_detected: bool
    obstacle_distance: Optional[float] = None  # em centímetros
    confidence: float = 0.0  # 0.0 a 1.0
    detection_method: str = "unknown"  # "vision", "ultrasonic", "tof", etc.


@dataclass
class DistanceMeasurement:
    """Medição de distância de um sensor."""
    distance_cm: float
    confidence: float = 0.0  # 0.0 a 1.0
    sensor_type: str = "unknown"


@dataclass
class IMUMeasurement:
    """Medição de IMU (aceleração, giroscópio, etc.)."""
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 0.0
    gyro_x: float = 0.0
    gyro_y: float = 0.0
    gyro_z: float = 0.0
    compass_heading: Optional[float] = None  # 0-360 graus


class ObstacleDetector(ABC):
    """Interface abstrata para detectores de obstáculos."""
    
    @abstractmethod
    def detect(self) -> ObstacleDetectionResult:
        """
        Detecta obstáculos usando o sensor específico.
        
        Returns:
            ObstacleDetectionResult com informações de detecção.
        """
        pass
    
    @abstractmethod
    def is_ready(self) -> bool:
        """Verifica se o sensor está pronto para uso."""
        pass
    
    @abstractmethod
    def get_sensor_type(self) -> str:
        """Retorna o tipo de sensor (ex: 'vision', 'ultrasonic', 'tof')."""
        pass


class DistanceSensor(ABC):
    """Interface abstrata para sensores de distância."""
    
    @abstractmethod
    def measure(self) -> Optional[DistanceMeasurement]:
        """
        Mede a distância até um objeto.
        
        Returns:
            DistanceMeasurement ou None se a medição falhar.
        """
        pass
    
    @abstractmethod
    def is_ready(self) -> bool:
        """Verifica se o sensor está pronto para uso."""
        pass


class IMUSensor(ABC):
    """Interface abstrata para sensores IMU."""
    
    @abstractmethod
    def read(self) -> IMUMeasurement:
        """
        Lê dados do IMU.
        
        Returns:
            IMUMeasurement com os dados do sensor.
        """
        pass
    
    @abstractmethod
    def is_ready(self) -> bool:
        """Verifica se o sensor está pronto para uso."""
        pass


class EncoderSensor(ABC):
    """Interface abstrata para encoders (odometria)."""
    
    @abstractmethod
    def get_position(self) -> tuple[float, float, float]:
        """
        Obtém a posição estimada (x, y, theta).
        
        Returns:
            Tupla (x, y, theta) em unidades de comprimento e radianos.
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reseta a posição para (0, 0, 0)."""
        pass
    
    @abstractmethod
    def is_ready(self) -> bool:
        """Verifica se o sensor está pronto para uso."""
        pass


class SensorManager:
    """
    Gerenciador central de sensores.
    
    Coordena múltiplos sensores e fornece uma interface unificada
    para o resto do sistema. Sensores podem ser adicionados ou removidos
    dinamicamente.
    """
    
    def __init__(self):
        self._obstacle_detectors: dict[str, ObstacleDetector] = {}
        self._distance_sensors: dict[str, DistanceSensor] = {}
        self._imu_sensors: dict[str, IMUSensor] = {}
        self._encoder_sensors: dict[str, EncoderSensor] = {}
    
    def register_obstacle_detector(self, name: str, detector: ObstacleDetector) -> None:
        """Registra um novo detector de obstáculos."""
        self._obstacle_detectors[name] = detector
    
    def register_distance_sensor(self, name: str, sensor: DistanceSensor) -> None:
        """Registra um novo sensor de distância."""
        self._distance_sensors[name] = sensor
    
    def register_imu_sensor(self, name: str, sensor: IMUSensor) -> None:
        """Registra um novo sensor IMU."""
        self._imu_sensors[name] = sensor
    
    def register_encoder_sensor(self, name: str, sensor: EncoderSensor) -> None:
        """Registra um novo sensor de encoder."""
        self._encoder_sensors[name] = sensor
    
    def detect_obstacles(self) -> list[ObstacleDetectionResult]:
        """
        Executa detecção de obstáculos em todos os sensores registrados.
        
        Returns:
            Lista de resultados de detecção de todos os sensores.
        """
        results = []
        for name, detector in self._obstacle_detectors.items():
            if detector.is_ready():
                try:
                    result = detector.detect()
                    results.append(result)
                except Exception as e:
                    print(f"Erro ao executar detector '{name}': {e}")
        return results
    
    def get_distance_measurements(self) -> list[DistanceMeasurement]:
        """
        Obtém medições de distância de todos os sensores registrados.
        
        Returns:
            Lista de medições de todos os sensores.
        """
        measurements = []
        for name, sensor in self._distance_sensors.items():
            if sensor.is_ready():
                try:
                    measurement = sensor.measure()
                    if measurement is not None:
                        measurements.append(measurement)
                except Exception as e:
                    print(f"Erro ao ler sensor de distância '{name}': {e}")
        return measurements
    
    def is_system_ready(self) -> bool:
        """
        Verifica se pelo menos o sensor de visão está pronto.
        
        O sistema pode funcionar apenas com visão, mas alertará
        se sensores opcionais não estiverem disponíveis.
        """
        return any(detector.is_ready() for detector in self._obstacle_detectors.values())
