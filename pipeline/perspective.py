"""
DocuScan U - Módulo de Corrección de Perspectiva y Detección de Bordes
Fase 1 del Pipeline
"""

import cv2
import numpy as np


def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Ordena 4 puntos en el sentido horario:
    [top-left, top-right, bottom-right, bottom-left]
    """
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # Top-left (menor suma x+y)
    rect[2] = pts[np.argmax(s)]  # Bottom-right (mayor suma x+y)

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # Top-right (menor diferencia y-x)
    rect[3] = pts[np.argmax(diff)]  # Bottom-left (mayor diferencia y-x)

    return rect


def detect_document_contour(image: np.ndarray, max_eval_dim: int = 1200):
    """
    Detecta automáticamente los 4 vértices del documento en la fotografía.
    Retorna los 4 puntos ordenados a escala completa y una máscara/imagen de depuración.
    """
    orig_h, orig_w = image.shape[:2]
    scale = max_eval_dim / max(orig_h, orig_w) if max(orig_h, orig_w) > max_eval_dim else 1.0

    if scale < 1.0:
        new_w, new_h = int(orig_w * scale), int(orig_h * scale)
        small = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    else:
        small = image.copy()

    # Preprocesamiento para detección de contornos
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY) if len(small.shape) == 3 else small.copy()
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Detección de bordes con Canny + Otsu para umbral automático
    high_thresh, _ = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    low_thresh = 0.5 * high_thresh
    edges = cv2.Canny(blurred, low_thresh, high_thresh)

    # Dilatación y cierre morfológico para cerrar bordes discontinuos
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    doc_cnt = None
    min_area = (small.shape[0] * small.shape[1]) * 0.15  # al menos 15% del área

    for cnt in contours[:5]:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            doc_cnt = approx.reshape(4, 2)
            break

    # Si no se encontró un cuadrilátero perfecto, intentar con el rectángulo orientado de área mínima
    if doc_cnt is None and len(contours) > 0 and cv2.contourArea(contours[0]) >= min_area:
        rect = cv2.minAreaRect(contours[0])
        box = cv2.boxPoints(rect)
        doc_cnt = box

    # Fallback: margen del 5% si la foto ya está recortada o el fondo es muy confuso
    if doc_cnt is None:
        margin_x = int(orig_w * 0.03)
        margin_y = int(orig_h * 0.03)
        pts = np.array([
            [margin_x, margin_y],
            [orig_w - margin_x, margin_y],
            [orig_w - margin_x, orig_h - margin_y],
            [margin_x, orig_h - margin_y]
        ], dtype=np.float32)
        return order_points(pts)

    # Escalar puntos a la dimensión original
    scaled_pts = doc_cnt.astype(np.float32) / scale
    return order_points(scaled_pts)


def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """
    Aplica corrección de perspectiva (homografía) usando los 4 puntos del cuadrilátero.
    Retorna la imagen corregida con vista ortogonal de la hoja.
    """
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    # Ancho del nuevo documento: máximo entre la base y la cima
    width_a = np.hypot(br[0] - bl[0], br[1] - bl[1])
    width_b = np.hypot(tr[0] - tl[0], tr[1] - tl[1])
    max_w = max(int(width_a), int(width_b))

    # Alto del nuevo documento: máximo entre el lateral izquierdo y derecho
    height_a = np.hypot(tr[0] - br[0], tr[1] - br[1])
    height_b = np.hypot(tl[0] - bl[0], tl[1] - bl[1])
    max_h = max(int(height_a), int(height_b))

    # Asegurar dimensiones válidas
    max_w = max(max_w, 200)
    max_h = max(max_h, 200)

    # Coordenadas de destino para la vista frontal plana
    dst = np.array([
        [0, 0],
        [max_w - 1, 0],
        [max_w - 1, max_h - 1],
        [0, max_h - 1]
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(
        image,
        M,
        (max_w, max_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )

    return warped

