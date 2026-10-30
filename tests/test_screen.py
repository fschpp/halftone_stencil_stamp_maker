import numpy as np

from hsm.screen import (DEFAULT_ANGLES, apply_calibration, global_hex_points, hex_angle_warnings,
                        max_coverage, separate_image, suggest_pitch)


def test_default_angles_have_no_hex_conflicts():
    assert hex_angle_warnings(DEFAULT_ANGLES) == []


def test_classic_cmyk_angles_collide_in_hex_grid():
    warns = hex_angle_warnings({"C": 15, "M": 75, "Y": 0, "K": 45})
    assert any("C y M" in w for w in warns)


def test_suggest_pitch_clamps_to_comfortable_range():
    assert suggest_pitch(10000) == 2.91
    assert suggest_pitch(5000) == 2.0
    assert suggest_pitch(50000) == 3.0


def test_max_coverage_matches_plan_table():
    # §6.2: p = 2,5 mm y puente 0,6 mm -> ≈52 %
    assert abs(max_coverage(2.5, 0.6) - 0.52) < 0.01


def test_global_grid_is_continuous_across_windows():
    a = global_hex_points(0, 0, 60, 60, 2.5, 15)
    b = global_hex_points(60, 0, 120, 60, 2.5, 15)
    both = global_hex_points(0, 0, 120, 60, 2.5, 15)
    key = lambda p: {(round(x, 6), round(y, 6)) for x, y in p}  # noqa: E731
    assert key(a) | key(b) == key(both)


def test_hex_grid_spacing_is_pitch():
    pts = global_hex_points(0, 0, 50, 50, 2.5, 0)
    d = np.hypot(*(pts[1:] - pts[0]).T)
    assert abs(d.min() - 2.5) < 1e-9


def test_calibration_inverts_the_measured_curve():
    curve = [[0.0, 0.0], [0.2, 0.3], [0.4, 0.55]]  # la pintura gana punto
    assert abs(float(apply_calibration(np.array([0.3]), curve)[0]) - 0.2) < 1e-9
    assert float(apply_calibration(np.array([0.1]), [])[0]) == 0.1


def test_separation_shapes_and_ranges(photo):
    sep = separate_image(photo, 480, 240, 2.5)
    assert set(sep.channels) == {"C", "M", "Y", "K"}
    for arr in sep.channels.values():
        assert 0.0 <= arr.min() and arr.max() <= 1.0
    s = sep.sample("C", np.array([0.0, 479.0]), np.array([0.0, 239.0]))
    assert s.shape == (2,)


def test_black_only_is_grayscale(photo):
    sep = separate_image(photo, 480, 240, 2.5, inks=("K",))
    assert set(sep.channels) == {"K"}
