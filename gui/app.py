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

try:
    from pipeline import (
        DocumentProcessor,
        compute_histogram,
        save_image,
        export_document_pdf,
        export_scientific_report
    )
except ImportError:
    from DoCam.pipeline import (
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
            text="PIPELINE AUTOMÁTICO",
            font=FONT_SUBTITLE,
            fg=TEXT_MUTED,
            bg=SURFACE_CARD,
            anchor="w"
        )
        lbl_side.pack(fill="x", padx=14, pady=(10, 4))

        # 1. Cargar Documento
        load_frame = tk.Frame(self.sidebar, bg=SURFACE_CARD)
        load_frame.pack(fill="x", padx=12, pady=(0, 6))

        btn_load = tk.Button(
            load_frame,
            text="📂 Abrir Fotografía...",
            font=FONT_BODY_BOLD,
            bg="#2563eb",
            fg=TEXT_WHITE,
            activebackground="#1d4ed8",
            activeforeground=TEXT_WHITE,
            bd=0,
            pady=7,
            cursor="hand2",
            command=self.open_file_dialog
        )
        btn_load.pack(fill="x")

        # Selector de imágenes de prueba reales del taller
        sample_frame = tk.Frame(self.sidebar, bg=SURFACE_CARD)
        sample_frame.pack(fill="x", padx=12, pady=(0, 6))

        tk.Label(sample_frame, text="Documentos de muestra (Taller):", font=("Segoe UI", 8), fg=TEXT_MUTED, bg=SURFACE_CARD).pack(anchor="w")
        self.sample_var = tk.StringVar(value="Seleccionar documento de muestra...")
        self.cb_samples = ttk.Combobox(sample_frame, textvariable=self.sample_var, state="readonly", font=FONT_BODY)
        self.cb_samples.pack(fill="x", pady=2)
        self.cb_samples.bind("<<ComboboxSelected>>", self._on_sample_selected)

        # Controles de Orientación y Giro Manual
        rot_frame = tk.Frame(self.sidebar, bg=SURFACE_CARD)
        rot_frame.pack(fill="x", padx=12, pady=(0, 6))

        tk.Label(rot_frame, text="Giro de Orientación Manual:", font=("Segoe UI", 8, "bold"), fg=TEXT_MUTED, bg=SURFACE_CARD).pack(anchor="w")

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
            pady=3,
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
            pady=3,
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
            pady=3,
            cursor="hand2",
            command=lambda: self.rotate_document("180")
        ).pack(side="left", fill="x", expand=True, padx=(2, 0))

        # 2. Panel de Decisiones y Optimización 100% Automática (Sin Sliders Manuales)
        auto_box = tk.LabelFrame(
            self.sidebar,
            text="🧠 Optimización Automática Dinámica",
            font=("Segoe UI", 8, "bold"),
            fg=ACCENT_PRIMARY,
            bg=SURFACE_CARD,
            bd=1,
            relief="solid"
        )
        auto_box.pack(fill="x", padx=12, pady=(0, 6))

        tk.Label(
            auto_box,
            text="El sistema evalúa y selecciona automáticamente los mejores filtros según las características de cada fotografía.",
            font=("Segoe UI", 7),
            fg=TEXT_MUTED,
            bg=SURFACE_CARD,
            wraplength=275,
            justify="left"
        ).pack(fill="x", padx=8, pady=(4, 6))

        self.auto_status_items = {}
        auto_defs = [
            ("orient", "🔄 Orientación", "Auto-Detección 360° (Hough/Perfiles)"),
            ("geom", "📐 Perspectiva", "Homografía 4 vértices sin recorte"),
            ("shadows", "🌓 Sombras", "División morfológica de fondo"),
            ("clahe", "⚡ Contraste", "CLAHE dinámico calibrado por RMS"),
            ("denoise", "🧹 Ruido", "Filtro preservador según SNR"),
            ("sharp", "🔤 Nitidez", "Unsharp Masking dinámico (Tenengrad)"),
            ("thresh", "📄 Binarización", "Segmentación adaptativa limpia"),
        ]

        for key, title, desc in auto_defs:
            f = tk.Frame(auto_box, bg=SURFACE_CARD)
            f.pack(fill="x", padx=8, pady=2)
            tk.Label(f, text=f"• {title}:", font=("Segoe UI", 8, "bold"), fg=TEXT_WHITE, bg=SURFACE_CARD).pack(anchor="w")
            lbl_desc = tk.Label(f, text=f"  {desc}", font=("Segoe UI", 7), fg=ACCENT_SUCCESS, bg=SURFACE_CARD, wraplength=270, justify="left")
            lbl_desc.pack(anchor="w")
            self.auto_status_items[key] = lbl_desc

        # 3. Botón de Procesamiento Continuo Automático
        self.btn_auto_continuous = tk.Button(
            self.sidebar,
            text="⚡ PROCESAR AUTOMÁTICAMENTE\n(100% Continuo e Inteligente)",
            font=("Segoe UI", 9, "bold"),
            bg="#059669",
            fg=TEXT_WHITE,
            activebackground="#10b981",
            activeforeground=TEXT_WHITE,
            bd=0,
            pady=8,
            cursor="hand2",
            command=self.run_auto_continuous_flow
        )
        self.btn_auto_continuous.pack(fill="x", padx=12, pady=(2, 6))

        # Botón de alternancia de Zoom/Pan sincronizado
        self.btn_toggle_sync = tk.Button(
            self.sidebar,
            text="🔗 Zoom Sincronizado: ACTIVO",
            font=("Segoe UI", 8, "bold"),
            bg=SURFACE_INNER,
            fg=ACCENT_SUCCESS,
            bd=1,
            relief="solid",
            pady=4,
            cursor="hand2",
            command=self.toggle_sync_zoom
        )
        self.btn_toggle_sync.pack(fill="x", padx=12, pady=(0, 6))

        # 4. Sección de Exportación Explícita (Control dedicado del usuario)
        export_box = tk.LabelFrame(
            self.sidebar,
            text="💾 Exportación Controlada por el Usuario",
            font=("Segoe UI", 8, "bold"),
            fg=ACCENT_PRIMARY,
            bg=SURFACE_CARD,
            bd=1,
            relief="solid"
        )
        export_box.pack(fill="x", padx=12, pady=(0, 6))

        self.btn_export_img = tk.Button(
            export_box,
            text="💾 Guardar Imagen Procesada...",
            font=FONT_BODY_BOLD,
            bg=SURFACE_INNER,
            fg=ACCENT_PRIMARY,
            bd=1,
            relief="solid",
            pady=4,
            cursor="hand2",
            command=self._export_image
        )
        self.btn_export_img.pack(fill="x", padx=8, pady=(4, 2))

        self.btn_export_txt = tk.Button(
            export_box,
            text="📋 Guardar Texto OCR (.txt)...",
            font=FONT_BODY_BOLD,
            bg=SURFACE_INNER,
            fg=ACCENT_SUCCESS,
            bd=1,
            relief="solid",
            pady=4,
            cursor="hand2",
            command=self.export_ocr_text
        )
        self.btn_export_txt.pack(fill="x", padx=8, pady=2)

        self.btn_export_pdf = tk.Button(
            export_box,
            text="📄 Exportar Documento PDF A4...",
            font=FONT_BODY,
            bg=SURFACE_INNER,
            fg=TEXT_WHITE,
            bd=1,
            relief="solid",
            pady=4,
            cursor="hand2",
            command=self._export_document_pdf
        )
        self.btn_export_pdf.pack(fill="x", padx=8, pady=2)

        self.btn_export_report = tk.Button(
            export_box,
            text="🎓 Informe Científico de Tesis (PDF)...",
            font=FONT_BODY,
            bg=SURFACE_INNER,
            fg=ACCENT_WARNING,
            bd=1,
            relief="solid",
            pady=4,
            cursor="hand2",
            command=self._export_scientific_report
        )
        self.btn_export_report.pack(fill="x", padx=8, pady=(2, 4))

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
        # 1. Barra de control de modo de visualización para la imagen procesada
        top_ctrl = tk.Frame(parent, bg=SURFACE_CARD, height=36, bd=1, relief="solid", highlightthickness=1, highlightbackground=SURFACE_BORDER)
        top_ctrl.pack(fill="x", pady=(0, 4))

        tk.Label(
            top_ctrl,
            text="Visualización de Salida:",
            font=("Segoe UI", 9, "bold"),
            fg=TEXT_WHITE,
            bg=SURFACE_CARD
        ).pack(side="left", padx=(10, 8), pady=4)

        self.proc_mode = "hd"
        self.btn_view_hd = tk.Button(
            top_ctrl,
            text="📄 Escáner HD (Recomendado)",
            font=("Segoe UI", 8, "bold"),
            bg="#0284c7",
            fg=TEXT_WHITE,
            bd=0,
            padx=10,
            pady=3,
            cursor="hand2",
            command=lambda: self.set_proc_view_mode("hd")
        )
        self.btn_view_hd.pack(side="left", padx=3, pady=4)

        self.btn_view_bin = tk.Button(
            top_ctrl,
            text="⚡ Modo Binario Limpio",
            font=("Segoe UI", 8, "bold"),
            bg=SURFACE_INNER,
            fg=TEXT_MUTED,
            bd=0,
            padx=10,
            pady=3,
            cursor="hand2",
            command=lambda: self.set_proc_view_mode("binary")
        )
        self.btn_view_bin.pack(side="left", padx=3, pady=4)

        # Botón de alternancia de sincronización de zoom
        self.btn_sync_toggle = tk.Button(
            top_ctrl,
            text="🔗 Zoom Sincronizado: ON",
            font=("Segoe UI", 8, "bold"),
            bg=SURFACE_INNER,
            fg=ACCENT_SUCCESS,
            bd=1,
            relief="solid",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.toggle_sync_zoom
        )
        self.btn_sync_toggle.pack(side="left", padx=6, pady=4)

        btn_re_auto = tk.Button(
            top_ctrl,
            text="⚡ Re-procesar Automático",
            font=("Segoe UI", 8, "bold"),
            bg="#059669",
            fg=TEXT_WHITE,
            bd=0,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.run_auto_continuous_flow
        )
        btn_re_auto.pack(side="right", padx=10, pady=4)

        # 2. Dos visores de Canvas interactivos lado a lado
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
            title="DOCUMENTO PROCESADO (Escáner HD Inteligente)",
            editable_corners=False
        )
        self.canvas_proc.pack(side="right", fill="both", expand=True, padx=(4, 0))

        # Vinculación bidireccional de Zoom y Paneo Sincronizado
        self.canvas_orig.set_peer_canvas(self.canvas_proc)
        self.canvas_proc.set_peer_canvas(self.canvas_orig)

        # 3. Paneles Inferiores: Resumen de Métricas Comparativas & Reconocimiento OCR
        bottom_box = tk.Frame(parent, bg=BG_DARK, height=185)
        bottom_box.pack(fill="x", pady=(4, 0))
        bottom_box.pack_propagate(False)

        # Subpanel Izquierdo: Métricas Comparativas y Resumen Técnico
        summary_card = tk.Frame(bottom_box, bg=SURFACE_CARD, bd=1, relief="solid", highlightthickness=1, highlightbackground=SURFACE_BORDER)
        summary_card.pack(side="left", fill="both", expand=True, padx=(0, 4))

        summary_header = tk.Frame(summary_card, bg=SURFACE_CARD)
        summary_header.pack(fill="x", padx=10, pady=(4, 2))

        tk.Label(
            summary_header,
            text="📊 Métricas Comparativas (Antes vs Después)",
            font=("Segoe UI", 9, "bold"),
            fg=ACCENT_PRIMARY,
            bg=SURFACE_CARD
        ).pack(side="left")

        self.btn_toggle_view_report = tk.Button(
            summary_header,
            text="Ver Informe Técnico",
            font=("Segoe UI", 7, "bold"),
            bg=SURFACE_INNER,
            fg=TEXT_MUTED,
            bd=1,
            relief="solid",
            padx=6,
            pady=1,
            cursor="hand2",
            command=self._toggle_metrics_report_view
        )
        self.btn_toggle_view_report.pack(side="right")

        # Contenedor para tabla de métricas comparativas
        self.frame_comp_metrics = tk.Frame(summary_card, bg=SURFACE_CARD)
        self.frame_comp_metrics.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        cols = ("metrica", "original", "procesado", "delta")
        self.tree_comp_metrics = ttk.Treeview(self.frame_comp_metrics, columns=cols, show="headings", height=5)
        self.tree_comp_metrics.heading("metrica", text="Indicador")
        self.tree_comp_metrics.heading("original", text="Original")
        self.tree_comp_metrics.heading("procesado", text="Procesado")
        self.tree_comp_metrics.heading("delta", text="Mejora Δ")

        self.tree_comp_metrics.column("metrica", width=160)
        self.tree_comp_metrics.column("original", width=90, anchor="center")
        self.tree_comp_metrics.column("procesado", width=90, anchor="center")
        self.tree_comp_metrics.column("delta", width=90, anchor="center")
        self.tree_comp_metrics.pack(fill="both", expand=True)

        self.txt_summary = tk.Text(
            summary_card,
            bg="#070a12",
            fg="#cbd5e1",
            font=("Consolas", 8),
            bd=0,
            padx=8,
            pady=4,
            wrap="word"
        )
        # Por defecto se muestra la tabla comparativa

        # Subpanel Derecho: Reconocimiento OCR y Texto Extraído
        ocr_card = tk.Frame(bottom_box, bg=SURFACE_CARD, bd=1, relief="solid", highlightthickness=1, highlightbackground=SURFACE_BORDER)
        ocr_card.pack(side="right", fill="both", expand=True, padx=(4, 0))

        ocr_header = tk.Frame(ocr_card, bg=SURFACE_CARD)
        ocr_header.pack(fill="x", padx=10, pady=(4, 2))

        tk.Label(
            ocr_header,
            text="🔤 Reconocimiento OCR de la Imagen",
            font=("Segoe UI", 9, "bold"),
            fg=ACCENT_SUCCESS,
            bg=SURFACE_CARD
        ).pack(side="left")

        self.lbl_ocr_chars = tk.Label(
            ocr_header,
            text="-- caracteres",
            font=("Segoe UI", 8),
            fg=TEXT_MUTED,
            bg=SURFACE_CARD
        )
        self.lbl_ocr_chars.pack(side="left", padx=8)

        btn_save_txt = tk.Button(
            ocr_header,
            text="💾 Guardar .txt",
            font=("Segoe UI", 7, "bold"),
            bg=SURFACE_INNER,
            fg=ACCENT_PRIMARY,
            bd=1,
            relief="solid",
            padx=6,
            pady=1,
            cursor="hand2",
            command=self.export_ocr_text
        )
        btn_save_txt.pack(side="right", padx=(2, 0))

        btn_copy = tk.Button(
            ocr_header,
            text="📋 Copiar",
            font=("Segoe UI", 7, "bold"),
            bg=SURFACE_INNER,
            fg=TEXT_WHITE,
            bd=1,
            relief="solid",
            padx=6,
            pady=1,
            cursor="hand2",
            command=self.copy_ocr_to_clipboard
        )
        btn_copy.pack(side="right", padx=2)

        self.txt_ocr_preview = tk.Text(
            ocr_card,
            bg="#070a12",
            fg="#f8fafc",
            font=("Consolas", 8),
            bd=0,
            padx=8,
            pady=4,
            wrap="word"
        )
        self.txt_ocr_preview.pack(fill="both", expand=True, padx=8, pady=(0, 4))

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
            ang_label = "90° Horario (↻)" if angle_type == "cw" else ("90° Antihorario (↺)" if angle_type == "ccw" else "180°")
            self.lbl_status.config(text=f"Documento girado ({ang_label}). Ejecutando optimización automática...")
            
            # Ejecutar automáticamente el flujo continuo sobre la nueva orientación
            self.run_auto_continuous_flow()

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

        # Actualizar barra KPI con valores base
        self.metrics_bar.update_metrics(self.processor.original_metrics, self.processor.original_metrics)

        # Limpiar campos OCR para nuevo documento
        if hasattr(self, 'txt_reference'):
            self.txt_reference.delete("1.0", "end")
        if hasattr(self, 'txt_extracted'):
            self.txt_extracted.delete("1.0", "end")

        # Ejecutar inmediatamente el flujo continuo inteligente
        self.run_auto_continuous_flow()

    def set_proc_view_mode(self, mode: str):
        """Alterna la visualización del visor derecho entre Escáner HD y Modo Binario."""
        self.proc_mode = mode
        if mode == "hd":
            if hasattr(self, 'btn_view_hd'):
                self.btn_view_hd.config(bg="#0284c7", fg=TEXT_WHITE)
            if hasattr(self, 'btn_view_bin'):
                self.btn_view_bin.config(bg=SURFACE_INNER, fg=TEXT_MUTED)
            if self.processor.hd_image is not None:
                self.canvas_proc.set_image(
                    self.processor.hd_image,
                    title="DOCUMENTO PROCESADO (Escáner HD Inteligente)"
                )
        elif mode == "binary":
            if hasattr(self, 'btn_view_bin'):
                self.btn_view_bin.config(bg="#0284c7", fg=TEXT_WHITE)
            if hasattr(self, 'btn_view_hd'):
                self.btn_view_hd.config(bg=SURFACE_INNER, fg=TEXT_MUTED)
            if self.processor.binary_image is not None:
                self.canvas_proc.set_image(
                    self.processor.binary_image,
                    title="DOCUMENTO PROCESADO (Modo Binario Limpio)"
                )

    def _on_clahe_slider_change(self, val):
        try:
            self.lbl_clahe_val.config(text=f"{float(val):.1f}")
        except Exception:
            pass

    def _on_unsharp_slider_change(self, val):
        try:
            self.lbl_unsharp_val.config(text=f"{float(val):.2f}x")
        except Exception:
            pass

    def toggle_sync_zoom(self):
        """Alterna el estado de sincronización bidireccional de Zoom/Pan entre visores."""
        self.sync_active = not getattr(self, "sync_active", True)
        self.canvas_orig.set_sync_active(self.sync_active)
        self.canvas_proc.set_sync_active(self.sync_active)
        if self.sync_active:
            if hasattr(self, 'btn_toggle_sync'):
                self.btn_toggle_sync.config(text="🔗 Zoom Sincronizado: ACTIVO", fg=ACCENT_SUCCESS)
            if hasattr(self, 'btn_sync_toggle'):
                self.btn_sync_toggle.config(text="🔗 Zoom Sincronizado: ON", fg=ACCENT_SUCCESS)
            self.canvas_orig._broadcast_view()
        else:
            if hasattr(self, 'btn_toggle_sync'):
                self.btn_toggle_sync.config(text="🔓 Zoom Sincronizado: INACTIVO", fg=TEXT_MUTED)
            if hasattr(self, 'btn_sync_toggle'):
                self.btn_sync_toggle.config(text="🔓 Zoom Sincronizado: OFF", fg=TEXT_MUTED)

    def copy_ocr_to_clipboard(self):
        """Copia el texto del cuadro OCR directamente al portapapeles."""
        text = self.txt_ocr_preview.get("1.0", "end-1c") if hasattr(self, 'txt_ocr_preview') else ""
        if not text.strip():
            messagebox.showinfo("OCR", "No hay texto extraído disponible para copiar.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.lbl_status.config(text="Texto OCR copiado al portapapeles.")

    def export_ocr_text(self):
        """Abre un diálogo filedialog explícito para guardar el texto OCR extraído."""
        text = self.txt_ocr_preview.get("1.0", "end-1c") if hasattr(self, 'txt_ocr_preview') else ""
        if not text.strip():
            messagebox.showwarning("Atención", "No hay texto OCR para exportar.")
            return
        filetypes = [("Archivo de Texto (*.txt)", "*.txt"), ("Todos los archivos", "*.*")]
        out_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=filetypes, title="Guardar Texto OCR Extraído")
        if out_path:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            messagebox.showinfo("Éxito", f"Texto OCR guardado correctamente en:\n{out_path}")
            self.lbl_status.config(text=f"Texto OCR exportado a: {os.path.basename(out_path)}")

    def _toggle_metrics_report_view(self):
        """Alterna entre la tabla comparativa de métricas y el informe técnico textual."""
        if hasattr(self, 'txt_summary') and hasattr(self, 'frame_comp_metrics'):
            if self.frame_comp_metrics.winfo_ismapped():
                self.frame_comp_metrics.pack_forget()
                self.txt_summary.pack(fill="both", expand=True, padx=8, pady=(0, 4))
                self.btn_toggle_view_report.config(text="Ver Tabla Comparativa")
            else:
                self.txt_summary.pack_forget()
                self.frame_comp_metrics.pack(fill="both", expand=True, padx=8, pady=(0, 4))
                self.btn_toggle_view_report.config(text="Ver Informe Técnico")

    def run_auto_continuous_flow(self):
        """
        Ejecuta el pipeline optimizado 100% automático en un solo flujo continuo:
        - Detecta bordes y corrige perspectiva y orientación.
        - Aplica dinámicamente división de fondo morfológica, CLAHE, reducción de ruido y unsharp.
        - Genera imagen Escáner HD y Modo Binario limpio.
        - Ejecuta OCR y extrae texto de la imagen de forma nativa/Tesseract.
        - Genera resumen técnico integral de transformaciones y métricas.
        """
        if self.processor.original_image is None:
            messagebox.showwarning("Atención", "Cargue primero una fotografía de documento.")
            return

        self.lbl_status.config(text="Procesando documento automáticamente en flujo continuo inteligente...")
        self.update_idletasks()

        # Ejecución 100% Automática: El motor decide los mejores filtros y parámetros
        t0 = time.time()
        res = self.processor.process_automatic_continuous()
        elapsed = (time.time() - t0) * 1000

        # Actualizar diagnóstico de decisiones automáticas
        if hasattr(self, 'auto_status_items'):
            angle = res.get("technical_summary", {}).get("angle", 0.0)
            orig_sharp = self.processor.original_metrics.get("sharpness", 0.0)
            rms = self.processor.original_metrics.get("rms_contrast", 0.0)
            snr = self.processor.original_metrics.get("snr_db", 0.0)

            if "orient" in self.auto_status_items:
                self.auto_status_items["orient"].config(text=f"  ✓ Orientación calibrada ({angle:.2f}°)")
            if "clahe" in self.auto_status_items:
                self.auto_status_items["clahe"].config(text=f"  ✓ CLAHE adaptativo (RMS {rms:.3f})")
            if "sharp" in self.auto_status_items:
                self.auto_status_items["sharp"].config(text=f"  ✓ Realce ajustado ({orig_sharp:.1f} var)")
            if "denoise" in self.auto_status_items:
                self.auto_status_items["denoise"].config(text=f"  ✓ Filtro según SNR ({snr:.1f} dB)")

        # Actualizar visores según modo activo
        if getattr(self, "proc_mode", "hd") == "binary" and res.get("binary_image") is not None:
            self.canvas_proc.set_image(res["binary_image"], title="DOCUMENTO PROCESADO (Modo Binario Limpio)")
        else:
            self.canvas_proc.set_image(res.get("hd_image"), title="DOCUMENTO PROCESADO (Escáner HD Inteligente)")

        self.canvas_orig.set_corners(self.processor.corners)

        # Actualizar barra KPI superior
        self.metrics_bar.update_metrics(self.processor.original_metrics, self.processor.processed_metrics)

        # Actualizar tabla comparativa de métricas en el panel inferior
        if hasattr(self, 'tree_comp_metrics'):
            for item in self.tree_comp_metrics.get_children():
                self.tree_comp_metrics.delete(item)

            orig = self.processor.original_metrics
            proc = self.processor.processed_metrics
            comp = self.processor.comparison_metrics

            sharp_orig = orig.get("sharpness", 0.0)
            sharp_proc = proc.get("sharpness", 0.0)
            sharp_delta = comp.get("sharpness", {}).get("delta_pct", 0.0)

            rms_orig = orig.get("rms_contrast", 0.0)
            rms_proc = proc.get("rms_contrast", 0.0)
            rms_delta = comp.get("rms_contrast", {}).get("delta_pct", 0.0)

            snr_orig = orig.get("snr_db", 0.0)
            snr_proc = proc.get("snr_db", 0.0)
            snr_diff = proc.get("snr_db", 0.0) - orig.get("snr_db", 0.0)

            conf_orig = orig.get("ocr_confidence", 0.0)
            conf_proc = proc.get("ocr_confidence", 0.0)
            conf_delta = comp.get("ocr_confidence", {}).get("delta_pct", 0.0)

            words_orig = orig.get("ocr_words", 0)
            words_proc = proc.get("ocr_words", 0)

            chars_orig = orig.get("ocr_chars", 0)
            chars_proc = proc.get("ocr_chars", 0)

            comp_rows = [
                ("Nitidez (Laplaciano)", f"{sharp_orig:.1f}", f"{sharp_proc:.1f}", f"{'+' if sharp_delta>=0 else ''}{sharp_delta:.1f}%"),
                ("Contraste RMS", f"{rms_orig:.3f}", f"{rms_proc:.3f}", f"{'+' if rms_delta>=0 else ''}{rms_delta:.1f}%"),
                ("Relación Señal/Ruido", f"{snr_orig:.1f} dB", f"{snr_proc:.1f} dB", f"{'+' if snr_diff>=0 else ''}{snr_diff:.1f} dB"),
                ("Confianza OCR Prom.", f"{conf_orig:.1f}%", f"{conf_proc:.1f}%", f"{'+' if conf_delta>=0 else ''}{conf_delta:.1f}%"),
                ("Palabras Detectadas", f"{words_orig}", f"{words_proc}", f"+{max(0, words_proc - words_orig)}"),
                ("Caracteres Detectados", f"{chars_orig}", f"{chars_proc}", f"+{max(0, chars_proc - chars_orig)}"),
            ]

            for row in comp_rows:
                self.tree_comp_metrics.insert("", "end", values=row)

        # Actualizar panel inferior: Resumen Técnico
        if hasattr(self, 'txt_summary'):
            self.txt_summary.delete("1.0", "end")
            self.txt_summary.insert("1.0", res.get("report_text", ""))

        # Actualizar panel inferior: OCR Preview
        if hasattr(self, 'txt_ocr_preview'):
            self.txt_ocr_preview.delete("1.0", "end")
            self.txt_ocr_preview.insert("1.0", res.get("extracted_text", ""))

        if hasattr(self, 'lbl_ocr_chars'):
            c_len = len(res.get("extracted_text", ""))
            is_tess = res.get("technical_summary", {}).get("is_tesseract", False)
            engine = "Tesseract" if is_tess else "Nativo"
            self.lbl_ocr_chars.config(text=f"{c_len} caracteres ({engine})")

        # Actualizar pestaña de OCR de tesis
        if hasattr(self, 'txt_extracted'):
            self.txt_extracted.delete("1.0", "end")
            self.txt_extracted.insert("1.0", res.get("extracted_text", ""))
        if hasattr(self, 'txt_reference'):
            if not self.txt_reference.get("1.0", "end-1c").strip():
                self.txt_reference.delete("1.0", "end")
                self.txt_reference.insert("1.0", res.get("extracted_text", ""))

        # Actualizar tabla de OCR
        if hasattr(self, 'tree_ocr') and res.get("ocr_results"):
            for item in self.tree_ocr.get_children():
                self.tree_ocr.delete(item)
            conclusions = [
                "Línea base: Alto error por sombras y perspectiva",
                "Mejora moderada: Letras tenues se vuelven legibles",
                "Gran reducción de error: Sombras eliminadas por binarización",
                "Óptimo: Renglones ortogonales y nítidos maximizan exactitud"
            ]
            for idx, r in enumerate(res["ocr_results"]):
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

        if self.active_tab == "histogram":
            self.update_histogram_plot()
        elif self.active_tab == "metrics":
            self.update_metrics_table()

        self.lbl_status.config(text="Procesamiento continuo completado: Perspectiva, Sombras, Nitidez y OCR automáticos.")
        self.lbl_time.config(text=f"Flujo Automático: {elapsed:.1f} ms")

    def _on_corners_dragged(self, new_corners):
        """Callback cuando el usuario arrastra manualmente uno de los 4 vértices en el visor izquierdo."""
        self.processor.corners = new_corners
        self.run_auto_continuous_flow()

    def _update_all_views(self):
        latest = self.processor.get_latest_processed_image()
        if latest is not None:
            self.processor.processed_metrics = self.processor.processed_metrics or {}
            try:
                from pipeline.metrics import compute_all_metrics
            except ImportError:
                from DoCam.pipeline.metrics import compute_all_metrics
            self.processor.processed_metrics = compute_all_metrics(latest)
            self.metrics_bar.update_metrics(self.processor.original_metrics, self.processor.processed_metrics)

            if self.active_tab == "histogram":
                self.update_histogram_plot()
            elif self.active_tab == "metrics":
                self.update_metrics_table()

    # ==========================================
    # 7. GRÁFICAS DE HISTOGRAMAS (MATPLOTLIB)
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

    def browse_tesseract_path(self):
        """Permite al usuario seleccionar la ruta de tesseract.exe en su equipo."""
        filetypes = [("Ejecutable de Tesseract", "tesseract.exe"), ("Todos los ejecutables", "*.exe")]
        path = filedialog.askopenfilename(title="Seleccionar ejecutable tesseract.exe", filetypes=filetypes)
        if path and os.path.isfile(path):
            try:
                from pipeline.ocr import set_custom_tesseract_path
            except ImportError:
                from DoCam.pipeline.ocr import set_custom_tesseract_path
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

