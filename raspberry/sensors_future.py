"""
Implementações de sensores futuros (placeholders).

Este módulo contém classes stub para sensores que serão integrados no futuro.
Cada classe implementa a interface apropriada, mas retorna valores padrão
ou informa que o sensor não está disponível.

Sensores:
- UltrasonicSensor: Sensor de distância ultrassônico
- ToFSensor: Sensor Time of Flight
- IMUSensor: Sensor Inertial Measurement Unit
- EncoderSensor: Encoders para odometria
"""

from typing import Optional
from .sensor_interface import (
    DistanceSensor,
    DistanceMeasurement,
    IMUSensor,
    IMUMeasurement,
    EncoderSensor,
)


class UltrasonicSensorFuture(DistanceSensor):
    """
    Placeholder para sensor ultrassônico.
    
    Será implementado quando o hardware for adicionado ao Arduino.
    Pinos sugeridos: A2 (TRIG), A3 (ECHO) no Arduino.
    """
    
    def __init__(self):
        self._available = False
        self._reason = "Sensor ultrassônico não está conectado"
    
    def measure(self) -> Optional[DistanceMeasurement]:
        """Retorna None pois o sensor não está disponível."""
        return None
    
    def is_ready(self) -> bool:
        """Retorna False pois o sensor não está instalado."""
        return False
    
    def get_info(self) -> str:
        """Retorna informação sobre por que o sensor não está disponível."""
        return self._reason


class ToFSensorFuture(DistanceSensor):
    """
    Placeholder para sensor ToF (Time of Flight).
    
    Será implementado quando o hardware for adicionado (ex: VL53L0X, VL53L1X).
    Comunicação: I2C (pinos SDA, SCL).
    """
    
    def __init__(self):
        self._available = False
        self._reason = "Sensor ToF não está conectado"
    
    def measure(self) -> Optional[DistanceMeasurement]:
        """Retorna None pois o sensor não está disponível."""
        return None
    
    def is_ready(self) -> bool:
        """Retorna False pois o sensor não está instalado."""
        return False
    
    def get_info(self) -> str:
        """Retorna informação sobre por que o sensor não está disponível."""
        return self._reason


class IMUSensorFuture(IMUSensor):
    """
    Placeholder para sensor IMU (Inertial Measurement Unit).
    
    Será implementado quando o hardware for adicionado (ex: MPU6050, MPU9250).
    Comunicação: I2C (pinos SDA, SCL).
    
    Fornecerá:
    - Aceleração em 3 eixos
    - Velocidade angular (giroscópio) em 3 eixos
    - Orientação (bússola magnética, opcional)
    """
    
    def __init__(self):
        self._available = False
        self._reason = "Sensor IMU não está conectado"
    
    def read(self) -> IMUMeasurement:
        """Retorna medição padrão (zeros) pois o sensor não está disponível."""
        return IMUMeasurement()
    
    def is_ready(self) -> bool:
        """Retorna False pois o sensor não está instalado."""
        return False
    
    def get_info(self) -> str:
        """Retorna informação sobre por que o sensor não está disponível."""
        return self._reason


class EncoderSensorFuture(EncoderSensor):
    """
    Placeholder para sensores de encoder (odometria).
    
    Será implementado quando encoders forem adicionados aos motores.
    Permitirá estimar a posição do robô através da odometria.
    
    Implementação futura:
    - Ler pulsadores dos encoders do Arduino
    - Calcular distância percorrida em cada roda
    - Estimar posição (x, y, theta) usando cinemática
    """
    
    def __init__(self):
        self._available = False
        self._reason = "Sensores de encoder não estão conectados"
        self._position = (0.0, 0.0, 0.0)  # (x, y, theta)
    
    def get_position(self) -> tuple:
        """Retorna posição estimada (sempre 0,0,0 pois sensor não está disponível)."""
        return self._position
    
    def reset(self) -> None:
        """Reseta a posição para origem."""
        self._position = (0.0, 0.0, 0.0)
    
    def is_ready(self) -> bool:
        """Retorna False pois os encoders não estão instalados."""
        return False
    
    def get_info(self) -> str:
        """Retorna informação sobre por que os sensores não estão disponíveis."""
        return self._reason


class LiDARSensorFuture:
    """
    Placeholder para sensor LiDAR.
    
    Será implementado quando hardware LiDAR for adicionado (ex: RPLiDAR A1, A2).
    Comunicação: UART serial.
    
    Fornecerá:
    - Nuvem de pontos 360°
    - Detecção de obstáculos em todas as direções
    - Mapeamento do ambiente
    """
    
    def __init__(self):
        self._available = False
        self._reason = "Sensor LiDAR não está conectado"
    
    def scan(self) -> Optional[list]:
        """Retorna None pois o sensor não está disponível."""
        return None
    
    def is_ready(self) -> bool:
        """Retorna False pois o sensor não está instalado."""
        return False
    
    def get_info(self) -> str:
        """Retorna informação sobre por que o sensor não está disponível."""
        return self._reason


# Mapa de sensores futuros disponíveis
FUTURE_SENSORS = {
    'ultrasonic': UltrasonicSensorFuture,
    'tof': ToFSensorFuture,
    'imu': IMUSensorFuture,
    'encoder': EncoderSensorFuture,
    'lidar': LiDARSensorFuture,
}


def get_future_sensor_info() -> dict:
    """
    Retorna informações sobre sensores que podem ser adicionados no futuro.
    
    Returns:
        Dicionário com informações de cada sensor
    """
    info = {}
    for name, sensor_class in FUTURE_SENSORS.items():
        if name not in ['encoder', 'lidar']:  # Não precisa instanciar estes
            sensor = sensor_class()
            info[name] = sensor.get_info()
        else:
            info[name] = f"Sensor {name} não está conectado"
    return info
