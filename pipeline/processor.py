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
        self.ocr_results: list[dict] = []
        self.reference_text: str = ""

    def load_image(self, file_path: str, auto_rotate_landscape: bool = True) -> bool:
        """Carga una imagen, corrige orientación si es horizontal y resetea las fases."""
        img = cv2.imread(file_path)
        if img is None:
            return False

        # Si la imagen fue fotografiada en horizontal (ancho > alto), auto-orientar a vertical
        if auto_rotate_landscape and img.shape[1] > img.shape[0]:
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

        self.file_path = file_path
        self.original_image = img
        self.phase_images["original"] = img.copy()

        # Calcular métricas originales
        self.original_metrics = compute_all_metrics(img)
        
        # Limpiar fases posteriores
        for k in ["fase1_perspective", "fase2_clahe", "fase3_denoise", "fase4_threshold", "fase5_deskew"]:
            self.phase_images[k] = None

        # Pre-detectar esquinas
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
        self.original_metrics = compute_all_metrics(self.original_image)

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
        for key in ["fase5_deskew", "fase4_threshold", "fase3_denoise", "fase2_clahe", "fase1_perspective"]:
            if self.phase_images[key] is not None:
                return self.phase_images[key]
        return self.original_image

