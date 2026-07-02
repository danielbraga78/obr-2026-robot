"""
Detector de obstáculos baseado em visão computacional.

Este detector utiliza técnicas de processamento de imagem para identificar
possíveis obstáculos no caminho do robô. Funciona analisando:
- Regiões de baixa luminosidade/sombras
- Mudanças abruptas de cor
- Texturas que indicam objetos
- Profundidade relativa através de perspectiva

Como não há sensor de distância disponível, este detector estima a proximidade
através de:
- Tamanho relativo do objeto na imagem
- Posição do objeto (objetos menores e mais altos estão mais distantes)
- Análise de contornos
"""

import cv2
import numpy as np
from typing import Optional
from dataclasses import dataclass

from ..sensor_interface import (
    ObstacleDetector,
    ObstacleDetectionResult,
)


@dataclass
class ObstacleAnalysis:
    """Resultado detalhado da análise de obstáculos."""
    obstacles_found: int
    primary_obstacle_area: float = 0.0
    primary_obstacle_distance_estimate: Optional[float] = None
    confidence: float = 0.0


class VisionBasedObstacleDetector(ObstacleDetector):
    """
    Detector de obstáculos baseado em análise de imagem.
    
    Estratégia de detecção:
    1. Analisa a imagem capturada pela câmera
    2. Procura por características que indicam obstáculos
    3. Estima a distância relativa através de tamanho e posição
    4. Reporta confiança baseada na análise
    """
    
    def __init__(
        self,
        frame_width: int = 320,
        frame_height: int = 240,
        confidence_threshold: float = 0.3,
        min_obstacle_area: int = 100,
    ):
        """
        Inicializa o detector de obstáculos visual.
        
        Args:
            frame_width: Largura da imagem de entrada (pixels)
            frame_height: Altura da imagem de entrada (pixels)
            confidence_threshold: Limiar de confiança para reportar obstáculos (0.0-1.0)
            min_obstacle_area: Área mínima em pixels para considerar um objeto como obstáculo
        """
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.confidence_threshold = confidence_threshold
        self.min_obstacle_area = min_obstacle_area
        self._ready = False
        self._last_analysis: Optional[ObstacleAnalysis] = None
    
    def set_frame(self, frame: np.ndarray) -> None:
        """
        Define o frame de entrada para análise.
        
        Args:
            frame: Imagem BGR do OpenCV ou None
        """
        if frame is not None:
            self._current_frame = frame
            self._ready = True
        else:
            self._ready = False
    
    def is_ready(self) -> bool:
        """Verifica se há frame disponível para análise."""
        return self._ready and hasattr(self, '_current_frame')
    
    def get_sensor_type(self) -> str:
        """Retorna o tipo de sensor."""
        return "vision"
    
    def detect(self) -> ObstacleDetectionResult:
        """
        Detecta obstáculos na imagem atual.
        
        Returns:
            ObstacleDetectionResult com informações de detecção.
        """
        if not self.is_ready():
            return ObstacleDetectionResult(
                obstacle_detected=False,
                confidence=0.0,
                detection_method="vision"
            )
        
        try:
            analysis = self._analyze_frame(self._current_frame)
            self._last_analysis = analysis
            
            obstacle_detected = (
                analysis.obstacles_found > 0 and
                analysis.confidence >= self.confidence_threshold
            )
            
            return ObstacleDetectionResult(
                obstacle_detected=obstacle_detected,
                obstacle_distance=analysis.primary_obstacle_distance_estimate,
                confidence=analysis.confidence,
                detection_method="vision"
            )
        except Exception as e:
            print(f"Erro ao detectar obstáculos: {e}")
            return ObstacleDetectionResult(
                obstacle_detected=False,
                confidence=0.0,
                detection_method="vision"
            )
    
    def _analyze_frame(self, frame: np.ndarray) -> ObstacleAnalysis:
        """
        Analisa o frame para detectar obstáculos.
        
        Estratégia:
        1. Detecta regiões de baixa luminosidade (possíveis obstáculos)
        2. Procura por contornos
        3. Estima distância relativa
        
        Args:
            frame: Imagem BGR
        
        Returns:
            ObstacleAnalysis com resultados da análise
        """
        # Converter para HSV para análise de luminosidade
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Extrair canal de valor (luminosidade)
        _, _, v = cv2.split(hsv)
        
        # Detectar áreas escuras (possíveis obstáculos à frente)
        # Focar na região central inferior (à frente do robô)
        height, width = frame.shape[:2]
        
        # ROI: centro inferior da imagem (onde seria um obstáculo frontal)
        roi_top = int(height * 0.3)
        roi_bottom = height
        roi_left = int(width * 0.2)
        roi_right = int(width * 0.8)
        
        roi_v = v[roi_top:roi_bottom, roi_left:roi_right]
        
        # Threshold para detectar áreas escuras
        _, dark_mask = cv2.threshold(roi_v, 80, 255, cv2.THRESH_BINARY_INV)
        
        # Encontrar contornos
        contours, _ = cv2.findContours(dark_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Analisar contornos
        obstacles = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= self.min_obstacle_area:
                x, y, w, h = cv2.boundingRect(contour)
                obstacles.append({
                    'area': area,
                    'width': w,
                    'height': h,
                    'x': x + roi_left,
                    'y': y + roi_top,
                })
        
        # Se houver obstáculos detectados
        if obstacles:
            # Ordenar por área (maior primeiro)
            obstacles.sort(key=lambda o: o['area'], reverse=True)
            primary = obstacles[0]
            
            # Estimar distância relativa pelo tamanho
            # Quanto maior o obstáculo na imagem, mais próximo
            normalized_area = primary['area'] / (width * height)
            
            # Estimar distância (0-100cm, onde 100cm = muito distante)
            if normalized_area > 0.1:
                estimated_distance = 20  # Muito próximo
            elif normalized_area > 0.05:
                estimated_distance = 35
            elif normalized_area > 0.02:
                estimated_distance = 50
            else:
                estimated_distance = 75
            
            # Calcular confiança
            # Maior confiança se há vários obstáculos ou um grande
            confidence = min(1.0, normalized_area * 10 + len(obstacles) * 0.1)
            
            return ObstacleAnalysis(
                obstacles_found=len(obstacles),
                primary_obstacle_area=primary['area'],
                primary_obstacle_distance_estimate=estimated_distance,
                confidence=confidence,
            )
        else:
            # Nenhum obstáculo detectado
            return ObstacleAnalysis(
                obstacles_found=0,
                confidence=0.0,
            )
    
    def get_last_analysis(self) -> Optional[ObstacleAnalysis]:
        """Retorna a última análise realizada."""
        return self._last_analysis
