"""
DocuScan U - Pipeline de Recuperación Inteligente de Documentos Fotografiados
"""

from .processor import DocumentProcessor
from .perspective import detect_document_contour, four_point_transform
from .enhancement import to_grayscale, apply_clahe, adjust_contrast_brightness
from .denoise import filter_noise, apply_wiener_filter
from .thresholding import apply_thresholding
from .deskew import deskew
from .metrics import compute_all_metrics, compute_histogram, compare_metrics
from .ocr import run_ocr, evaluate_thesis_stages, set_custom_tesseract_path
from .exporter import save_image, export_document_pdf, export_scientific_report

