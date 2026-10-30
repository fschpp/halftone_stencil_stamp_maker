"""Archivo de proyecto JSON (plan, Anexo B) y parámetros derivados."""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass

from .screen import DEFAULT_ANGLES, INKS

DEFAULTS = {
    "version": 1,
    "imagen": "",
    "ancho_mm": 3000.0,
    "alto_mm": 1000.0,
    "distancia_observacion_mm": 10000.0,
    "tintas": ["C", "M", "Y", "K"],
    "salida": "stencil",  # stencil | sello | probeta
    "gcr": 0.6,
    "trama": {
        "modo": "A",
        "paso_mm": 2.5,
        "angulos": dict(DEFAULT_ANGLES),
        "puente_min_mm": 0.6,
        "diametro_min_mm": 0.5,
    },
    "material": {
        "nombre": "PP",
        "factor_escala": [1.0, 1.0],
        "compensacion_agujero_mm": 0.0,
    },
    "plancha": {
        "espesor_mm": 0.6,
        "baldosa_activa_mm": [240.0, 240.0],
        "marco_mm": 5.0,
        "marco_alto_mm": 1.2,
    },
    "sello": {
        "fuente": "chart",
        "lado_mm": 40.0,
        "paso_mm": 2.0,
        "base_mm": 1.2,
        "pin_alto_mm": 0.7,
        "pin_min_mm": 0.6,
        "separacion_min_mm": 0.4,
        "chaflan_mm": 3.0,
        "marco_registro": {"holgura_mm": 0.3, "espesor_mm": 4.0, "margen_mm": 15.0},
    },
    "calibracion": {
        "pintura": "",
        "distancia_rociado_mm": 250.0,
        "curva": [],  # [[cobertura del stencil, cobertura real], ...]
    },
}


def _merge(base: dict, new: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (new or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


@dataclass
class StencilParams:
    pitch: float
    angles: dict
    mode: str
    w_min: float
    d_min: float
    hole_comp: float
    thickness: float
    frame_w: float
    frame_h: float
    active: float
    scale: tuple
    gcr: float
    calib: list
    inks: tuple


class Project:
    """Contenedor de parámetros con valores por defecto; `data` sigue el esquema del Anexo B."""

    def __init__(self, data: dict | None = None):
        self.data = _merge(DEFAULTS, data or {})

    # --- E/S -------------------------------------------------------------
    @classmethod
    def load(cls, path: str) -> "Project":
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    # --- acceso rápido -----------------------------------------------------
    @property
    def width(self) -> float:
        return float(self.data["ancho_mm"])

    @property
    def height(self) -> float:
        return float(self.data["alto_mm"])

    @property
    def inks(self) -> tuple:
        got = tuple(i for i in self.data["tintas"] if i in INKS)
        return got or ("K",)

    def stencil_params(self) -> StencilParams:
        t, m, p = self.data["trama"], self.data["material"], self.data["plancha"]
        return StencilParams(
            pitch=float(t["paso_mm"]), angles={k: float(v) for k, v in t["angulos"].items()},
            mode=str(t["modo"]).upper(), w_min=float(t["puente_min_mm"]),
            d_min=float(t["diametro_min_mm"]), hole_comp=float(m["compensacion_agujero_mm"]),
            thickness=float(p["espesor_mm"]), frame_w=float(p["marco_mm"]),
            frame_h=float(p["marco_alto_mm"]), active=float(p["baldosa_activa_mm"][0]),
            scale=(float(m["factor_escala"][0]), float(m["factor_escala"][1])),
            gcr=float(self.data["gcr"]), calib=self.data["calibracion"]["curva"], inks=self.inks,
        )
