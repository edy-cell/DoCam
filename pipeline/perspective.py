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


def detect_document_contour(image: np.ndarray, max_eval_dim: int = 900) -> np.ndarray:
    """
    Detecta automáticamente los 4 vértices del documento en la fotografía.
    Emplea una estrategia multiescala combinada:
    1. Segmentación radiométrica de fondo vs documento (periferia vs centro).
    2. Umbralización Otsu con cierre morfológico.
    3. Bordes Canny con dilatación controlada.
    4. Aproximación poligonal adaptativa sobre Convex Hull y MinAreaRect de respaldo.
    """
    orig_h, orig_w = image.shape[:2]
    scale = max_eval_dim / max(orig_h, orig_w) if max(orig_h, orig_w) > max_eval_dim else 1.0

    if scale < 1.0:
        new_w, new_h = int(orig_w * scale), int(orig_h * scale)
        small = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    else:
        small = image.copy()

    sh, sw = small.shape[:2]
    total_area = float(sw * sh)

    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY) if len(small.shape) == 3 else small.copy()
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # 1. Muestreo de luminancia del fondo (márgenes exteriores 4%) vs centro del documento
    margin_w = max(5, int(sw * 0.04))
    margin_h = max(5, int(sh * 0.04))
    bg_sample = np.concatenate([
        gray[:margin_h, :].ravel(),
        gray[-margin_h:, :].ravel(),
        gray[:, :margin_w].ravel(),
        gray[:, -margin_w:].ravel()
    ])
    bg_mean = float(np.mean(bg_sample))
    center_sample = gray[int(sh * 0.25):int(sh * 0.75), int(sw * 0.25):int(sw * 0.75)]
    center_mean = float(np.mean(center_sample))

    candidates = []

    # Estrategia A: Máscara por contraste de fondo vs papel
    if abs(center_mean - bg_mean) > 12.0:
        th_val = (bg_mean + center_mean) / 2.0
        mask_bg = (blurred > th_val).astype(np.uint8) * 255 if center_mean > bg_mean else (blurred < th_val).astype(np.uint8) * 255
        k_sz = max(7, int(min(sw, sh) * 0.03))
        if k_sz % 2 == 0:
            k_sz += 1
        mask_bg = cv2.morphologyEx(mask_bg, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k_sz, k_sz)))
        candidates.append(mask_bg)

    # Estrategia B: Otsu directo e invertido
    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    k_sz = max(7, int(min(sw, sh) * 0.025))
    if k_sz % 2 == 0:
        k_sz += 1
    otsu_closed = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k_sz, k_sz)))
    candidates.append(otsu_closed)
    candidates.append(cv2.bitwise_not(otsu_closed))

    # Estrategia C: Canny con dilatación de bordes
    edges = cv2.Canny(blurred, 25, 110)
    dilated_edges = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)), iterations=2)
    candidates.append(dilated_edges)

    best_poly = None
    best_area = 0.0

    # Búsqueda de cuadrilátero convexo óptimo en las máscaras candidatas
    for mask in candidates:
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            area = cv2.contourArea(c)
            if 0.12 * total_area < area < 0.98 * total_area:
                hull = cv2.convexHull(c)
                hull_area = cv2.contourArea(hull)
                peri = cv2.arcLength(hull, True)
                for eps in np.linspace(0.015, 0.08, 14):
                    ap = cv2.approxPolyDP(hull, eps * peri, True)
                    if len(ap) == 4 and cv2.isContourConvex(ap):
                        if hull_area > best_area:
                            best_area = hull_area
                            best_poly = ap.reshape(4, 2)
                        break
        if best_poly is not None and best_area > 0.28 * total_area:
            break

    # Si no se encontró un cuadrilátero exacto, intentar con minAreaRect sobre el contorno dominante
    if best_poly is None:
        for mask in candidates:
            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in cnts:
                area = cv2.contourArea(c)
                if 0.15 * total_area < area < 0.96 * total_area:
                    rect = cv2.minAreaRect(c)
                    best_poly = cv2.boxPoints(rect)
                    best_area = area
                    break
            if best_poly is not None:
                break

    # Fallback inteligente: documento que ocupa casi todo el encuadre (margen mínimo del 2%)
    if best_poly is None:
        m_x = orig_w * 0.02
        m_y = orig_h * 0.02
        pts = np.array([
            [m_x, m_y],
            [orig_w - m_x, m_y],
            [orig_w - m_x, orig_h - m_y],
            [m_x, orig_h - m_y]
        ], dtype=np.float32)
        return order_points(pts)

    scaled_pts = best_poly.astype(np.float32) / scale
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

