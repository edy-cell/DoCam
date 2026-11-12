"""
DocuScan U - Tarjetas y Paneles de Métricas de Calidad Documental
Muestra indicadores visuales de legibilidad con comparativas antes/después
"""

import tkinter as tk
from .styles import SURFACE_CARD, SURFACE_INNER, SURFACE_BORDER, ACCENT_PRIMARY, ACCENT_SUCCESS, ACCENT_WARNING, TEXT_WHITE, TEXT_MUTED


class MetricCard(tk.Frame):
    """Tarjeta individual tipo KPI que muestra un valor con su delta porcentual."""
    def __init__(self, parent, title: str, unit: str = "", **kwargs):
        super().__init__(parent, bg=SURFACE_INNER, bd=1, relief="solid", highlightthickness=1, highlightbackground=SURFACE_BORDER, **kwargs)
        self.unit = unit

        self.lbl_title = tk.Label(
            self,
            text=title,
            font=("Segoe UI", 8, "bold"),
            fg=TEXT_MUTED,
            bg=SURFACE_INNER,
            anchor="w"
        )
        self.lbl_title.pack(fill="x", padx=10, pady=(6, 2))

        self.frame_values = tk.Frame(self, bg=SURFACE_INNER)
        self.frame_values.pack(fill="x", padx=10, pady=(0, 6))

        self.lbl_value = tk.Label(
            self.frame_values,
            text="--",
            font=("Segoe UI", 14, "bold"),
            fg=TEXT_WHITE,
            bg=SURFACE_INNER,
            anchor="w"
        )
        self.lbl_value.pack(side="left")

        self.lbl_delta = tk.Label(
            self.frame_values,
            text="",
            font=("Segoe UI", 8, "bold"),
            fg=ACCENT_SUCCESS,
            bg=SURFACE_INNER,
            anchor="w"
        )
        self.lbl_delta.pack(side="left", padx=8)

    def set_value(self, current_val, original_val=None, format_str="{:.2f}", is_higher_better=True):
        if current_val is None:
            self.lbl_value.config(text="--")
            self.lbl_delta.config(text="")
            return

        formatted = format_str.format(current_val)
        if self.unit:
            formatted += f" {self.unit}"
        self.lbl_value.config(text=formatted)

        if original_val is not None and original_val != 0:
            delta = ((current_val - original_val) / abs(original_val)) * 100.0
            sign = "+" if delta >= 0 else ""
            delta_text = f"{sign}{delta:.1f}%"
            
            # Color del delta según si es mejor
            if delta > 0.5:
                color = ACCENT_SUCCESS if is_higher_better else ACCENT_WARNING
            elif delta < -0.5:
                color = ACCENT_WARNING if is_higher_better else ACCENT_SUCCESS
            else:
                color = TEXT_MUTED

            self.lbl_delta.config(text=delta_text, fg=color)
        else:
            self.lbl_delta.config(text="")


class MetricsSummaryBar(tk.Frame):
    """Barra horizontal de tarjetas de métricas para la pantalla de evaluación."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=SURFACE_CARD, **kwargs)

        self.card_sharpness = MetricCard(self, "NITIDEZ (LAPLACIANO)")
        self.card_sharpness.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        self.card_contrast = MetricCard(self, "CONTRASTE RMS")
        self.card_contrast.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        self.card_snr = MetricCard(self, "RELACIÓN SEÑAL/RUIDO", unit="dB")
        self.card_snr.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        self.card_ink = MetricCard(self, "COBERTURA DE TEXTO", unit="%")
        self.card_ink.pack(side="left", fill="both", expand=True, padx=4, pady=4)

    def update_metrics(self, original_metrics: dict, processed_metrics: dict):
        if not processed_metrics:
            return

        orig_sharp = original_metrics.get("sharpness", 0.0)
        proc_sharp = processed_metrics.get("sharpness", 0.0)
        self.card_sharpness.set_value(proc_sharp, orig_sharp, format_str="{:.1f}")

        orig_rms = original_metrics.get("rms_contrast", 0.0)
        proc_rms = processed_metrics.get("rms_contrast", 0.0)
        self.card_contrast.set_value(proc_rms, orig_rms, format_str="{:.3f}")

        orig_snr = original_metrics.get("snr_db", 0.0)
        proc_snr = processed_metrics.get("snr_db", 0.0)
        self.card_snr.set_value(proc_snr, orig_snr, format_str="{:.1f}")

        orig_ink = original_metrics.get("ink_ratio_pct", 0.0)
        proc_ink = processed_metrics.get("ink_ratio_pct", 0.0)
        self.card_ink.set_value(proc_ink, orig_ink, format_str="{:.1f}", is_higher_better=False)

