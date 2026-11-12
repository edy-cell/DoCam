"""
DocuScan U - Módulo de Filtrado de Ruido
Fase 3 del Pipeline: Reducción de granularidad y preservación de bordes de texto
"""

import cv2
import numpy as np


def make_gaussian_psf(shape: tuple[int, int], size: int = 5, sigma: float = 1.2) -> np.ndarray:
    """
    Genera la PSF (Point Spread Function, molde de desenfoque h)
    con respuesta impulsional Gaussiana, centrada en el origen de frecuencias (0,0).
    """
    k = size if size % 2 == 1 else size + 1
    ax = np.linspace(-(k // 2), k // 2, k)
    gauss = np.exp(-0.5 * np.square(ax) / (max(sigma, 1e-4) ** 2))
    kernel = np.outer(gauss, gauss)
    kernel /= (kernel.sum() + 1e-12)

    psf = np.zeros(shape, dtype=np.float32)
    kh, kw = kernel.shape
    psf[:kh, :kw] = kernel
    # Desplazar el centro del kernel al origen (0, 0) para convolución de Fourier sin desfase
    psf = np.roll(psf, -kh // 2, axis=0)
    psf = np.roll(psf, -kw // 2, axis=1)
    return psf


def apply_wiener_filter(image: np.ndarray, psf_size: int = 5, psf_sigma: float = 1.2, k: float = 0.02) -> np.ndarray:
    """
    Filtro de Wiener en el dominio de la frecuencia (FFT 2D):
    Modelo de degradación:
        g = h * f + n
        g: imagen observada (borrosa y con ruido)
        f: imagen original a restaurar
        h: PSF (Point Spread Function, molde del desenfoque)
        n: ruido aditivo

    Restauración en frecuencia:
        F(u,v) = [ H*(u,v) / ( |H(u,v)|² + K ) ] · G(u,v)

        H*(u,v): conjugado complejo de H(u,v) = FFT2(h)
        |H(u,v)|²: densidad espectral de potencia de la PSF
        K: relación ruido/señal (NSR).
           Si K = 0: filtro inverso puro (muy inestable con ruido).
           Si K grande: mayor suavizado y regularización.
    """
    is_color = (len(image.shape) == 3 and image.shape[2] >= 3)
    
    if is_color:
        channels = cv2.split(image)
        restored_channels = [
            _wiener_single_channel(ch, psf_size=psf_size, psf_sigma=psf_sigma, k=k)
            for ch in channels
        ]
        return cv2.merge(restored_channels)
    else:
        return _wiener_single_channel(image, psf_size=psf_size, psf_sigma=psf_sigma, k=k)


def _wiener_single_channel(channel: np.ndarray, psf_size: int = 5, psf_sigma: float = 1.2, k: float = 0.02) -> np.ndarray:
    """Aplica el filtro de Wiener sobre un solo canal 2D en punto flotante."""
    h, w = channel.shape[:2]
    img_float = channel.astype(np.float32) / 255.0

    # 1. Crear PSF del desenfoque h(x,y)
    psf = make_gaussian_psf((h, w), size=psf_size, sigma=psf_sigma)

    # 2. Transformada de Fourier 2D: G(u,v) y H(u,v)
    G = np.fft.fft2(img_float)
    H = np.fft.fft2(psf)

    # 3. H*(u,v) y |H(u,v)|²
    H_conj = np.conj(H)
    H_mag_sq = np.real(H * H_conj)

    # 4. Función de transferencia del Filtro de Wiener W(u,v)
    k_val = max(float(k), 1e-6)
    W = H_conj / (H_mag_sq + k_val)

    # 5. Imagen recuperada en frecuencia: F(u,v) = W(u,v) * G(u,v)
    F = W * G

    # 6. Transformada inversa de Fourier 2D: f(x,y) = IFFT2(F)
    f_restored = np.real(np.fft.ifft2(F))

    # 7. Normalización y recorte al rango válido [0, 255]
    f_clipped = np.clip(f_restored * 255.0, 0, 255).astype(np.uint8)
    return f_clipped


def apply_gaussian_filter(image: np.ndarray, ksize: int = 5, sigma: float = 1.0) -> np.ndarray:
    """Filtro Gaussiano para suavizado general del ruido de sensor."""
    k = ksize if ksize % 2 == 1 else ksize + 1
    return cv2.GaussianBlur(image, (k, k), sigmaX=float(sigma))


def apply_median_filter(image: np.ndarray, ksize: int = 3) -> np.ndarray:
    """Filtro de Mediana: idóneo para ruido impulsivo (sal y pimienta, motas de polvo)."""
    k = ksize if ksize % 2 == 1 else ksize + 1
    return cv2.medianBlur(image, k)


def apply_bilateral_filter(image: np.ndarray, d: int = 9, sigma_color: float = 75.0, sigma_space: float = 75.0) -> np.ndarray:
    """
    Filtro Bilateral: suaviza texturas del papel (grano, arrugas) mientras
    mantiene nítidos y definidos los bordes de los caracteres tipográficos.
    """
    return cv2.bilateralFilter(image, d=int(d), sigmaColor=float(sigma_color), sigmaSpace=float(sigma_space))


def filter_noise(image: np.ndarray, method: str = "wiener", **kwargs) -> np.ndarray:
    """
    Selector unificado de filtrado de ruido.
    Métodos: 'wiener', 'bilateral', 'gaussian', 'median', 'none'
    """
    method = method.lower()
    if method == "wiener":
        psf_size = kwargs.get("psf_size", 5)
        psf_sigma = kwargs.get("psf_sigma", 1.2)
        k = kwargs.get("k", 0.02)
        return apply_wiener_filter(image, psf_size=psf_size, psf_sigma=psf_sigma, k=k)
    elif method == "bilateral":
        d = kwargs.get("d", 7)
        sigma_color = kwargs.get("sigma_color", 50.0)
        sigma_space = kwargs.get("sigma_space", 50.0)
        return apply_bilateral_filter(image, d=d, sigma_color=sigma_color, sigma_space=sigma_space)
    elif method == "gaussian":
        ksize = kwargs.get("ksize", 5)
        sigma = kwargs.get("sigma", 1.0)
        return apply_gaussian_filter(image, ksize=ksize, sigma=sigma)
    elif method == "median":
        ksize = kwargs.get("ksize", 3)
        return apply_median_filter(image, ksize=ksize)
    else:
        return image.copy()

