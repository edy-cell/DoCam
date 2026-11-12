"""
DocuScan U - Módulo de Corrección de Inclinación (Deskew)
Fase 5 del Pipeline: Detección y rectificación angular del texto
"""

import cv2
import numpy as np


def detect_skew_angle_hough(binary_or_gray: np.ndarray, max_angle: float = 30.0) -> float:
    """
    Detecta el ángulo de inclinación predominante del texto usando Transformada Probabilística de Hough.
    Busca líneas de renglones y calcula la mediana de las pendientes.
    """
    img = binary_or_gray.copy()
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Invertir si el fondo es blanco (el texto debe ser blanco para análisis de bordes/líneas)
    if np.mean(img) > 127:
        inv = cv2.bitwise_not(img)
    else:
        inv = img.copy()

    # Operación morfológica para unir caracteres de una misma línea en un bloque horizontal
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 2))
    dilated = cv2.dilate(inv, kernel, iterations=1)

    edges = cv2.Canny(dilated, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=80, maxLineGap=20)

    if lines is None or len(lines) == 0:
        return 0.0

    angles = []
    for line in lines:
        coords = np.asarray(line).ravel()
        if len(coords) < 4:
            continue
        x1, y1, x2, y2 = coords[:4]
        dx = float(x2 - x1)
        dy = float(y2 - y1)
        if dx == 0:
            continue
        angle = np.degrees(np.arctan2(dy, dx))
        if abs(angle) <= max_angle:
            angles.append(angle)

    if len(angles) == 0:
        return 0.0

    return float(np.median(angles))


def detect_skew_angle_min_area(binary: np.ndarray, max_angle: float = 45.0) -> float:
    """
    Detecta el ángulo de inclinación calculando el rectángulo delimitador mínimo
    de todos los píxeles de texto (componentes no vacíos).
    """
    if len(binary.shape) == 3:
        binary = cv2.cvtColor(binary, cv2.COLOR_BGR2GRAY)

    # Asegurar que el texto sea blanco (255) y el fondo negro (0)
    if np.mean(binary) > 127:
        text_pixels = cv2.bitwise_not(binary)
    else:
        text_pixels = binary.copy()

    coords = np.column_stack(np.where(text_pixels > 0))
    if len(coords) < 100:
        return 0.0

    # minAreaRect retorna center, (width, height), angle [-90, 0)
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    if abs(angle) > max_angle:
        return 0.0

    return float(angle)


def rotate_image(image: np.ndarray, angle: float, bg_color: int = 255) -> np.ndarray:
    """
    Rota la imagen según el ángulo dado alrededor de su centro,
    rellenando los nuevos bordes con blanco para simular papel.
    """
    if abs(angle) < 0.1:
        return image.copy()

    h, w = image.shape[:2]
    center = (w // 2, h // 2)

    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Calcular nuevos límites para no recortar esquinas
    cos_val = abs(M[0, 0])
    sin_val = abs(M[0, 1])
    new_w = int((h * sin_val) + (w * cos_val))
    new_h = int((h * cos_val) + (w * sin_val))

    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]

    border_val = (bg_color, bg_color, bg_color) if len(image.shape) == 3 else bg_color
    rotated = cv2.warpAffine(
        image,
        M,
        (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border_val
    )
    return rotated


def deskew(image: np.ndarray, method: str = "hough") -> tuple[np.ndarray, float]:
    """
    Corrige automáticamente la inclinación de la imagen.
    Retorna la imagen rotada y el ángulo corregido en grados.
    """
    if method == "hough":
        angle = detect_skew_angle_hough(image)
    else:
        angle = detect_skew_angle_min_area(image)

    # Si el ángulo es significativo, rotamos (sentido inverso para enderezar)
    corrected_img = rotate_image(image, angle)
    return corrected_img, angle
