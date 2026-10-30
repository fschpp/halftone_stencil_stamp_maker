"""Interfaz gráfica GTK4 (PyGObject). Toda la lógica vive en `session.py`; esto es solo la capa visual.

Requiere: python3-gi y gir1.2-gtk-4.0 (ver README).
"""
from __future__ import annotations

import os
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from .project import Project  # noqa: E402
from .session import Session  # noqa: E402

APP_ID = "io.github.fschpp.HalftoneStencilStampMaker"


def pil_to_texture(img):
    img = img.convert("RGB")
    w, h = img.size
    return Gdk.MemoryTexture.new(w, h, Gdk.MemoryFormat.R8G8B8, GLib.Bytes.new(img.tobytes()), w * 3)


def make_picture():
    pic = Gtk.Picture()
    pic.set_hexpand(True)
    pic.set_vexpand(True)
    pic.set_can_shrink(True)
    if hasattr(pic, "set_content_fit"):
        pic.set_content_fit(Gtk.ContentFit.CONTAIN)
    return pic


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app, session: Session):
        super().__init__(application=app, title="Halftone stencil & stamp maker")
        self.session = session
        self.set_default_size(1280, 800)
        self._widgets = []      # (tipo, widget, ruta) para refrescar al abrir un proyecto
        self._loading = False
        self._debounce = 0
        self._overview_size = None

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_start_child(self._build_controls())
        paned.set_end_child(self._build_views())
        paned.set_resize_start_child(False)
        paned.set_shrink_start_child(False)
        paned.set_position(400)
        self.set_child(paned)
        self.refresh_widgets()
        self._update_info()

    # ------------------------------------------------------------------ datos
    def _get(self, path):
        cur = self.session.project.data
        for k in path:
            cur = cur[k]
        return cur

    def _set(self, path, value):
        cur = self.session.project.data
        for k in path[:-1]:
            cur = cur[k]
        cur[path[-1]] = value

    def _on_value(self, path, value):
        if self._loading:
            return
        self._set(path, value)
        if path == ("plancha", "baldosa_activa_mm", 0):  # la zona activa es cuadrada
            self._set(("plancha", "baldosa_activa_mm", 1), value)
        self._schedule_info()

    # --------------------------------------------------------------- controles
    def _build_controls(self):
        outer = Gtk.ScrolledWindow()
        outer.set_min_content_width(380)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for side in ("start", "end", "top", "bottom"):
            getattr(box, f"set_margin_{side}")(10)
        outer.set_child(box)

        # --- botones de archivo
        row = Gtk.Box(spacing=6)
        b = Gtk.Button(label="Elegir foto…")
        b.connect("clicked", lambda *_: self._pick_image())
        row.append(b)
        self.image_label = Gtk.Label(label="(sin foto)", xalign=0, hexpand=True)
        self.image_label.set_ellipsize(3)  # Pango.EllipsizeMode.END
        row.append(self.image_label)
        box.append(row)

        row = Gtk.Box(spacing=6)
        for text, cb in (("Abrir proyecto…", self._open_project), ("Guardar proyecto…", self._save_project)):
            b = Gtk.Button(label=text)
            b.connect("clicked", lambda _b, cb=cb: cb())
            row.append(b)
        box.append(row)

        # --- salida
        g = self._group(box, "Salida", expanded=True)
        self._dropdown(g, 0, "Tipo", ("salida",),
                       [("stencil", "Stencil (aerosol, PP)"), ("sello", "Sello TPU (tintas al alcohol)"),
                        ("probeta", "Probeta de stencil (Fase 0)")], on_change=self._update_visibility)

        # --- diseño
        g = self._group(box, "Diseño (stencil)", expanded=True)
        self.design_group = g.get_parent()
        self._spin(g, 0, "Ancho final (mm)", ("ancho_mm",), 50, 20000, 10, 0)
        self._spin(g, 1, "Alto final (mm)", ("alto_mm",), 50, 20000, 10, 0)
        self._spin(g, 2, "Distancia de observación (mm)", ("distancia_observacion_mm",), 500, 100000, 500, 0)
        self._spin(g, 3, "Paso de trama (mm)", ("trama", "paso_mm"), 1.0, 8.0, 0.05, 2)
        b = Gtk.Button(label="Usar paso sugerido para la distancia")
        b.connect("clicked", lambda *_: self._use_suggested_pitch())
        g.attach(b, 0, 4, 2, 1)
        self._spin(g, 5, "Reemplazo de gris (GCR)", ("gcr",), 0.0, 1.0, 0.05, 2)
        ink_row = Gtk.Box(spacing=8)
        ink_row.append(Gtk.Label(label="Tintas:"))
        self.ink_checks = {}
        for ink in "CMYK":
            c = Gtk.CheckButton(label=ink)
            c.connect("toggled", lambda *_: self._on_inks())
            self.ink_checks[ink] = c
            ink_row.append(c)
        g.attach(ink_row, 0, 6, 2, 1)
        self._dropdown(g, 7, "Modo de trama", ("trama", "modo"),
                       [("A", "A (superposición)"), ("B", "B (sin superposición, experimental)")])

        g = self._group(box, "Trama y ángulos", expanded=False)
        for n, ink in enumerate("CMYK"):
            self._spin(g, n, f"Ángulo {ink} (°)", ("trama", "angulos", ink), 0, 179, 1, 0)
        self._spin(g, 4, "Puente mínimo (mm)", ("trama", "puente_min_mm"), 0.3, 2.0, 0.05, 2)
        self._spin(g, 5, "Diámetro mínimo de agujero (mm)", ("trama", "diametro_min_mm"), 0.3, 2.0, 0.05, 2)

        g = self._group(box, "Plancha y material", expanded=False)
        self._dropdown(g, 0, "Material", ("material", "nombre"), [(m, m) for m in ("PP", "PLA", "PETG")])
        self._spin(g, 1, "Espesor (mm)", ("plancha", "espesor_mm"), 0.2, 2.0, 0.05, 2)
        self._spin(g, 2, "Zona activa por baldosa (mm)", ("plancha", "baldosa_activa_mm", 0), 50, 250, 1, 0)
        self._spin(g, 3, "Ancho del marco (mm)", ("plancha", "marco_mm"), 2, 15, 0.5, 1)
        self._spin(g, 4, "Alto del marco sobre la plancha (mm)", ("plancha", "marco_alto_mm"), 0.4, 3.0, 0.1, 1)
        self._spin(g, 5, "Escala X (contracción)", ("material", "factor_escala", 0), 0.9, 1.1, 0.001, 3)
        self._spin(g, 6, "Escala Y (contracción)", ("material", "factor_escala", 1), 0.9, 1.1, 0.001, 3)
        self._spin(g, 7, "Compensación de agujeros (mm)", ("material", "compensacion_agujero_mm"),
                   -0.3, 0.6, 0.01, 2)

        g = self._group(box, "Sello TPU", expanded=False)
        self.stamp_group = g.get_parent()
        self._dropdown(g, 0, "Fuente", ("sello", "fuente"), [("chart", "Carta de parches"), ("photo", "Foto")])
        self._spin(g, 1, "Lado del sello (mm)", ("sello", "lado_mm"), 20, 200, 1, 0)
        self._spin(g, 2, "Paso (mm)", ("sello", "paso_mm"), 1.0, 5.0, 0.1, 1)
        self._spin(g, 3, "Base (mm)", ("sello", "base_mm"), 0.6, 3.0, 0.1, 1)
        self._spin(g, 4, "Alto del pin (mm)", ("sello", "pin_alto_mm"), 0.3, 1.0, 0.05, 2)
        self._spin(g, 5, "Pin mínimo (mm)", ("sello", "pin_min_mm"), 0.4, 1.5, 0.05, 2)
        self._spin(g, 6, "Separación mínima entre pines (mm)", ("sello", "separacion_min_mm"), 0.2, 1.0, 0.05, 2)
        self._spin(g, 7, "Chaflán (mm)", ("sello", "chaflan_mm"), 1, 8, 0.5, 1)

        # --- vista previa / exportación
        g = self._group(box, "Vista previa", expanded=True)
        self._dropdown_local(g, 0, "Modelo de color", [("translucent", "Tintas translúcidas"),
                                                       ("opaque", "Aerosol opaco (orden Y, M, C, K)")],
                             "preview_model")
        self.limited_check = Gtk.CheckButton(label="Mostrar rango tonal limitado del stencil")
        self.limited_check.set_active(True)
        g.attach(self.limited_check, 0, 1, 2, 1)
        b = Gtk.Button(label="Actualizar vista previa")
        b.add_css_class("suggested-action")
        b.connect("clicked", lambda *_: self._run_preview())
        g.attach(b, 0, 2, 2, 1)

        g = self._group(box, "Exportar", expanded=True)
        self.tiles_entry = Gtk.Entry()
        self.tiles_entry.set_placeholder_text("Baldosas, p. ej. 0,0 1,0 (vacío = todas)")
        g.attach(self.tiles_entry, 0, 0, 2, 1)
        b = Gtk.Button(label="Exportar STL…")
        b.connect("clicked", lambda *_: self._export())
        g.attach(b, 0, 1, 2, 1)

        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        box.append(self.progress)
        self.status = Gtk.Label(label="Listo.", xalign=0, wrap=True)
        box.append(self.status)
        return outer

    def _group(self, parent, title, expanded=True):
        exp = Gtk.Expander(label=title)
        exp.set_expanded(expanded)
        grid = Gtk.Grid(column_spacing=8, row_spacing=4)
        grid.set_margin_top(4)
        exp.set_child(grid)
        parent.append(exp)
        return grid

    def _spin(self, grid, row, label, path, lo, hi, step, digits):
        lab = Gtk.Label(label=label, xalign=0, hexpand=True)
        spin = Gtk.SpinButton.new_with_range(lo, hi, step)
        spin.set_digits(digits)
        spin.connect("value-changed", lambda s, p=path: self._on_value(p, s.get_value()))
        grid.attach(lab, 0, row, 1, 1)
        grid.attach(spin, 1, row, 1, 1)
        self._widgets.append(("spin", spin, path))

    def _dropdown(self, grid, row, label, path, options, on_change=None):
        lab = Gtk.Label(label=label, xalign=0, hexpand=True)
        dd = Gtk.DropDown.new_from_strings([t for _, t in options])
        values = [v for v, _ in options]

        def changed(d, _pspec, p=path, vals=values):
            if self._loading:
                return
            self._set(p, vals[d.get_selected()])
            if on_change:
                on_change()
            self._schedule_info()
        dd.connect("notify::selected", changed)
        grid.attach(lab, 0, row, 1, 1)
        grid.attach(dd, 1, row, 1, 1)
        self._widgets.append(("dropdown", dd, path, values))

    def _dropdown_local(self, grid, row, label, options, attr):
        lab = Gtk.Label(label=label, xalign=0, hexpand=True)
        dd = Gtk.DropDown.new_from_strings([t for _, t in options])
        setattr(self, attr, options[0][0])
        dd.connect("notify::selected", lambda d, _p: setattr(self, attr, options[d.get_selected()][0]))
        grid.attach(lab, 0, row, 1, 1)
        grid.attach(dd, 1, row, 1, 1)

    def refresh_widgets(self):
        self._loading = True
        try:
            for item in self._widgets:
                kind, w, path = item[0], item[1], item[2]
                val = self._get(path)
                if kind == "spin":
                    w.set_value(float(val))
                else:
                    vals = item[3]
                    w.set_selected(vals.index(val) if val in vals else 0)
            for ink, c in self.ink_checks.items():
                c.set_active(ink in self.session.project.data["tintas"])
            img = self.session.project.data["imagen"]
            self.image_label.set_text(os.path.basename(img) if img else "(sin foto)")
        finally:
            self._loading = False
        self._update_visibility()

    def _update_visibility(self):
        mode = self.session.project.data["salida"]
        self.design_group.set_visible(mode == "stencil")
        self.stamp_group.set_visible(mode == "sello")

    def _on_inks(self):
        if self._loading:
            return
        inks = [i for i, c in self.ink_checks.items() if c.get_active()]
        self.session.project.data["tintas"] = inks or ["K"]
        self._schedule_info()

    def _use_suggested_pitch(self):
        self.session.project.data["trama"]["paso_mm"] = self.session.suggested_pitch()
        self.refresh_widgets()
        self._schedule_info()

    # ------------------------------------------------------------------ vistas
    def _build_views(self):
        nb = Gtk.Notebook()
        self.notebook = nb

        self.overview_pic = make_picture()
        gc = Gtk.GestureClick.new()
        gc.connect("pressed", self._on_overview_click)
        self.overview_pic.add_controller(gc)
        nb.append_page(self.overview_pic, Gtk.Label(label="General"))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        bar = Gtk.Box(spacing=6)
        self.detail_spins = {}
        for key, label, val, hi in (("x", "x (mm)", 0, 20000), ("y", "y (mm)", 0, 20000),
                                    ("w", "ancho ventana (mm)", 60, 400), ("h", "alto ventana (mm)", 40, 400)):
            bar.append(Gtk.Label(label=label))
            s = Gtk.SpinButton.new_with_range(0 if key in "xy" else 10, hi, 5)
            s.set_value(val)
            self.detail_spins[key] = s
            bar.append(s)
        b = Gtk.Button(label="Ver detalle")
        b.connect("clicked", lambda *_: self._run_detail())
        bar.append(b)
        box.append(bar)
        box.append(Gtk.Label(label="Tip: hacé clic sobre la imagen de la pestaña General para centrar el detalle.",
                             xalign=0))
        self.detail_pic = make_picture()
        box.append(self.detail_pic)
        nb.append_page(box, Gtk.Label(label="Detalle de trama"))

        self.map_pic = make_picture()
        nb.append_page(self.map_pic, Gtk.Label(label="Mapa de baldosas"))

        self.info_view = Gtk.TextView()
        self.info_view.set_editable(False)
        self.info_view.set_monospace(True)
        self.info_view.set_wrap_mode(Gtk.WrapMode.WORD)
        sw = Gtk.ScrolledWindow()
        sw.set_child(self.info_view)
        nb.append_page(sw, Gtk.Label(label="Informe"))
        return nb

    def _show(self, pic, img):
        pic.set_paintable(pil_to_texture(img))

    def _set_text(self, text):
        self.info_view.get_buffer().set_text(text, -1)

    def _schedule_info(self):
        if self._debounce:
            GLib.source_remove(self._debounce)
        self._debounce = GLib.timeout_add(300, self._update_info)

    def _update_info(self):
        self._debounce = 0
        d = self.session.project.data
        try:
            if d["salida"] == "stencil":
                self._set_text(self.session.report_text())
                self._show(self.map_pic, self.session.tile_map_image(self._parse_tiles(silent=True)))
            else:
                self._set_text("Modo %s: usá «Actualizar vista previa» o «Exportar STL…»." % d["salida"])
        except Exception as exc:  # no romper la GUI por un valor intermedio inválido
            self._set_text(f"No se pudo calcular el informe: {exc}")
        return False

    # -------------------------------------------------------------- acciones
    def _msg(self, text, error=False):
        self.status.set_markup(f'<span foreground="#b00020">{GLib.markup_escape_text(text)}</span>'
                               if error else GLib.markup_escape_text(text))

    def _run_bg(self, work, done, label):
        self._msg(label)
        self.progress.set_fraction(0.0)
        self.progress.set_text("")
        self.progress.pulse()

        def target():
            try:
                res, err = work(), None
            except Exception as exc:  # noqa: BLE001
                res, err = None, exc
            GLib.idle_add(lambda: (done(res, err), False)[1])
        threading.Thread(target=target, daemon=True).start()

    def _parse_tiles(self, silent=False):
        text = self.tiles_entry.get_text().replace(";", " ").strip()
        if not text:
            return None
        try:
            return [tuple(int(v) for v in t.split(",")) for t in text.split()]
        except ValueError:
            if not silent:
                raise ValueError("Formato de baldosas inválido: usá pares X,Y separados por espacios.")
            return None

    def _run_preview(self):
        mode = self.session.project.data["salida"]
        model, limited = self.preview_model, self.limited_check.get_active()
        if mode == "stencil":
            def work():
                ov = self.session.overview_image(model, limited)
                self._overview_size = ov.size
                return ov, self._detail_image(model)

            def done(res, err):
                if err:
                    return self._msg(str(err), True)
                self._show(self.overview_pic, res[0])
                self._show(self.detail_pic, res[1])
                self._update_info()
                self._msg("Vista previa actualizada.")
                self.progress.set_fraction(1.0)
            self._run_bg(work, done, "Calculando vista previa…")
        else:
            def work():
                out = self.session.temp_dir()
                log = self.session._run_tools(mode, out)
                return log, self.session.stamp_preview_path(out)

            def done(res, err):
                if err:
                    return self._msg(str(err), True)
                log, path = res
                self._set_text(log)
                if os.path.exists(path):
                    from PIL import Image
                    self._show(self.overview_pic, Image.open(path))
                self.notebook.set_current_page(0)
                self._msg("Vista previa generada.")
                self.progress.set_fraction(1.0)
            self._run_bg(work, done, "Generando…")

    def _detail_image(self, model):
        s = {k: v.get_value() for k, v in self.detail_spins.items()}
        return self.session.detail_image(s["x"], s["y"], s["w"], s["h"], 12.0, model)

    def _run_detail(self):
        if self.session.project.data["salida"] != "stencil":
            return self._msg("El detalle de trama es solo para stencils.", True)
        model = self.preview_model

        def done(res, err):
            if err:
                return self._msg(str(err), True)
            self._show(self.detail_pic, res)
            self._msg("Detalle actualizado.")
        self._run_bg(lambda: self._detail_image(model), done, "Calculando detalle…")

    def _on_overview_click(self, gesture, n_press, x, y):
        if not self._overview_size or self.session.project.data["salida"] != "stencil":
            return
        pic = self.overview_pic
        ww, wh = pic.get_width(), pic.get_height()
        iw, ih = self._overview_size
        scale = min(ww / iw, wh / ih)
        ox, oy = (ww - iw * scale) / 2, (wh - ih * scale) / 2
        fx, fy = (x - ox) / (iw * scale), (y - oy) / (ih * scale)
        if not (0 <= fx <= 1 and 0 <= fy <= 1):
            return
        p = self.session.project
        w, h = self.detail_spins["w"].get_value(), self.detail_spins["h"].get_value()
        self.detail_spins["x"].set_value(max(0.0, fx * p.width - w / 2))
        self.detail_spins["y"].set_value(max(0.0, (1 - fy) * p.height - h / 2))
        self.notebook.set_current_page(1)
        self._run_detail()

    def _export(self):
        try:
            tiles = self._parse_tiles()
        except ValueError as exc:
            return self._msg(str(exc), True)
        self._choose_folder("Carpeta de salida", lambda path: self._do_export(path, tiles))

    def _do_export(self, out_dir, tiles):
        def progress(done_n, total, name):
            GLib.idle_add(lambda: (self.progress.set_fraction(done_n / total),
                                   self.progress.set_text(f"{done_n}/{total}  {name}"), False)[2])

        def done(res, err):
            if err:
                return self._msg(str(err), True)
            self._set_text(res)
            self.progress.set_fraction(1.0)
            self._msg("Exportación terminada.")
        self._run_bg(lambda: self.session.export(out_dir, tiles, progress), done, "Exportando…")

    # ------------------------------------------------------- archivos / proyecto
    def _filter(self, name, patterns=None, mimes=None):
        f = Gtk.FileFilter()
        f.set_name(name)
        for p in patterns or []:
            f.add_pattern(p)
        for m in mimes or []:
            f.add_mime_type(m)
        return f

    def _dialog(self, title, callback, kind="open", file_filter=None):
        """Abre un diálogo de archivos; `kind` = open | save | folder. Llama a callback(ruta)."""
        if hasattr(Gtk, "FileDialog"):  # GTK >= 4.10
            dlg = Gtk.FileDialog()
            dlg.set_title(title)
            if file_filter is not None:
                dlg.set_default_filter(file_filter)

            def finished(d, res):
                try:
                    f = {"open": d.open_finish, "save": d.save_finish,
                         "folder": d.select_folder_finish}[kind](res)
                except GLib.Error:
                    return  # cancelado
                if f is not None:
                    callback(f.get_path())
            {"open": dlg.open, "save": dlg.save, "folder": dlg.select_folder}[kind](self, None, finished)
        else:  # GTK 4.0-4.8
            action = {"open": Gtk.FileChooserAction.OPEN, "save": Gtk.FileChooserAction.SAVE,
                      "folder": Gtk.FileChooserAction.SELECT_FOLDER}[kind]
            dlg = Gtk.FileChooserNative.new(title, self, action, "Aceptar", "Cancelar")
            if file_filter is not None:
                dlg.add_filter(file_filter)

            def response(d, resp):
                if resp == Gtk.ResponseType.ACCEPT:
                    callback(d.get_file().get_path())
                d.destroy()
            dlg.connect("response", response)
            self._native = dlg  # evitar que lo recoja el GC
            dlg.show()

    def _choose_folder(self, title, callback):
        self._dialog(title, callback, "folder")

    def _pick_image(self):
        flt = self._filter("Imágenes", mimes=["image/png", "image/jpeg", "image/webp", "image/tiff"])

        def got(path):
            self.session.project.data["imagen"] = path
            self.image_label.set_text(os.path.basename(path))
            self._schedule_info()
            self._msg("Foto cargada. Usá «Actualizar vista previa».")
        self._dialog("Elegir foto", got, "open", flt)

    def _open_project(self):
        def got(path):
            try:
                self.session.project = Project.load(path)
                self.session._sep_key = None
            except Exception as exc:  # noqa: BLE001
                return self._msg(f"No se pudo abrir el proyecto: {exc}", True)
            self.refresh_widgets()
            self._schedule_info()
            self._msg(f"Proyecto abierto: {os.path.basename(path)}")
        self._dialog("Abrir proyecto", got, "open", self._filter("Proyecto JSON", patterns=["*.json"]))

    def _save_project(self):
        def got(path):
            if not path.endswith(".json"):
                path += ".json"
            self.session.project.save(path)
            self._msg(f"Proyecto guardado: {os.path.basename(path)}")
        self._dialog("Guardar proyecto", got, "save", self._filter("Proyecto JSON", patterns=["*.json"]))


class App(Gtk.Application):
    def __init__(self, project_path=None):
        super().__init__(application_id=APP_ID)
        self.project_path = project_path

    def do_activate(self):
        project = Project.load(self.project_path) if self.project_path else Project()
        MainWindow(self, Session(project)).present()


def run(project_path=None) -> int:
    return App(project_path).run([sys.argv[0]])


if __name__ == "__main__":
    sys.exit(run(sys.argv[1] if len(sys.argv) > 1 else None))
