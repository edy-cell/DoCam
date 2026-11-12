"""
DocuScan U - Módulo de Exportación y Generación de Reportes
Salida en PNG, JPG, PDF y Reporte Científico de Métricas
"""

import os
import cv2
import numpy as np
from datetime import datetime
from fpdf import FPDF


def save_image(image: np.ndarray, file_path: str) -> bool:
    """Guarda la imagen procesada en disco (PNG, JPG, TIFF)."""
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.jpg', '.jpeg']:
            cv2.imwrite(file_path, image, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        elif ext == '.png':
            cv2.imwrite(file_path, image, [int(cv2.IMWRITE_PNG_COMPRESSION), 3])
        else:
            cv2.imwrite(file_path, image)
        return True
    except Exception as e:
        print(f"Error al guardar imagen: {e}")
        return False


def export_document_pdf(image: np.ndarray, output_path: str, title: str = "DocuScan U - Documento Digitalizado") -> bool:
    """Exporta el documento procesado como un archivo PDF de página completa."""
    try:
        temp_img_path = "temp_export_pdf.png"
        cv2.imwrite(temp_img_path, image)

        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # Tamaño de página A4: 210 x 297 mm
        margin = 10
        usable_w = 210 - (2 * margin)
        usable_h = 297 - (2 * margin)

        h, w = image.shape[:2]
        img_aspect = w / h
        page_aspect = usable_w / usable_h

        if img_aspect > page_aspect:
            # Ancho manda
            draw_w = usable_w
            draw_h = usable_w / img_aspect
            x = margin
            y = margin + (usable_h - draw_h) / 2
        else:
            # Alto manda
            draw_h = usable_h
            draw_w = usable_h * img_aspect
            x = margin + (usable_w - draw_w) / 2
            y = margin

        pdf.image(temp_img_path, x=x, y=y, w=draw_w, h=draw_h)
        pdf.output(output_path)

        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)
        return True
    except Exception as e:
        print(f"Error exportando PDF: {e}")
        return False


def export_scientific_report(
    output_pdf_path: str,
    original_metrics: dict,
    processed_metrics: dict,
    ocr_results: list[dict],
    pipeline_params: dict,
    student_info: dict | None = None
) -> bool:
    """
    Genera un informe académico/científico formal en PDF con:
    - Portada institucional
    - Parámetros utilizados en cada fase
    - Tabla comparativa de métricas visuales (Nitidez, Contraste RMS, SNR)
    - Matriz de experimentos OCR (CER, WER, Exactitud por etapas)
    """
    try:
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Encabezado Institucional
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(26, 43, 76)  # Deep Navy
        pdf.cell(0, 10, "DocuScan U: Digitalizacion Institucional Inteligente", ln=True, align="C")
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 6, "Reporte Cientifico de Calidad Documental y Rendimiento de OCR", ln=True, align="C")
        pdf.ln(4)

        # Línea divisoria
        pdf.set_draw_color(56, 189, 248)  # Cyan
        pdf.set_line_width(0.8)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(6)

        # Metadatos del Trabajo
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(40, 6, "Fecha y Hora:", 0, 0)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, datetime.now().strftime("%d/%m/%Y %H:%M:%S"), 0, 1)

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(40, 6, "Autores:", 0, 0)
        pdf.set_font("Helvetica", "", 10)
        autores = "J. Pascal, I. Quishpe, E. Lopez" if not student_info else student_info.get("autores", "Investigadores")
        pdf.cell(0, 6, autores, 0, 1)

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(40, 6, "Asignatura / Carrera:", 0, 0)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, "Procesamiento de Imagenes | Ciencias de la Computacion", 0, 1)
        pdf.ln(4)

        # Sección 1: Parámetros del Pipeline
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 7, "1. Parametros de Configuracion del Pipeline", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(51, 65, 85)
        for phase, params in pipeline_params.items():
            param_str = ", ".join(f"{k}: {v}" for k, v in params.items())
            pdf.cell(0, 5, f"   * {phase}: {param_str}", ln=True)
        pdf.ln(4)

        # Sección 2: Métricas Visuales de Legibilidad
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 7, "2. Metricas Comparativas de Calidad de Imagen", ln=True)

        # Tabla de métricas
        pdf.set_fill_color(241, 245, 249)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(60, 7, "Indicador Visual", 1, 0, 'C', fill=True)
        pdf.cell(40, 7, "Original", 1, 0, 'C', fill=True)
        pdf.cell(40, 7, "Procesado", 1, 0, 'C', fill=True)
        pdf.cell(40, 7, "Delta (%)", 1, 1, 'C', fill=True)

        pdf.set_font("Helvetica", "", 9)
        metrics_map = [
            ("Nitidez (Varianza Laplaciana)", "sharpness", "{:.2f}"),
            ("Contraste RMS [0, 1]", "rms_contrast", "{:.4f}"),
            ("Contraste Michelson [0, 1]", "michelson_contrast", "{:.4f}"),
            ("Relacion Senal/Ruido SNR (dB)", "snr_db", "{:.2f} dB"),
            ("Porcentaje de Tinta (%)", "ink_ratio_pct", "{:.2f}%"),
        ]

        for label, key, fmt in metrics_map:
            val_orig = original_metrics.get(key, 0.0)
            val_proc = processed_metrics.get(key, 0.0)
            orig_str = fmt.format(val_orig)
            proc_str = fmt.format(val_proc)
            
            delta = ((val_proc - val_orig) / abs(val_orig) * 100.0) if val_orig != 0 else 0.0
            delta_str = f"{'+' if delta >= 0 else ''}{delta:.1f}%"

            pdf.cell(60, 6, label, 1, 0, 'L')
            pdf.cell(40, 6, orig_str, 1, 0, 'C')
            pdf.cell(40, 6, proc_str, 1, 0, 'C')
            pdf.cell(40, 6, delta_str, 1, 1, 'C')

        pdf.ln(5)

        # Sección 3: Insumo para Tesis - Experimento OCR
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 7, "3. Insumo para Tesis: Impacto del Preprocesamiento en OCR", ln=True)

        pdf.set_fill_color(241, 245, 249)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(70, 7, "Etapa Evaluada", 1, 0, 'C', fill=True)
        pdf.cell(35, 7, "CER (%)", 1, 0, 'C', fill=True)
        pdf.cell(35, 7, "WER (%)", 1, 0, 'C', fill=True)
        pdf.cell(40, 7, "Exactitud (%)", 1, 1, 'C', fill=True)

        pdf.set_font("Helvetica", "", 9)
        for r in ocr_results:
            pdf.cell(70, 6, r.get("stage", ""), 1, 0, 'L')
            pdf.cell(35, 6, f"{r.get('cer_pct', 0.0):.2f}%", 1, 0, 'C')
            pdf.cell(35, 6, f"{r.get('wer_pct', 0.0):.2f}%", 1, 0, 'C')
            pdf.cell(40, 6, f"{r.get('accuracy_pct', 0.0):.2f}%", 1, 1, 'C')

        pdf.ln(5)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.multi_cell(0, 4, "Nota cientifica: CER (Character Error Rate) y WER (Word Error Rate) calculados mediante la distancia minima de edicion de Levenshtein contra el texto patron de referencia.")

        pdf.output(output_pdf_path)
        return True
    except Exception as e:
        print(f"Error generando reporte cientifico PDF: {e}")
        return False

