"""Línea de comandos: `python -m hsm <info|stencil|sellos|probeta|gui>`."""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import tools
from .project import Project
from .session import Session
from .stencil import tile_counts


def _add_design_args(ap):
    ap.add_argument("--project", help="archivo de proyecto JSON (los demás argumentos lo pisan)")
    ap.add_argument("--image", help="foto de entrada")
    ap.add_argument("--width", type=float, help="ancho final en mm")
    ap.add_argument("--height", type=float, help="alto final en mm")
    ap.add_argument("--distance", type=float, help="distancia de observación en mm")
    ap.add_argument("--pitch", type=float, help="paso de trama en mm (por defecto, el sugerido)")
    ap.add_argument("--inks", help="tintas a usar, por ejemplo CMYK, KY o K")
    ap.add_argument("--angles", type=float, nargs=4, metavar=("C", "M", "Y", "K"))
    ap.add_argument("--mode", choices=["A", "B"], help="modo de trama (§6.4)")
    ap.add_argument("--w-min", type=float, help="puente mínimo (mm)")
    ap.add_argument("--d-min", type=float, help="diámetro mínimo de agujero (mm)")
    ap.add_argument("--hole-comp", type=float, help="compensación de agujeros (mm)")
    ap.add_argument("--thickness", type=float, help="espesor de la plancha (mm)")
    ap.add_argument("--active", type=float, help="lado de la zona activa de cada baldosa (mm)")
    ap.add_argument("--frame", type=float, help="ancho del marco (mm)")
    ap.add_argument("--frame-h", type=float, help="alto del marco sobre la plancha (mm)")
    ap.add_argument("--scale-x", type=float)
    ap.add_argument("--scale-y", type=float)
    ap.add_argument("--gcr", type=float)
    ap.add_argument("--material", help="PP, PLA, PETG (solo densidad y nombre)")


def project_from_args(a) -> Project:
    proj = Project.load(a.project) if getattr(a, "project", None) else Project()
    d = proj.data
    if a.image:
        d["imagen"] = os.path.abspath(a.image)
    if a.width:
        d["ancho_mm"] = a.width
    if a.height:
        d["alto_mm"] = a.height
    if a.distance:
        d["distancia_observacion_mm"] = a.distance
    if a.inks:
        d["tintas"] = [c for c in a.inks.upper() if c in "CMYK"]
    if a.angles:
        d["trama"]["angulos"] = dict(zip("CMYK", a.angles))
    if a.mode:
        d["trama"]["modo"] = a.mode
    if a.w_min:
        d["trama"]["puente_min_mm"] = a.w_min
    if a.d_min:
        d["trama"]["diametro_min_mm"] = a.d_min
    if a.hole_comp is not None:
        d["material"]["compensacion_agujero_mm"] = a.hole_comp
    if a.material:
        d["material"]["nombre"] = a.material
    if a.thickness:
        d["plancha"]["espesor_mm"] = a.thickness
    if a.active:
        d["plancha"]["baldosa_activa_mm"] = [a.active, a.active]
    if a.frame:
        d["plancha"]["marco_mm"] = a.frame
    if a.frame_h:
        d["plancha"]["marco_alto_mm"] = a.frame_h
    if a.scale_x or a.scale_y:
        sx, sy = d["material"]["factor_escala"]
        d["material"]["factor_escala"] = [a.scale_x or sx, a.scale_y or sy]
    if a.gcr is not None:
        d["gcr"] = a.gcr
    if a.pitch:
        d["trama"]["paso_mm"] = a.pitch
    elif not (getattr(a, "project", None)) and a.distance:
        d["trama"]["paso_mm"] = Session(proj).suggested_pitch()
    return proj


def _parse_tiles(spec):
    if not spec:
        return None
    return [tuple(int(v) for v in t.split(",")) for t in spec]


def cmd_info(a):
    proj = project_from_args(a)
    print(Session(proj).report_text())
    return 0


def cmd_stencil(a):
    proj = project_from_args(a)
    proj.data["salida"] = "stencil"
    ses = Session(proj)
    print(ses.report_text(), "\n")
    nx, ny = tile_counts(proj.width, proj.height, proj.stencil_params().active)
    tiles = _parse_tiles(a.tiles)
    if tiles:
        bad = [t for t in tiles if not (0 <= t[0] < nx and 0 <= t[1] < ny)]
        if bad:
            sys.exit(f"error: baldosas fuera de rango {bad}; la grilla es {nx} x {ny}")

    def progress(done, total, name):
        print(f"  [{done}/{total}] {name}", flush=True)

    print(ses.export(a.out, tiles, progress))
    ses.overview_image().save(os.path.join(a.out, "vista_general.png"))
    return 0


def cmd_gui(a):
    from .gui import run
    return run(a.project)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="hsm", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("info", help="informe de diseño (baldosas, tiempo, material, avisos)")
    _add_design_args(p)
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("stencil", help="genera los STL de stencils por baldosa y tinta")
    _add_design_args(p)
    p.add_argument("--out", default="salida")
    p.add_argument("--tiles", nargs="*", metavar="X,Y",
                   help="solo estas baldosas (por ejemplo 0,0 1,0); por defecto, todas")
    p.set_defaults(func=cmd_stencil)

    for name, hlp in (("sellos", "sellos de TPU + marco de registro (Anexo A2)"),
                      ("probeta", "plancha de prueba de stencil (Anexo A)")):
        p = sub.add_parser(name, help=hlp, add_help=False)
        p.add_argument("rest", nargs=argparse.REMAINDER)
        p.set_defaults(func=lambda a, n=name: tools.main([n] + a.rest))

    p = sub.add_parser("gui", help="abre la interfaz gráfica (GTK4)")
    p.add_argument("--project", help="proyecto JSON a abrir")
    p.set_defaults(func=cmd_gui)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
