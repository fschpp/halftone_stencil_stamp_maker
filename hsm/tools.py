#!/usr/bin/env python3
"""
halftone_tools.py -- Fase 0 y Fase 0b del plan de stencils / sellos CMYK.

Dos subcomandos (ver Anexo A y Anexo A2 del plan.md):

  probeta   STL de una plancha de prueba con celdas de agujeros (paso x cobertura),
            una ventana abierta de referencia y un marco en relieve del lado exterior.

  sellos    4 sellos (C, M, Y, K) con pines en relieve para TPU, un marco de registro
            con ventana, un layout.json y una vista previa simulada (preview.png).
            Fuente: carta de parches (chart) o una foto (photo).

Ejemplos:
  python3 halftone_tools.py probeta --out salida/ --material PP
  python3 halftone_tools.py sellos --source chart --out salida/
  python3 halftone_tools.py sellos --source photo --image foto.jpg --size 40 --out salida/

Dependencias: numpy, shapely>=2, trimesh, mapbox-earcut, manifold3d, pillow.
  pip install numpy shapely trimesh mapbox-earcut manifold3d pillow

Todas las medidas estan en milimetros. Los valores por defecto son estimaciones
(marcadas [I] en el plan) y se ajustan con las pruebas.

Angulos de trama: la convencion clasica (C 15, M 75, Y 0, K 45) es para tramas en cuadricula
(se repite cada 90 grados). Con trama hexagonal el patron se repite cada 60 grados, y 15 y 75
coinciden. Por eso el valor por defecto es C 15, M 45, Y 0, K 30 (15 grados entre todos los pares).

Orientacion de los sellos: los pines se generan en la orientacion de "estampado"
(u hacia la derecha, v hacia arriba, vistos desde arriba sobre el papel) y el STL
se exporta girado 180 grados alrededor del eje Y, listo para imprimir con los pines
hacia arriba. Para usarlo, se da vuelta el sello alrededor de su lado vertical (eje Y).
"""
import argparse
import json
import math
import os
import sys

import numpy as np
import shapely
import trimesh
from shapely import affinity
from shapely.geometry import Polygon, box

K_HEX = math.pi / (2 * math.sqrt(3))  # 0.9069: cobertura = K_HEX * (d / p) ** 2
INKS = ("C", "M", "Y", "K")
INK_RGB = {"C": (0, 174, 239), "M": (236, 0, 140), "Y": (255, 242, 0), "K": (35, 31, 32)}

# Carta de parches 3 x 3: (nombre, {tinta: fraccion de la cobertura maxima})
CHART = [
    ("cian", {"C": 1.0}),
    ("magenta", {"M": 1.0}),
    ("amarillo", {"Y": 1.0}),
    ("rojo (M+Y)", {"M": 1.0, "Y": 1.0}),
    ("verde (C+Y)", {"C": 1.0, "Y": 1.0}),
    ("azul (C+M)", {"C": 1.0, "M": 1.0}),
    ("C+M+Y", {"C": 1.0, "M": 1.0, "Y": 1.0}),
    ("negro 50 %", {"K": 0.5}),
    ("negro 100 %", {"K": 1.0}),
]


# ----------------------------------------------------------------------------
# Utilidades de trama y geometria
# ----------------------------------------------------------------------------
def diam_from_cov(cov, pitch):
    """Diametro de punto para una cobertura dada en una trama hexagonal."""
    return pitch * math.sqrt(max(cov, 0.0) / K_HEX)


def cov_from_diam(d, pitch):
    return K_HEX * (d / pitch) ** 2


def hex_points(width, height, pitch, angle_deg, cx, cy):
    """Puntos de una rejilla hexagonal rotada, centrada en (cx, cy), que cubre un rectangulo."""
    r = math.hypot(width, height) / 2 + pitch
    n = int(r / (pitch * 0.8660254)) + 2
    ni = 2 * n + 2  # la rejilla esta sesgada: hace falta mas rango en i
    th = math.radians(angle_deg)
    co, si = math.cos(th), math.sin(th)
    i = np.arange(-ni, ni + 1)
    j = np.arange(-n, n + 1)
    ii, jj = np.meshgrid(i, j)
    lx = (ii + 0.5 * jj) * pitch
    ly = jj * pitch * 0.8660254
    x = cx + lx * co - ly * si
    y = cy + lx * si + ly * co
    return np.column_stack([x.ravel(), y.ravel()])


def circle_coords(x, y, r, n=20):
    ang = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return [(x + r * math.cos(a), y + r * math.sin(a)) for a in ang]


def union_meshes(meshes):
    """Union booleana con manifold3d; si falla, concatena (el slicer los tolera)."""
    try:
        return trimesh.boolean.union(meshes, engine="manifold")
    except Exception as exc:  # pragma: no cover
        print(f"  aviso: union booleana no disponible ({exc}); se concatenan las piezas")
        return trimesh.util.concatenate(meshes)


def check_and_save(mesh, path):
    mesh.export(path)
    wt = mesh.is_watertight
    print(f"  {os.path.basename(path)}: estanca={wt}, caras={len(mesh.faces)}, "
          f"dim={np.round(mesh.extents, 2).tolist()} mm")
    return wt


# ----------------------------------------------------------------------------
# Subcomando: probeta (stencil)
# ----------------------------------------------------------------------------
def cmd_probeta(a):
    os.makedirs(a.out, exist_ok=True)
    size, t, fw, fh = a.size, a.thickness, a.frame_w, a.frame_h
    covs = [c / 100.0 for c in a.coverages]
    gap, strip = 2.0, 12.0
    inner = size - 2 * fw
    cw = (inner - (len(a.pitches) - 1) * gap) / len(a.pitches)
    ch = (inner - strip - gap - (len(covs) - 1) * gap) / len(covs)

    holes = []
    # ventana abierta de referencia (cobertura de pintura al 100 %)
    wx0, wy0 = fw + 1.0, size - fw - strip + 1.0
    holes.append(list(box(wx0, wy0, wx0 + 10, wy0 + 10).exterior.coords)[:-1])

    cells = []
    for ci, p in enumerate(a.pitches):
        x0 = fw + ci * (cw + gap)
        for ri, c in enumerate(covs):
            y1 = size - fw - strip - gap - ri * (ch + gap)
            y0 = y1 - ch
            d = diam_from_cov(c, p) + a.hole_comp
            w = p - d
            ok = (w >= a.w_min) and (d >= a.d_min)
            pts = hex_points(cw, ch, p, a.angle, x0 + cw / 2, y0 + ch / 2)
            m = 0.6 + d / 2
            keep = ((pts[:, 0] >= x0 + m) & (pts[:, 0] <= x0 + cw - m) &
                    (pts[:, 1] >= y0 + m) & (pts[:, 1] <= y0 + ch - m))
            for x, y in pts[keep]:
                holes.append(circle_coords(x, y, d / 2))
            cells.append({
                "paso_mm": p, "cobertura_objetivo": c, "diametro_mm": round(d, 3),
                "puente_mm": round(w, 3), "dentro_de_limite": bool(ok),
                "agujeros": int(keep.sum()), "x0": round(x0, 2), "y0": round(y0, 2),
                "ancho": round(cw, 2), "alto": round(ch, 2),
            })

    plate_poly = Polygon(list(box(0, 0, size, size).exterior.coords), holes)
    if not plate_poly.is_valid:
        sys.exit("error: la plancha con agujeros no es un poligono valido (agujeros solapados)")
    plate = trimesh.creation.extrude_polygon(plate_poly, t)

    ring = Polygon(list(box(0, 0, size, size).exterior.coords),
                   [list(box(fw, fw, size - fw, size - fw).exterior.coords)])
    frame = trimesh.creation.extrude_polygon(ring, fh)
    frame.apply_translation([0, 0, t])  # el marco va del lado exterior; la cara de contacto queda plana

    mesh = union_meshes([plate, frame])
    mesh.apply_scale([a.scale_x, a.scale_y, 1.0])

    name = f"probeta_{a.material}_t{t:g}.stl"
    print("Probeta de stencil:")
    wt = check_and_save(mesh, os.path.join(a.out, name))
    fuera = [c for c in cells if not c["dentro_de_limite"]]
    print(f"  celdas: {len(cells)}; fuera de limite (se imprimen igual): {len(fuera)}")
    for c in fuera:
        print(f"    p={c['paso_mm']} cobertura={c['cobertura_objetivo']:.0%} "
              f"d={c['diametro_mm']} puente={c['puente_mm']}")
    layout = {"parametros": {k: v for k, v in vars(a).items() if k != "func"},
              "ventana_referencia": {"x0": wx0, "y0": wy0, "lado": 10}, "celdas": cells}
    with open(os.path.join(a.out, "probeta_layout.json"), "w", encoding="utf-8") as f:
        json.dump(layout, f, indent=2, ensure_ascii=False)
    return 0 if wt else 1


# ----------------------------------------------------------------------------
# Subcomando: sellos (TPU) + marco de registro
# ----------------------------------------------------------------------------
def base_polygon(size, chamfer):
    """Cuadrado con una esquina cortada en (size, 0): evita colocar el sello girado."""
    return Polygon([(0, 0), (size - chamfer, 0), (size, chamfer), (size, size), (0, size)])


def chart_rects(size):
    """Rectangulos de los 9 parches (u0, v0, u1, v1) en la orientacion de estampado."""
    ps, g = 12.0, 1.0
    origin = (size - (3 * ps + 2 * g)) / 2
    rects = []
    for idx in range(9):
        r, c = divmod(idx, 3)
        u0 = origin + c * (ps + g)
        v1 = size - origin - r * (ps + g)
        rects.append((u0, v1 - ps, u0 + ps, v1))
    return rects


def photo_fractions(path, size, ppm=10, gcr=0.6):
    """Fraccion de cada tinta (0..1) en una grilla de ppm px/mm.

    Separacion CMYK con reemplazo parcial de gris (GCR): el negro toma `gcr` veces el minimo de
    C, M, Y y se resta de los tres. Con gcr=0 no hay negro; con gcr=1 el gris sale solo en negro.
    """
    from PIL import Image
    img = Image.open(path).convert("RGB")
    w, h = img.size
    s = min(w, h)
    img = img.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    n = int(size * ppm)
    arr = np.asarray(img.resize((n, n), Image.LANCZOS), dtype=float) / 255.0
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    c0, m0, y0 = 1 - r, 1 - g, 1 - b
    k = gcr * np.minimum(np.minimum(c0, m0), y0)
    return {"C": c0 - k, "M": m0 - k, "Y": y0 - k, "K": k}, ppm


def make_pins(a, ink, angle, cov_max, cov_min, base_poly, fraction_at):
    """Lista de (u, v, d) para una tinta; fraction_at(u, v) devuelve (fraccion, rect|None)."""
    p = a.pitch
    pts = hex_points(a.size, a.size, p, angle, a.size / 2, a.size / 2)
    inside = shapely.contains_xy(base_poly.buffer(-1.0), pts[:, 0], pts[:, 1])
    d_max = p - a.gap_min
    pins = []
    for (u, v), ok in zip(pts, inside):
        if not ok:
            continue
        f, rect = fraction_at(u, v)
        if f is None or f <= 0:
            continue
        c = f * cov_max
        if c < 0.35 * cov_min:
            continue
        d = min(max(diam_from_cov(c, p), a.pin_min), d_max)
        if rect is not None:  # el circulo debe quedar dentro del parche
            r = d / 2
            if not (rect[0] + r <= u <= rect[2] - r and rect[1] + r <= v <= rect[3] - r):
                continue
        pins.append((float(u), float(v), float(d)))
    return pins


def build_stamp(a, pins, base_poly):
    pin_h, base = a.pin_h, a.base
    total_h = pin_h + base
    slab = trimesh.creation.extrude_polygon(base_poly, base)
    slab.apply_translation([0, 0, pin_h])
    parts = [slab]
    if pins:
        tmpl = trimesh.creation.cylinder(radius=1.0, height=1.0, sections=16)
        cyls = []
        for u, v, d in pins:
            m = tmpl.copy()
            m.apply_scale([d / 2, d / 2, pin_h + 0.1])  # 0,1 mm dentro de la base
            m.apply_translation([u, v, (pin_h + 0.1) / 2])
            cyls.append(m)
        parts.append(trimesh.util.concatenate(cyls))
    mesh = union_meshes(parts)
    # orientacion de estampado -> orientacion de impresion (giro de 180 grados sobre Y)
    rot = np.array([[-1, 0, 0, a.size], [0, 1, 0, 0], [0, 0, -1, total_h], [0, 0, 0, 1]], dtype=float)
    mesh.apply_transform(rot)
    mesh.apply_scale([a.scale_x, a.scale_y, 1.0])
    return mesh


def build_jig(a, base_poly):
    big = a.size + 2 * a.jig_margin
    window = base_poly.buffer(a.jig_clearance / 2, join_style=2)
    window = affinity.translate(window, a.jig_margin, a.jig_margin)
    plate = Polygon(list(box(0, 0, big, big).exterior.coords), [list(window.exterior.coords)])
    return trimesh.creation.extrude_polygon(plate, a.jig_thickness)


def render_preview(path, size, pins_by_ink, gain=0.0, ppm=12, ss=3):
    """Simulacion ideal: tintas translucidas que se multiplican sobre papel blanco."""
    from PIL import Image, ImageDraw
    n = int(size * ppm)
    out = np.ones((n, n, 3))
    for ink in ("Y", "M", "C", "K"):
        im = Image.new("L", (n * ss, n * ss), 0)
        dr = ImageDraw.Draw(im)
        for u, v, d in pins_by_ink[ink]:
            r = (d + gain) / 2 * ppm * ss
            x, y = u * ppm * ss, (size - v) * ppm * ss
            dr.ellipse([x - r, y - r, x + r, y + r], fill=255)
        mask = np.asarray(im.resize((n, n), Image.BOX), dtype=float) / 255.0
        rgb = np.array(INK_RGB[ink]) / 255.0
        out *= 1 - mask[..., None] * (1 - rgb)
    Image.fromarray((out * 255).astype("uint8")).save(path)


def cmd_sellos(a):
    os.makedirs(a.out, exist_ok=True)
    p = a.pitch
    cov_max = cov_from_diam(p - a.gap_min, p)
    cov_min = cov_from_diam(a.pin_min, p)
    if a.pin_min > p - a.gap_min:
        sys.exit("error: el paso es demasiado chico para el pin minimo y la separacion pedidos")
    base_poly = base_polygon(a.size, a.chamfer)
    angles = dict(zip(INKS, a.angles))
    # En una trama hexagonal el patron se repite cada 60 grados: dos angulos que difieren en
    # 60 coinciden (por ejemplo 15 y 75 de la convencion clasica, pensada para cuadricula).
    for i, x in enumerate(INKS):
        for y in INKS[i + 1:]:
            dif = abs(angles[x] - angles[y]) % 60
            if min(dif, 60 - dif) < 5:
                print(f"  AVISO: los angulos de {x} e {y} son casi equivalentes en una trama "
                      f"hexagonal (se repite cada 60 grados): sus puntos coinciden")
    print(f"Sellos: paso {p} mm, cobertura util {cov_min:.1%} a {cov_max:.1%}, angulos {angles}")

    if a.source == "chart":
        rects = chart_rects(a.size)
        per_ink = {ink: [] for ink in INKS}
        for (name, inks), rect in zip(CHART, rects):
            for ink, f in inks.items():
                per_ink[ink].append((rect, f))

        def make_lookup(ink):
            def lookup(u, v):
                for rect, f in per_ink[ink]:
                    if rect[0] <= u <= rect[2] and rect[1] <= v <= rect[3]:
                        return f, rect
                return None, None
            return lookup
        lookups = {ink: make_lookup(ink) for ink in INKS}
    else:
        if not a.image:
            sys.exit("error: --source photo requiere --image")
        fr, ppm = photo_fractions(a.image, a.size, gcr=a.gcr)
        n = fr["K"].shape[0]

        def make_lookup(ink):
            arr = fr[ink]

            def lookup(u, v):
                col = min(max(int(u * ppm), 0), n - 1)
                row = min(max(int((a.size - v) * ppm), 0), n - 1)
                return float(arr[row, col]), None
            return lookup
        lookups = {ink: make_lookup(ink) for ink in INKS}

    pins_by_ink, ok_all = {}, True
    for ink in INKS:
        pins = make_pins(a, ink, angles[ink], cov_max, cov_min, base_poly, lookups[ink])
        pins_by_ink[ink] = pins
        mesh = build_stamp(a, pins, base_poly)
        ok_all &= check_and_save(mesh, os.path.join(a.out, f"sello_{ink}.stl"))
        print(f"    pines: {len(pins)}")
    jig = build_jig(a, base_poly)
    ok_all &= check_and_save(jig, os.path.join(a.out, "marco_registro.stl"))

    render_preview(os.path.join(a.out, "preview.png"), a.size, pins_by_ink, gain=a.dot_gain)
    layout = {
        "parametros": {k: v for k, v in vars(a).items() if k != "func"},
        "cobertura_minima": round(cov_min, 4), "cobertura_maxima": round(cov_max, 4),
        "pines_por_tinta": {ink: len(v) for ink, v in pins_by_ink.items()},
        "diametro_pin_mm": {ink: [round(min(d for *_, d in v), 3), round(max(d for *_, d in v), 3)]
                            for ink, v in pins_by_ink.items() if v},
    }
    if a.source == "chart":
        layout["parches"] = [{"nombre": n, "tintas": i, "rect_uv_mm": [round(x, 2) for x in r]}
                             for (n, i), r in zip(CHART, chart_rects(a.size))]
    with open(os.path.join(a.out, "layout.json"), "w", encoding="utf-8") as f:
        json.dump(layout, f, indent=2, ensure_ascii=False)
    print("  preview.png y layout.json escritos")
    print("Recordatorio: dar vuelta cada sello alrededor de su lado vertical (eje Y) antes de usarlo.")
    return 0 if ok_all else 1


# ----------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("probeta", help="plancha de prueba de stencil (Anexo A)")
    pr.add_argument("--out", default="salida")
    pr.add_argument("--material", default="PP", help="solo para el nombre del archivo")
    pr.add_argument("--size", type=float, default=100.0)
    pr.add_argument("--thickness", type=float, default=0.6)
    pr.add_argument("--frame-w", type=float, default=4.0, help="ancho del marco")
    pr.add_argument("--frame-h", type=float, default=1.2, help="alto del marco sobre la plancha")
    pr.add_argument("--pitches", type=float, nargs="+", default=[2.0, 2.5, 3.0])
    pr.add_argument("--coverages", type=float, nargs="+", default=[8, 16, 24, 32, 40, 48],
                    help="coberturas objetivo en %%")
    pr.add_argument("--w-min", type=float, default=0.6, help="puente minimo")
    pr.add_argument("--d-min", type=float, default=0.5, help="diametro minimo de agujero")
    pr.add_argument("--hole-comp", type=float, default=0.0, help="compensacion de agujeros (mm)")
    pr.add_argument("--angle", type=float, default=45.0)
    pr.add_argument("--scale-x", type=float, default=1.0, help="compensacion de contraccion")
    pr.add_argument("--scale-y", type=float, default=1.0)
    pr.set_defaults(func=cmd_probeta)

    st = sub.add_parser("sellos", help="sellos de TPU + marco de registro (Anexo A2)")
    st.add_argument("--out", default="salida")
    st.add_argument("--source", choices=["chart", "photo"], default="chart")
    st.add_argument("--image", help="foto, si --source photo")
    st.add_argument("--size", type=float, default=40.0)
    st.add_argument("--pitch", type=float, default=2.0)
    st.add_argument("--angles", type=float, nargs=4, default=[15, 45, 0, 30],
                    metavar=("C", "M", "Y", "K"))
    st.add_argument("--gcr", type=float, default=0.6,
                    help="reemplazo de gris por negro en modo photo (0 = sin negro, 1 = todo el gris en negro)")
    st.add_argument("--base", type=float, default=1.2)
    st.add_argument("--pin-h", type=float, default=0.7)
    st.add_argument("--pin-min", type=float, default=0.6)
    st.add_argument("--gap-min", type=float, default=0.4)
    st.add_argument("--chamfer", type=float, default=3.0)
    st.add_argument("--jig-clearance", type=float, default=0.3)
    st.add_argument("--jig-thickness", type=float, default=4.0)
    st.add_argument("--jig-margin", type=float, default=15.0)
    st.add_argument("--dot-gain", type=float, default=0.0, help="solo para la vista previa (mm)")
    st.add_argument("--scale-x", type=float, default=1.0, help="compensacion de contraccion")
    st.add_argument("--scale-y", type=float, default=1.0)
    st.set_defaults(func=cmd_sellos)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
