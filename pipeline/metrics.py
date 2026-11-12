"""
DocuScan U - Módulo de Evaluación de Legibilidad y Métricas Visuales
Fase 6 del Pipeline: Cuantificación objetiva de nitidez, contraste, ruido e histogramas
"""

import cv2
import numpy as np


def calculate_rms_contrast(image: np.ndarray) -> float:
    """
    Contraste RMS (Root Mean Square Contrast):
    Desviación estándar de los niveles de gris normalizados en el rango [0, 1].
    Mide la dispersión general de tonalidades en la imagen.
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    norm = image.astype(np.float32) / 255.0
    return float(np.std(norm))


def calculate_michelson_contrast(image: np.ndarray) -> float:
    """
    Contraste de Michelson: (I_max - I_min) / (I_max + I_min).
    Rango [0, 1].
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    p_min = float(np.percentile(image, 2))
    p_max = float(np.percentile(image, 98))
    denom = p_max + p_min
    if denom == 0:
        return 0.0
    return float((p_max - p_min) / denom)


def calculate_sharpness_laplacian(image: np.ndarray) -> float:
    """
    Métrica de Nitidez mediante Varianza del Laplaciano (Tenengrad).
    Un valor mayor indica bordes de caracteres más definidos y menos desenfoque.
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(image, cv2.CV_64F)
    return float(lap.var())


def calculate_snr_estimate(image: np.ndarray) -> float:
    """
    Estimación de Relación Señal-Ruido (SNR en dB):
    10 * log10(mu^2 / sigma^2) en zonas representativas.
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mean_val = float(np.mean(image))
    std_val = float(np.std(image))
    if std_val < 1e-5:
        return 40.0
    snr = 10.0 * np.log10(max((mean_val ** 2) / (std_val ** 2), 1e-4))
    return float(snr)


def calculate_ink_ratio(binary_or_gray: np.ndarray) -> float:
    """
    Calcula el porcentaje de píxeles oscuros (tinta/texto) respecto al total.
    """
    if len(binary_or_gray.shape) == 3:
        img = cv2.cvtColor(binary_or_gray, cv2.COLOR_BGR2GRAY)
    else:
        img = binary_or_gray

    if np.mean(img) > 127:
        dark_pixels = np.sum(img < 128)
    else:
        dark_pixels = np.sum(img > 128)

    total_pixels = img.shape[0] * img.shape[1]
    return float((dark_pixels / total_pixels) * 100.0)


def compute_histogram(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Retorna los valores del histograma y los bordes de los contenedores (0..255)."""
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hist, bins = np.histogram(image.ravel(), 256, [0, 256])
    norm_hist = hist / (hist.sum() + 1e-8)
    return norm_hist, bins[:-1]


def compute_all_metrics(image: np.ndarray) -> dict:
    """Calcula todas las métricas de legibilidad para una imagen dada."""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    return {
        "rms_contrast": calculate_rms_contrast(gray),
        "michelson_contrast": calculate_michelson_contrast(gray),
        "sharpness": calculate_sharpness_laplacian(gray),
        "snr_db": calculate_snr_estimate(gray),
        "brightness_mean": float(np.mean(gray)),
        "ink_ratio_pct": calculate_ink_ratio(gray),
        "dimensions": f"{image.shape[1]} x {image.shape[0]} px"
    }


def compare_metrics(original_metrics: dict, processed_metrics: dict) -> dict:
    """Compara métricas calculando el porcentaje de cambio o mejora."""
    diff = {}
    for key in ["rms_contrast", "sharpness", "snr_db", "michelson_contrast"]:
        orig = original_metrics.get(key, 0.0)
        proc = processed_metrics.get(key, 0.0)
        if orig != 0:
            change_pct = ((proc - orig) / abs(orig)) * 100.0
        else:
            change_pct = 0.0
        diff[key] = {
            "original": orig,
            "processed": proc,
            "delta_pct": change_pct
        }
    return diff

