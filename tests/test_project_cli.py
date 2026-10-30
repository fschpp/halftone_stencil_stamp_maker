import os

from hsm import cli, tools
from hsm.project import Project


def test_project_roundtrip(tmp_path):
    p = Project({"ancho_mm": 1234, "trama": {"paso_mm": 2.2}})
    path = tmp_path / "p.json"
    p.save(str(path))
    q = Project.load(str(path))
    assert q.width == 1234 and q.data["trama"]["paso_mm"] == 2.2
    assert q.data["trama"]["angulos"]["M"] == 45.0  # los valores por defecto se conservan


def test_cli_info(capsys):
    assert cli.main(["info", "--width", "1000", "--height", "3000", "--distance", "10000"]) == 0
    assert "65" in capsys.readouterr().out


def test_cli_stencil_single_tile(tmp_path, photo):
    out = tmp_path / "out"
    code = cli.main(["stencil", "--image", photo, "--width", "120", "--height", "60", "--active", "60",
                     "--pitch", "2.5", "--inks", "K", "--tiles", "1,0", "--out", str(out)])
    assert code == 0
    files = sorted(os.listdir(out))
    assert "stencil_x01_y00_K.stl" in files and "proyecto.json" in files and "informe.json" in files


def test_stamp_chart_from_original_script(tmp_path):
    assert tools.main(["sellos", "--source", "chart", "--out", str(tmp_path)]) == 0
    for name in ("sello_C.stl", "sello_M.stl", "sello_Y.stl", "sello_K.stl", "marco_registro.stl"):
        assert (tmp_path / name).exists()
