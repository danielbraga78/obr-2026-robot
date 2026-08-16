"""Métricas de forma compartilhadas pelos detectores.

Na arena de 2026 a cor sozinha não distingue os objetos: a linha de entrada da
área de resgate é prateada como uma das bolas, e a linha de saída é preta como a
outra. Nos dois pares a cor é idêntica e **só a forma separa** — por isso estas
métricas ficam num módulo próprio, usado por mais de um detector.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class ShapeMetrics:
    area: float
    perimeter: float
    circularity: float  # 4·π·área / perímetro², ~1.0 no círculo perfeito
    aspect: float  # maior lado / menor lado do minAreaRect
    center_x: float
    center_y: float
    base_y: float  # maior y do contorno: onde o objeto toca o chão


def contour_metrics(contour: np.ndarray) -> ShapeMetrics:
    area = float(cv2.contourArea(contour))
    perimeter = float(cv2.arcLength(contour, True))
    circularity = (4.0 * math.pi * area / (perimeter * perimeter)) if perimeter > 0 else 0.0

    (_, _), (width, height), _ = cv2.minAreaRect(contour)
    longer, shorter = max(width, height), min(width, height)
    aspect = (longer / shorter) if shorter > 0 else float("inf")

    moments = cv2.moments(contour)
    if moments["m00"]:
        center_x = moments["m10"] / moments["m00"]
        center_y = moments["m01"] / moments["m00"]
    else:
        center_x, center_y = float(contour[:, 0, 0].mean()), float(contour[:, 0, 1].mean())

    return ShapeMetrics(
        area=area,
        perimeter=perimeter,
        circularity=circularity,
        aspect=aspect,
        center_x=center_x,
        center_y=center_y,
        base_y=float(contour[:, 0, 1].max()),
    )


def looks_like_ball(metrics: ShapeMetrics, min_area: float, min_circularity: float, max_aspect: float) -> bool:
    """Aceita o blob como bola.

    Os dois critérios de forma são redundantes de propósito: um erro de
    segmentação que infle o perímetro derruba a circularidade sem afetar o
    aspecto, e vice-versa. Medido em formas sintéticas na escala do quadro
    processado, bolas ficam em circularidade 0,81 a 0,89 com aspecto 1,00; o pior
    caso de linha (trecho curto na diagonal) fica em 0,51 com aspecto 3,89.
    """
    return (
        metrics.area >= min_area
        and metrics.circularity >= min_circularity
        and metrics.aspect <= max_aspect
    )


def looks_like_line(metrics: ShapeMetrics, min_area: float, min_aspect: float) -> bool:
    """Aceita o blob como linha ou faixa no chão: alongado, não compacto."""
    return metrics.area >= min_area and metrics.aspect >= min_aspect


def clean_mask(mask: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
