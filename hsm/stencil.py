"""Stencils por baldosa: agujeros según la trama global, marco en relieve y muescas (plan §6.5-6.7, §9)."""
from __future__ import annotations

import math
import os

import manifold3d as m3d
import numpy as np
import trimesh
from shapely.geometry import Polygon, box

from .project import Project, StencilParams
from .screen import (INKS, Separation, apply_calibration, diam_from_cov, global_hex_points,
                     hex_angle_warnings, max_coverage, max_pitch_for_distance)

BED_MM = 256.0  # cama de la Bambu Lab A1
DENSITY = {"PP": 0.9, "PLA": 1.24, "PETG": 1.27}


def tile_counts(width: float, height: float, active: float) -> tuple[int, int]:
    return max(1, math.ceil(width / active - 1e-9)), max(1, math.ceil(height / active - 1e-9))


def ink_offset(ink: str, pitch: float, mode: str) -> tuple[float, float]:
    """Modo A: todas las rejillas comparten origen. Modo B (experimental): rejillas desplazadas."""
    if str(mode).upper() != "B":
        return (0.0, 0.0)
    k = INKS.index(ink)
    ang = math.radians(30 + 60 * k)
    return (math.cos(ang) * pitch * 0.25 * k, math.sin(ang) * pitch * 0.25 * k)


def ink_dots(sep: Separation, ink: str, window, P: StencilParams) -> np.ndarray:
    """Agujeros (x, y, d) en mm globales cuyo círculo toca `window` = (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = window
    pitch = P.pitch
    pts = global_hex_points(x0 - pitch, y0 - pitch, x1 + pitch, y1 + pitch, pitch,
                            P.angles[ink], ink_offset(ink, pitch, P.mode))
    if len(pts) == 0:
        return np.zeros((0, 3))
    cmax = max_coverage(pitch, P.w_min)
    value = sep.sample(ink, pts[:, 0], pts[:, 1])
    cov = np.clip(apply_calibration(value * cmax, P.calib), 0.0, cmax)
    d = pitch * np.sqrt(cov / 0.9068996821171089)
    keep = d >= 0.6 * P.d_min
    d = np.minimum(np.maximum(d, P.d_min) + P.hole_comp, pitch - P.w_min)
    r = d / 2
    keep &= (pts[:, 0] + r > x0) & (pts[:, 0] - r < x1) & (pts[:, 1] + r > y0) & (pts[:, 1] - r < y1)
    return np.column_stack([pts[keep], d[keep]])


def _circle(x, y, r, n):
    ang = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.column_stack([x + r * np.cos(ang), y + r * np.sin(ang)])


def _outer_ring(S: float, f: float, active: float, nd: float):
    """Contorno de la plancha con 8 muescas en V sobre las líneas de la grilla (§6.7, §9.6)."""
    nw = nd  # semiancho de la muesca (V de 90°)
    c1, c2 = f, f + active
    pts = [(0, 0)]
    for c in (c1, c2):
        pts += [(c - nw, 0), (c, nd), (c + nw, 0)]
    pts.append((S, 0))
    for c in (c1, c2):
        pts += [(S, c - nw), (S - nd, c), (S, c + nw)]
    pts.append((S, S))
    for c in (c2, c1):
        pts += [(c + nw, S), (c, S - nd), (c - nw, S)]
    pts.append((0, S))
    for c in (c2, c1):
        pts += [(0, c + nw), (nd, c), (0, c - nw)]
    return pts



def _to_trimesh(man) -> trimesh.Trimesh:
    mm = man.to_mesh()
    return trimesh.Trimesh(mm.vert_properties[:, :3].copy(), mm.tri_verts.copy(), process=False)


def extrude_banded(contours, height: float, size: float, band: float = 25.0):
    """Extruye un polígono con muchos agujeros (contornos, regla par-impar) en bandas.

    La triangulación crece mucho más que linealmente con la cantidad de agujeros; cortar en
    bandas de `band` mm y unir con manifold3d baja el tiempo de ~13 s a ~1,6 s por plancha.
    """
    cs = m3d.CrossSection([np.asarray(c, dtype=float) for c in contours], m3d.FillRule.EvenOdd)
    nb = max(1, math.ceil(size / band))
    h = size / nb
    parts = []
    for k in range(nb):
        piece = cs ^ m3d.CrossSection.square((size, h)).translate((0, k * h))
        if not piece.is_empty():
            parts.append(m3d.Manifold.extrude(piece, height))
    return m3d.Manifold.batch_boolean(parts, m3d.OpType.Add)


def build_tile(sep: Separation, ink: str, i: int, j: int, P: StencilParams):
    """Devuelve (malla, estadísticas) del stencil de la tinta `ink` en la baldosa (i, j)."""
    A, f = P.active, P.frame_w
    S = A + 2 * f
    wx0, wy0 = i * A, j * A
    wx1, wy1 = min(wx0 + A, sep.width_mm), min(wy0 + A, sep.height_mm)
    dots = ink_dots(sep, ink, (wx0, wy0, wx1, wy1), P)
    nd = min(0.6 * f, 2.5)
    outer = _outer_ring(S, f, A, nd)
    ww, wh = wx1 - wx0, wy1 - wy0
    win_local = box(f, f, f + ww, f + wh)

    holes, area_holes = [], 0.0
    for x, y, d in dots:
        lx, ly, r = x - wx0 + f, y - wy0 + f, d / 2
        n = 16 if d < 1.2 else 24
        if lx - r >= f and lx + r <= f + ww and ly - r >= f and ly + r <= f + wh:
            holes.append(_circle(lx, ly, r, n))
            area_holes += 0.5 * n * r * r * math.sin(2 * math.pi / n)
        else:
            clipped = Polygon(_circle(lx, ly, r, n)).intersection(win_local)
            if clipped.geom_type == "Polygon" and clipped.area > 0.15:
                holes.append(np.asarray(clipped.exterior.coords)[:-1])
                area_holes += clipped.area
    plate = extrude_banded([outer] + holes, P.thickness, S)
    active_sq = m3d.CrossSection([np.array([(f, f), (f + A, f), (f + A, f + A), (f, f + A)], float)],
                                 m3d.FillRule.EvenOdd)
    ring_cs = m3d.CrossSection([np.asarray(outer, float)], m3d.FillRule.EvenOdd) - active_sq
    # marco del lado exterior: la cara de contacto queda plana (§6.7)
    ring = m3d.Manifold.extrude(ring_cs, P.frame_h).translate((0, 0, P.thickness))
    mesh = _to_trimesh(plate + ring)
    mesh.apply_scale([P.scale[0], P.scale[1], 1.0])

    cmax = max_coverage(P.pitch, P.w_min)
    stats = {
        "tinta": ink, "baldosa": [i, j], "agujeros": len(holes),
        "diametro_min_mm": round(float(dots[:, 2].min()), 3) if len(dots) else None,
        "diametro_max_mm": round(float(dots[:, 2].max()), 3) if len(dots) else None,
        "cobertura_maxima_stencil": round(cmax, 4),
        "area_plancha_mm2": round(S * S - area_holes, 1),
        "tamano_plancha_mm": round(S, 2),
        "estanca": bool(mesh.is_watertight),
    }
    return mesh, stats


def tile_name(i: int, j: int, ink: str) -> str:
    return f"stencil_x{i:02d}_y{j:02d}_{ink}.stl"


def export_tiles(sep: Separation, proj: Project, out_dir: str, tiles=None, progress=None) -> list:
    """Genera los STL de las baldosas indicadas (o todas) para todas las tintas del proyecto."""
    P = proj.stencil_params()
    os.makedirs(out_dir, exist_ok=True)
    nx, ny = tile_counts(proj.width, proj.height, P.active)
    todo = [(i, j) for j in range(ny) for i in range(nx)] if tiles is None else list(tiles)
    total = len(todo) * len(P.inks)
    done, results = 0, []
    for (i, j) in todo:
        for ink in P.inks:
            mesh, st = build_tile(sep, ink, i, j, P)
            mesh.export(os.path.join(out_dir, tile_name(i, j, ink)))
            st["archivo"] = tile_name(i, j, ink)
            results.append(st)
            done += 1
            if progress:
                progress(done, total, st["archivo"])
    return results


def design_report(proj: Project) -> dict:
    """Informe de diseño: piezas, tiempo y material estimados, avisos (plan §6.5, §10)."""
    P = proj.stencil_params()
    nx, ny = tile_counts(proj.width, proj.height, P.active)
    tiles, n_ink = nx * ny, len(P.inks)
    S = P.active + 2 * P.frame_w
    cmax = max_coverage(P.pitch, P.w_min)
    holes_tile = P.active ** 2 / (0.8660254 * P.pitch ** 2)
    stencils = tiles * n_ink
    h_lo, h_hi = 1.5 * holes_tile / 11500, 3.0 * holes_tile / 11500
    dens = DENSITY.get(proj.data["material"]["nombre"], 0.9)
    vol_mm3 = stencils * S * S * P.thickness * (1 - 0.25) * 1.15
    max_p = max_pitch_for_distance(float(proj.data["distancia_observacion_mm"]))
    warn = hex_angle_warnings({k: P.angles[k] for k in P.inks})
    if P.pitch > max_p:
        warn.append(f"El paso ({P.pitch} mm) supera ≈{max_p:.2f} mm: a "
                    f"{proj.data['distancia_observacion_mm'] / 1000:g} m la trama se vería como puntos.")
    if S > BED_MM:
        warn.append(f"La plancha ({S:g} mm) no entra en la cama de la A1 ({BED_MM:g} mm).")
    if P.pitch - P.w_min < P.d_min:
        warn.append("Paso demasiado chico para el puente y el diámetro mínimos pedidos.")
    if P.mode == "A" and len(P.inks) > 1:
        warn.append("Modo A: con aerosol opaco la mezcla depende del orden de pintado (§6.4).")
    if P.mode == "B":
        warn.append("Modo B (experimental): rejillas desplazadas por tinta; falta validarlo (Fase 2).")
    return {
        "baldosas": [nx, ny], "cantidad_baldosas": tiles, "tintas": list(P.inks),
        "stencils_totales": stencils, "paso_mm": P.pitch, "paso_maximo_mm": round(max_p, 2),
        "cobertura_maxima_por_stencil": round(cmax, 4), "plancha_mm": round(S, 2),
        "agujeros_por_baldosa_aprox": int(holes_tile),
        "horas_impresion_estimadas": [round(stencils * h_lo), round(stencils * h_hi)],
        "kg_material_estimados": round(vol_mm3 / 1000 * dens / 1000, 2),
        "avisos": warn,
    }
