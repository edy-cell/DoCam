"""
DocuScan U - Sistema de Diseño y Estilos UI
Paleta de colores moderna, tipografías y configuración temática institucional
"""

# Paleta de Colores Moderna (Cyber-Academic Dark Theme)
BG_DARK = "#090d16"         # Fondo principal de la ventana
SURFACE_CARD = "#111827"    # Contenedores, tarjetas y paneles principales
SURFACE_INNER = "#1e293b"   # Superficies internas, marcos y cajas de control
SURFACE_BORDER = "#334155"  # Bordes sutiles y divisores
SURFACE_HOVER = "#243247"   # Efecto hover sobre tarjetas

# Colores de Acento y Estado
ACCENT_PRIMARY = "#38bdf8"  # Cyan eléctrico (Acción principal, foco)
ACCENT_PRIMARY_HOVER = "#0284c7"
ACCENT_SUCCESS = "#10b981"  # Verde esmeralda (Completado, flujo exitoso)
ACCENT_SUCCESS_HOVER = "#059669"
ACCENT_WARNING = "#f59e0b"  # Ámbar (Alertas, valores intermedios)
ACCENT_INFO = "#6366f1"     # Indigo / Violeta institucional
ACCENT_DANGER = "#ef4444"   # Coral / Rojo suave

# Tipografía y Textos
TEXT_WHITE = "#f8fafc"      # Blanco puro para títulos y métricas clave
TEXT_MUTED = "#94a3b8"      # Gris claro para etiquetas secundarias
TEXT_FAINT = "#64748b"      # Gris atenuado para notas al pie y versiones

# Fuentes del Sistema
FONT_TITLE_MAIN = ("Segoe UI", 16, "bold")
FONT_TITLE_PANEL = ("Segoe UI", 12, "bold")
FONT_SUBTITLE = ("Segoe UI", 10, "bold")
FONT_BODY = ("Segoe UI", 9)
FONT_BODY_BOLD = ("Segoe UI", 9, "bold")
FONT_MONO = ("Consolas", 9)
FONT_METRIC_VALUE = ("Segoe UI", 16, "bold")
FONT_METRIC_LABEL = ("Segoe UI", 8)
FONT_PHASE_NUM = ("Segoe UI", 10, "bold")


def configure_app_styles(root):
    """Configura los estilos base de ttk y la ventana raíz."""
    root.configure(bg=BG_DARK)
    
    # Intento de activación de alta resolución DPI en Windows
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

