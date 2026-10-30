"""Prueba el cableado de la GUI con un `gi` simulado (el entorno de CI no tiene GTK4)."""
import importlib
import sys
from unittest.mock import MagicMock

import pytest


class Stub:
    def __init__(self, *a, **k):
        pass

    def __getattr__(self, name):
        return MagicMock()


@pytest.fixture
def gui(monkeypatch):
    gtk, gdk, glib = MagicMock(), MagicMock(), MagicMock()
    gtk.ApplicationWindow, gtk.Application = Stub, Stub
    fake_gi = MagicMock()
    fake_gi.repository.Gtk, fake_gi.repository.Gdk, fake_gi.repository.GLib = gtk, gdk, glib
    monkeypatch.setitem(sys.modules, "gi", fake_gi)
    monkeypatch.setitem(sys.modules, "gi.repository", fake_gi.repository)
    sys.modules.pop("hsm.gui", None)
    mod = importlib.import_module("hsm.gui")
    yield mod
    sys.modules.pop("hsm.gui", None)


def test_every_control_is_bound_to_a_valid_project_path(gui):
    from hsm.session import Session
    win = gui.MainWindow(MagicMock(), Session())
    assert len(win._widgets) >= 25
    for item in win._widgets:
        win._get(item[2])          # la ruta existe en el proyecto por defecto


def test_value_changes_update_the_project(gui):
    from hsm.session import Session
    ses = Session()
    win = gui.MainWindow(MagicMock(), ses)
    win._on_value(("trama", "paso_mm"), 2.75)
    win._on_value(("plancha", "baldosa_activa_mm", 0), 200.0)
    win._on_value(("trama", "angulos", "K"), 33.0)
    d = ses.project.data
    assert d["trama"]["paso_mm"] == 2.75 and d["trama"]["angulos"]["K"] == 33.0
    assert d["plancha"]["baldosa_activa_mm"] == [200.0, 200.0]


def test_loading_a_project_refreshes_without_writing_back(gui):
    from hsm.project import Project
    from hsm.session import Session
    ses = Session()
    win = gui.MainWindow(MagicMock(), ses)
    ses.project = Project({"ancho_mm": 777, "tintas": ["K", "Y"]})
    win.refresh_widgets()
    assert ses.project.data["ancho_mm"] == 777 and ses.project.data["tintas"] == ["K", "Y"]


def test_tile_entry_parsing(gui):
    from hsm.session import Session
    win = gui.MainWindow(MagicMock(), Session())
    win.tiles_entry.get_text.return_value = "0,0 2,1"
    assert win._parse_tiles() == [(0, 0), (2, 1)]
    win.tiles_entry.get_text.return_value = "abc"
    with pytest.raises(ValueError):
        win._parse_tiles()
    assert win._parse_tiles(silent=True) is None
