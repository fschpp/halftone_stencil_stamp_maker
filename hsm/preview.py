"""Vistas previas simuladas: resultado global, detalle de trama y mapa de baldosas."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from .project import Project, StencilParams
from .screen import INK_RGB, Separation, max_coverage
from .stencil import ink_dots, tile_counts

PAINT_ORDER = ("Y", "M", "C", "K")  # orden de pintado probable (§6.4)


def _compose(layers, model: str, n_shape):
    """layers: [(tinta, máscara 0..1)] en orden de pintado sobre papel blanco."""
    out = np.ones(n_shape + (3,), dtype=np.float32)
    for ink, mask in layers:
        rgb = np.array(INK_RGB[ink], dtype=np.float32) / 255.0
        m = mask[..., None]
        if model == "opaque":  # aerosol opaco: la última tinta tapa a las anteriores
            out = out * (1 - m) + rgb * m
        else:  # tintas translúcidas: se multiplican
            out = out * (1 - m * (1 - rgb))
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype("uint8"))


def overview(sep: Separation, P: StencilParams, model: str = "translucent", limited: bool = True,
             max_px: int = 1100) -> Image.Image:
    """Resultado global sin dibujar los puntos. `limited` aplica el techo de cobertura (§6.2)."""
    cmax = max_coverage(P.pitch, P.w_min) if limited else 1.0
    scale = min(1.0, max_px / max(sep.channels[next(iter(sep.channels))].shape))
    layers = []
    for ink in PAINT_ORDER:
        if ink not in P.inks or ink not in sep.channels:
            continue
        arr = sep.channels[ink]
        im = Image.fromarray(arr, mode="F")
        if scale < 1.0:
            im = im.resize((max(int(arr.shape[1] * scale), 1), max(int(arr.shape[0] * scale), 1)),
                           Image.BOX)
        layers.append((ink, np.clip(np.asarray(im, dtype=np.float32) * cmax, 0, 1)))
    shape = layers[0][1].shape
    return _compose(layers, model, shape)


def detail(sep: Separation, P: StencilParams, x0: float, y0: float, w: float, h: float,
           pxmm: float = 12.0, model: str = "translucent", gain: float = 0.0,
           ss: int = 3) -> Image.Image:
    """Puntos reales (los mismos agujeros que se exportan) en la ventana (x0, y0, w, h) mm."""
    pxmm = min(pxmm, 2400.0 / max(w, h, 1.0))
    nx, ny = max(int(w * pxmm), 1), max(int(h * pxmm), 1)
    layers = []
    for ink in PAINT_ORDER:
        if ink not in P.inks:
            continue
        dots = ink_dots(sep, ink, (x0, y0, x0 + w, y0 + h), P)
        big = Image.new("L", (nx * ss, ny * ss), 0)
        dr = ImageDraw.Draw(big)
        for x, y, d in dots:
            r = (d + gain) / 2 * pxmm * ss
            cx, cy = (x - x0) * pxmm * ss, (y0 + h - y) * pxmm * ss
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
        mask = np.asarray(big.resize((nx, ny), Image.BOX), dtype=np.float32) / 255.0
        layers.append((ink, mask))
    return _compose(layers, model, (ny, nx))


def tile_map(proj: Project, selected=None, px: int = 900) -> Image.Image:
    """Mapa numerado de baldosas con las líneas de la grilla de registro (§8, §9.6)."""
    P = proj.stencil_params()
    W, H, A = proj.width, proj.height, P.active
    nx, ny = tile_counts(W, H, A)
    s = px / max(W, H)
    pad = 24
    img = Image.new("RGB", (int(W * s) + 2 * pad, int(H * s) + 2 * pad), (250, 250, 250))
    dr = ImageDraw.Draw(img)
    dr.rectangle([pad, pad, pad + W * s, pad + H * s], fill=(255, 255, 255), outline=(60, 60, 60))
    sel = set(map(tuple, selected)) if selected else set()
    for j in range(ny):
        for i in range(nx):
            x0, x1 = pad + i * A * s, pad + min((i + 1) * A, W) * s
            y1, y0 = pad + H * s - j * A * s, pad + H * s - min((j + 1) * A, H) * s
            if (i, j) in sel:
                dr.rectangle([x0, y0, x1, y1], fill=(255, 235, 170))
            dr.rectangle([x0, y0, x1, y1], outline=(0, 120, 200))
            if (x1 - x0) > 28 and (y1 - y0) > 14:
                dr.text((x0 + 4, y0 + 3), f"{i},{j}", fill=(0, 70, 130))
    dr.text((pad, 6), f"{W:g} x {H:g} mm  |  baldosa activa {A:g} mm  |  {nx} x {ny} = {nx * ny} baldosas",
            fill=(40, 40, 40))
    return img
