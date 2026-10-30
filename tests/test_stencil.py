import numpy as np

from hsm.project import Project
from hsm.screen import separate_image
from hsm.stencil import build_tile, design_report, ink_dots, tile_counts


def small_project(photo):
    p = Project({"imagen": photo, "ancho_mm": 120, "alto_mm": 60})
    p.data["plancha"]["baldosa_activa_mm"] = [60.0, 60.0]
    p.data["trama"]["paso_mm"] = 2.5
    return p


def test_tile_counts():
    assert tile_counts(1000, 3000, 240) == (5, 13)
    assert tile_counts(240, 240, 240) == (1, 1)
    assert tile_counts(241, 240, 240) == (2, 1)


def test_report_for_the_wall_matches_plan_ranges():
    r = design_report(Project({"ancho_mm": 1000, "alto_mm": 3000}))
    assert r["cantidad_baldosas"] == 65 and r["stencils_totales"] == 260
    assert 190 <= r["stencils_totales"] <= 260  # §6.5


def test_dots_respect_bridge_and_min_diameter(photo):
    p = small_project(photo)
    P = p.stencil_params()
    sep = separate_image(photo, p.width, p.height, P.pitch)
    for ink in "CMYK":
        dots = ink_dots(sep, ink, (0, 0, 60, 60), P)
        assert len(dots)
        assert dots[:, 2].max() <= P.pitch - P.w_min + 1e-9
        assert dots[:, 2].min() >= P.d_min - 1e-9


def test_adjacent_tiles_share_the_same_lattice(photo):
    p = small_project(photo)
    P = p.stencil_params()
    sep = separate_image(photo, p.width, p.height, P.pitch)
    a = ink_dots(sep, "M", (0, 0, 60, 60), P)
    b = ink_dots(sep, "M", (60, 0, 120, 60), P)
    both = ink_dots(sep, "M", (0, 0, 120, 60), P)
    key = lambda d: {(round(x, 5), round(y, 5), round(r, 5)) for x, y, r in d}  # noqa: E731
    assert key(a) | key(b) == key(both)


def test_tile_mesh_is_watertight_single_body_with_notched_frame(photo):
    p = small_project(photo)
    P = p.stencil_params()
    sep = separate_image(photo, p.width, p.height, P.pitch)
    mesh, st = build_tile(sep, "K", 0, 0, P)
    assert st["estanca"] and mesh.is_watertight
    assert len(mesh.split(only_watertight=False)) == 1
    assert np.allclose(mesh.extents[:2], [70, 70])  # zona activa 60 + 2 x marco 5
    assert abs(mesh.extents[2] - (P.thickness + P.frame_h)) < 1e-6
    assert st["agujeros"] > 100


def test_contact_face_is_flat_and_frame_is_on_top(photo):
    p = small_project(photo)
    P = p.stencil_params()
    sep = separate_image(photo, p.width, p.height, P.pitch)
    mesh, _ = build_tile(sep, "Y", 1, 0, P)
    assert abs(mesh.bounds[0][2]) < 1e-9                      # cara de contacto en z = 0
    top = mesh.vertices[:, 2] > P.thickness + 1e-6
    assert top.any()
    v = mesh.vertices[top]                                    # el marco queda fuera de la zona activa
    inside = (v[:, 0] > P.frame_w + 1e-6) & (v[:, 0] < P.frame_w + P.active - 1e-6) & \
             (v[:, 1] > P.frame_w + 1e-6) & (v[:, 1] < P.frame_w + P.active - 1e-6)
    assert not inside.any()
