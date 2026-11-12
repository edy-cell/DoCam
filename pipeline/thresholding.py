"""
DocuScan U - Módulo de Umbralización Adaptativa y Binarización
Fase 4 del Pipeline: Eliminación de sombras, iluminación desigual y separación texto/fondo
"""

import cv2
import numpy as np


def threshold_adaptive_gaussian(image: np.ndarray, block_size: int = 21, c: int = 10) -> np.ndarray:
    """
    Umbralización adaptativa con ponderación Gaussiana local.
    Excelente para compensar gradientes de sombra suaves generados por teléfonos.
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    block_size = block_size if block_size % 2 == 1 else block_size + 1
    block_size = max(3, block_size)
    return cv2.adaptiveThreshold(
        image,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        c
    )


def threshold_adaptive_mean(image: np.ndarray, block_size: int = 21, c: int = 10) -> np.ndarray:
    """Umbralización adaptativa con media aritmética local."""
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    block_size = block_size if block_size % 2 == 1 else block_size + 1
    block_size = max(3, block_size)
    return cv2.adaptiveThreshold(
        image,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        block_size,
        c
    )


def threshold_otsu(image: np.ndarray) -> np.ndarray:
    """Umbralización global óptima mediante método de Otsu."""
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def threshold_sauvola(image: np.ndarray, window_size: int = 25, k: float = 0.2, r: float = 128.0) -> np.ndarray:
    """
    Algoritmo de Sauvola y Pietikäinen:
    T(x,y) = mean(x,y) * (1 + k * (std(x,y) / R - 1))
    Estándar de oro para documentos históricos, formularios y hojas con sombras no uniformes.
    Implementación vectorizada de alto rendimiento mediante boxFilter de OpenCV.
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    w = window_size if window_size % 2 == 1 else window_size + 1
    img_float = image.astype(np.float32)

    # Media local E[X]
    mean = cv2.boxFilter(img_float, cv2.CV_32F, (w, w), borderType=cv2.BORDER_REPLICATE)
    # Media de cuadrados E[X^2]
    mean_sq = cv2.boxFilter(img_float * img_float, cv2.CV_32F, (w, w), borderType=cv2.BORDER_REPLICATE)
    # Varianza Var = E[X^2] - (E[X])^2
    var = np.maximum(mean_sq - (mean * mean), 0.0)
    std = np.sqrt(var)

    threshold = mean * (1.0 + k * ((std / r) - 1.0))
    binary = np.where(img_float >= threshold, 255, 0).astype(np.uint8)
    return binary


def apply_thresholding(image: np.ndarray, method: str = "adaptive_gaussian", **kwargs) -> np.ndarray:
    """Selector de algoritmo de umbralización."""
    method = method.lower()
    if method == "adaptive_gaussian":
        block_size = kwargs.get("block_size", 25)
        c = kwargs.get("c", 11)
        return threshold_adaptive_gaussian(image, block_size=block_size, c=c)
    elif method == "sauvola":
        window_size = kwargs.get("window_size", 25)
        k = kwargs.get("k", 0.2)
        return threshold_sauvola(image, window_size=window_size, k=k)
    elif method == "otsu":
        return threshold_otsu(image)
    elif method == "adaptive_mean":
        block_size = kwargs.get("block_size", 25)
        c = kwargs.get("c", 10)
        return threshold_adaptive_mean(image, block_size=block_size, c=c)
    else:
        return threshold_adaptive_gaussian(image)

