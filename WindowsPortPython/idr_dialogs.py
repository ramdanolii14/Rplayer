#!/usr/bin/env python3
# ============================================================
#  idr_dialogs.py
#  Dialog-dialog aplikasi: SettingsDialog (pengaturan warna
#  spektrum & grafik) dan AboutDialog (info aplikasi, logo,
#  maintainer, versi dari GitHub).
#
#  Bagian dari IDR Spectrum Player.
# ============================================================

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

from pathlib import Path

from idr_config import SPECTRUM_COLOR_NAMES, CHART_COLOR_NAMES


class SettingsDialog(Gtk.Dialog):
    """Dialog pengaturan warna spektrum dan grafik chart."""
    def __init__(self, parent, spec_color, chart_color, on_spec_color, on_chart_color):
        super().__init__(title="Pengaturan", transient_for=parent, modal=True)
        self.set_default_size(420, -1)
        self._on_spec_color  = on_spec_color
        self._on_chart_color = on_chart_color

        close_btn = Gtk.Button(label="Tutup")
        close_btn.connect("clicked", lambda _: self.destroy())
        self.add_action_widget(close_btn, Gtk.ResponseType.CLOSE)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(16); box.set_margin_bottom(16)
        box.set_margin_start(18); box.set_margin_end(18)

        # ── Spectrum Color ──
        spec_title = Gtk.Label(label="WARNA SPEKTRUM")
        spec_title.add_css_class("section-title")
        spec_title.add_css_class("mono")
        spec_title.set_halign(Gtk.Align.START)
        box.append(spec_title)

        spec_grid = Gtk.FlowBox()
        spec_grid.set_max_children_per_line(4)
        spec_grid.set_selection_mode(Gtk.SelectionMode.NONE)
        spec_grid.set_column_spacing(6)
        spec_grid.set_row_spacing(6)

        self._spec_btns = {}
        for name in SPECTRUM_COLOR_NAMES:
            b = Gtk.Button(label=name)
            b.add_css_class("tab-pill")
            if name == spec_color:
                b.add_css_class("active")
            b.connect("clicked", self._spec_color_clicked, name)
            self._spec_btns[name] = b
            spec_grid.append(b)
        box.append(spec_grid)

        sep1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box.append(sep1)

        # ── Chart Color ──
        chart_title = Gtk.Label(label="WARNA GRAFIK IDR")
        chart_title.add_css_class("section-title")
        chart_title.add_css_class("mono")
        chart_title.set_halign(Gtk.Align.START)
        box.append(chart_title)

        chart_grid = Gtk.FlowBox()
        chart_grid.set_max_children_per_line(4)
        chart_grid.set_selection_mode(Gtk.SelectionMode.NONE)
        chart_grid.set_column_spacing(6)
        chart_grid.set_row_spacing(6)

        self._chart_btns = {}
        for name in CHART_COLOR_NAMES:
            b = Gtk.Button(label=name)
            b.add_css_class("tab-pill")
            if name == chart_color:
                b.add_css_class("active")
            b.connect("clicked", self._chart_color_clicked, name)
            self._chart_btns[name] = b
            chart_grid.append(b)
        box.append(chart_grid)

        self.get_content_area().append(box)

    def _spec_color_clicked(self, _btn, name):
        for n, b in self._spec_btns.items():
            b.remove_css_class("active")
        self._spec_btns[name].add_css_class("active")
        self._on_spec_color(name)

    def _chart_color_clicked(self, _btn, name):
        for n, b in self._chart_btns.items():
            b.remove_css_class("active")
        self._chart_btns[name].add_css_class("active")
        self._on_chart_color(name)


# ── About Dialog ───────────────────────────────────────────────────────────────
class AboutDialog(Gtk.Dialog):
    """Dialog informasi aplikasi dengan logo, maintainer, version, dan sha256."""
    def __init__(self, parent):
        super().__init__(title="Tentang IDR Spectrum Player", transient_for=parent, modal=True)
        self.set_default_size(440, -1)

        close_btn = Gtk.Button(label="Tutup")
        close_btn.connect("clicked", lambda _: self.destroy())
        self.add_action_widget(close_btn, Gtk.ResponseType.CLOSE)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_top(22); box.set_margin_bottom(20)
        box.set_margin_start(28); box.set_margin_end(28)

        # ── Logo ──
        try:
            from gi.repository import GdkPixbuf
            svg_candidates = [
                Path(__file__).parent / "id.ramdanolii.idrspectrum.svg",
                Path(__file__).parent / "IDRSpectrum.AppDir" / "id.ramdanolii.idrspectrum.svg",
            ]
            logo = None
            for svg_path in svg_candidates:
                if svg_path.exists():
                    pb = GdkPixbuf.Pixbuf.new_from_file_at_size(str(svg_path), 80, 80)
                    logo = Gtk.Image.new_from_pixbuf(pb)
                    break
            if logo is None:
                logo = Gtk.Image.new_from_icon_name("id.ramdanolii.idrspectrum")
                logo.set_pixel_size(80)
        except Exception:
            logo = Gtk.Label(label="♫")
        logo.set_halign(Gtk.Align.CENTER)
        box.append(logo)

        # ── Nama Aplikasi ──
        app_name = Gtk.Label(label="IDR Spectrum Player")
        app_name.set_halign(Gtk.Align.CENTER)
        app_name.add_css_class("section-title")
        app_name.add_css_class("mono")
        box.append(app_name)

        desc = Gtk.Label(label="Pemutar Musik dengan Spektrum Visualizer & Kurs Rupiah")
        desc.set_halign(Gtk.Align.CENTER)
        desc.add_css_class("dim")
        desc.set_wrap(True)
        box.append(desc)

        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # ── Info Grid ──
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(16)

        def key_lbl(text):
            l = Gtk.Label(label=text)
            l.add_css_class("dim")
            l.set_halign(Gtk.Align.END)
            return l

        def val_lbl(text):
            l = Gtk.Label(label=text)
            l.set_halign(Gtk.Align.START)
            l.set_selectable(True)
            return l

        def link_btn(uri, label):
            b = Gtk.LinkButton.new_with_label(uri, label)
            b.set_halign(Gtk.Align.START)
            return b

        grid.attach(key_lbl("Maintainer"), 0, 0, 1, 1)
        grid.attach(val_lbl("ramdanolii14"),            1, 0, 1, 1)

        grid.attach(key_lbl("Email"),      0, 1, 1, 1)
        grid.attach(link_btn("mailto:ramdanolii1410@gmail.com", "ramdanolii1410@gmail.com"), 1, 1, 1, 1)

        grid.attach(key_lbl("Repositori"), 0, 2, 1, 1)
        grid.attach(link_btn("https://github.com/ramdanolii14/Rplayer",
                              "github.com/ramdanolii14/Rplayer"),           1, 2, 1, 1)

        grid.attach(key_lbl("Lisensi"),    0, 3, 1, 1)
        grid.attach(link_btn("https://github.com/ramdanolii14/Rplayer/blob/main/LICENSE",
                              "GNU GPL v3"),                                 1, 3, 1, 1)

        grid.attach(key_lbl("Versi"),      0, 4, 1, 1)
        self._ver_lbl = val_lbl("Memuat...")
        grid.attach(self._ver_lbl, 1, 4, 1, 1)


        box.append(grid)
        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # ── Kontributor ──
        contrib_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        contrib_title = Gtk.Label(label="INGIN BERKONTRIBUSI?")
        contrib_title.add_css_class("section-title")
        contrib_title.add_css_class("mono")
        contrib_title.set_halign(Gtk.Align.CENTER)
        contrib_box.append(contrib_title)

        contrib_links = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        contrib_links.set_halign(Gtk.Align.CENTER)
        contrib_links.append(link_btn(
            "https://github.com/ramdanolii14/Rplayer/issues",
            "🐛  Laporkan Bug"
        ))
        contrib_links.append(link_btn(
            "https://github.com/ramdanolii14/Rplayer/pulls",
            "🔧  Pull Request"
        ))
        contrib_links.append(link_btn(
            "https://github.com/ramdanolii14/Rplayer/fork",
            "🍴  Fork Repo"
        ))
        contrib_box.append(contrib_links)
        box.append(contrib_box)

        self.get_content_area().append(box)

        # Load versi & SHA256 di background thread
        GLib.timeout_add(80, self._start_load)

    def _start_load(self):
        import threading
        threading.Thread(target=self._load_info, daemon=True).start()
        return False

    def _load_info(self):
        import urllib.request, json as _json

        # Versi dari GitHub (commit SHA terbaru di main)
        try:
            req = urllib.request.Request(
                "https://api.github.com/repos/ramdanolii14/Rplayer/commits/main",
                headers={"Accept": "application/vnd.github.v3+json",
                         "User-Agent": "IDRSpectrum/1.0"}
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                d = _json.loads(r.read())
            short_sha = d["sha"][:7]
            msg       = d["commit"]["message"].split("\n")[0][:50]
            ver_text  = f"{short_sha}  —  {msg}"
        except Exception:
            ver_text = "offline (tidak dapat terhubung ke GitHub)"

        GLib.idle_add(self._apply_info, ver_text)

    def _apply_info(self, ver):
        self._ver_lbl.set_text(ver)
        return False
