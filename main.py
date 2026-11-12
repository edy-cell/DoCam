"""
DocuScan U: Recuperación Inteligente de Documentos Fotografiados
Digitalización Institucional - Procesamiento Digital de Imágenes

Punto de entrada de la aplicación.
Ejecuta la interfaz gráfica profesional en modo pantalla completa y centrado.
"""

import sys
import os

# Asegurar que el directorio del proyecto esté en el sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCAM_DIR = os.path.join(BASE_DIR, "DoCam")

if os.path.isdir(DOCAM_DIR) and DOCAM_DIR not in sys.path:
    sys.path.insert(0, DOCAM_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from gui.app import DocuScanApp


def main():
    print("Iniciando DocuScan U - Digitalización Institucional...")
    app = DocuScanApp()
    app.mainloop()


if __name__ == "__main__":
    main()

