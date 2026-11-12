"""
DocuScan U - Módulo de Escala de Grises y CLAHE
Fase 2 del Pipeline: Normalización tonal y mejora de contraste local
"""

import cv2
import numpy as np


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convierte una imagen a escala de grises si es BGR o RGB."""
    if len(image.shape) == 2:
        return image.copy()
    if image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def apply_clahe(gray: np.ndarray, clip_limit: float = 2.5, tile_size: int = 8) -> np.ndarray:
    """
    Aplica CLAHE (Contrast Limited Adaptive Histogram Equalization).
    Mejora el contraste local de trazos débiles sin sobreexponer ni amplificar ruido en el fondo.
    """
    if len(gray.shape) == 3:
        gray = to_grayscale(gray)

    tile_size = max(2, int(tile_size))
    clahe = cv2.createCLAHE(clipLimit=float(clip_limit), tileGridSize=(tile_size, tile_size))
    enhanced = clahe.apply(gray)
    return enhanced


def adjust_contrast_brightness(gray: np.ndarray, alpha: float = 1.0, beta: int = 0) -> np.ndarray:
    """
    Ajuste lineal de contraste (alpha) y brillo (beta): g(x) = alpha * f(x) + beta.
    """
    return cv2.convertScaleAbs(gray, alpha=alpha, beta=beta)

