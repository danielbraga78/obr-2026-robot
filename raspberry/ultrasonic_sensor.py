"""Implementação de sensor ultrassônico HC-SR04 via Arduino.

O Arduino mede a distância usando o sensor ultrassônico HC-SR04
e envia mensagens DIST,<value> quando ativado.

Hardware:
- Pinos Arduino: A2 (TRIG), A3 (ECHO)
- Alimentação: 5V
- Protocolo: UART serial

Configuração:
- Ativar via config: SENSOR_ENABLED['ultrasonic'] = True
- Se desativado, não envia/processa mensagens DIST
"""

import logging
import time
from typing import Optional

from .sensor_interface import DistanceSensor, DistanceMeasurement

logger = logging.getLogger(__name__)


class ArduinoUltrasonicSensor(DistanceSensor):
    """Sensor ultrassônico conectado via Arduino.

    Recebe leituras do Arduino através de mensagens DIST,<centimeters>.
    O Arduino controla o timing e envia as medições periodicamente.
    """

    def __init__(self, serial_transport, update_interval: float = 0.1):
        """Inicializa o sensor ultrassônico.

        Args:
            serial_transport: Instância de SerialTransport para comunicação
            update_interval: Intervalo mínimo entre leituras (segundos)
        """
        self.serial = serial_transport
        self._update_interval = update_interval
        self._last_measurement: Optional[DistanceMeasurement] = None
        self._last_update = 0.0
        self._enabled = False
        self._consecutive_failures = 0
        self._max_failures = 5
        
        logger.info("Sensor ultrassônico inicializado (Arduino HC-SR04)")
    
    def enable(self) -> None:
        """Ativa o sensor ultrassônico no Arduino."""
        if not self._enabled:
            self.serial.send_command("SENSOR,ULTRASONIC,ON")
            self._enabled = True
            logger.info("Sensor ultrassônico ativado")
    
    def disable(self) -> None:
        """Desativa o sensor ultrassônico no Arduino."""
        if self._enabled:
            self.serial.send_command("SENSOR,ULTRASONIC,OFF")
            self._enabled = False
            logger.info("Sensor ultrassônico desativado")
    
    def measure(self) -> Optional[DistanceMeasurement]:
        """Retorna a última leitura do sensor.
        
        Retorna None se o sensor não estiver disponível ou se não houver
        leitura recente.
        """
        now = time.monotonic()
        if not self._enabled or not self.serial.is_connected():
            return None
        
        # Retornar última medição se ainda for recente
        if (self._last_measurement is not None and
            now - self._last_measurement.timestamp < 1.0):
            return self._last_measurement
        
        return None
    
    def is_ready(self) -> bool:
        """Verifica se o sensor está pronto.
        
        Retorna True se:
        - Serial está conectado
        - Sensor está ativado
        - Houve pelo menos uma leitura nos últimos 2 segundos
        """
        if not self._enabled or not self.serial.is_connected():
            return False
        
        if self._last_measurement is None:
            return False
        
        age = time.monotonic() - self._last_measurement.timestamp
        return age < 2.0
    
    def process_message(self, message: str) -> None:
        """Processa mensagens DIST do Arduino.
        
        Formato esperado: DIST,<centimeters>
        
        Args:
            message: Mensagem recebida do Arduino
        """
        if not message.startswith("DIST,"):
            return
        
        try:
            parts = message.split(",")
            if len(parts) != 2:
                logger.debug("Formato DIST inválido: %s", message)
                return
            
            distance_cm = float(parts[1])
            
            # Validar range (sensores ultrassônicos típicos: 2cm a 400cm)
            if distance_cm < 2 or distance_cm > 400:
                logger.debug("Leitura fora do range: %s cm", distance_cm)
                self._consecutive_failures += 1
                return
            
            # Criar medição
            self._last_measurement = DistanceMeasurement(
                distance=distance_cm,
                distance_unit="cm",
                confidence=0.9,  # Ultrassônico é confiável
                timestamp=time.monotonic()
            )
            
            self._consecutive_failures = 0
            logger.debug("Medição ultrassônica: %.1f cm", distance_cm)
        
        except (ValueError, IndexError) as exc:
            logger.debug("Erro ao processar DIST: %s", exc)
            self._consecutive_failures += 1
            
            # Desativar sensor após múltiplas falhas
            if self._consecutive_failures >= self._max_failures:
                logger.warning("Sensor ultrassônico desabilitado após %d falhas",
                             self._max_failures)
                self.disable()
    
    def get_info(self) -> str:
        """Retorna informação sobre o status do sensor."""
        if not self.is_ready():
            return "Ultrassônico não disponível"
        
        if self._last_measurement:
            return f"Ultrassônico: {self._last_measurement.distance:.1f} cm"
        
        return "Ultrassônico: aguardando leitura"
