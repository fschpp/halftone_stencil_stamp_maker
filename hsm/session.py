"""Lógica de la aplicación sin dependencias de GTK (la GUI es una capa fina encima)."""
from __future__ import annotations

import contextlib
import io
import os
import tempfile

from . import preview, tools
from .project import Project
from .screen import Separation, separate_image, suggest_pitch
from .stencil import design_report, export_tiles, tile_counts

MODES = ("stencil", "sello", "probeta")


class Session:
    def __init__(self, project: Project | None = None):
        self.project = project or Project()
        self._sep: Separation | None = None
        self._sep_key = None

    # --- separación (con caché) --------------------------------------------
    def separation(self) -> Separation:
        d, P = self.project.data, self.project.stencil_params()
        if not d["imagen"] or not os.path.exists(d["imagen"]):
            raise ValueError("Elegí primero una foto.")
        key = (d["imagen"], os.path.getmtime(d["imagen"]), self.project.width, self.project.height,
               P.pitch, P.inks, round(P.gcr, 3))
        if key != self._sep_key:
            self._sep = separate_image(d["imagen"], self.project.width, self.project.height,
                                       P.pitch, P.inks, P.gcr)
            self._sep_key = key
        return self._sep

    def suggested_pitch(self) -> float:
        return suggest_pitch(float(self.project.data["distancia_observacion_mm"]))

    # --- vistas ----------------------------------------------------------
    def overview_image(self, model="translucent", limited=True):
        return preview.overview(self.separation(), self.project.stencil_params(), model, limited)

    def detail_image(self, x0, y0, w, h, pxmm=12.0, model="translucent", gain=0.0):
        W, H = self.project.width, self.project.height
        w, h = min(w, W), min(h, H)
        x0, y0 = min(max(x0, 0.0), W - w), min(max(y0, 0.0), H - h)
        return preview.detail(self.separation(), self.project.stencil_params(), x0, y0, w, h,
                              pxmm, model, gain)

    def tile_map_image(self, selected=None):
        return preview.tile_map(self.project, selected)

    def report_text(self) -> str:
        r = design_report(self.project)
        lo, hi = r["horas_impresion_estimadas"]
        lines = [
            f"Baldosas: {r['baldosas'][0]} x {r['baldosas'][1]} = {r['cantidad_baldosas']}",
            f"Tintas: {', '.join(r['tintas'])}  ->  {r['stencils_totales']} stencils",
            f"Paso de trama: {r['paso_mm']} mm (máximo para la distancia: {r['paso_maximo_mm']} mm)",
            f"Cobertura máxima por stencil: {r['cobertura_maxima_por_stencil']:.0%}",
            f"Plancha: {r['plancha_mm']} x {r['plancha_mm']} mm, ~{r['agujeros_por_baldosa_aprox']} agujeros",
            f"Impresión estimada: {lo}-{hi} h (estimación gruesa [I], se mide en la Fase 1b)",
            f"Material estimado: {r['kg_material_estimados']} kg",
        ]
        if r["avisos"]:
            lines.append("")
            lines += [f"AVISO: {a}" for a in r["avisos"]]
        return "\n".join(lines)

    # --- exportación -----------------------------------------------------
    def export(self, out_dir: str, tiles=None, progress=None) -> str:
        """Genera los archivos del modo elegido y devuelve un texto de registro."""
        mode = self.project.data["salida"]
        os.makedirs(out_dir, exist_ok=True)
        if mode == "stencil":
            results = export_tiles(self.separation(), self.project, out_dir, tiles, progress)
            import json
            with open(os.path.join(out_dir, "informe.json"), "w", encoding="utf-8") as f:
                json.dump({"proyecto": self.project.data, "informe": design_report(self.project),
                           "piezas": results}, f, indent=2, ensure_ascii=False, default=float)
            self.project.save(os.path.join(out_dir, "proyecto.json"))
            preview.tile_map(self.project, tiles).save(os.path.join(out_dir, "mapa_baldosas.png"))
            bad = [r["archivo"] for r in results if not r["estanca"]]
            log = f"{len(results)} STL generados en {out_dir}."
            return log + (f"\nATENCIÓN: mallas no estancas: {', '.join(bad)}" if bad else
                          "\nTodas las mallas son estancas.")
        return self._run_tools(mode, out_dir)

    def _run_tools(self, mode: str, out_dir: str) -> str:
        d, m = self.project.data, self.project.data["material"]
        sx, sy = m["factor_escala"]
        if mode == "probeta":
            P = self.project.stencil_params()
            argv = ["probeta", "--out", out_dir, "--material", m["nombre"],
                    "--thickness", P.thickness, "--frame-h", P.frame_h, "--w-min", P.w_min,
                    "--d-min", P.d_min, "--hole-comp", P.hole_comp, "--scale-x", sx, "--scale-y", sy]
        else:
            s, r = d["sello"], d["sello"]["marco_registro"]
            a = d["trama"]["angulos"]
            argv = ["sellos", "--out", out_dir, "--source", s["fuente"], "--size", s["lado_mm"],
                    "--pitch", s["paso_mm"], "--angles", a["C"], a["M"], a["Y"], a["K"],
                    "--gcr", d["gcr"], "--base", s["base_mm"], "--pin-h", s["pin_alto_mm"],
                    "--pin-min", s["pin_min_mm"], "--gap-min", s["separacion_min_mm"],
                    "--chamfer", s["chaflan_mm"], "--jig-clearance", r["holgura_mm"],
                    "--jig-thickness", r["espesor_mm"], "--jig-margin", r["margen_mm"],
                    "--scale-x", sx, "--scale-y", sy]
            if s["fuente"] == "photo":
                if not d["imagen"]:
                    raise ValueError("El sello en modo foto necesita una imagen.")
                argv += ["--image", d["imagen"]]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                code = tools.main([str(x) for x in argv])
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
                if isinstance(exc.code, str):
                    buf.write(exc.code + "\n")
        return buf.getvalue() + ("" if not code else "\n(terminó con avisos o errores)")

    def stamp_preview_path(self, out_dir: str) -> str:
        return os.path.join(out_dir, "preview.png")

    def temp_dir(self) -> str:
        return tempfile.mkdtemp(prefix="hsm_")
