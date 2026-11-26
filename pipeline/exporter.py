"""
DocuScan U - Módulo de Exportación y Generación de Reportes
Salida en PNG, JPG, PDF y Reporte Científico de Métricas
Soporta exportación nativa sin dependencias externas obligatorias
"""

import os
import cv2
import numpy as np
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Importación segura de FPDF
try:
    from fpdf import FPDF
    HAS_FPDF = True
except Exception:
    HAS_FPDF = False
    FPDF = None


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
    """
    Exporta el documento procesado como un archivo PDF de página completa.
    Utiliza Pillow nativo (instalado con PIL) sin requerir librerías externas.
    """
    try:
        if len(image.shape) == 2:
            pil_img = Image.fromarray(image).convert("RGB")
        elif image.shape[2] == 3:
            pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        else:
            pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGRA2RGB))

        # Guardar en PDF de alta calidad
        pil_img.save(output_path, "PDF", resolution=150.0)
        return True
    except Exception as e:
        print(f"Error exportando PDF documental: {e}")
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
    Genera un informe académico/científico formal en PDF.
    Si FPDF está instalado lo utiliza; en caso contrario, genera el PDF
    mediante renderizado vectorial de Pillow o informe textual de alta precisión.
    """
    if HAS_FPDF and FPDF is not None:
        try:
            return _export_report_fpdf(output_pdf_path, original_metrics, processed_metrics, ocr_results, pipeline_params, student_info)
        except Exception as e:
            print(f"FPDF report falló ({e}), usando motor nativo de respaldo.")

    return _export_report_pillow(output_pdf_path, original_metrics, processed_metrics, ocr_results, pipeline_params, student_info)


def _export_report_fpdf(output_pdf_path, original_metrics, processed_metrics, ocr_results, pipeline_params, student_info):
    """Generador de reporte formal usando FPDF."""
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Encabezado Institucional
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(26, 43, 76)
    pdf.cell(0, 10, "DocuScan U: Digitalizacion Institucional Inteligente", ln=True, align="C")
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, "Reporte Cientifico de Calidad Documental y Rendimiento de OCR", ln=True, align="C")
    pdf.ln(4)

    # Línea divisoria
    pdf.set_draw_color(56, 189, 248)
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

    # Sección 2: Métricas Visuales
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 7, "2. Metricas Comparativas de Calidad de Imagen", ln=True)

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

    # Sección 3: Insumo para Tesis - OCR
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

    pdf.output(output_pdf_path)
    return True


def _export_report_pillow(output_pdf_path, original_metrics, processed_metrics, ocr_results, pipeline_params, student_info):
    """Generador nativo de reporte en PDF usando Pillow (sin dependencias adicionales)."""
    try:
        # Página A4 a 150 DPI: 1240 x 1754 px
        img = Image.new("RGB", (1240, 1754), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Cargar fuentes del sistema
        font_title = None
        font_body = None
        font_bold = None
        for fp in ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/segoeui.ttf"]:
            if os.path.isfile(fp):
                try:
                    font_title = ImageFont.truetype(fp, 32)
                    font_bold = ImageFont.truetype(fp, 18)
                    font_body = ImageFont.truetype(fp, 15)
                    break
                except Exception:
                    continue

        if font_title is None:
            font_title = ImageFont.load_default()
            font_bold = font_title
            font_body = font_title

        # Título
        draw.text((80, 60), "DocuScan U: Digitalización Institucional Inteligente", fill=(26, 43, 76), font=font_title)
        draw.text((80, 110), "Reporte Científico de Calidad Documental y OCR (Insumo de Tesis)", fill=(100, 116, 139), font=font_bold)
        draw.line([(80, 145), (1160, 145)], fill=(56, 189, 248), width=3)

        # Metadatos
        y = 170
        draw.text((80, y), f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", fill=(15, 23, 42), font=font_body)
        draw.text((80, y + 25), "Autores: J. Pascal, I. Quishpe, E. Lopez", fill=(15, 23, 42), font=font_body)
        draw.text((80, y + 50), "Asignatura: Procesamiento de Imágenes | Ciencias de la Computación", fill=(15, 23, 42), font=font_body)

        # Parámetros
        y = 270
        draw.text((80, y), "1. Parámetros de Configuración del Pipeline", fill=(30, 41, 59), font=font_bold)
        y += 30
        for ph, params in pipeline_params.items():
            p_str = ", ".join(f"{k}: {v}" for k, v in params.items())
            draw.text((100, y), f"• {ph}: {p_str}", fill=(71, 85, 105), font=font_body)
            y += 24

        # Tabla de Métricas
        y += 20
        draw.text((80, y), "2. Métricas Comparativas de Calidad de Imagen", fill=(30, 41, 59), font=font_bold)
        y += 35

        # Encabezado tabla
        draw.rectangle([(80, y), (1160, y + 30)], fill=(241, 245, 249))
        draw.text((90, y + 6), "Indicador Visual", fill=(15, 23, 42), font=font_bold)
        draw.text((550, y + 6), "Original", fill=(15, 23, 42), font=font_bold)
        draw.text((750, y + 6), "Procesado", fill=(15, 23, 42), font=font_bold)
        draw.text((950, y + 6), "Delta (%)", fill=(15, 23, 42), font=font_bold)
        y += 35

        metrics_map = [
            ("Nitidez (Varianza Laplaciana)", "sharpness", "{:.2f}"),
            ("Contraste RMS [0, 1]", "rms_contrast", "{:.4f}"),
            ("Contraste Michelson [0, 1]", "michelson_contrast", "{:.4f}"),
            ("Relación Señal/Ruido SNR (dB)", "snr_db", "{:.2f} dB"),
            ("Porcentaje de Tinta (%)", "ink_ratio_pct", "{:.2f}%"),
        ]

        for label, key, fmt in metrics_map:
            vo = original_metrics.get(key, 0.0)
            vp = processed_metrics.get(key, 0.0)
            so = fmt.format(vo)
            sp = fmt.format(vp)
            delta = ((vp - vo) / abs(vo) * 100.0) if vo != 0 else 0.0
            sd = f"{'+' if delta >= 0 else ''}{delta:.1f}%"

            draw.line([(80, y), (1160, y)], fill=(226, 232, 240), width=1)
            draw.text((90, y + 5), label, fill=(51, 65, 85), font=font_body)
            draw.text((550, y + 5), so, fill=(51, 65, 85), font=font_body)
            draw.text((750, y + 5), sp, fill=(51, 65, 85), font=font_body)
            draw.text((950, y + 5), sd, fill=(51, 65, 85), font=font_body)
            y += 28

        # Sección OCR
        y += 30
        draw.text((80, y), "3. Insumo para Tesis: Impacto del Preprocesamiento en OCR", fill=(30, 41, 59), font=font_bold)
        y += 35

        draw.rectangle([(80, y), (1160, y + 30)], fill=(241, 245, 249))
        draw.text((90, y + 6), "Etapa Evaluada", fill=(15, 23, 42), font=font_bold)
        draw.text((550, y + 6), "CER (%)", fill=(15, 23, 42), font=font_bold)
        draw.text((750, y + 6), "WER (%)", fill=(15, 23, 42), font=font_bold)
        draw.text((950, y + 6), "Exactitud (%)", fill=(15, 23, 42), font=font_bold)
        y += 35

        for r in ocr_results:
            draw.line([(80, y), (1160, y)], fill=(226, 232, 240), width=1)
            draw.text((90, y + 5), r.get("stage", ""), fill=(51, 65, 85), font=font_body)
            draw.text((550, y + 5), f"{r.get('cer_pct', 0.0):.2f}%", fill=(51, 65, 85), font=font_body)
            draw.text((750, y + 5), f"{r.get('wer_pct', 0.0):.2f}%", fill=(51, 65, 85), font=font_body)
            draw.text((950, y + 5), f"{r.get('accuracy_pct', 0.0):.2f}%", fill=(51, 65, 85), font=font_body)
            y += 28

        img.save(output_pdf_path, "PDF", resolution=150.0)
        return True
    except Exception as e:
        print(f"Error generando reporte con Pillow: {e}")
        return False
