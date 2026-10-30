"""Separación CMYK y trama hexagonal en coordenadas globales (mm).

Convención de coordenadas del diseño: origen abajo a la izquierda, x hacia la derecha,
y hacia arriba. La rejilla de cada tinta se define en esas coordenadas para toda la imagen,
de modo que los puntos son continuos entre baldosas vecinas (plan §9.4).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage

K_HEX = math.pi / (2 * math.sqrt(3))  # 0,9069: cobertura = K_HEX * (d / p) ** 2
INKS = ("C", "M", "Y", "K")
INK_RGB = {"C": (0, 174, 239), "M": (236, 0, 140), "Y": (255, 242, 0), "K": (35, 31, 32)}
DEFAULT_ANGLES = {"C": 15.0, "M": 45.0, "Y": 0.0, "K": 30.0}  # trama hexagonal (§6.3)
EYE_RAD = 0.000291  # 1 minuto de arco


def diam_from_cov(cov: float, pitch: float) -> float:
    return pitch * math.sqrt(max(cov, 0.0) / K_HEX)


def cov_from_diam(d: float, pitch: float) -> float:
    return K_HEX * (d / pitch) ** 2


def max_coverage(pitch: float, margin: float) -> float:
    """Cobertura máxima con puente (stencil) o separación (sello) mínimos `margin`."""
    return cov_from_diam(max(pitch - margin, 0.0), pitch)


def max_pitch_for_distance(distance_mm: float) -> float:
    """Paso máximo para que la trama se funda en tono continuo (§6.1)."""
    return distance_mm * EYE_RAD


def suggest_pitch(distance_mm: float, lo: float = 2.0, hi: float = 3.0) -> float:
    """Paso sugerido: el máximo que el ojo no resuelve, acotado al rango cómodo de la A1."""
    return round(min(max(max_pitch_for_distance(distance_mm), lo), hi), 2)


def hex_angle_warnings(angles: dict[str, float], tol: float = 5.0) -> list[str]:
    """Avisa si dos ángulos son casi equivalentes en trama hexagonal (se repite cada 60°)."""
    out = []
    keys = list(angles)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            dif = abs(angles[a] - angles[b]) % 60
            if min(dif, 60 - dif) < tol:
                out.append(f"Los ángulos de {a} y {b} son casi equivalentes en trama hexagonal "
                           f"(se repite cada 60°): sus puntos coinciden.")
    return out


def global_hex_points(x0, y0, x1, y1, pitch, angle_deg, offset=(0.0, 0.0)) -> np.ndarray:
    """Centros de una rejilla hexagonal rotada, con origen global, dentro de [x0,x1]x[y0,y1]."""
    th = math.radians(angle_deg)
    a1 = np.array([math.cos(th), math.sin(th)]) * pitch
    a2 = np.array([math.cos(th + math.pi / 3), math.sin(th + math.pi / 3)]) * pitch
    basis = np.column_stack([a1, a2])
    inv = np.linalg.inv(basis)
    off = np.asarray(offset, dtype=float)
    corners = np.array([[x0, y0], [x1, y0], [x0, y1], [x1, y1]], dtype=float) - off
    ij = corners @ inv.T
    i0, i1 = int(math.floor(ij[:, 0].min())) - 1, int(math.ceil(ij[:, 0].max())) + 1
    j0, j1 = int(math.floor(ij[:, 1].min())) - 1, int(math.ceil(ij[:, 1].max())) + 1
    ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1))
    pts = ii.ravel()[:, None] * a1 + jj.ravel()[:, None] * a2 + off
    m = (pts[:, 0] >= x0) & (pts[:, 0] <= x1) & (pts[:, 1] >= y0) & (pts[:, 1] <= y1)
    return pts[m]


@dataclass
class Separation:
    """Mapas de fracción de tinta (0..1) para todo el diseño."""
    width_mm: float
    height_mm: float
    ppm: float  # píxeles por mm
    channels: dict[str, np.ndarray] = field(default_factory=dict)

    def sample(self, ink: str, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        arr = self.channels.get(ink)
        if arr is None:
            return np.zeros(len(x))
        rows = (self.height_mm - np.asarray(y)) * self.ppm - 0.5
        cols = np.asarray(x) * self.ppm - 0.5
        return ndimage.map_coordinates(arr, [rows, cols], order=1, mode="nearest")


def separate_image(path_or_image, width_mm: float, height_mm: float, pitch: float,
                   inks=INKS, gcr: float = 0.6, max_px: int = 6000) -> Separation:
    """Separa una foto en tintas para un diseño de width_mm x height_mm (recorte centrado).

    Con GCR (reemplazo de gris) el negro toma `gcr` veces el mínimo de C, M, Y. Si K es la
    única tinta, la imagen se convierte a escala de grises (Fase 1b del plan).
    """
    from PIL import Image
    img = path_or_image if hasattr(path_or_image, "convert") else Image.open(path_or_image)
    img = img.convert("RGB")
    w, h = img.size
    target = width_mm / height_mm
    if w / h > target:  # demasiado ancha: recorta a los lados
        nw = int(round(h * target))
        img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(round(w / target))
        img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    ppm = min(max(4.0 / pitch, 1.0), max_px / max(width_mm, height_mm))
    nx, ny = max(int(width_mm * ppm), 2), max(int(height_mm * ppm), 2)
    arr = np.asarray(img.resize((nx, ny), Image.LANCZOS), dtype=np.float32) / 255.0
    inks = tuple(inks)
    if inks == ("K",):
        lum = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
        ch = {"K": 1.0 - lum}
    else:
        c0, m0, y0 = 1 - arr[..., 0], 1 - arr[..., 1], 1 - arr[..., 2]
        g = gcr if "K" in inks else 0.0
        k = g * np.minimum(np.minimum(c0, m0), y0)
        ch = {"C": c0 - k, "M": m0 - k, "Y": y0 - k, "K": k}
    sigma = 0.35 * pitch * ppm  # promedio por celda de la trama
    out = {}
    for ink in inks:
        a = np.clip(ch[ink], 0.0, 1.0)
        out[ink] = np.clip(ndimage.gaussian_filter(a, sigma), 0.0, 1.0).astype(np.float32)
    return Separation(width_mm, height_mm, ppm, out)


def separation_from_rects(width_mm, height_mm, rects, ppm=10.0) -> Separation:
    """Separación a partir de rectángulos: [(x0, y0, x1, y1, {tinta: fracción})]."""
    nx, ny = int(width_mm * ppm), int(height_mm * ppm)
    ch = {ink: np.zeros((ny, nx), dtype=np.float32) for ink in INKS}
    for x0, y0, x1, y1, inks in rects:
        r0, r1 = int((height_mm - y1) * ppm), int((height_mm - y0) * ppm)
        c0, c1 = int(x0 * ppm), int(x1 * ppm)
        for ink, f in inks.items():
            ch[ink][r0:r1, c0:c1] = f
    return Separation(width_mm, height_mm, ppm, ch)


def apply_calibration(desired: np.ndarray, curve) -> np.ndarray:
    """Invierte la curva medida [[cobertura_stencil, cobertura_real], ...] (§11.2)."""
    if not curve or len(curve) < 2:
        return desired
    pts = np.asarray(sorted(curve), dtype=float)
    stencil, real = pts[:, 0], np.maximum.accumulate(pts[:, 1])
    return np.interp(desired, real, stencil)
