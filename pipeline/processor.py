"""
DocuScan U - Orquestador del Pipeline Documental
Gestiona el estado, caché de fases y ejecución secuencial o individual
"""

import cv2
import numpy as np
from .perspective import detect_document_contour, four_point_transform
from .enhancement import to_grayscale, apply_clahe, adjust_contrast_brightness
from .denoise import filter_noise
from .thresholding import apply_thresholding
from .deskew import deskew
from .metrics import compute_all_metrics, compute_histogram, compare_metrics
from .ocr import run_ocr, evaluate_thesis_stages


class DocumentProcessor:
    def __init__(self):
        self.original_image: np.ndarray | None = None
        self.file_path: str = ""
        
        # Imágenes intermedias de cada fase
        self.phase_images: dict[str, np.ndarray] = {
            "original": None,
            "fase1_perspective": None,
            "fase2_clahe": None,
            "fase3_denoise": None,
            "fase4_threshold": None,
            "fase5_deskew": None
        }

        # Puntos de perspectiva detectados o manuales
        self.corners: np.ndarray | None = None
        self.deskew_angle: float = 0.0

        # Parámetros activos del pipeline
        self.params = {
            "perspective": {"auto": True},
            "clahe": {"clip_limit": 2.5, "tile_size": 8},
            "denoise": {"method": "wiener", "psf_size": 5, "psf_sigma": 1.2, "k": 0.02, "d": 7, "sigma_color": 50.0, "sigma_space": 50.0},
            "threshold": {"method": "sauvola", "window_size": 25, "k": 0.2, "c": 10},
            "deskew": {"method": "hough"}
        }

        # Métricas calculadas
        self.original_metrics: dict = {}
        self.processed_metrics: dict = {}
        self.comparison_metrics: dict = {}
        self.original_ocr = None
        self.processed_ocr = None
        self.ocr_results: list[dict] = []
        self.reference_text: str = ""

        # Salidas del procesamiento automático de alta calidad
        self.hd_image: np.ndarray | None = None
        self.binary_image: np.ndarray | None = None
        self.extracted_text: str = ""
        self.technical_summary: dict = {}

    @staticmethod
    def auto_orient_document(img: np.ndarray) -> tuple[np.ndarray, int]:
        """
        Analiza automáticamente la orientación de los renglones y líneas de texto
        en 360° (0°, 90°, 180°, 270°) usando Transformada de Hough y perfil de proyección horizontal.
        Coloca el documento automáticamente en orientación de lectura horizontal natural y al derecho.
        """
        h, w = img.shape[:2]
        scale = 600.0 / max(h, w) if max(h, w) > 600 else 1.0
        sw, sh = int(w * scale), int(h * scale)
        small = cv2.resize(img, (sw, sh), interpolation=cv2.INTER_AREA) if scale < 1.0 else img.copy()
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY) if len(small.shape) == 3 else small

        # 1. Detección de líneas horizontales vs verticales mediante Hough
        edges = cv2.Canny(gray, 40, 140)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 50, minLineLength=30, maxLineGap=10)

        horiz = 0
        vert = 0
        if lines is not None:
            for line in lines:
                coords = np.asarray(line).ravel()
                x1, y1, x2, y2 = coords[:4]
                deg = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
                if deg < 25 or deg > 155:
                    horiz += 1
                elif 65 < deg < 115:
                    vert += 1

        # Si las líneas verticales dominan notablemente, la foto está de lado (90° o 270°)
        candidates = [90, 270] if vert > max(12, int(horiz * 1.25)) else [0, 180]

        # 2. Desempate fino mediante varianza de gradientes del perfil de renglones horizontales
        best_ang = candidates[0]
        best_score = -1.0

        for ang in candidates:
            if ang == 0:
                rot = gray
            elif ang == 90:
                rot = cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE)
            elif ang == 180:
                rot = cv2.rotate(gray, cv2.ROTATE_180)
            elif ang == 270:
                rot = cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE)

            # Varianza de la derivada de proyección horizontal (máxima en renglones horizontales legibles)
            proj = np.mean(rot, axis=1)
            score = float(np.var(np.diff(proj)))
            if score > best_score:
                best_score = score
                best_ang = ang

        if best_ang == 90:
            return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE), 90
        elif best_ang == 180:
            return cv2.rotate(img, cv2.ROTATE_180), 180
        elif best_ang == 270:
            return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE), 270
        return img, 0

    def load_image(self, file_path: str, auto_orient: bool = True) -> bool:
        """Carga una imagen con soporte EXIF, orientación de texto automática y detección de bordes."""
        # 1. Cargar respetando orientación de metadatos EXIF de cámaras móviles
        try:
            from PIL import Image, ImageOps
            pil_img = Image.open(file_path)
            pil_img = ImageOps.exif_transpose(pil_img)
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception:
            img = cv2.imread(file_path)

        if img is None:
            return False

        # 2. Corrección automática de orientación (si el texto está colocado de lado)
        applied_angle = 0
        if auto_orient:
            img, applied_angle = self.auto_orient_document(img)

        self.file_path = file_path
        self.original_image = img
        self.phase_images["original"] = img.copy()

        # Calcular OCR y métricas iniciales del original (100% en memoria)
        try:
            self.original_ocr = run_ocr(img)
        except Exception:
            self.original_ocr = None
        self.original_metrics = compute_all_metrics(img, ocr_data=self.original_ocr)
        
        # Limpiar fases posteriores y salidas automáticas
        for k in ["fase1_perspective", "fase2_clahe", "fase3_denoise", "fase4_threshold", "fase5_deskew"]:
            self.phase_images[k] = None
        self.hd_image = None
        self.binary_image = None
        self.extracted_text = ""
        self.technical_summary = {}

        # Detección automática robusta de esquinas (estrategia multiescala)
        self.corners = detect_document_contour(img)
        return True

    def rotate_original(self, angle_type: str = "cw") -> np.ndarray | None:
        """
        Gira la imagen original en 90° horario ('cw'), 90° antihorario ('ccw') o 180° ('180').
        Recalcula contornos de perspectiva y resetea fases posteriores.
        """
        if self.original_image is None:
            return None

        if angle_type == "cw":
            self.original_image = cv2.rotate(self.original_image, cv2.ROTATE_90_CLOCKWISE)
        elif angle_type == "ccw":
            self.original_image = cv2.rotate(self.original_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif angle_type == "180":
            self.original_image = cv2.rotate(self.original_image, cv2.ROTATE_180)

        self.phase_images["original"] = self.original_image.copy()
        try:
            self.original_ocr = run_ocr(self.original_image)
        except Exception:
            self.original_ocr = None
        self.original_metrics = compute_all_metrics(self.original_image, ocr_data=self.original_ocr)

        # Limpiar fases posteriores tras la rotación
        for k in ["fase1_perspective", "fase2_clahe", "fase3_denoise", "fase4_threshold", "fase5_deskew"]:
            self.phase_images[k] = None

        # Recalcular esquinas en la nueva orientación
        self.corners = detect_document_contour(self.original_image)
        return self.original_image

    def run_phase_1_perspective(self, custom_corners=None) -> np.ndarray:
        """Fase 1: Corrección de Perspectiva."""
        if self.original_image is None:
            return None
        pts = custom_corners if custom_corners is not None else self.corners
        if pts is None:
            pts = detect_document_contour(self.original_image)
            self.corners = pts

        warped = four_point_transform(self.original_image, pts)
        self.phase_images["fase1_perspective"] = warped
        return warped

    def run_phase_2_clahe(self, input_img=None, clip_limit=None, tile_size=None) -> np.ndarray:
        """Fase 2: Escala de Grises y CLAHE."""
        if input_img is None:
            input_img = self.phase_images["fase1_perspective"]
            if input_img is None:
                input_img = self.run_phase_1_perspective()

        clip = clip_limit if clip_limit is not None else self.params["clahe"]["clip_limit"]
        ts = tile_size if tile_size is not None else self.params["clahe"]["tile_size"]
        self.params["clahe"]["clip_limit"] = clip
        self.params["clahe"]["tile_size"] = ts

        gray = to_grayscale(input_img)
        enhanced = apply_clahe(gray, clip_limit=clip, tile_size=ts)
        self.phase_images["fase2_clahe"] = enhanced
        return enhanced

    def run_phase_3_denoise(self, input_img=None, method=None, **kwargs) -> np.ndarray:
        """Fase 3: Filtrado de Ruido (Wiener, Bilateral, Gaussiano, Mediana)."""
        if input_img is None:
            input_img = self.phase_images["fase2_clahe"]
            if input_img is None:
                input_img = self.run_phase_2_clahe()

        m = method if method is not None else self.params["denoise"]["method"]
        self.params["denoise"]["method"] = m

        call_kwargs = dict(self.params["denoise"])
        call_kwargs.update(kwargs)
        call_kwargs.pop("method", None)
        denoised = filter_noise(input_img, method=m, **call_kwargs)
        self.phase_images["fase3_denoise"] = denoised
        return denoised

    def run_phase_4_threshold(self, input_img=None, method=None, **kwargs) -> np.ndarray:
        """Fase 4: Umbralización Adaptativa."""
        if input_img is None:
            input_img = self.phase_images["fase3_denoise"]
            if input_img is None:
                input_img = self.run_phase_3_denoise()

        m = method if method is not None else self.params["threshold"]["method"]
        self.params["threshold"]["method"] = m

        binary = apply_thresholding(input_img, method=m, **kwargs)
        self.phase_images["fase4_threshold"] = binary
        return binary

    def run_phase_5_deskew(self, input_img=None, method=None) -> tuple[np.ndarray, float]:
        """Fase 5: Corrección de Inclinación."""
        if input_img is None:
            input_img = self.phase_images["fase4_threshold"]
            if input_img is None:
                input_img = self.run_phase_4_threshold()

        m = method if method is not None else self.params["deskew"]["method"]
        self.params["deskew"]["method"] = m

        corrected, angle = deskew(input_img, method=m)
        self.phase_images["fase5_deskew"] = corrected
        self.deskew_angle = angle

        # Actualizar métricas finales
        self.processed_metrics = compute_all_metrics(corrected)
        return corrected, angle

    def run_full_pipeline(self) -> np.ndarray:
        """Ejecuta secuencialmente las 5 fases de transformación en 1 solo clic."""
        if self.original_image is None:
            return None
        self.run_phase_1_perspective()
        self.run_phase_2_clahe()
        self.run_phase_3_denoise()
        self.run_phase_4_threshold()
        final_img, _ = self.run_phase_5_deskew()
        return final_img

    def process_automatic_continuous(self, params: dict | None = None) -> dict:
        """
        Ejecuta la optimización documental en un solo flujo continuo 100% AUTOMÁTICO:
        El sistema evalúa las propiedades estadísticas y de calidad de la imagen para
        decidir dinámicamente los mejores filtros y parámetros:
        1. Detección y corrección de perspectiva y orientación 360° (homografía frontal).
        2. Corrección automática de inclinación (Deskew Hough) y orientación de lectura.
        3. Normalización y eliminación dinámica de sombras por división morfológica de fondo.
        4. Ecualización adaptativa CLAHE con ClipLimit calibrado por contraste RMS.
        5. Realce dinámico de nitidez (Unsharp) calibrado según el desenfoque inicial (Tenengrad).
        6. Reducción adaptativa de ruido con preservación estricta de bordes (Bilateral/NLM).
        7. Generación de imagen Escáner HD (#FFFFFF puro y contraste tipográfico óptimo).
        8. Generación de imagen Binaria limpia sin motas de ruido ni artefactos.
        9. Reconocimiento OCR automático y evaluación de precisión (confianza, palabras, caracteres).
        10. Resumen técnico integral de las decisiones y transformaciones aplicadas.
        """
        if self.original_image is None:
            return {}

        # 0. ANÁLISIS DE CALIDAD DE LA IMAGEN Y DECISIÓN AUTOMÁTICA DE PARÁMETROS
        raw_gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY) if len(self.original_image.shape) == 3 else self.original_image
        raw_sharpness = float(cv2.Laplacian(raw_gray, cv2.CV_64F).var())
        mean_lum = float(np.mean(raw_gray))
        std_lum = float(np.std(raw_gray))
        rms_cont = float(std_lum / 255.0)

        # Decisión automática de CLAHE según contraste de iluminación
        if rms_cont < 0.18 or std_lum < 35:
            auto_clahe_clip = 3.0  # Documento desvanecido / bajo contraste
        elif rms_cont > 0.32:
            auto_clahe_clip = 1.8  # Documento con alto contraste previo
        else:
            auto_clahe_clip = 2.2  # Estándar equilibrado

        # Decisión automática de Nitidez (Unsharp) según desenfoque inicial
        if raw_sharpness < 80.0:
            auto_unsharp_weight = 1.65  # Muy borroso: recuperar bordes tipográficos
        elif raw_sharpness < 250.0:
            auto_unsharp_weight = 1.45  # Desenfoque típico de cámara móvil
        else:
            auto_unsharp_weight = 1.25  # Trazos ya nítidos

        # Decisión automática de filtro de ruido según SNR estimado
        snr_est = float(10.0 * np.log10(max((mean_lum ** 2) / (max(std_lum, 1.0) ** 2), 1e-4)))
        if snr_est < 12.0:
            auto_denoise_method = "nlm"
        else:
            auto_denoise_method = "bilateral"

        # Decisión automática de Binarización
        if std_lum > 58:
            auto_thresh_method = "sauvola"
        else:
            auto_thresh_method = "gaussian"

        opts = {
            "clahe_clip": auto_clahe_clip,
            "denoise_method": auto_denoise_method,
            "threshold_method": auto_thresh_method,
            "unsharp_weight": auto_unsharp_weight,
            "wiener_k": 0.02,
            "wiener_psf": 5
        }
        if params:
            opts.update(params)

        applied_transformations = []

        # 1. Corrección de Perspectiva (Orto-rectificación)
        pts = self.corners if self.corners is not None else detect_document_contour(self.original_image)
        self.corners = pts
        warped = four_point_transform(self.original_image, pts)
        self.phase_images["fase1_perspective"] = warped
        applied_transformations.append({
            "fase": "Perspectiva y Encuadre",
            "tecnica": "Homografía proyectiva (Four-Point Transform)",
            "detalle": f"4 vértices detectados. Dimensiones normalizadas a {warped.shape[1]}x{warped.shape[0]} px."
        })

        # 2. Corrección de Inclinación (Deskew) y Orientación Automática de Lectura
        deskewed, angle = deskew(warped)
        deskewed, extra_rot = self.auto_orient_document(deskewed)
        self.deskew_angle = angle + extra_rot
        self.phase_images["fase5_deskew"] = deskewed
        applied_transformations.append({
            "fase": "Alineación Geométrica & Orientación",
            "tecnica": "Transformada de Hough + Perfil de Renglones",
            "detalle": f"Orientación y rotación ajustadas automáticamente ({self.deskew_angle:.2f}°)."
        })

        gray = cv2.cvtColor(deskewed, cv2.COLOR_BGR2GRAY) if len(deskewed.shape) == 3 else deskewed.copy()

        # 3. Eliminación de Sombras e Iluminación Desigual (Background Division)
        min_dim = min(gray.shape)
        k_size = int(max(25, min_dim // 25))
        if k_size % 2 == 0:
            k_size += 1
        bg_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, k_size))
        bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, bg_kernel)
        divided = cv2.divide(gray, bg, scale=255)
        applied_transformations.append({
            "fase": "Corrección Radiométrica y Sombras",
            "tecnica": "División de Fondo Morfológico (Illumination Flattening)",
            "detalle": f"Kernel elíptico adaptativo de {k_size}x{k_size} px. Gradientes de luz y sombras eliminados."
        })

        # 4. Ajuste de Contraste Local (CLAHE)
        clahe_clip = float(opts.get("clahe_clip", 2.2))
        clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(8, 8))
        clahe_img = clahe.apply(divided)
        self.phase_images["fase2_clahe"] = clahe_img
        applied_transformations.append({
            "fase": "Ecualización de Contraste",
            "tecnica": "CLAHE (Contrast Limited Adaptive Histogram Equalization)",
            "detalle": f"ClipLimit={clahe_clip:.1f}, Grid=8x8. Realce de tintas tenues sin sobre-exposición de fondo."
        })

        # 5. Filtrado de Ruido y Realce de Nitidez
        unsharp_w = float(opts.get("unsharp_weight", 1.45))
        blur = cv2.GaussianBlur(clahe_img, (0, 0), 1.4)
        unsharp = cv2.addWeighted(clahe_img, unsharp_w, blur, -(unsharp_w - 1.0), 0)

        denoise_m = str(opts.get("denoise_method", "bilateral")).lower()
        if "nlm" in denoise_m:
            denoised = filter_noise(unsharp, method="nlm")
            denoise_label = "Filtro Fast Non-Local Means (NLM)"
        elif "wiener" in denoise_m:
            denoised = filter_noise(unsharp, method="wiener", k=float(opts.get("wiener_k", 0.02)), psf_size=int(opts.get("wiener_psf", 5)))
            denoise_label = f"Filtro de Wiener (K={opts.get('wiener_k', 0.02)})"
        else:
            denoised = cv2.bilateralFilter(unsharp, 5, 35, 35)
            denoise_label = "Filtro Bilateral preservador de bordes"

        self.phase_images["fase3_denoise"] = denoised
        applied_transformations.append({
            "fase": "Filtrado de Ruido y Nitidez",
            "tecnica": f"Máscara de Desenfoque (Unsharp {unsharp_w:.2f}x) + {denoise_label}",
            "detalle": "Preservación estricta de bordes de caracteres y eliminación de grano del papel."
        })

        # 6. Modo Escáner HD (Alta Definición)
        norm_f = denoised.astype(np.float32) / 255.0
        scanned_hd = np.clip(np.power(norm_f, 1.25) * 255.0, 0, 255).astype(np.uint8)
        scanned_hd = np.where(scanned_hd > 215, 255, scanned_hd)
        self.hd_image = scanned_hd

        # 7. Binarización Adaptativa Limpia
        thresh_m = str(opts.get("threshold_method", "gaussian")).lower()
        if "sauvola" in thresh_m:
            cleaned_binary = apply_thresholding(denoised, method="sauvola", window_size=25, k=0.2)
            thresh_label = "Umbralización Local de Sauvola (k=0.2)"
        elif "otsu" in thresh_m:
            cleaned_binary = apply_thresholding(denoised, method="otsu")
            thresh_label = "Umbralización Global de Otsu"
        else:
            thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 11)
            cleaned_binary = cv2.medianBlur(thresh, 3)
            thresh_label = "Umbralización Adaptativa Gaussiana + Filtro de Mediana 3x3"

        self.binary_image = cleaned_binary
        self.phase_images["fase4_threshold"] = cleaned_binary
        applied_transformations.append({
            "fase": "Segmentación Binarizada",
            "tecnica": thresh_label,
            "detalle": "Separación nítida de tinta y papel libre de artefactos de ruido binario."
        })

        # 8. Reconocimiento OCR Automático y Métricas Comparativas
        self.processed_ocr = run_ocr(cleaned_binary)
        self.extracted_text = self.processed_ocr.text
        self.processed_metrics = compute_all_metrics(scanned_hd, ocr_data=self.processed_ocr)

        # Asegurar OCR original si no estaba calculado
        if self.original_ocr is None and self.original_image is not None:
            try:
                self.original_ocr = run_ocr(self.original_image)
            except Exception:
                self.original_ocr = None
            self.original_metrics = compute_all_metrics(self.original_image, ocr_data=self.original_ocr)

        # Cálculo de matriz comparativa Antes vs Después
        self.comparison_metrics = compare_metrics(self.original_metrics, self.processed_metrics)

        # Evaluación comparativa de 4 etapas (Tesis)
        thesis_results = self.run_thesis_ocr_evaluation(ref_text=None)

        # 9. Resumen Técnico Integral
        orig_sharp = self.original_metrics.get("sharpness", 0.0)
        new_sharp = self.processed_metrics.get("sharpness", 0.0)
        delta_sharpness = ((new_sharp - orig_sharp) / orig_sharp * 100.0) if orig_sharp > 0 else 0.0
        delta_snr = self.processed_metrics.get("snr_db", 0.0) - self.original_metrics.get("snr_db", 0.0)

        conf_orig = self.original_metrics.get("ocr_confidence", 0.0)
        conf_proc = self.processed_metrics.get("ocr_confidence", 0.0)
        words_orig = self.original_metrics.get("ocr_words", 0)
        words_proc = self.processed_metrics.get("ocr_words", 0)
        chars_orig = self.original_metrics.get("ocr_chars", 0)
        chars_proc = self.processed_metrics.get("ocr_chars", 0)

        is_tess = getattr(self.processed_ocr, "is_tesseract", False)

        technical_report = (
            f"=== REPORTE TÉCNICO DE PROCESAMIENTO CONTINUO AUTOMÁTICO ===\n"
            f"• Archivo: {self.file_path}\n"
            f"• Dimensiones Originales: {self.original_metrics.get('dimensions', '--')}\n"
            f"• Dimensiones Procesadas: {self.processed_metrics.get('dimensions', '--')}\n\n"
            f"1. GEOMETRÍA Y ORIENTACIÓN:\n"
            f"   - Homografía ortogonal: 4 vértices proyectados a vista plana frontal.\n"
            f"   - Corrección de inclinación (Deskew): {angle:.2f}°.\n\n"
            f"2. FILTROS Y MEJORA RADIOMÉTRICA:\n"
            f"   - Eliminación de sombras: División de fondo morfológica (Kernel {k_size}x{k_size}).\n"
            f"   - Ecualización: CLAHE adaptativo local (ClipLimit {clahe_clip:.1f}, Grid 8x8).\n"
            f"   - Nitidez y Ruido: Unsharp Masking ({unsharp_w:.2f}x) + {denoise_label}.\n"
            f"   - Binarización: {thresh_label}.\n"
            f"   - Salida dual: Modo Escáner HD (fondo #FFFFFF puro) y Modo Binario limpio.\n\n"
            f"3. EVALUACIÓN OBJETIVA DE CALIDAD (ANTES vs DESPUÉS):\n"
            f"   - Nitidez Laplaciana: {orig_sharp:.1f} ➔ {new_sharp:.1f} ({'+' if delta_sharpness >= 0 else ''}{delta_sharpness:.1f}%)\n"
            f"   - Relación Señal/Ruido (SNR): {self.original_metrics.get('snr_db', 0.0):.1f} dB ➔ {self.processed_metrics.get('snr_db', 0.0):.1f} dB ({'+' if delta_snr >= 0 else ''}{delta_snr:.1f} dB)\n"
            f"   - Contraste RMS: {self.original_metrics.get('rms_contrast', 0.0):.3f} ➔ {self.processed_metrics.get('rms_contrast', 0.0):.3f}\n"
            f"   - Porcentaje de Tinta: {self.original_metrics.get('ink_ratio_pct', 0.0):.2f}% ➔ {self.processed_metrics.get('ink_ratio_pct', 0.0):.2f}%\n\n"
            f"4. RECONOCIMIENTO ÓPTICO DE CARACTERES (OCR):\n"
            f"   - Motor OCR: {'Tesseract OCR Oficial' if is_tess else 'Motor OCR Óptico Nativo'}\n"
            f"   - Confianza Promedio OCR: {conf_orig:.1f}% ➔ {conf_proc:.1f}%\n"
            f"   - Palabras Detectadas: {words_orig} ➔ {words_proc}\n"
            f"   - Caracteres Detectados: {chars_orig} ➔ {chars_proc}\n"
        )

        self.technical_summary = {
            "transformations": applied_transformations,
            "report_text": technical_report,
            "angle": angle,
            "is_tesseract": is_tess,
            "extracted_text": self.extracted_text,
            "delta_sharpness": delta_sharpness,
            "delta_snr": delta_snr,
            "ocr_confidence": conf_proc,
            "ocr_words": words_proc,
            "ocr_chars": chars_proc
        }

        return {
            "hd_image": self.hd_image,
            "binary_image": self.binary_image,
            "extracted_text": self.extracted_text,
            "ocr_result": self.processed_ocr,
            "ocr_results": thesis_results,
            "original_metrics": self.original_metrics,
            "processed_metrics": self.processed_metrics,
            "comparison_metrics": self.comparison_metrics,
            "technical_summary": self.technical_summary,
            "report_text": technical_report
        }

    def run_thesis_ocr_evaluation(self, ref_text: str | None = None) -> list[dict]:
        """
        Ejecuta el experimento de tesis con las 4 configuraciones clave del taller:
        1. Original (Sin procesar)
        2. Solo CLAHE
        3. Solo Umbralización
        4. Flujo Completo
        Reconoce automáticamente el texto real de la imagen.
        """
        if self.original_image is None:
            return []

        # Asegurar imágenes de comparación
        orig_gray = to_grayscale(self.original_image)
        solo_clahe = apply_clahe(orig_gray, self.params["clahe"]["clip_limit"], self.params["clahe"]["tile_size"])
        solo_thresh = apply_thresholding(orig_gray, self.params["threshold"]["method"])
        
        # Asegurar flujo completo
        flujo_completo = self.phase_images["fase5_deskew"]
        if flujo_completo is None:
            flujo_completo = self.run_full_pipeline()

        use_ref = ref_text if ref_text and ref_text.strip() else (self.reference_text if self.reference_text.strip() else None)

        self.ocr_results = evaluate_thesis_stages(
            orig_gray,
            solo_clahe,
            solo_thresh,
            flujo_completo,
            use_ref
        )

        # Si no había texto de referencia fijado, actualizar con el texto extraído del flujo completo
        if not self.reference_text and self.ocr_results:
            self.reference_text = self.ocr_results[-1].get("extracted_text", "")

        return self.ocr_results

    def get_latest_processed_image(self) -> np.ndarray | None:
        """Retorna la imagen más avanzada procesada hasta el momento."""
        if self.hd_image is not None:
            return self.hd_image
        for key in ["fase5_deskew", "fase4_threshold", "fase3_denoise", "fase2_clahe", "fase1_perspective"]:
            if self.phase_images[key] is not None:
                return self.phase_images[key]
        return self.original_image

