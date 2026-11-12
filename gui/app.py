"""
DocuScan U - Interfaz Gráfica Principal
Ejecución en Pantalla Completa, Diseño Profesional y Separación de Fases por Botones
"""

import os
import glob
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import cv2
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from pipeline import (
    DocumentProcessor,
    compute_histogram,
    save_image,
    export_document_pdf,
    export_scientific_report
)
from .styles import (
    BG_DARK, SURFACE_CARD, SURFACE_INNER, SURFACE_BORDER, SURFACE_HOVER,
    ACCENT_PRIMARY, ACCENT_PRIMARY_HOVER, ACCENT_SUCCESS, ACCENT_SUCCESS_HOVER,
    ACCENT_WARNING, ACCENT_INFO, ACCENT_DANGER,
    TEXT_WHITE, TEXT_MUTED, TEXT_FAINT,
    FONT_TITLE_MAIN, FONT_TITLE_PANEL, FONT_SUBTITLE, FONT_BODY, FONT_BODY_BOLD, FONT_MONO,
    configure_app_styles
)
from .canvas_viewer import ZoomableImageCanvas
from .metric_cards import MetricsSummaryBar


class DocuScanApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DocuScan U | Recuperación Inteligente de Documentos Fotografiados")
        self.configure(bg=BG_DARK)
        configure_app_styles(self)

        # Configuración de Pantalla Completa y Centrado
        self.is_fullscreen = False
        try:
            self.state('zoomed')  # Maximizado nativo en Windows
        except Exception:
            self.geometry("1400x900+50+50")

        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.exit_fullscreen)

        # Procesador documental
        self.processor = DocumentProcessor()
        self.active_phase = "original"

        # Contenedor principal centrado
        self._build_header()
        self._build_main_layout()
        self._build_status_bar()

        # Cargar lista de imágenes de muestra
        self._scan_sample_images()

    def toggle_fullscreen(self, event=None):
        """Alterna entre pantalla completa sin bordes y ventana maximizada."""
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        return "break"

    def exit_fullscreen(self, event=None):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.attributes("-fullscreen", False)
        return "break"

    # ==========================================
    # 1. ENCABEZADO SUPERIOR
    # ==========================================
    def _build_header(self):
        header = tk.Frame(self, bg=SURFACE_CARD, height=60, bd=1, relief="solid", highlightthickness=1, highlightbackground=SURFACE_BORDER)
        header.pack(side="top", fill="x", padx=10, pady=(10, 5))

        # Título y Subtítulo
        title_box = tk.Frame(header, bg=SURFACE_CARD)
        title_box.pack(side="left", padx=16, pady=8)

        lbl_app = tk.Label(
            title_box,
            text="📑 DocuScan U",
            font=FONT_TITLE_MAIN,
            fg=ACCENT_PRIMARY,
            bg=SURFACE_CARD
        )
        lbl_app.pack(side="left")

        lbl_pipe = tk.Label(
            title_box,
            text=" | Recuperación Inteligente de Documentos Fotografiados",
            font=FONT_TITLE_PANEL,
            fg=TEXT_WHITE,
            bg=SURFACE_CARD
        )
        lbl_pipe.pack(side="left")

        lbl_inst = tk.Label(
            title_box,
            text=" (Digitalización Institucional)",
            font=FONT_SUBTITLE,
            fg=TEXT_MUTED,
            bg=SURFACE_CARD
        )
        lbl_inst.pack(side="left")

        # Indicador de Archivo Activo y Botón de Pantalla Completa a la derecha
        right_box = tk.Frame(header, bg=SURFACE_CARD)
        right_box.pack(side="right", padx=16, pady=8)

        self.lbl_active_doc = tk.Label(
            right_box,
            text="📄 Sin documento activo",
            font=FONT_BODY_BOLD,
            fg=ACCENT_WARNING,
            bg=SURFACE_INNER,
            padx=10,
            pady=4,
            relief="flat"
        )
        self.lbl_active_doc.pack(side="left", padx=10)

        btn_fs = tk.Button(
            right_box,
            text="⛶ Pantalla Completa (F11)",
            font=FONT_BODY,
            bg=SURFACE_INNER,
            fg=TEXT_WHITE,
            bd=1,
            relief="solid",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.toggle_fullscreen
        )
        btn_fs.pack(side="left")

    # ==========================================
    # 2. CUERPO PRINCIPAL (SIDEBAR + WORKSPACE)
    # ==========================================
    def _build_main_layout(self):
        body = tk.Frame(self, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=10, pady=5)

        # ----------------------------------------------------
        # PANEL IZQUIERDO: SEPARACIÓN DE FASES EN BOTONES
        # ----------------------------------------------------
        self.sidebar = tk.Frame(body, bg=SURFACE_CARD, width=340, bd=1, relief="solid", highlightthickness=1, highlightbackground=SURFACE_BORDER)
        self.sidebar.pack(side="left", fill="y", padx=(0, 8), pady=0)
        self.sidebar.pack_propagate(False)

        self._build_sidebar_content()

        # ----------------------------------------------------
        # ÁREA DE TRABAJO DERECHA (PANELES Y VISORES)
        # ----------------------------------------------------
        self.workspace = tk.Frame(body, bg=BG_DARK)
        self.workspace.pack(side="right", fill="both", expand=True)

        self._build_workspace_content()

    def _build_sidebar_content(self):
        # Título del Menú
        lbl_side = tk.Label(
            self.sidebar,
            text="FASES DEL PROCESAMIENTO",
            font=FONT_SUBTITLE,
            fg=TEXT_MUTED,
            bg=SURFACE_CARD,
            anchor="w"
        )
        lbl_side.pack(fill="x", padx=14, pady=(12, 6))

        # Cargar Documento
        load_frame = tk.Frame(self.sidebar, bg=SURFACE_CARD)
        load_frame.pack(fill="x", padx=12, pady=(0, 8))

        btn_load = tk.Button(
            load_frame,
            text="📂 Abrir Fotografía...",
            font=FONT_BODY_BOLD,
            bg="#2563eb",
            fg=TEXT_WHITE,
            activebackground="#1d4ed8",
            activeforeground=TEXT_WHITE,
            bd=0,
            pady=6,
            cursor="hand2",
            command=self.open_file_dialog
        )
        btn_load.pack(fill="x")

        # Selector de imágenes de prueba incluidas en el taller
        sample_frame = tk.Frame(self.sidebar, bg=SURFACE_CARD)
        sample_frame.pack(fill="x", padx=12, pady=(0, 10))

        tk.Label(sample_frame, text="Documentos de muestra (Taller):", font=("Segoe UI", 8), fg=TEXT_MUTED, bg=SURFACE_CARD).pack(anchor="w")
        self.sample_var = tk.StringVar(value="Seleccionar documento de muestra...")
        self.cb_samples = ttk.Combobox(sample_frame, textvariable=self.sample_var, state="readonly", font=FONT_BODY)
        self.cb_samples.pack(fill="x", pady=2)
        self.cb_samples.bind("<<ComboboxSelected>>", self._on_sample_selected)

        # Controles de Orientación y Giro Manual
        rot_frame = tk.Frame(self.sidebar, bg=SURFACE_CARD)
        rot_frame.pack(fill="x", padx=12, pady=(0, 6))

        tk.Label(rot_frame, text="Giro de Orientación:", font=("Segoe UI", 8, "bold"), fg=TEXT_MUTED, bg=SURFACE_CARD).pack(anchor="w")

        rot_box = tk.Frame(rot_frame, bg=SURFACE_CARD)
        rot_box.pack(fill="x", pady=2)

        tk.Button(
            rot_box,
            text="↺ 90° Antihor.",
            font=("Segoe UI", 8, "bold"),
            bg=SURFACE_INNER,
            fg=TEXT_WHITE,
            bd=1,
            relief="solid",
            pady=4,
            cursor="hand2",
            command=lambda: self.rotate_document("ccw")
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))

        tk.Button(
            rot_box,
            text="↻ 90° Horario",
            font=("Segoe UI", 8, "bold"),
            bg=SURFACE_INNER,
            fg=TEXT_WHITE,
            bd=1,
            relief="solid",
            pady=4,
            cursor="hand2",
            command=lambda: self.rotate_document("cw")
        ).pack(side="left", fill="x", expand=True, padx=(2, 2))

        tk.Button(
            rot_box,
            text="🔄 180°",
            font=("Segoe UI", 8, "bold"),
            bg=SURFACE_INNER,
            fg=TEXT_WHITE,
            bd=1,
            relief="solid",
            pady=4,
            cursor="hand2",
            command=lambda: self.rotate_document("180")
        ).pack(side="left", fill="x", expand=True, padx=(2, 0))

        # Divisor sutil
        tk.Frame(self.sidebar, bg=SURFACE_BORDER, height=1).pack(fill="x", padx=12, pady=4)

        # Botones de las 5 Fases de Transformación Documental
        self.btn_phases = {}
        phases_def = [
            ("fase1", "📐 FASE 1: Corrección de Perspectiva", self.run_phase_1, "#0284c7"),
            ("fase2", "🌓 FASE 2: Escala de Grises y CLAHE", self.run_phase_2, "#0369a1"),
            ("fase3", "🧹 FASE 3: Filtrado de Ruido", self.run_phase_3, "#075985"),
            ("fase4", "⚡ FASE 4: Umbralización Adaptativa", self.run_phase_4, "#0c4a6e"),
            ("fase5", "🔄 FASE 5: Corrección de Inclinación", self.run_phase_5, "#164e63"),
        ]

        for code, label, cmd, col in phases_def:
            b = tk.Button(
                self.sidebar,
                text=label,
                font=FONT_BODY_BOLD,
                bg=SURFACE_INNER,
                fg=TEXT_WHITE,
                activebackground=SURFACE_HOVER,
                activeforeground=ACCENT_PRIMARY,
                bd=1,
                relief="solid",
                anchor="w",
                padx=12,
                pady=6,
                cursor="hand2",
                command=cmd
            )
            b.pack(fill="x", padx=12, pady=3)
            self.btn_phases[code] = b

        # Divisor
        tk.Frame(self.sidebar, bg=SURFACE_BORDER, height=1).pack(fill="x", padx=12, pady=6)

        # Botón Flujo Completo Automático (1 solo clic)
        self.btn_full = tk.Button(
            self.sidebar,
            text="🚀 FLUJO COMPLETO AUTOMÁTICO",
            font=("Segoe UI", 10, "bold"),
            bg=ACCENT_SUCCESS,
            fg="#022c22",
            activebackground=ACCENT_SUCCESS_HOVER,
            activeforeground=TEXT_WHITE,
            bd=0,
            pady=8,
            cursor="hand2",
            command=self.run_full_pipeline
        )
        self.btn_full.pack(fill="x", padx=12, pady=4)

        # Botones de Evaluación y Exportación
        eval_frame = tk.Frame(self.sidebar, bg=SURFACE_CARD)
        eval_frame.pack(fill="x", padx=12, pady=4)

        self.btn_eval = tk.Button(
            eval_frame,
            text="📊 Evaluación de Legibilidad",
            font=FONT_BODY_BOLD,
            bg=SURFACE_INNER,
            fg=ACCENT_PRIMARY,
            bd=1,
            relief="solid",
            pady=6,
            cursor="hand2",
            command=lambda: self.switch_view_tab("metrics")
        )
        self.btn_eval.pack(fill="x", pady=2)

        self.btn_ocr = tk.Button(
            eval_frame,
            text="🔤 Insumo Tesis: OCR (CER & WER)",
            font=FONT_BODY_BOLD,
            bg=SURFACE_INNER,
            fg=ACCENT_WARNING,
            bd=1,
            relief="solid",
            pady=6,
            cursor="hand2",
            command=lambda: self.switch_view_tab("ocr")
        )
        self.btn_ocr.pack(fill="x", pady=2)

        self.btn_export = tk.Button(
            eval_frame,
            text="💾 Exportar Documento & Reporte",
            font=FONT_BODY_BOLD,
            bg="#3b82f6",
            fg=TEXT_WHITE,
            activebackground="#1d4ed8",
            activeforeground=TEXT_WHITE,
            bd=0,
            pady=6,
            cursor="hand2",
            command=self.show_export_dialog
        )
        self.btn_export.pack(fill="x", pady=2)

        # Panel de Parámetros Interactivo para la fase seleccionada
        self.param_box = tk.LabelFrame(
            self.sidebar,
            text="Parámetros de la Fase Activa",
            font=("Segoe UI", 8, "bold"),
            fg=ACCENT_PRIMARY,
            bg=SURFACE_INNER,
            bd=1,
            relief="solid"
        )
        self.param_box.pack(fill="both", expand=True, padx=12, pady=8)
        self._build_param_controls()

    def _build_param_controls(self):
        # Contenedor dinámico de parámetros
        self.param_container = tk.Frame(self.param_box, bg=SURFACE_INNER)
        self.param_container.pack(fill="both", expand=True, padx=8, pady=4)

        self.lbl_param_info = tk.Label(
            self.param_container,
            text="Seleccione una fase para ajustar sus parámetros en tiempo real.",
            font=FONT_BODY,
            fg=TEXT_MUTED,
            bg=SURFACE_INNER,
            wraplength=280,
            justify="left"
        )
        self.lbl_param_info.pack(anchor="w", pady=6)

    def _build_workspace_content(self):
        # 1. Barra de Resumen de Métricas KPI en la parte superior
        self.metrics_bar = MetricsSummaryBar(self.workspace)
        self.metrics_bar.pack(fill="x", pady=(0, 6))

        # 2. Pestañas de Vista (Visual Lado a Lado, Histogramas, Métricas, OCR Tesis)
        tabs_bar = tk.Frame(self.workspace, bg=BG_DARK)
        tabs_bar.pack(fill="x", pady=(0, 6))

        self.tab_buttons = {}
        tabs = [
            ("viewer", "👁️ Comparación Lado a Lado", lambda: self.switch_view_tab("viewer")),
            ("histogram", "📈 Histogramas Radiométricos", lambda: self.switch_view_tab("histogram")),
            ("metrics", "📊 Matriz de Métricas Visuales", lambda: self.switch_view_tab("metrics")),
            ("ocr", "🔤 Experimento de Tesis: OCR (CER/WER)", lambda: self.switch_view_tab("ocr")),
        ]

        for tab_id, tab_label, cmd in tabs:
            btn = tk.Button(
                tabs_bar,
                text=tab_label,
                font=FONT_BODY_BOLD,
                bg=SURFACE_INNER,
                fg=TEXT_MUTED,
                activebackground=SURFACE_HOVER,
                activeforeground=TEXT_WHITE,
                bd=1,
                relief="solid",
                padx=12,
                pady=4,
                cursor="hand2",
                command=cmd
            )
            btn.pack(side="left", padx=(0, 6))
            self.tab_buttons[tab_id] = btn

        # Marcar pestaña activa
        self.active_tab = "viewer"
        self._highlight_tab_button("viewer")

        # 3. Contenedor de Vistas Intercambiables
        self.view_container = tk.Frame(self.workspace, bg=BG_DARK)
        self.view_container.pack(fill="both", expand=True)

        # Vista 1: Visor Dual Lado a Lado
        self.view_viewer = tk.Frame(self.view_container, bg=BG_DARK)
        self._build_dual_viewer(self.view_viewer)

        # Vista 2: Histograma Embebido con Matplotlib
        self.view_histogram = tk.Frame(self.view_container, bg=SURFACE_CARD, bd=1, relief="solid", highlightthickness=1, highlightbackground=SURFACE_BORDER)
        self._build_histogram_view(self.view_histogram)

        # Vista 3: Matriz de Métricas
        self.view_metrics = tk.Frame(self.view_container, bg=SURFACE_CARD, bd=1, relief="solid", highlightthickness=1, highlightbackground=SURFACE_BORDER)
        self._build_metrics_view(self.view_metrics)

        # Vista 4: OCR Tesis
        self.view_ocr = tk.Frame(self.view_container, bg=SURFACE_CARD, bd=1, relief="solid", highlightthickness=1, highlightbackground=SURFACE_BORDER)
        self._build_ocr_view(self.view_ocr)

        # Mostrar por defecto el visor dual
        self.view_viewer.pack(fill="both", expand=True)

    def _build_dual_viewer(self, parent):
        # Dos visores de Canvas interactivos lado a lado
        dual_frame = tk.Frame(parent, bg=BG_DARK)
        dual_frame.pack(fill="both", expand=True)

        # Canvas Izquierdo: Documento Original
        self.canvas_orig = ZoomableImageCanvas(
            dual_frame,
            title="ORIGINAL FOTOGRAFIADO (Defectos: Sombras, Perspectiva, Inclinación)",
            editable_corners=True,
            on_corners_changed=self._on_corners_dragged,
            on_rotate=self.rotate_document
        )
        self.canvas_orig.pack(side="left", fill="both", expand=True, padx=(0, 4))

        # Canvas Derecho: Documento Procesado
        self.canvas_proc = ZoomableImageCanvas(
            dual_frame,
            title="DOCUMENTO EN FASE ACTUAL / PROCESADO FINAL",
            editable_corners=False
        )
        self.canvas_proc.pack(side="right", fill="both", expand=True, padx=(4, 0))

    def _build_histogram_view(self, parent):
        lbl = tk.Label(parent, text="Distribución Radiométrica: Histograma Original vs Procesado", font=FONT_TITLE_PANEL, fg=TEXT_WHITE, bg=SURFACE_CARD)
        lbl.pack(anchor="w", padx=16, pady=10)

        # Figura de Matplotlib en tema oscuro
        self.fig_hist = Figure(figsize=(8, 4.5), facecolor="#111827", dpi=100)
        self.ax_hist = self.fig_hist.add_subplot(111)
        self.ax_hist.set_facecolor("#0b0f19")
        self.ax_hist.tick_params(colors="#94a3b8", labelsize=8)
        for spine in self.ax_hist.spines.values():
            spine.set_color("#334155")

        self.canvas_hist = FigureCanvasTkAgg(self.fig_hist, master=parent)
        self.canvas_hist.get_tk_widget().pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def _build_metrics_view(self, parent):
        lbl = tk.Label(parent, text="Evaluación Cuantitativa de Legibilidad y Calidad de Imagen", font=FONT_TITLE_PANEL, fg=TEXT_WHITE, bg=SURFACE_CARD)
        lbl.pack(anchor="w", padx=16, pady=10)

        # Tabla estilo Treeview moderno
        cols = ("indicador", "original", "procesado", "delta", "interpretacion")
        self.tree_metrics = ttk.Treeview(parent, columns=cols, show="headings", height=8)
        self.tree_metrics.heading("indicador", text="Indicador de Legibilidad")
        self.tree_metrics.heading("original", text="Valor Original")
        self.tree_metrics.heading("procesado", text="Valor Procesado")
        self.tree_metrics.heading("delta", text="Mejora (%)")
        self.tree_metrics.heading("interpretacion", text="Impacto Documental")

        self.tree_metrics.column("indicador", width=220)
        self.tree_metrics.column("original", width=120, anchor="center")
        self.tree_metrics.column("procesado", width=120, anchor="center")
        self.tree_metrics.column("delta", width=100, anchor="center")
        self.tree_metrics.column("interpretacion", width=360)

        self.tree_metrics.pack(fill="both", expand=True, padx=16, pady=10)

        # Explicación del taller
        info_frame = tk.Frame(parent, bg=SURFACE_INNER, bd=1, relief="solid", highlightthickness=1, highlightbackground=SURFACE_BORDER)
        info_frame.pack(fill="x", padx=16, pady=(0, 16))

        tk.Label(
            info_frame,
            text="📌 Fundamento Académico:\n"
                 "• Nitidez (Tenengrad): Incrementa al acentuarse los bordes de los caracteres tipográficos.\n"
                 "• Contraste RMS: Un valor equilibrado separa nítidamente las letras negras del papel blanco.\n"
                 "• SNR: Mide la reducción del granulado del sensor y de arrugas del papel sin perder texto.",
            font=FONT_BODY,
            fg=TEXT_MUTED,
            bg=SURFACE_INNER,
            justify="left"
        ).pack(anchor="w", padx=12, pady=8)

    def _build_ocr_view(self, parent):
        top_ocr = tk.Frame(parent, bg=SURFACE_CARD)
        top_ocr.pack(fill="x", padx=16, pady=10)

        lbl = tk.Label(top_ocr, text="Insumo para Tesis: OCR Automático y Evaluación (CER & WER)", font=FONT_TITLE_PANEL, fg=TEXT_WHITE, bg=SURFACE_CARD)
        lbl.pack(side="left")

        self.lbl_ocr_engine = tk.Label(top_ocr, text="[Reconocimiento Automático Activo]", font=("Segoe UI", 9, "bold"), fg=ACCENT_SUCCESS, bg=SURFACE_CARD)
        self.lbl_ocr_engine.pack(side="left", padx=14)

        btn_run_ocr = tk.Button(
            top_ocr,
            text="⚡ Re-ejecutar OCR",
            font=FONT_BODY_BOLD,
            bg=ACCENT_PRIMARY,
            fg="#0b1120",
            activebackground=ACCENT_PRIMARY_HOVER,
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=lambda: self.run_ocr_thesis_benchmark(force_refresh_ref=False)
        )
        btn_run_ocr.pack(side="right")

        btn_tess = tk.Button(
            top_ocr,
            text="📁 Vincular Tesseract.exe...",
            font=FONT_BODY,
            bg=SURFACE_INNER,
            fg=TEXT_MUTED,
            bd=1,
            relief="solid",
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.browse_tesseract_path
        )
        btn_tess.pack(side="right", padx=(0, 8))

        # Tabla comparativa de las 4 etapas del problema
        cols = ("etapa", "cer", "wer", "exactitud", "estado")
        self.tree_ocr = ttk.Treeview(parent, columns=cols, show="headings", height=5)
        self.tree_ocr.heading("etapa", text="Configuración Evaluada")
        self.tree_ocr.heading("cer", text="CER (Char Error %)")
        self.tree_ocr.heading("wer", text="WER (Word Error %)")
        self.tree_ocr.heading("exactitud", text="Exactitud Reconocimiento")
        self.tree_ocr.heading("estado", text="Conclusión Académica")

        self.tree_ocr.column("etapa", width=220)
        self.tree_ocr.column("cer", width=130, anchor="center")
        self.tree_ocr.column("wer", width=130, anchor="center")
        self.tree_ocr.column("exactitud", width=150, anchor="center")
        self.tree_ocr.column("estado", width=300)

        self.tree_ocr.pack(fill="x", padx=16, pady=6)

        # Paneles inferiores: Texto Extraído vs Texto Patrón de Referencia
        texts_frame = tk.Frame(parent, bg=SURFACE_CARD)
        texts_frame.pack(fill="both", expand=True, padx=16, pady=(6, 16))

        # Cuadro Izquierdo: Texto Reconocido
        box_left = tk.Frame(texts_frame, bg=SURFACE_CARD)
        box_left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(box_left, text="Texto Extraído Automáticamente de su Imagen:", font=FONT_SUBTITLE, fg=TEXT_WHITE, bg=SURFACE_CARD).pack(anchor="w")
        self.txt_extracted = tk.Text(box_left, bg="#070a12", fg=TEXT_WHITE, font=FONT_MONO, height=8, bd=1, relief="solid")
        self.txt_extracted.pack(fill="both", expand=True, pady=4)

        # Cuadro Derecho: Texto de Referencia Ground Truth (Editable por el usuario)
        box_right = tk.Frame(texts_frame, bg=SURFACE_CARD)
        box_right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        tk.Label(box_right, text="Texto de Referencia Ground Truth (Auto-poblado / Editable):", font=FONT_SUBTITLE, fg=TEXT_WHITE, bg=SURFACE_CARD).pack(anchor="w")
        self.txt_reference = tk.Text(box_right, bg="#070a12", fg="#38bdf8", font=FONT_MONO, height=8, bd=1, relief="solid")
        self.txt_reference.pack(fill="both", expand=True, pady=4)

    # ==========================================
    # 3. BARRA DE ESTADO INFERIOR
    # ==========================================
    def _build_status_bar(self):
        self.status_bar = tk.Frame(self, bg=SURFACE_CARD, height=28, bd=1, relief="solid", highlightthickness=1, highlightbackground=SURFACE_BORDER)
        self.status_bar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

        self.lbl_status = tk.Label(
            self.status_bar,
            text="Listo. Abra una fotografía para comenzar la recuperación documental.",
            font=FONT_BODY,
            fg=TEXT_MUTED,
            bg=SURFACE_CARD
        )
        self.lbl_status.pack(side="left", padx=12, pady=4)

        self.lbl_time = tk.Label(
            self.status_bar,
            text="Tiempo: -- ms",
            font=FONT_BODY,
            fg=TEXT_MUTED,
            bg=SURFACE_CARD
        )
        self.lbl_time.pack(side="right", padx=12, pady=4)

    # ==========================================
    # 4. GESTIÓN DE PESTAÑAS Y VISTAS
    # ==========================================
    def switch_view_tab(self, tab_id: str):
        self.active_tab = tab_id
        self._highlight_tab_button(tab_id)

        # Ocultar todas las vistas
        self.view_viewer.pack_forget()
        self.view_histogram.pack_forget()
        self.view_metrics.pack_forget()
        self.view_ocr.pack_forget()

        if tab_id == "viewer":
            self.view_viewer.pack(fill="both", expand=True)
        elif tab_id == "histogram":
            self.view_histogram.pack(fill="both", expand=True)
            self.update_histogram_plot()
        elif tab_id == "metrics":
            self.view_metrics.pack(fill="both", expand=True)
            self.update_metrics_table()
        elif tab_id == "ocr":
            self.view_ocr.pack(fill="both", expand=True)
            self.run_ocr_thesis_benchmark()

    def _highlight_tab_button(self, active_id: str):
        for tid, btn in self.tab_buttons.items():
            if tid == active_id:
                btn.config(bg=ACCENT_PRIMARY, fg="#0f172a", relief="solid")
            else:
                btn.config(bg=SURFACE_INNER, fg=TEXT_MUTED, relief="flat")

    # ==========================================
    # 5. CARGA DE ARCHIVOS Y MUESTRAS
    # ==========================================
    def _scan_sample_images(self):
        """Escanea las carpetas de muestra del taller (Edy, Ivan)."""
        search_paths = [
            os.path.join("DoCam", "Imagenes", "Edy", "*.jpeg"),
            os.path.join("DoCam", "Imagenes", "Edy", "*.jpg"),
            os.path.join("DoCam", "Imagenes", "Ivan", "*.jpeg"),
            os.path.join("DoCam", "Imagenes", "Ivan", "*.jpg"),
            os.path.join("Imagenes", "Edy", "*.jpeg"),
            os.path.join("Imagenes", "Ivan", "*.jpeg"),
        ]
        self.sample_files = []
        for pat in search_paths:
            self.sample_files.extend(glob.glob(pat))

        if self.sample_files:
            names = [f"📄 {os.path.basename(p)} ({os.path.dirname(p).split(os.sep)[-1]})" for p in self.sample_files]
            self.cb_samples['values'] = names
            self.sample_var.set("Seleccionar documento de muestra...")

    def rotate_document(self, angle_type: str = "cw"):
        """Gira la imagen original en 90° o 180° y re-calibra contornos."""
        if self.processor.original_image is None:
            messagebox.showinfo("Atención", "Cargue primero una imagen para poder girarla.")
            return

        rotated = self.processor.rotate_original(angle_type)
        if rotated is not None:
            doc_name = os.path.basename(self.processor.file_path) if self.processor.file_path else "Documento"
            self.canvas_orig.set_image(
                self.processor.original_image,
                corners=self.processor.corners,
                title=f"ORIGINAL ROTADO: {doc_name}"
            )
            # Limpiar canvas procesado para que el usuario ejecute la fase sobre la nueva orientación
            self.canvas_proc.set_image(None, title="DOCUMENTO EN FASE ACTUAL (Seleccione una fase)")
            self.metrics_bar.update_metrics(self.processor.original_metrics, self.processor.original_metrics)

            ang_label = "90° Horario (↻)" if angle_type == "cw" else ("90° Antihorario (↺)" if angle_type == "ccw" else "180°")
            self.lbl_status.config(text=f"Documento girado correctamente ({ang_label}). Orientación y esquinas actualizadas.")

    def _on_sample_selected(self, event=None):
        idx = self.cb_samples.current()
        if 0 <= idx < len(self.sample_files):
            self.load_image_file(self.sample_files[idx])

    def open_file_dialog(self):
        filetypes = [
            ("Imágenes de Documentos", "*.jpeg;*.jpg;*.png;*.bmp;*.tiff"),
            ("Todos los archivos", "*.*")
        ]
        path = filedialog.askopenfilename(title="Seleccionar fotografía de documento", filetypes=filetypes)
        if path:
            self.load_image_file(path)

    def load_image_file(self, path: str):
        if not os.path.isfile(path):
            return

        t0 = time.time()
        ok = self.processor.load_image(path)
        if not ok:
            messagebox.showerror("Error", f"No se pudo cargar la imagen:\n{path}")
            return

        elapsed = (time.time() - t0) * 1000
        fname = os.path.basename(path)
        self.lbl_active_doc.config(text=f"📄 {fname}")
        self.lbl_status.config(text=f"Documento cargado correctamente: {fname}")
        self.lbl_time.config(text=f"Carga: {elapsed:.1f} ms")

        # Mostrar en el canvas izquierdo con los 4 vértices de perspectiva detectados
        self.canvas_orig.set_image(
            self.processor.original_image,
            corners=self.processor.corners,
            title=f"ORIGINAL: {fname}"
        )
        # Limpiar canvas derecho
        self.canvas_proc.set_image(None, title="DOCUMENTO EN FASE ACTUAL")

        # Actualizar barra KPI
        self.metrics_bar.update_metrics(self.processor.original_metrics, self.processor.original_metrics)

        # Limpiar campos OCR para nuevo documento
        if hasattr(self, 'txt_reference'):
            self.txt_reference.delete("1.0", "end")
        if hasattr(self, 'txt_extracted'):
            self.txt_extracted.delete("1.0", "end")

        if self.active_tab == "ocr":
            self.run_ocr_thesis_benchmark()

        # Restablecer botones de fase
        self._reset_phase_buttons()
        self.show_phase_parameters("fase1")

    def _reset_phase_buttons(self):
        for btn in self.btn_phases.values():
            btn.config(bg=SURFACE_INNER, fg=TEXT_WHITE)

    def _mark_phase_active(self, phase_code: str, update_parameters: bool = True):
        self._reset_phase_buttons()
        if phase_code in self.btn_phases:
            self.btn_phases[phase_code].config(bg="#0369a1", fg="#ffffff")
        if update_parameters:
            self.show_phase_parameters(phase_code)

    def _on_corners_dragged(self, new_corners):
        """Callback cuando el usuario arrastra uno de los 4 vértices en el canvas."""
        self.processor.corners = new_corners
        if self.active_phase == "fase1":
            self.run_phase_1(skip_redraw_orig=True)

    # ==========================================
    # 6. EJECUCIÓN DE FASES (ACTIVIDADES)
    # ==========================================
    def run_phase_1(self, skip_redraw_orig=False):
        """Fase 1: Corrección de Perspectiva."""
        if self.processor.original_image is None:
            messagebox.showwarning("Atención", "Cargue primero un documento.")
            return

        t0 = time.time()
        warped = self.processor.run_phase_1_perspective()
        elapsed = (time.time() - t0) * 1000

        self.active_phase = "fase1"
        self._mark_phase_active("fase1")

        if not skip_redraw_orig:
            self.canvas_orig.set_corners(self.processor.corners)

        self.canvas_proc.set_image(warped, title="FASE 1: Perspectiva Corregida (Vista Frontal Orto-rectificada)")
        self.lbl_status.config(text="Fase 1 completada: Perspectiva corregida mediante homografía proyectiva.")
        self.lbl_time.config(text=f"Fase 1: {elapsed:.1f} ms")
        self._update_all_views()

    def run_phase_2(self):
        """Fase 2: Escala de Grises y CLAHE."""
        if self.processor.original_image is None:
            messagebox.showwarning("Atención", "Cargue primero un documento.")
            return

        t0 = time.time()
        enhanced = self.processor.run_phase_2_clahe()
        elapsed = (time.time() - t0) * 1000

        self.active_phase = "fase2"
        self._mark_phase_active("fase2")

        self.canvas_proc.set_image(enhanced, title="FASE 2: Escala de Grises y CLAHE (Mejora de Contraste Local)")
        self.lbl_status.config(text="Fase 2 completada: Contraste local acentuado sin amplificar ruido de fondo.")
        self.lbl_time.config(text=f"Fase 2: {elapsed:.1f} ms")
        self._update_all_views()

    def run_phase_3(self):
        """Fase 3: Filtrado de Ruido."""
        if self.processor.original_image is None:
            messagebox.showwarning("Atención", "Cargue primero un documento.")
            return

        t0 = time.time()
        denoised = self.processor.run_phase_3_denoise()
        elapsed = (time.time() - t0) * 1000

        self.active_phase = "fase3"
        self._mark_phase_active("fase3")

        self.canvas_proc.set_image(denoised, title="FASE 3: Filtrado de Ruido (Preservación de Bordes de Texto)")
        self.lbl_status.config(text="Fase 3 completada: Texturas del papel atenuadas y bordes tipográficos preservados.")
        self.lbl_time.config(text=f"Fase 3: {elapsed:.1f} ms")
        self._update_all_views()

    def run_phase_4(self):
        """Fase 4: Umbralización Adaptativa."""
        if self.processor.original_image is None:
            messagebox.showwarning("Atención", "Cargue primero un documento.")
            return

        t0 = time.time()
        binary = self.processor.run_phase_4_threshold()
        elapsed = (time.time() - t0) * 1000

        self.active_phase = "fase4"
        self._mark_phase_active("fase4")

        self.canvas_proc.set_image(binary, title="FASE 4: Umbralización Adaptativa (Eliminación Total de Sombras)")
        self.lbl_status.config(text="Fase 4 completada: Binarización adaptativa aplicada. Sombras de iluminación eliminadas.")
        self.lbl_time.config(text=f"Fase 4: {elapsed:.1f} ms")
        self._update_all_views()

    def run_phase_5(self):
        """Fase 5: Corrección de Inclinación."""
        if self.processor.original_image is None:
            messagebox.showwarning("Atención", "Cargue primero un documento.")
            return

        t0 = time.time()
        corrected, angle = self.processor.run_phase_5_deskew()
        elapsed = (time.time() - t0) * 1000

        self.active_phase = "fase5"
        self._mark_phase_active("fase5")

        self.canvas_proc.set_image(corrected, title=f"FASE 5: Deskew Final (Ángulo Corregido: {angle:.2f}°)")
        self.lbl_status.config(text=f"Fase 5 completada: Renglones alineados horizontalmente (Giro: {angle:.2f}°).")
        self.lbl_time.config(text=f"Fase 5: {elapsed:.1f} ms")
        self._update_all_views()

    def run_full_pipeline(self):
        """Ejecuta el pipeline completo de principio a fin."""
        if self.processor.original_image is None:
            messagebox.showwarning("Atención", "Cargue primero un documento.")
            return

        t0 = time.time()
        final_img = self.processor.run_full_pipeline()
        elapsed = (time.time() - t0) * 1000

        self.active_phase = "fase5"
        self._mark_phase_active("fase5")

        self.canvas_orig.set_corners(self.processor.corners)
        self.canvas_proc.set_image(
            final_img,
            title=f"FLUJO COMPLETO FINALIZADO (Ángulo Deskew: {self.processor.deskew_angle:.2f}°)"
        )
        self.lbl_status.config(text="Flujo completo ejecutado exitosamente: Perspectiva -> CLAHE -> Filtro -> Umbral -> Deskew.")
        self.lbl_time.config(text=f"Flujo Total: {elapsed:.1f} ms")
        self._update_all_views()

    def _update_all_views(self):
        latest = self.processor.get_latest_processed_image()
        if latest is not None:
            self.processor.processed_metrics = self.processor.processed_metrics or {}
            # Recalcular métricas actuales
            from pipeline.metrics import compute_all_metrics
            self.processor.processed_metrics = compute_all_metrics(latest)
            self.metrics_bar.update_metrics(self.processor.original_metrics, self.processor.processed_metrics)

            if self.active_tab == "histogram":
                self.update_histogram_plot()
            elif self.active_tab == "metrics":
                self.update_metrics_table()

    # ==========================================
    # 7. PARÁMETROS INTERACTIVOS POR FASE
    # ==========================================
    def show_phase_parameters(self, phase_code: str, force: bool = False):
        """Muestra los controles específicos para calibrar la fase seleccionada sin parpadeos."""
        if not force and getattr(self, "_current_param_phase", None) == phase_code:
            return
        self._current_param_phase = phase_code

        for w in self.param_container.winfo_children():
            w.destroy()

        if phase_code == "fase1":
            tk.Label(self.param_container, text="Ajuste de Esquinas:", font=FONT_BODY_BOLD, fg=TEXT_WHITE, bg=SURFACE_INNER).pack(anchor="w")
            tk.Label(
                self.param_container,
                text="• Arrastre los 4 vértices directamente en la foto de la izquierda para calibrar los bordes.",
                font=("Segoe UI", 8),
                fg=TEXT_MUTED,
                bg=SURFACE_INNER,
                wraplength=270,
                justify="left"
            ).pack(anchor="w", pady=4)

            btn_re_detect = tk.Button(
                self.param_container,
                text="🔄 Re-detectar Automáticamente",
                font=FONT_BODY,
                bg=SURFACE_CARD,
                fg=ACCENT_PRIMARY,
                bd=1,
                relief="solid",
                pady=4,
                cursor="hand2",
                command=lambda: [setattr(self.processor, 'corners', None), self.run_phase_1()]
            )
            btn_re_detect.pack(fill="x", pady=6)

        elif phase_code == "fase2":
            tk.Label(self.param_container, text="Parámetros CLAHE:", font=FONT_BODY_BOLD, fg=TEXT_WHITE, bg=SURFACE_INNER).pack(anchor="w")

            # Clip Limit Slider
            tk.Label(self.param_container, text="Clip Limit (Límite de contraste):", font=FONT_BODY, fg=TEXT_MUTED, bg=SURFACE_INNER).pack(anchor="w", pady=(4, 0))
            self.slider_clip = tk.Scale(
                self.param_container,
                from_=1.0,
                to=6.0,
                resolution=0.5,
                orient="horizontal",
                bg=SURFACE_INNER,
                fg=TEXT_WHITE,
                highlightthickness=0,
                troughcolor="#0f172a",
                command=self._on_clahe_slider_change
            )
            self.slider_clip.set(self.processor.params["clahe"]["clip_limit"])
            self.slider_clip.pack(fill="x")

            # Tile Size Slider
            tk.Label(self.param_container, text="Tamaño de Malla (Grid):", font=FONT_BODY, fg=TEXT_MUTED, bg=SURFACE_INNER).pack(anchor="w", pady=(4, 0))
            self.slider_tile = tk.Scale(
                self.param_container,
                from_=4,
                to=16,
                resolution=2,
                orient="horizontal",
                bg=SURFACE_INNER,
                fg=TEXT_WHITE,
                highlightthickness=0,
                troughcolor="#0f172a",
                command=self._on_clahe_slider_change
            )
            self.slider_tile.set(self.processor.params["clahe"]["tile_size"])
            self.slider_tile.pack(fill="x")

            btn_apply = tk.Button(
                self.param_container,
                text="Aplicar CLAHE",
                font=FONT_BODY_BOLD,
                bg=ACCENT_PRIMARY,
                fg="#0f172a",
                bd=0,
                pady=4,
                cursor="hand2",
                command=lambda: [
                    self.processor.run_phase_2_clahe(clip_limit=self.slider_clip.get(), tile_size=self.slider_tile.get()),
                    self.run_phase_2()
                ]
            )
            btn_apply.pack(fill="x", pady=8)

        elif phase_code == "fase3":
            tk.Label(self.param_container, text="Algoritmo de Filtrado de Ruido:", font=FONT_BODY_BOLD, fg=TEXT_WHITE, bg=SURFACE_INNER).pack(anchor="w")
            self.filter_var = tk.StringVar(value=self.processor.params["denoise"].get("method", "wiener"))

            for m_val, m_lbl in [
                ("wiener", "Filtro de Wiener (Desconvolución FFT)"),
                ("bilateral", "Bilateral (Conserva bordes)"),
                ("gaussian", "Gaussiano (Suave)"),
                ("median", "Mediana (Sal y Pimienta)")
            ]:
                tk.Radiobutton(
                    self.param_container,
                    text=m_lbl,
                    value=m_val,
                    variable=self.filter_var,
                    font=FONT_BODY,
                    fg=TEXT_WHITE,
                    bg=SURFACE_INNER,
                    selectcolor="#0f172a",
                    activebackground=SURFACE_INNER,
                    activeforeground=TEXT_WHITE,
                    command=lambda: self.show_phase_parameters("fase3", force=True)
                ).pack(anchor="w")

            curr_m = self.filter_var.get()
            if curr_m == "wiener":
                # K slider con respuesta interactiva inmediata
                tk.Label(self.param_container, text="Parámetro K (Relación Ruido/Señal):", font=FONT_BODY, fg=TEXT_MUTED, bg=SURFACE_INNER).pack(anchor="w", pady=(4, 0))
                self.slider_k = tk.Scale(
                    self.param_container,
                    from_=0.001,
                    to=0.100,
                    resolution=0.002,
                    orient="horizontal",
                    bg=SURFACE_INNER,
                    fg=TEXT_WHITE,
                    highlightthickness=0,
                    troughcolor="#0f172a",
                    command=self._on_wiener_slider_change
                )
                self.slider_k.set(self.processor.params["denoise"].get("k", 0.02))
                self.slider_k.pack(fill="x")

                # PSF Size slider con respuesta interactiva inmediata
                tk.Label(self.param_container, text="Tamaño PSF (Molde desenfoque h):", font=FONT_BODY, fg=TEXT_MUTED, bg=SURFACE_INNER).pack(anchor="w", pady=(4, 0))
                self.slider_psf_size = tk.Scale(
                    self.param_container,
                    from_=3,
                    to=15,
                    resolution=2,
                    orient="horizontal",
                    bg=SURFACE_INNER,
                    fg=TEXT_WHITE,
                    highlightthickness=0,
                    troughcolor="#0f172a",
                    command=self._on_wiener_slider_change
                )
                self.slider_psf_size.set(self.processor.params["denoise"].get("psf_size", 5))
                self.slider_psf_size.pack(fill="x")

                # PSF Sigma slider con respuesta interactiva inmediata
                tk.Label(self.param_container, text="Sigma PSF (Dispersión):", font=FONT_BODY, fg=TEXT_MUTED, bg=SURFACE_INNER).pack(anchor="w", pady=(4, 0))
                self.slider_psf_sigma = tk.Scale(
                    self.param_container,
                    from_=0.5,
                    to=3.0,
                    resolution=0.1,
                    orient="horizontal",
                    bg=SURFACE_INNER,
                    fg=TEXT_WHITE,
                    highlightthickness=0,
                    troughcolor="#0f172a",
                    command=self._on_wiener_slider_change
                )
                self.slider_psf_sigma.set(self.processor.params["denoise"].get("psf_sigma", 1.2))
                self.slider_psf_sigma.pack(fill="x")

                # Cuadro explicativo del modelo de Wiener
                tk.Label(
                    self.param_container,
                    text="⚡ Modelo: g = h * f + n (En tiempo real)\nF(u,v) = [ H*(u,v) / (|H(u,v)|² + K) ] · G(u,v)\n• Mueva las barras para ver el cambio directo.\n• K bajo = filtro inverso; K alto = mayor suavizado.",
                    font=("Segoe UI", 7, "italic"),
                    fg="#38bdf8",
                    bg="#0f172a",
                    padx=6,
                    pady=4,
                    justify="left"
                ).pack(fill="x", pady=4)

            btn_apply = tk.Button(
                self.param_container,
                text="Aplicar Filtrado",
                font=FONT_BODY_BOLD,
                bg=ACCENT_PRIMARY,
                fg="#0f172a",
                bd=0,
                pady=4,
                cursor="hand2",
                command=self._apply_phase_3_from_gui
            )
            btn_apply.pack(fill="x", pady=8)

        elif phase_code == "fase4":
            tk.Label(self.param_container, text="Algoritmo de Binarización:", font=FONT_BODY_BOLD, fg=TEXT_WHITE, bg=SURFACE_INNER).pack(anchor="w")
            self.thresh_var = tk.StringVar(value=self.processor.params["threshold"]["method"])
            for t_val, t_lbl in [
                ("sauvola", "Sauvola (Estándar de Oro Tesis)"),
                ("adaptive_gaussian", "Adaptativo Gaussiano (OpenCV)"),
                ("otsu", "Otsu (Umbral Global Óptimo)"),
                ("adaptive_mean", "Adaptativo Media Local")
            ]:
                tk.Radiobutton(
                    self.param_container,
                    text=t_lbl,
                    value=t_val,
                    variable=self.thresh_var,
                    font=FONT_BODY,
                    fg=TEXT_WHITE,
                    bg=SURFACE_INNER,
                    selectcolor="#0f172a",
                    activebackground=SURFACE_INNER,
                    activeforeground=TEXT_WHITE
                ).pack(anchor="w")

            btn_apply = tk.Button(
                self.param_container,
                text="Aplicar Umbralización",
                font=FONT_BODY_BOLD,
                bg=ACCENT_PRIMARY,
                fg="#0f172a",
                bd=0,
                pady=4,
                cursor="hand2",
                command=lambda: [
                    self.processor.run_phase_4_threshold(method=self.thresh_var.get()),
                    self.run_phase_4()
                ]
            )
            btn_apply.pack(fill="x", pady=8)

        elif phase_code == "fase5":
            tk.Label(self.param_container, text="Detección de Inclinación:", font=FONT_BODY_BOLD, fg=TEXT_WHITE, bg=SURFACE_INNER).pack(anchor="w")
            self.deskew_var = tk.StringVar(value=self.processor.params["deskew"]["method"])
            for d_val, d_lbl in [("hough", "Transformada de Hough"), ("min_area", "Rectángulo Mínimo de Texto")]:
                tk.Radiobutton(
                    self.param_container,
                    text=d_lbl,
                    value=d_val,
                    variable=self.deskew_var,
                    font=FONT_BODY,
                    fg=TEXT_WHITE,
                    bg=SURFACE_INNER,
                    selectcolor="#0f172a",
                    activebackground=SURFACE_INNER,
                    activeforeground=TEXT_WHITE
                ).pack(anchor="w")

            btn_apply = tk.Button(
                self.param_container,
                text="Aplicar Deskew",
                font=FONT_BODY_BOLD,
                bg=ACCENT_PRIMARY,
                fg="#0f172a",
                bd=0,
                pady=4,
                cursor="hand2",
                command=lambda: [
                    self.processor.run_phase_5_deskew(method=self.deskew_var.get()),
                    self.run_phase_5()
                ]
            )
            btn_apply.pack(fill="x", pady=8)

    # ==========================================
    # 8. GRÁFICAS DE HISTOGRAMAS (MATPLOTLIB)
    # ==========================================
    def update_histogram_plot(self):
        if self.processor.original_image is None:
            return

        self.ax_hist.clear()
        self.ax_hist.set_facecolor("#0b0f19")

        # Histograma original
        orig_hist, bins = compute_histogram(self.processor.original_image)
        self.ax_hist.plot(bins, orig_hist, color="#ef4444", label="Original Fotográfico (Gris)", linewidth=1.8, alpha=0.85)
        self.ax_hist.fill_between(bins, orig_hist, color="#ef4444", alpha=0.15)

        # Histograma procesado actual
        latest = self.processor.get_latest_processed_image()
        if latest is not None:
            proc_hist, _ = compute_histogram(latest)
            self.ax_hist.plot(bins, proc_hist, color="#38bdf8", label="Documento Procesado", linewidth=2.0)
            self.ax_hist.fill_between(bins, proc_hist, color="#38bdf8", alpha=0.2)

        self.ax_hist.set_title("Comparación de Densidad de Niveles de Gris (0=Negro Texto, 255=Blanco Fondo)", color="#f8fafc", fontsize=10, pad=10)
        self.ax_hist.set_xlabel("Nivel de Intensidad (Píxel)", color="#94a3b8", fontsize=9)
        self.ax_hist.set_ylabel("Frecuencia Normalizada", color="#94a3b8", fontsize=9)
        self.ax_hist.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#f8fafc")
        self.ax_hist.grid(True, linestyle="--", alpha=0.2, color="#64748b")

        self.fig_hist.tight_layout()
        self.canvas_hist.draw_idle()

    # ==========================================
    # 9. MATRIZ DE MÉTRICAS VISUALES
    # ==========================================
    def update_metrics_table(self):
        # Limpiar filas existentes
        for item in self.tree_metrics.get_children():
            self.tree_metrics.delete(item)

        orig = self.processor.original_metrics
        proc = self.processor.processed_metrics

        if not orig or not proc:
            return

        rows = [
            ("Nitidez (Varianza Laplaciana)", f"{orig.get('sharpness', 0):.1f}", f"{proc.get('sharpness', 0):.1f}", "Aumenta la definición de los contornos de las letras"),
            ("Contraste RMS", f"{orig.get('rms_contrast', 0):.3f}", f"{proc.get('rms_contrast', 0):.3f}", "Maximiza la diferencia entre la tinta del texto y el papel"),
            ("Contraste Michelson", f"{orig.get('michelson_contrast', 0):.3f}", f"{proc.get('michelson_contrast', 0):.3f}", "Acentúa la reflectancia en rangos extremos"),
            ("Relación Señal/Ruido (SNR)", f"{orig.get('snr_db', 0):.1f} dB", f"{proc.get('snr_db', 0):.1f} dB", "Reduce granularidad y sombras sin deformar caracteres"),
            ("Porcentaje de Tinta (%)", f"{orig.get('ink_ratio_pct', 0):.2f}%", f"{proc.get('ink_ratio_pct', 0):.2f}%", "Aísla el texto y limpia artefactos oscuros del fondo"),
            ("Dimensiones de Imagen", orig.get("dimensions", "--"), proc.get("dimensions", "--"), "Resolución ajustada tras homografía y deskew")
        ]

        for ind, val_o, val_p, desc in rows:
            try:
                num_o = float(val_o.replace(" dB", "").replace("%", ""))
                num_p = float(val_p.replace(" dB", "").replace("%", ""))
                delta = ((num_p - num_o) / abs(num_o) * 100) if num_o != 0 else 0
                sign = "+" if delta >= 0 else ""
                delta_str = f"{sign}{delta:.1f}%"
            except Exception:
                delta_str = "--"

            self.tree_metrics.insert("", "end", values=(ind, val_o, val_p, delta_str, desc))

    def _on_wiener_slider_change(self, value=None):
        """Disparado inmediatamente al mover cualquiera de las barras interactivas de Wiener."""
        if hasattr(self, "_wiener_timer") and self._wiener_timer:
            try:
                self.after_cancel(self._wiener_timer)
            except Exception:
                pass
        self._wiener_timer = self.after(35, self._apply_wiener_live)

    def _apply_wiener_live(self):
        """Aplica el filtro de Wiener en tiempo real sobre el visor derecho."""
        self._wiener_timer = None
        if self.processor.original_image is None:
            return

        try:
            k_val = getattr(self, "slider_k", None)
            k = float(k_val.get()) if k_val else 0.02
            psf_size_val = getattr(self, "slider_psf_size", None)
            psf_size = int(round(float(psf_size_val.get()))) if psf_size_val else 5
            if psf_size % 2 == 0:
                psf_size += 1
            psf_sigma_val = getattr(self, "slider_psf_sigma", None)
            psf_sigma = float(psf_sigma_val.get()) if psf_sigma_val else 1.2

            self.processor.params["denoise"].update({
                "method": "wiener",
                "k": k,
                "psf_size": psf_size,
                "psf_sigma": psf_sigma
            })

            denoised = self.processor.run_phase_3_denoise(
                method="wiener",
                k=k,
                psf_size=psf_size,
                psf_sigma=psf_sigma
            )

            self.active_phase = "fase3"
            self._mark_phase_active("fase3", update_parameters=False)

            self.canvas_proc.set_image(
                denoised,
                title=f"FASE 3: Filtro Wiener en Vivo (K={k:.3f}, PSF={psf_size}px, σ={psf_sigma:.1f})"
            )
            self.lbl_status.config(
                text=f"Wiener interactivo: K={k:.3f} | Molde PSF={psf_size}x{psf_size}px | Sigma={psf_sigma:.1f}"
            )
            self._update_all_views()
        except Exception as e:
            print(f"Error en Wiener interactivo: {e}")

    def _on_clahe_slider_change(self, value=None):
        """Disparado en tiempo real al mover barras de CLAHE."""
        if hasattr(self, "_clahe_timer") and self._clahe_timer:
            try:
                self.after_cancel(self._clahe_timer)
            except Exception:
                pass
        self._clahe_timer = self.after(35, self._apply_clahe_live)

    def _apply_clahe_live(self):
        self._clahe_timer = None
        if self.processor.original_image is None:
            return
        try:
            clip = float(self.slider_clip.get())
            tile = int(round(float(self.slider_tile.get())))
            self.processor.params["clahe"]["clip_limit"] = clip
            self.processor.params["clahe"]["tile_size"] = tile
            enhanced = self.processor.run_phase_2_clahe(clip_limit=clip, tile_size=tile)
            self.active_phase = "fase2"
            self._mark_phase_active("fase2", update_parameters=False)
            self.canvas_proc.set_image(enhanced, title=f"FASE 2: CLAHE en Vivo (Clip={clip:.1f}, Grid={tile}x{tile})")
            self._update_all_views()
        except Exception as e:
            print(f"Error CLAHE interactivo: {e}")

    def _apply_phase_3_from_gui(self):
        """Aplica la configuración de Fase 3 (Wiener o filtros espaciales)."""
        m = self.filter_var.get()
        if m == "wiener":
            self._apply_wiener_live()
        else:
            self.processor.params["denoise"]["method"] = m
            self.processor.run_phase_3_denoise(method=m)
            self.run_phase_3()

    def browse_tesseract_path(self):
        """Permite al usuario seleccionar la ruta de tesseract.exe en su equipo."""
        filetypes = [("Ejecutable de Tesseract", "tesseract.exe"), ("Todos los ejecutables", "*.exe")]
        path = filedialog.askopenfilename(title="Seleccionar ejecutable tesseract.exe", filetypes=filetypes)
        if path and os.path.isfile(path):
            from pipeline.ocr import set_custom_tesseract_path
            set_custom_tesseract_path(path)
            messagebox.showinfo("Tesseract Vinculado", f"Tesseract configurado correctamente:\n{path}")
            self.run_ocr_thesis_benchmark(force_refresh_ref=True)

    # ==========================================
    # 10. EXPERIMENTO DE TESIS: OCR (CER & WER)
    # ==========================================
    def run_ocr_thesis_benchmark(self, force_refresh_ref: bool = False):
        """
        Ejecuta automáticamente el reconocimiento OCR sobre la imagen actual
        y calcula el benchmark de las 4 etapas del taller.
        """
        if self.processor.original_image is None:
            return

        ref_text = None
        if not force_refresh_ref:
            current_ref = self.txt_reference.get("1.0", "end-1c").strip()
            if current_ref:
                ref_text = current_ref

        self.lbl_status.config(text="Reconociendo automáticamente texto de la imagen y calculando CER/WER...")
        self.update_idletasks()

        t0 = time.time()
        results = self.processor.run_thesis_ocr_evaluation(ref_text=ref_text)
        elapsed = (time.time() - t0) * 1000

        # Limpiar filas previas
        for item in self.tree_ocr.get_children():
            self.tree_ocr.delete(item)

        conclusions = [
            "Línea base: Alto error por sombras y perspectiva",
            "Mejora moderada: Letras tenues se vuelven legibles",
            "Gran reducción de error: Sombras eliminadas por binarización",
            "Óptimo: Renglones ortogonales y nítidos maximizan exactitud"
        ]

        for idx, r in enumerate(results):
            concl = conclusions[idx] if idx < len(conclusions) else "Completado"
            self.tree_ocr.insert(
                "",
                "end",
                values=(
                    r["stage"],
                    f"{r['cer_pct']:.2f}%",
                    f"{r['wer_pct']:.2f}%",
                    f"{r['accuracy_pct']:.2f}%",
                    concl
                )
            )

        # Mostrar texto extraído de la etapa óptima (flujo completo)
        if results:
            best = results[-1]
            self.txt_extracted.delete("1.0", "end")
            self.txt_extracted.insert("1.0", best["extracted_text"])

            # Auto-poblar el texto de referencia con la transcripción obtenida si estaba vacío
            if not self.txt_reference.get("1.0", "end-1c").strip():
                self.txt_reference.delete("1.0", "end")
                self.txt_reference.insert("1.0", self.processor.reference_text)

            is_tess = best.get("is_real_tesseract", False)
            engine_str = "Tesseract OCR Oficial" if is_tess else "OCR Óptico Nativo (Directo de la Imagen)"
            if hasattr(self, 'lbl_ocr_engine'):
                self.lbl_ocr_engine.config(text=f"Motor Activo: {engine_str}")

        self.lbl_status.config(text=f"OCR completado automáticamente. Texto de su imagen extraído.")
        self.lbl_time.config(text=f"Benchmark OCR: {elapsed:.1f} ms")

    # ==========================================
    # 11. EXPORTACIÓN DE DOCUMENTO Y REPORTE
    # ==========================================
    def show_export_dialog(self):
        latest = self.processor.get_latest_processed_image()
        if latest is None:
            messagebox.showwarning("Atención", "No hay ningún documento procesado para exportar.")
            return

        export_win = tk.Toplevel(self)
        export_win.title("Exportar Documento Digitalizado y Reporte Científico")
        export_win.geometry("560x360")
        export_win.configure(bg=SURFACE_CARD)
        export_win.grab_set()

        # Centrar ventana modal
        export_win.update_idletasks()
        w = export_win.winfo_width()
        h = export_win.winfo_height()
        x = (export_win.winfo_screenwidth() // 2) - (w // 2)
        y = (export_win.winfo_screenheight() // 2) - (h // 2)
        export_win.geometry(f"+{x}+{y}")

        tk.Label(
            export_win,
            text="Opciones de Exportación Institucional",
            font=FONT_TITLE_PANEL,
            fg=TEXT_WHITE,
            bg=SURFACE_CARD
        ).pack(anchor="w", padx=20, pady=(16, 8))

        # Botón 1: Exportar Imagen PNG / JPG
        btn_img = tk.Button(
            export_win,
            text="🖼️ Guardar Imagen Digitalizada (PNG / JPG / TIFF)",
            font=FONT_BODY_BOLD,
            bg=SURFACE_INNER,
            fg=ACCENT_PRIMARY,
            bd=1,
            relief="solid",
            pady=8,
            cursor="hand2",
            command=lambda: [self._export_image(), export_win.destroy()]
        )
        btn_img.pack(fill="x", padx=20, pady=6)

        # Botón 2: Exportar PDF Documental
        btn_pdf = tk.Button(
            export_win,
            text="📄 Generar Documento PDF A4 (Listo para Archivo)",
            font=FONT_BODY_BOLD,
            bg=SURFACE_INNER,
            fg=ACCENT_SUCCESS,
            bd=1,
            relief="solid",
            pady=8,
            cursor="hand2",
            command=lambda: [self._export_document_pdf(), export_win.destroy()]
        )
        btn_pdf.pack(fill="x", padx=20, pady=6)

        # Botón 3: Generar Reporte Científico Académico de Tesis
        btn_report = tk.Button(
            export_win,
            text="🎓 Generar Informe Científico de Métricas y OCR (PDF)",
            font=FONT_BODY_BOLD,
            bg=SURFACE_INNER,
            fg=ACCENT_WARNING,
            bd=1,
            relief="solid",
            pady=8,
            cursor="hand2",
            command=lambda: [self._export_scientific_report(), export_win.destroy()]
        )
        btn_report.pack(fill="x", padx=20, pady=6)

        # Botón Cancelar
        btn_cancel = tk.Button(
            export_win,
            text="Cerrar",
            font=FONT_BODY,
            bg=SURFACE_CARD,
            fg=TEXT_MUTED,
            bd=0,
            cursor="hand2",
            command=export_win.destroy
        )
        btn_cancel.pack(pady=12)

    def _export_image(self):
        latest = self.processor.get_latest_processed_image()
        filetypes = [
            ("Imagen PNG (*.png)", "*.png"),
            ("Imagen JPEG (*.jpg)", "*.jpg"),
            ("Todos los archivos", "*.*")
        ]
        out_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=filetypes, title="Guardar Documento Procesado")
        if out_path:
            ok = save_image(latest, out_path)
            if ok:
                messagebox.showinfo("Éxito", f"Documento guardado correctamente:\n{out_path}")

    def _export_document_pdf(self):
        latest = self.processor.get_latest_processed_image()
        filetypes = [("Documento PDF (*.pdf)", "*.pdf")]
        out_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=filetypes, title="Exportar Documento PDF A4")
        if out_path:
            ok = export_document_pdf(latest, out_path)
            if ok:
                messagebox.showinfo("Éxito", f"Documento PDF generado exitosamente:\n{out_path}")

    def _export_scientific_report(self):
        latest = self.processor.get_latest_processed_image()
        if latest is None:
            return

        # Asegurar OCR calculado
        if not self.processor.ocr_results:
            self.processor.run_thesis_ocr_evaluation(self.txt_reference.get("1.0", "end-1c").strip())

        filetypes = [("Reporte Científico PDF (*.pdf)", "*.pdf")]
        out_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=filetypes, title="Guardar Reporte Académico PDF")
        if out_path:
            ok = export_scientific_report(
                out_path,
                self.processor.original_metrics,
                self.processor.processed_metrics,
                self.processor.ocr_results,
                self.processor.params
            )
            if ok:
                messagebox.showinfo("Éxito", f"Reporte Científico PDF generado con éxito:\n{out_path}")

