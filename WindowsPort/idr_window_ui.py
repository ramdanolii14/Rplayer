#!/usr/bin/env python3
# ============================================================
#  idr_window_ui.py
#  Mixin pembangun UI jendela utama: navbar, panel library,
#  kartu kurs IDR, kartu spektrum, player bar, album art, serta
#  semua handler interaksi (library, playback navigation,
#  toggle tema/shuffle/repeat/spektrum, dialog pengaturan).
#
#  WindowUIMixin TIDAK berdiri sendiri — digabung dengan
#  idr_window_core.WindowCore di idr_spectrum_player.py untuk
#  membentuk class IDRSpectrumWindow yang lengkap.
#
#  Bagian dari IDR Spectrum Player.
# ============================================================

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gst", "1.0")
from gi.repository import Gtk, Gdk, Gst, GLib, GdkPixbuf

import os
import random
from pathlib import Path

from idr_config import DARK_THEME, LIGHT_THEME, save_config, AUDIO_EXTS
from idr_widgets import IDRChart, SpectrumVisualizer
from idr_dialogs import SettingsDialog, AboutDialog


class WindowUIMixin:
    """Mixin berisi pembangunan UI & handler interaksi.

    Mengasumsikan dipakai bersama idr_window_core.WindowCore yang
    menyediakan atribut seperti self.theme, self.library,
    self.pipeline, self.idr_rate, dst.
    """

    # ── UI Build ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # ── HEADER / NAVBAR ──
        navbar = self._build_navbar()
        root.append(navbar)

        # ── BODY ──
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        body.set_margin_top(8); body.set_margin_bottom(12)
        body.set_margin_start(12); body.set_margin_end(12)

        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # LEFT: Library
        lib_panel = self._build_library_panel()
        lib_panel.set_size_request(240, -1)
        content.append(lib_panel)

        # RIGHT: Currency + Spectrum (collapsible) + Player (fixed bottom)
        right_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        right_col.set_hexpand(True)

        # Currency + Chart card
        currency_card = self._build_currency_card()
        right_col.append(currency_card)

        # Spectrum card (collapsible)
        self._spec_card = self._build_spectrum_card()
        right_col.append(self._spec_card)

        content.append(right_col)
        body.append(content)

        # Track label + Player bar — ALWAYS at fixed position, tidak ikut spectrum
        self.track_lbl = Gtk.Label(label="// tidak ada file yang dipilih")
        self.track_lbl.set_halign(Gtk.Align.CENTER)
        self.track_lbl.add_css_class("track-label")
        self.track_lbl.add_css_class("mono")
        body.append(self.track_lbl)

        player_bar = self._build_player_bar()
        body.append(player_bar)

        root.append(body)
        self.set_child(root)

    def _build_navbar(self):
        """Header bar dengan title, settings, dan theme toggle."""
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bar.set_margin_top(10); bar.set_margin_bottom(8)
        bar.set_margin_start(14); bar.set_margin_end(14)

        # App icon + title
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon_lbl = Gtk.Label(label="♫")
        icon_lbl.add_css_class("mono")
        # buat icon beranimasi saat playing
        self._navbar_icon = icon_lbl
        title_lbl = Gtk.Label(label="IDR SPECTRUM PLAYER")
        title_lbl.add_css_class("section-title")
        title_lbl.add_css_class("mono")
        title_box.append(icon_lbl)
        title_box.append(title_lbl)
        title_box.set_hexpand(True)
        title_box.set_halign(Gtk.Align.START)

        # Settings MenuButton dengan dropdown
        settings_btn = Gtk.MenuButton()
        settings_btn.set_label("⚙")
        settings_btn.add_css_class("icon-btn")
        settings_btn.set_tooltip_text("Menu pengaturan")
        settings_btn.set_focusable(False)
        settings_btn.set_focus_on_click(False)

        popover = Gtk.Popover()
        popover.set_has_arrow(False)
        pop_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        pop_box.set_margin_top(6); pop_box.set_margin_bottom(6)
        pop_box.set_margin_start(4); pop_box.set_margin_end(4)

        def _on_settings_item(_b):
            popover.popdown()
            self._open_settings(None)

        def _on_about_item(_b):
            popover.popdown()
            self._open_about(None)

        settings_item = Gtk.Button(label="⚙   Pengaturan Warna")
        settings_item.add_css_class("flat")
        settings_item.set_halign(Gtk.Align.FILL)
        settings_item.connect("clicked", _on_settings_item)

        about_item = Gtk.Button(label="ℹ   Tentang Aplikasi")
        about_item.add_css_class("flat")
        about_item.set_halign(Gtk.Align.FILL)
        about_item.connect("clicked", _on_about_item)

        pop_box.append(settings_item)
        pop_box.append(about_item)
        popover.set_child(pop_box)
        settings_btn.set_popover(popover)

        # Theme toggle
        self.theme_btn = Gtk.Button(label="☀")
        self.theme_btn.add_css_class("icon-btn")
        self.theme_btn.set_tooltip_text("Ganti tema terang/gelap")
        self.theme_btn.set_focusable(False)
        self.theme_btn.set_focus_on_click(False)
        self.theme_btn.connect("clicked", self._toggle_theme)

        bar.append(title_box)
        bar.append(settings_btn)
        bar.append(self.theme_btn)

        # Separator bawah navbar
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        wrap.append(bar)
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        wrap.append(sep)
        return wrap

    def _build_library_panel(self):
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        panel.add_css_class("card")

        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        lbl = Gtk.Label(label="LIBRARY")
        lbl.add_css_class("section-title")
        lbl.add_css_class("mono")
        lbl.set_hexpand(True)
        lbl.set_halign(Gtk.Align.START)

        self.lib_count_lbl = Gtk.Label(label="0 lagu")
        self.lib_count_lbl.add_css_class("dim")

        hdr.append(lbl)
        hdr.append(self.lib_count_lbl)
        panel.append(hdr)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        panel.append(sep)

        # ── Action buttons — rework: dua baris, lebih visual ──
        # Baris atas: tambah file + tambah folder (full-width look)
        add_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        add_file_btn = Gtk.Button()
        add_file_btn.add_css_class("lib-add-btn")
        add_file_btn.set_focusable(False)
        add_file_btn.set_focus_on_click(False)
        af_inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        af_icon  = Gtk.Label(label="🎵")
        af_label = Gtk.Label(label="Tambah File Musik")
        af_label.set_halign(Gtk.Align.START)
        af_label.set_hexpand(True)
        af_inner.append(af_icon)
        af_inner.append(af_label)
        add_file_btn.set_child(af_inner)
        add_file_btn.set_tooltip_text("Tambah satu atau beberapa file audio")
        add_file_btn.connect("clicked", self._lib_add_file)

        add_folder_btn = Gtk.Button()
        add_folder_btn.add_css_class("lib-add-btn")
        add_folder_btn.set_focusable(False)
        add_folder_btn.set_focus_on_click(False)
        fo_inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fo_icon  = Gtk.Label(label="📂")
        fo_label = Gtk.Label(label="Tambah Folder")
        fo_label.set_halign(Gtk.Align.START)
        fo_label.set_hexpand(True)
        fo_inner.append(fo_icon)
        fo_inner.append(fo_label)
        add_folder_btn.set_child(fo_inner)
        add_folder_btn.set_tooltip_text("Scan seluruh folder secara rekursif")
        add_folder_btn.connect("clicked", self._lib_add_folder)

        add_box.append(add_file_btn)
        add_box.append(add_folder_btn)

        # Baris bawah: clear semua (kecil, di kanan)
        clear_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        clear_row.set_halign(Gtk.Align.END)
        clear_btn = Gtk.Button(label="✕  Hapus Semua")
        clear_btn.add_css_class("lib-clear-btn")
        clear_btn.set_focusable(False)
        clear_btn.set_focus_on_click(False)
        clear_btn.set_tooltip_text("Hapus semua lagu dari library")
        clear_btn.connect("clicked", self._lib_clear)
        clear_row.append(clear_btn)

        panel.append(add_box)
        panel.append(clear_row)

        sep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        panel.append(sep2)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.lib_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        scroll.set_child(self.lib_list)
        panel.append(scroll)

        return panel

    def _build_currency_card(self):
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        card.add_css_class("card")

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left.set_size_request(220, -1)

        sub_lbl = Gtk.Label(label="1 Dolar Amerika Serikat sama dengan")
        sub_lbl.set_halign(Gtk.Align.START)
        sub_lbl.add_css_class("dim")
        sub_lbl.set_wrap(True)

        self.rate_lbl = Gtk.Label()
        self.rate_lbl.set_halign(Gtk.Align.START)
        self.rate_lbl.set_wrap(True)
        self.rate_lbl.add_css_class("rate-display")
        self.rate_lbl.add_css_class("mono")
        self._refresh_rate_lbl()

        src_lbl = Gtk.Label(label="Kenangan Pahit · Keuangan Indonesia")
        src_lbl.set_halign(Gtk.Align.START)
        src_lbl.add_css_class("dim")

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)

        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(8)

        self.usd_entry = Gtk.Entry()
        self.usd_entry.set_text("1")
        self.usd_entry.add_css_class("conv-entry")
        usd_lbl = Gtk.Label(label="USD")
        usd_lbl.add_css_class("dim")
        usd_lbl.set_halign(Gtk.Align.START)

        self.idr_entry = Gtk.Entry()
        self.idr_entry.set_text(f"{self.idr_rate:,.2f}")
        self.idr_entry.add_css_class("conv-entry")
        idr_lbl = Gtk.Label(label="IDR")
        idr_lbl.add_css_class("dim")
        idr_lbl.set_halign(Gtk.Align.START)

        grid.attach(self.usd_entry, 0, 0, 1, 1)
        grid.attach(usd_lbl,       1, 0, 1, 1)
        grid.attach(self.idr_entry, 0, 1, 1, 1)
        grid.attach(idr_lbl,       1, 1, 1, 1)

        self.usd_entry.connect("changed", self._usd_changed)
        self.idr_entry.connect("changed", self._idr_changed)

        sarcs = Gtk.Label(label="Kejatuhan Mata Uang Rupiah Terparah Sepanjang Sejarah")
        sarcs.set_halign(Gtk.Align.START)
        sarcs.add_css_class("sarcasm-tag")
        sarcs.set_wrap(True)

        for w in (sub_lbl, self.rate_lbl, src_lbl, sep, grid, sarcs):
            left.append(w)

        self.chart = IDRChart(self.theme)

        chart_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        tab_row   = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        tab_row.set_halign(Gtk.Align.END)
        for lbl_t in ("1DTK", "1HR", "5HR", "1BLN", "1TH", "5TH", "Maks"):
            b = Gtk.Button(label=lbl_t)
            b.add_css_class("tab-pill")
            if lbl_t == "1DTK":
                b.add_css_class("active")
            tab_row.append(b)

        chart_box.append(tab_row)
        chart_box.append(self.chart)
        chart_box.set_hexpand(True)

        card.append(left)
        card.append(chart_box)
        return card

    def _build_spectrum_card(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.add_css_class("card")

        # Header row — HANYA label + view tabs + toggle icon
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        spec_lbl = Gtk.Label(label="SPEKTRUM")
        spec_lbl.add_css_class("section-title")
        spec_lbl.add_css_class("mono")
        spec_lbl.set_hexpand(True)
        spec_lbl.set_halign(Gtk.Align.START)

        # View mode tabs
        tab_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self._view_btns = {}
        for mode in ("BASS", "MID", "FULL", "WAVE", "MAKS"):
            b = Gtk.Button(label=mode)
            b.add_css_class("tab-pill")
            b.set_focusable(False)
            b.set_focus_on_click(False)
            if mode == "FULL":
                b.add_css_class("active")
            b.connect("clicked", self._switch_view, mode)
            tab_row.append(b)
            self._view_btns[mode] = b

        # Toggle spektrum — ICON saja, bukan teks panjang
        self.hide_spec_btn = Gtk.Button(label="⊟")
        self.hide_spec_btn.add_css_class("icon-btn")
        self.hide_spec_btn.set_tooltip_text("Tampilkan/Sembunyikan spektrum  [H]")
        self.hide_spec_btn.set_focusable(False)
        self.hide_spec_btn.set_focus_on_click(False)
        self.hide_spec_btn.connect("clicked", self._toggle_spectrum)

        hdr.append(spec_lbl)
        hdr.append(tab_row)
        hdr.append(self.hide_spec_btn)
        card.append(hdr)

        # Visualizer — hanya ini yang disembunyikan, bukan card-nya
        self.viz = SpectrumVisualizer(self.theme)
        self._viz_revealer = Gtk.Revealer()
        self._viz_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self._viz_revealer.set_transition_duration(200)
        self._viz_revealer.set_reveal_child(True)
        self._viz_revealer.set_child(self.viz)
        card.append(self._viz_revealer)

        return card

    def _build_player_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        bar.add_css_class("player-bar")

        ctrl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # ── Album Art / Music Icon ──
        self._album_art = Gtk.DrawingArea()
        self._album_art.set_size_request(44, 44)
        self._album_art.set_draw_func(self._draw_album_art)
        self._album_art_pixbuf = None  # None = pakai default SVG
        ctrl.append(self._album_art)

        def _nb(btn):
            # Non-focusable button — klik tidak steal keyboard focus.
            btn.set_focusable(False)
            btn.set_focus_on_click(False)
            return btn

        open_btn = _nb(Gtk.Button(label="☰"))
        open_btn.add_css_class("ctrl-btn")
        open_btn.set_tooltip_text("Buka file musik  [Ctrl+O]")
        open_btn.connect("clicked", self._open_file)

        self.prev_btn = _nb(Gtk.Button(label="⏮"))
        self.prev_btn.add_css_class("ctrl-btn")
        self.prev_btn.set_tooltip_text("Lagu sebelumnya  [Ctrl+←]")
        self.prev_btn.connect("clicked", self._prev_track)

        self.play_btn = _nb(Gtk.Button(label="▶"))
        self.play_btn.add_css_class("play-btn")
        self.play_btn.set_sensitive(False)
        self.play_btn.set_tooltip_text("Play / Pause  [Space]")
        self.play_btn.connect("clicked", self._play_pause)

        self.next_btn = _nb(Gtk.Button(label="⏭"))
        self.next_btn.add_css_class("ctrl-btn")
        self.next_btn.set_tooltip_text("Lagu berikutnya  [Ctrl+→]")
        self.next_btn.connect("clicked", self._next_track)

        self.shuffle_btn = _nb(Gtk.Button(label="⇄"))
        self.shuffle_btn.add_css_class("ctrl-btn")
        self.shuffle_btn.set_tooltip_text("Shuffle  [S]")
        self.shuffle_btn.connect("clicked", self._toggle_shuffle)

        self.repeat_btn = _nb(Gtk.Button(label="↺"))
        self.repeat_btn.add_css_class("ctrl-btn")
        self.repeat_btn.set_tooltip_text("Repeat  [R]")
        self.repeat_btn.connect("clicked", self._toggle_repeat)

        self.seek_bar = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        self.seek_bar.set_range(0, 100)
        self.seek_bar.set_draw_value(False)
        self.seek_bar.set_hexpand(True)
        self.seek_bar.set_focusable(False)
        self.seek_bar.set_focus_on_click(False)
        self.seek_bar.set_tooltip_text("Posisi lagu  [← / → untuk ±5 detik]")
        self.seek_bar.connect("change-value", self._on_seek)

        self.time_lbl = Gtk.Label(label="0:00 / 0:00")
        self.time_lbl.set_width_chars(13)
        self.time_lbl.add_css_class("dim")
        self.time_lbl.add_css_class("mono")

        vol_lbl = Gtk.Label(label="Vol")
        vol_lbl.add_css_class("dim")
        self.vol_bar = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        self.vol_bar.set_range(0, 1)
        self.vol_bar.set_value(1.0)
        self.vol_bar.set_draw_value(False)
        self.vol_bar.set_size_request(70, -1)
        self.vol_bar.set_focusable(False)
        self.vol_bar.set_focus_on_click(False)
        self.vol_bar.set_tooltip_text("Volume  [Ctrl+↑ / Ctrl+↓]")
        self.vol_bar.connect("value-changed", self._on_vol)

        for w in (open_btn, self.prev_btn, self.play_btn, self.next_btn,
                  self.shuffle_btn, self.repeat_btn,
                  self.seek_bar, self.time_lbl, vol_lbl, self.vol_bar):
            ctrl.append(w)

        bar.append(ctrl)
        return bar

    def _draw_album_art(self, _w, cr, width, height):
        """Gambar album art atau default music icon."""
        import math as _m
        r = min(width, height) / 2
        cx, cy = width / 2, height / 2

        if self._album_art_pixbuf is not None:
            # Album art dari metadata — tampilkan sebagai kotak (bukan lingkaran)
            from gi.repository import GdkPixbuf
            pb = self._album_art_pixbuf
            scale = min(width / pb.get_width(), height / pb.get_height())
            sw = pb.get_width() * scale
            sh = pb.get_height() * scale
            ox = (width - sw) / 2
            oy = (height - sh) / 2
            cr.save()
            # Clip kotak dengan sudut sedikit rounded
            radius = 4.0
            cr.new_sub_path()
            cr.arc(radius, radius, radius, _m.pi, 3 * _m.pi / 2)
            cr.arc(width - radius, radius, radius, 3 * _m.pi / 2, 0)
            cr.arc(width - radius, height - radius, radius, 0, _m.pi / 2)
            cr.arc(radius, height - radius, radius, _m.pi / 2, _m.pi)
            cr.close_path()
            cr.clip()
            cr.scale(scale, scale)
            from gi.repository import Gdk
            Gdk.cairo_set_source_pixbuf(cr, pb, ox / scale, oy / scale)
            cr.paint()
            cr.restore()
            # Border tipis kotak
            cr.set_source_rgba(1, 1, 1, 0.12)
            cr.set_line_width(1.0)
            cr.new_sub_path()
            cr.arc(radius, radius, radius, _m.pi, 3 * _m.pi / 2)
            cr.arc(width - radius, radius, radius, 3 * _m.pi / 2, 0)
            cr.arc(width - radius, height - radius, radius, 0, _m.pi / 2)
            cr.arc(radius, height - radius, radius, _m.pi / 2, _m.pi)
            cr.close_path()
            cr.stroke()
        else:
            # Default music icon — vinyl disc style
            t = self.theme
            # Outer disc
            cr.arc(cx, cy, r - 1, 0, 2 * _m.pi)
            cr.set_source_rgb(0.10, 0.11, 0.13)
            cr.fill()
            # Grooves
            for ri in [r * 0.85, r * 0.70, r * 0.55]:
                cr.arc(cx, cy, ri, 0, 2 * _m.pi)
                cr.set_source_rgba(1, 1, 1, 0.04)
                cr.set_line_width(1)
                cr.stroke()
            # Center label
            cr.arc(cx, cy, r * 0.38, 0, 2 * _m.pi)
            if self.is_dark:
                cr.set_source_rgb(0.11, 0.18, 0.38)
            else:
                cr.set_source_rgb(0.18, 0.31, 0.72)
            cr.fill()
            # Center dot
            cr.arc(cx, cy, r * 0.10, 0, 2 * _m.pi)
            cr.set_source_rgb(0.06, 0.06, 0.07)
            cr.fill()
            # Music note
            cr.set_source_rgba(0.48, 0.67, 1.0, 0.85)
            cr.set_font_size(r * 0.40)
            cr.select_font_face("sans-serif", 0, 0)
            ext = cr.text_extents("♫")
            cr.move_to(cx - ext.width / 2 - ext.x_bearing,
                       cy - ext.height / 2 - ext.y_bearing)
            cr.show_text("♫")
            # Border ring
            cr.arc(cx, cy, r - 1, 0, 2 * _m.pi)
            cr.set_source_rgba(1, 1, 1, 0.08)
            cr.set_line_width(1.5)
            cr.stroke()

    def _update_album_art(self, idx: int):
        """Load album art untuk track idx, update DrawingArea."""
        from gi.repository import GdkPixbuf, GLib as _GL
        self._album_art_pixbuf = None
        raw = self.library.get_cover_bytes(idx)
        if raw:
            try:
                loader = GdkPixbuf.PixbufLoader()
                loader.write(raw)
                loader.close()
                pb = loader.get_pixbuf()
                if pb:
                    self._album_art_pixbuf = pb
            except Exception:
                pass
        self._album_art.queue_draw()

    # ── Library Actions ───────────────────────────────────────────────────────
    def _lib_add_file(self, _btn):
        dialog = Gtk.FileChooserDialog(
            title="Pilih File Musik",
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.set_transient_for(self)
        dialog.set_select_multiple(True)
        dialog.add_button("Batal",    Gtk.ResponseType.CANCEL)
        dialog.add_button("▶  Tambah", Gtk.ResponseType.ACCEPT)

        af = Gtk.FileFilter()
        af.set_name("File Audio")
        for ext in AUDIO_EXTS:
            af.add_pattern(f"*{ext}")
        dialog.add_filter(af)
        dialog.connect("response", self._files_chosen)
        dialog.present()

    def _files_chosen(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            files = dialog.get_files()
            for f in files:
                self.library.add(f.get_path())
            self._refresh_library_ui()
            save_config(self._build_current_config())
        dialog.destroy()

    def _lib_add_folder(self, _btn):
        dialog = Gtk.FileChooserDialog(
            title="Pilih Folder Musik",
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.set_transient_for(self)
        dialog.add_button("Batal",   Gtk.ResponseType.CANCEL)
        dialog.add_button("Tambah",  Gtk.ResponseType.ACCEPT)
        dialog.connect("response", self._folder_chosen)
        dialog.present()

    def _folder_chosen(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            folder = dialog.get_file().get_path()
            self.library.add_folder(folder)
            self._refresh_library_ui()
            save_config(self._build_current_config())
        dialog.destroy()

    def _lib_clear(self, _btn):
        self.library.clear()
        self.current_idx = -1
        self._refresh_library_ui()
        save_config(self._build_current_config())

    def _refresh_library_ui(self):
        child = self.lib_list.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.lib_list.remove(child)
            child = nxt

        for i, path in enumerate(self.library.tracks):
            row = self._make_lib_row(i, path)
            self.lib_list.append(row)

        self.lib_count_lbl.set_text(f"{len(self.library)} lagu")

    def _make_lib_row(self, idx: int, path: str):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.add_css_class("lib-row")
        if idx == self.current_idx:
            row.add_css_class("lib-row-active")

        num = Gtk.Label(label=f"{idx+1:02d}")
        num.add_css_class("lib-num")

        name = Gtk.Label(label=os.path.basename(path))
        name.add_css_class("lib-name")
        name.set_halign(Gtk.Align.START)
        name.set_hexpand(True)
        name.set_ellipsize(3)

        del_btn = Gtk.Button(label="✕")
        del_btn.add_css_class("ctrl-btn")
        del_btn.set_focusable(False)
        del_btn.set_focus_on_click(False)
        del_btn.connect("clicked", self._lib_remove, idx)

        row.append(num)
        row.append(name)
        row.append(del_btn)

        gesture = Gtk.GestureClick()
        gesture.connect("released", self._lib_row_clicked, idx)
        row.add_controller(gesture)

        return row

    def _lib_row_clicked(self, _gesture, _n, _x, _y, idx):
        self._play_index(idx)

    def _lib_remove(self, _btn, idx):
        self.library.remove(idx)
        if idx == self.current_idx:
            self.current_idx = -1
        elif idx < self.current_idx:
            self.current_idx -= 1
        self._refresh_library_ui()
        save_config(self._build_current_config())

    # ── Playback ──────────────────────────────────────────────────────────────
    def _play_index(self, idx: int):
        if idx < 0 or idx >= len(self.library):
            return
        self.current_idx = idx
        path = self.library.tracks[idx]
        self._load(path)
        self._do_play()
        self._refresh_library_ui()
        self._update_album_art(idx)
        save_config(self._build_current_config())

    def _prev_track(self, _btn=None):
        n = len(self.library)
        if n == 0: return
        idx = (self.current_idx - 1) % n
        self._play_index(idx)

    def _next_track(self, _btn=None):
        n = len(self.library)
        if n == 0: return
        if self.shuffle:
            idx = random.randint(0, n - 1)
        else:
            idx = (self.current_idx + 1) % n
        self._play_index(idx)

    def _toggle_shuffle(self, _btn):
        self.shuffle = not self.shuffle
        if self.shuffle:
            self.shuffle_btn.add_css_class("active")
        else:
            self.shuffle_btn.remove_css_class("active")
        save_config(self._build_current_config())

    def _toggle_repeat(self, _btn):
        modes  = ["none", "all", "one"]
        labels = {"none": "↺", "all": "↺↺", "one": "①"}
        self.repeat_mode = modes[(modes.index(self.repeat_mode) + 1) % 3]
        self.repeat_btn.set_label(labels[self.repeat_mode])
        if self.repeat_mode != "none":
            self.repeat_btn.add_css_class("active")
        else:
            self.repeat_btn.remove_css_class("active")
        save_config(self._build_current_config())

    def _toggle_spectrum(self, _btn):
        self.spec_visible = not self.spec_visible
        self._viz_revealer.set_reveal_child(self.spec_visible)
        if self.spec_visible:
            self.hide_spec_btn.set_label("⊟")
            self.hide_spec_btn.set_tooltip_text("Sembunyikan spektrum")
            self.hide_spec_btn.remove_css_class("active")
        else:
            self.hide_spec_btn.set_label("⊞")
            self.hide_spec_btn.set_tooltip_text("Tampilkan spektrum")
            self.hide_spec_btn.add_css_class("active")
        save_config(self._build_current_config())

    def _toggle_theme(self, _btn):
        self.is_dark = not self.is_dark
        self.theme = DARK_THEME if self.is_dark else LIGHT_THEME
        self.theme_btn.set_label("☀" if self.is_dark else "☾")
        self.theme_btn.set_tooltip_text("Ganti ke Light" if self.is_dark else "Ganti ke Dark")
        self._reload_css()
        save_config(self._build_current_config())

    def _open_settings(self, _btn):
        dlg = SettingsDialog(
            self,
            self._spec_color,
            self._chart_color,
            self._on_spec_color_changed,
            self._on_chart_color_changed,
        )
        dlg.present()

    def _open_about(self, _btn):
        dlg = AboutDialog(self)
        dlg.present()

    def _on_spec_color_changed(self, name: str):
        self._spec_color = name
        self.viz.color_preset = name
        self.viz.queue_draw()
        save_config(self._build_current_config())

    def _on_chart_color_changed(self, name: str):
        self._chart_color = name
        self.chart.color_preset = name
        self.chart.queue_draw()
        save_config(self._build_current_config())

    def _load(self, path: str):
        self.current_file = path
        self.pipeline.set_state(Gst.State.NULL)
        # GStreamer filesrc di Windows tidak toleran backslash — gunakan URI
        # Gst.filename_to_uri() menangani path Windows maupun POSIX dengan benar
        try:
            uri = Gst.filename_to_uri(path)
        except Exception:
            uri = Path(path).as_uri()
        self.src.set_property("location", uri)
        self.pipeline.set_state(Gst.State.PAUSED)
        self.is_playing = False
        self.play_btn.set_label("▶")
        self.play_btn.set_sensitive(True)
        fname = os.path.basename(path)
        self.track_lbl.set_text(f"// {fname}")
        # Update window title — muncul di taskbar
        self.set_title(f"♫ {os.path.splitext(fname)[0]} — IDR Spectrum")
        self.duration_ns = 0
        GLib.timeout_add(300, self._query_duration)

    def _do_play(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        self.is_playing = True
        self.play_btn.set_label("⏸")
        GLib.timeout_add(400, self._query_duration)

    def _play_pause(self, _btn):
        if self.is_playing:
            self.pipeline.set_state(Gst.State.PAUSED)
            self.is_playing = False
            self.play_btn.set_label("▶")
        else:
            if self.current_file:
                self.pipeline.set_state(Gst.State.PLAYING)
                self.is_playing = True
                self.play_btn.set_label("⏸")
                GLib.timeout_add(400, self._query_duration)

    def _open_file(self, _btn):
        dialog = Gtk.FileChooserDialog(
            title="Pilih File Musik",
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.set_transient_for(self)
        dialog.add_button("Batal",     Gtk.ResponseType.CANCEL)
        dialog.add_button("▶  Buka",  Gtk.ResponseType.ACCEPT)

        af = Gtk.FileFilter()
        af.set_name("File Audio")
        for ext in AUDIO_EXTS:
            af.add_pattern(f"*{ext}")
        dialog.add_filter(af)
        dialog.connect("response", self._single_file_chosen)
        dialog.present()

    def _single_file_chosen(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            path = dialog.get_file().get_path()
            self.library.add(path)
            idx = self.library.tracks.index(path)
            self._refresh_library_ui()
            self._play_index(idx)
            save_config(self._build_current_config())
        dialog.destroy()

    def _on_seek(self, _scale, _scroll_type, value):
        if self._upd_pos: return False
        if self.duration_ns > 0:
            pos = int(value / 100 * self.duration_ns)
            self.pipeline.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                pos,
            )
        return False

    def _on_vol(self, scale):
        self.volume_el.set_property("volume", scale.get_value())

    def _switch_view(self, _btn, mode: str):
        for m, b in self._view_btns.items():
            b.remove_css_class("active")
        self._view_btns[mode].add_css_class("active")
        self.viz.view_mode = mode
        self.viz.queue_draw()

    # ── Currency Helpers ──────────────────────────────────────────────────────
    def _refresh_rate_lbl(self):
        self.rate_lbl.set_text(f"Rp{self.idr_rate:,.2f}\nRupiah Indonesia")

    @staticmethod
    def _pf(s: str) -> float:
        return float(s.replace(",", "").strip() or "0")

    def _usd_changed(self, entry):
        try:
            result = self._pf(entry.get_text()) * self.idr_rate
            self.idr_entry.handler_block_by_func(self._idr_changed)
            self.idr_entry.set_text(f"{result:,.2f}")
            self.idr_entry.handler_unblock_by_func(self._idr_changed)
        except ValueError:
            pass

    def _idr_changed(self, entry):
        try:
            result = self._pf(entry.get_text()) / self.idr_rate
            self.usd_entry.handler_block_by_func(self._usd_changed)
            self.usd_entry.set_text(f"{result:,.4f}")
            self.usd_entry.handler_unblock_by_func(self._usd_changed)
        except ValueError:
            pass

