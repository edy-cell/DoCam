"""
DocuScan U - Visor Interactivo de Imágenes sobre Canvas
Soporta Zoom fluido, Paneo (arrastre), Ajuste a Pantalla y Puntos de Perspectiva
"""

import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
import cv2
from .styles import BG_DARK, SURFACE_CARD, SURFACE_BORDER, ACCENT_PRIMARY, ACCENT_SUCCESS, TEXT_WHITE, TEXT_MUTED


class ZoomableImageCanvas(tk.Frame):
    def __init__(self, parent, title="Documento", editable_corners=False, on_corners_changed=None, on_rotate=None, **kwargs):
        super().__init__(parent, bg=SURFACE_CARD, bd=1, relief="solid", highlightthickness=1, highlightbackground=SURFACE_BORDER, **kwargs)
        
        self.title_text = title
        self.editable_corners = editable_corners
        self.on_corners_changed = on_corners_changed
        self.on_rotate = on_rotate

        self.cv_image: np.ndarray | None = None
        self.pil_image: Image.Image | None = None
        self.tk_image: ImageTk.PhotoImage | None = None

        self.zoom_scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.drag_start_x = 0
        self.drag_start_y = 0

        # Puntos de perspectiva (esquinas cuadrilátero) en coordenadas originales [4, 2]
        self.corners: np.ndarray | None = None
        self.selected_corner_idx: int | None = None
        self.handle_radius = 8

        self._build_header()
        self._build_canvas()

    def _build_header(self):
        self.header_frame = tk.Frame(self, bg=SURFACE_CARD, height=32)
        self.header_frame.pack(side="top", fill="x", padx=8, pady=4)

        self.lbl_title = tk.Label(
            self.header_frame,
            text=self.title_text,
            font=("Segoe UI", 10, "bold"),
            fg=TEXT_WHITE,
            bg=SURFACE_CARD
        )
        self.lbl_title.pack(side="left")

        self.lbl_info = tk.Label(
            self.header_frame,
            text="Sin imagen",
            font=("Segoe UI", 8),
            fg=TEXT_MUTED,
            bg=SURFACE_CARD
        )
        self.lbl_info.pack(side="left", padx=10)

        # Botones de control de zoom y rotación
        self.btn_reset = tk.Button(
            self.header_frame,
            text="⛶ Ajustar",
            font=("Segoe UI", 8, "bold"),
            bg="#1e293b",
            fg=ACCENT_PRIMARY,
            bd=0,
            padx=6,
            pady=1,
            cursor="hand2",
            activebackground="#334155",
            activeforeground=TEXT_WHITE,
            command=self.fit_to_canvas
        )
        self.btn_reset.pack(side="right", padx=2)

        self.btn_zoom_out = tk.Button(
            self.header_frame,
            text="－",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg=TEXT_WHITE,
            bd=0,
            padx=6,
            pady=0,
            cursor="hand2",
            command=lambda: self.zoom(0.8)
        )
        self.btn_zoom_out.pack(side="right", padx=2)

        self.btn_zoom_in = tk.Button(
            self.header_frame,
            text="＋",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg=TEXT_WHITE,
            bd=0,
            padx=6,
            pady=0,
            cursor="hand2",
            command=lambda: self.zoom(1.25)
        )
        self.btn_zoom_in.pack(side="right", padx=2)

        if self.on_rotate:
            self.btn_rot_cw = tk.Button(
                self.header_frame,
                text="↻ Girar 90°",
                font=("Segoe UI", 8, "bold"),
                bg="#1e293b",
                fg=TEXT_WHITE,
                bd=0,
                padx=6,
                pady=1,
                cursor="hand2",
                activebackground="#334155",
                activeforeground=ACCENT_PRIMARY,
                command=lambda: self.on_rotate("cw")
            )
            self.btn_rot_cw.pack(side="right", padx=(8, 2))

            self.btn_rot_ccw = tk.Button(
                self.header_frame,
                text="↺",
                font=("Segoe UI", 9, "bold"),
                bg="#1e293b",
                fg=TEXT_WHITE,
                bd=0,
                padx=6,
                pady=0,
                cursor="hand2",
                activebackground="#334155",
                activeforeground=ACCENT_PRIMARY,
                command=lambda: self.on_rotate("ccw")
            )
            self.btn_rot_ccw.pack(side="right", padx=2)

    def _build_canvas(self):
        self.canvas = tk.Canvas(
            self,
            bg="#070a12",
            bd=0,
            highlightthickness=0,
            cursor="cross"
        )
        self.canvas.pack(fill="both", expand=True)

        # Eventos de interacción
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<ButtonPress-1>", self._on_button_press)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_button_release)

    def set_image(self, cv_img: np.ndarray | None, corners: np.ndarray | None = None, title: str | None = None):
        """Asigna una nueva imagen en formato OpenCV (BGR o Escala de Grises)."""
        if title:
            self.title_text = title
            self.lbl_title.config(text=title)

        if cv_img is None:
            self.cv_image = None
            self.pil_image = None
            self.tk_image = None
            self.canvas.delete("all")
            self.lbl_info.config(text="Sin imagen")
            return

        self.cv_image = cv_img.copy()

        # Convertir a PIL Image
        if len(cv_img.shape) == 2:
            self.pil_image = Image.fromarray(cv_img)
        elif cv_img.shape[2] == 3:
            rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            self.pil_image = Image.fromarray(rgb)
        elif cv_img.shape[2] == 4:
            rgba = cv2.cvtColor(cv_img, cv2.COLOR_BGRA2RGBA)
            self.pil_image = Image.fromarray(rgba)

        h, w = cv_img.shape[:2]
        self.lbl_info.config(text=f"{w}×{h} px")

        if corners is not None:
            self.corners = corners.copy().astype(np.float32)

        self.fit_to_canvas()

    def set_corners(self, corners: np.ndarray | None):
        """Actualiza los puntos de perspectiva a proyectar sobre la imagen."""
        if corners is not None:
            self.corners = corners.copy().astype(np.float32)
        else:
            self.corners = None
        self._render()

    def fit_to_canvas(self):
        """Ajusta la imagen para ocupar todo el canvas disponible manteniendo proporción."""
        if not self.pil_image:
            return

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        if canvas_w <= 1 or canvas_h <= 1:
            self.after(50, self.fit_to_canvas)
            return

        img_w, img_h = self.pil_image.size
        scale_w = canvas_w / img_w
        scale_h = canvas_h / img_h
        self.zoom_scale = min(scale_w, scale_h) * 0.95

        # Centrar la imagen en el canvas
        scaled_w = int(img_w * self.zoom_scale)
        scaled_h = int(img_h * self.zoom_scale)
        self.pan_x = (canvas_w - scaled_w) // 2
        self.pan_y = (canvas_h - scaled_h) // 2

        self._render()

    def zoom(self, factor: float):
        """Aplica zoom centrado en la vista."""
        if not self.pil_image:
            return

        new_scale = self.zoom_scale * factor
        # Límites de zoom entre 10% y 800%
        if new_scale < 0.05 or new_scale > 15.0:
            return

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        center_x = canvas_w / 2
        center_y = canvas_h / 2

        # Ajustar paneo para mantener el centro
        self.pan_x = center_x - (center_x - self.pan_x) * factor
        self.pan_y = center_y - (center_y - self.pan_y) * factor
        self.zoom_scale = new_scale

        self._render()

    def _on_resize(self, event):
        if self.pil_image and self.zoom_scale == 1.0:
            self.fit_to_canvas()
        else:
            self._render()

    def _on_mousewheel(self, event):
        if not self.pil_image:
            return
        factor = 1.15 if event.delta > 0 else 0.85
        self.zoom(factor)

    def _img_to_canvas_coords(self, x: float, y: float) -> tuple[float, float]:
        cx = (x * self.zoom_scale) + self.pan_x
        cy = (y * self.zoom_scale) + self.pan_y
        return cx, cy

    def _canvas_to_img_coords(self, cx: float, cy: float) -> tuple[float, float]:
        ix = (cx - self.pan_x) / self.zoom_scale
        iy = (cy - self.pan_y) / self.zoom_scale
        return ix, iy

    def _on_button_press(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

        if self.editable_corners and self.corners is not None and self.pil_image:
            # Comprobar si el usuario hizo clic en alguno de los 4 vértices
            for idx, pt in enumerate(self.corners):
                cx, cy = self._img_to_canvas_coords(pt[0], pt[1])
                dist = np.hypot(event.x - cx, event.y - cy)
                if dist <= (self.handle_radius + 6):
                    self.selected_corner_idx = idx
                    self.canvas.config(cursor="fleur")
                    return

        self.selected_corner_idx = None
        self.canvas.config(cursor="hand1")

    def _on_mouse_drag(self, event):
        if not self.pil_image:
            return

        # Si se está arrastrando una esquina de perspectiva
        if self.selected_corner_idx is not None and self.corners is not None:
            ix, iy = self._canvas_to_img_coords(event.x, event.y)
            w, h = self.pil_image.size
            ix = max(0, min(w, ix))
            iy = max(0, min(h, iy))
            self.corners[self.selected_corner_idx] = [ix, iy]
            self._render()
            if self.on_corners_changed:
                self.on_corners_changed(self.corners.copy())
            return

        # Paneo general de la imagen
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        self.pan_x += dx
        self.pan_y += dy
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self._render()

    def _on_button_release(self, event):
        self.selected_corner_idx = None
        self.canvas.config(cursor="cross")

    def _render(self):
        """Redibuja la imagen escalada y los gráficos en el canvas."""
        self.canvas.delete("all")
        if not self.pil_image:
            # Mensaje placeholder
            cw = max(200, self.canvas.winfo_width())
            ch = max(200, self.canvas.winfo_height())
            self.canvas.create_text(
                cw // 2,
                ch // 2,
                text="Ningún documento cargado\nSeleccione una imagen para comenzar",
                fill="#475569",
                font=("Segoe UI", 12),
                justify="center"
            )
            return

        orig_w, orig_h = self.pil_image.size
        scaled_w = max(1, int(orig_w * self.zoom_scale))
        scaled_h = max(1, int(orig_h * self.zoom_scale))

        # Redimensionar usando Pillow
        resized = self.pil_image.resize((scaled_w, scaled_h), Image.Resampling.BILINEAR)
        self.tk_image = ImageTk.PhotoImage(resized)

        self.canvas.create_image(
            int(self.pan_x),
            int(self.pan_y),
            anchor="nw",
            image=self.tk_image
        )

        # Si hay esquinas de cuadrilátero que mostrar
        if self.corners is not None and len(self.corners) == 4:
            canvas_pts = []
            for pt in self.corners:
                cx, cy = self._img_to_canvas_coords(pt[0], pt[1])
                canvas_pts.append((cx, cy))

            # Dibujar polígono semi-translúcido / borde de perspectiva
            poly_coords = []
            for p in canvas_pts:
                poly_coords.extend([p[0], p[1]])

            self.canvas.create_polygon(
                poly_coords,
                outline=ACCENT_PRIMARY,
                width=2,
                fill="",
                dash=(6, 4)
            )

            # Dibujar los 4 vértices como manijas arrastrables
            labels = ["1: Sup-Izq", "2: Sup-Der", "3: Inf-Der", "4: Inf-Izq"]
            colors = [ACCENT_PRIMARY, ACCENT_SUCCESS, ACCENT_SUCCESS, ACCENT_PRIMARY]

            for i, (cx, cy) in enumerate(canvas_pts):
                r = self.handle_radius
                self.canvas.create_oval(
                    cx - r, cy - r, cx + r, cy + r,
                    fill=colors[i],
                    outline="#ffffff",
                    width=2
                )
                self.canvas.create_text(
                    cx + 12,
                    cy - 10,
                    text=labels[i],
                    fill="#38bdf8",
                    font=("Segoe UI", 8, "bold"),
                    anchor="w"
                )

        # Indicador de zoom en la esquina inferior izquierda
        zoom_pct = int(self.zoom_scale * 100)
        self.canvas.create_text(
            15,
            self.canvas.winfo_height() - 15 if self.canvas.winfo_height() > 30 else 20,
            text=f"Zoom: {zoom_pct}%",
            fill="#64748b",
            font=("Segoe UI", 8, "bold"),
            anchor="sw"
        )

