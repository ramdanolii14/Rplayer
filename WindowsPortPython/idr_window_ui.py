#!/usr/bin/env python3
# ============================================================
#  idr_window_ui.py  —  IDR Spectrum Player  (UI Rewrite v2)
#
#  Perubahan dari v1:
#   • Layout 3-kolom (lib | chart+spectrum | album) untuk
#     menghindari overlap dan resize yang aneh.
#   • Custom titlebar lewat Gtk.HeaderBar dengan semua
#     elemen kontrol di dalam GTK — tidak bergantung pada
#     dekorasi Windows agar dark mode tidak bocor.
#   • Semua widget pakai CSS class yang sangat eksplisit;
#     tidak ada widget yang bergantung pada default GTK theme.
#   • Spectrum card dan chart card digabung agar height
#     konsisten dan tidak ada gap kosong.
#   • Player bar di bawah, full-width, dengan album art
#     terintegrasi di dalam bar (bukan floating).
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
    """Mixin UI — harus dipakai bersama WindowCore."""

    # ═══════════════════════════════════════════════════════════
    #  ROOT BUILD
    # ═══════════════════════════════════════════════════════════
    def _build_ui(self):
        # Pakai custom HeaderBar agar titlebar ikut dark mode
        self._build_headerbar()

        # Root vertical box
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Body: 2 kolom (lib | main)
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        body.set_vexpand(True)

        # ── Kolom Kiri: Library ──────────────────────────────────────────────
        lib_panel = self._build_library_panel()
        lib_panel.set_size_request(260, -1)
        body.append(lib_panel)

        # Divider vertikal
        vsep = Gtk.Box()
        vsep.set_size_request(1, -1)
        vsep.add_css_class("vsep")
        body.append(vsep)

        # ── Kolom Kanan: Chart + Spectrum ────────────────────────────────────
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        right.set_hexpand(True)
        right.set_vexpand(True)

        right.append(self._build_currency_panel())

        hsep = Gtk.Box()
        hsep.set_size_request(-1, 1)
        hsep.add_css_class("hsep")
        right.append(hsep)

        right.append(self._build_spectrum_panel())

        body.append(right)
        root.append(body)

        # ── Player Bar ───────────────────────────────────────────────────────
        root.append(self._build_player_bar())

        self.set_child(root)

    # ═══════════════════════════════════════════════════════════
    #  CUSTOM HEADER BAR
    # ═══════════════════════════════════════════════════════════
    def _build_headerbar(self):
        hb = Gtk.HeaderBar()
        hb.set_show_title_buttons(True)
        hb.add_css_class("app-header")

        # Title kiri
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon_lbl = Gtk.Label(label="♫")
        icon_lbl.add_css_class("header-icon")
        self._navbar_icon = icon_lbl
        title_lbl = Gtk.Label(label="IDR SPECTRUM PLAYER")
        title_lbl.add_css_class("header-title")
        title_box.append(icon_lbl)
        title_box.append(title_lbl)
        hb.set_title_widget(title_box)

        def _nb(btn):
            btn.set_focusable(False)
            btn.set_focus_on_click(False)
            return btn

        # Settings button (buka popover)
        settings_btn = Gtk.MenuButton()
        settings_btn.set_label("⚙")
        settings_btn.add_css_class("hdr-btn")
        settings_btn.set_tooltip_text("Pengaturan")
        settings_btn.set_focusable(False)
        settings_btn.set_focus_on_click(False)

        pop = Gtk.Popover()
        pop.set_has_arrow(False)
        pop_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        pop_box.set_margin_top(6); pop_box.set_margin_bottom(6)
        pop_box.set_margin_start(4); pop_box.set_margin_end(4)

        def _settings_click(_b):
            pop.popdown()
            self._open_settings(None)

        def _about_click(_b):
            pop.popdown()
            self._open_about(None)

        for lbl, cb in [("⚙   Pengaturan Warna", _settings_click),
                         ("ℹ   Tentang Aplikasi",  _about_click)]:
            btn = Gtk.Button(label=lbl)
            btn.add_css_class("pop-item")
            btn.set_halign(Gtk.Align.FILL)
            btn.connect("clicked", cb)
            pop_box.append(btn)

        pop.set_child(pop_box)
        settings_btn.set_popover(pop)

        # Theme toggle
        self.theme_btn = _nb(Gtk.Button(label="☀"))
        self.theme_btn.add_css_class("hdr-btn")
        self.theme_btn.set_tooltip_text("Ganti tema [Dark/Light]")
        self.theme_btn.connect("clicked", self._toggle_theme)

        hb.pack_end(self.theme_btn)
        hb.pack_end(settings_btn)

        self.set_titlebar(hb)

    # ═══════════════════════════════════════════════════════════
    #  LIBRARY PANEL (kiri)
    # ═══════════════════════════════════════════════════════════
    def _build_library_panel(self):
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        panel.add_css_class("lib-panel")

        # ── Header ──────────────────────────────────────────────────────────
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        hdr.add_css_class("lib-header")
        hdr.set_margin_start(14); hdr.set_margin_end(10)
        hdr.set_margin_top(10); hdr.set_margin_bottom(10)

        lbl = Gtk.Label(label="LIBRARY")
        lbl.add_css_class("section-cap")
        lbl.set_hexpand(True)
        lbl.set_halign(Gtk.Align.START)

        self.lib_count_lbl = Gtk.Label(label="0 lagu")
        self.lib_count_lbl.add_css_class("muted-lbl")

        hdr.append(lbl)
        hdr.append(self.lib_count_lbl)
        panel.append(hdr)

        sep = Gtk.Box(); sep.add_css_class("hsep"); sep.set_size_request(-1, 1)
        panel.append(sep)

        # ── Add Buttons ──────────────────────────────────────────────────────
        btn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        btn_box.set_margin_start(10); btn_box.set_margin_end(10)
        btn_box.set_margin_top(8); btn_box.set_margin_bottom(4)

        add_file_btn = self._lib_action_btn("🎵", "Tambah File Musik",
                                             self._lib_add_file)
        add_folder_btn = self._lib_action_btn("📂", "Tambah Folder",
                                               self._lib_add_folder)
        btn_box.append(add_file_btn)
        btn_box.append(add_folder_btn)

        # Clear row
        clear_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        clear_row.set_margin_top(2)
        clear_btn = Gtk.Button(label="✕  Hapus Semua")
        clear_btn.add_css_class("clear-btn")
        clear_btn.set_focusable(False)
        clear_btn.set_focus_on_click(False)
        clear_btn.set_halign(Gtk.Align.END)
        clear_btn.set_hexpand(True)
        clear_btn.connect("clicked", self._lib_clear)
        clear_row.append(clear_btn)
        btn_box.append(clear_row)

        panel.append(btn_box)

        sep2 = Gtk.Box(); sep2.add_css_class("hsep"); sep2.set_size_request(-1, 1)
        panel.append(sep2)

        # ── Scrollable Track List ────────────────────────────────────────────
        scroll = Gtk.ScrolledWindow()
        scroll.add_css_class("lib-scroll")
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.lib_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.lib_list.add_css_class("lib-list-inner")
        self.lib_list.set_margin_start(8); self.lib_list.set_margin_end(8)
        self.lib_list.set_margin_top(6); self.lib_list.set_margin_bottom(6)

        scroll.set_child(self.lib_list)
        panel.append(scroll)

        return panel

    def _lib_action_btn(self, icon, text, callback):
        btn = Gtk.Button()
        btn.add_css_class("lib-add-btn")
        btn.set_focusable(False)
        btn.set_focus_on_click(False)

        inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        inner.set_margin_start(4); inner.set_margin_end(4)
        ic = Gtk.Label(label=icon)
        tx = Gtk.Label(label=text)
        tx.set_halign(Gtk.Align.START)
        tx.set_hexpand(True)
        inner.append(ic)
        inner.append(tx)
        btn.set_child(inner)
        btn.connect("clicked", callback)
        return btn

    # ═══════════════════════════════════════════════════════════
    #  CURRENCY PANEL (kanan atas)
    # ═══════════════════════════════════════════════════════════
    def _build_currency_panel(self):
        panel = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        panel.add_css_class("currency-panel")

        # ── Info kiri ───────────────────────────────────────────────────────
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        info.add_css_class("currency-info")
        info.set_margin_start(18); info.set_margin_end(14)
        info.set_margin_top(14); info.set_margin_bottom(14)
        info.set_size_request(230, -1)

        sub = Gtk.Label(label="1 Dolar Amerika Serikat sama dengan")
        sub.add_css_class("muted-lbl")
        sub.set_halign(Gtk.Align.START)
        sub.set_wrap(True)

        self.rate_lbl = Gtk.Label()
        self.rate_lbl.add_css_class("rate-big")
        self.rate_lbl.set_halign(Gtk.Align.START)
        self.rate_lbl.set_wrap(True)
        self._refresh_rate_lbl()

        src = Gtk.Label(label="Kenangan Pahit · Keuangan Indonesia")
        src.add_css_class("muted-lbl")
        src.set_halign(Gtk.Align.START)

        hsep = Gtk.Box(); hsep.add_css_class("hsep"); hsep.set_size_request(-1, 1)

        # Konverter
        conv = Gtk.Grid()
        conv.set_row_spacing(6)
        conv.set_column_spacing(10)

        self.usd_entry = Gtk.Entry()
        self.usd_entry.set_text("1")
        self.usd_entry.add_css_class("conv-entry")
        usd_lbl = Gtk.Label(label="USD")
        usd_lbl.add_css_class("unit-lbl")
        usd_lbl.set_halign(Gtk.Align.START)

        self.idr_entry = Gtk.Entry()
        self.idr_entry.set_text(f"{self.idr_rate:,.2f}")
        self.idr_entry.add_css_class("conv-entry")
        idr_lbl = Gtk.Label(label="IDR")
        idr_lbl.add_css_class("unit-lbl")
        idr_lbl.set_halign(Gtk.Align.START)

        conv.attach(self.usd_entry, 0, 0, 1, 1)
        conv.attach(usd_lbl,       1, 0, 1, 1)
        conv.attach(self.idr_entry, 0, 1, 1, 1)
        conv.attach(idr_lbl,       1, 1, 1, 1)

        self.usd_entry.connect("changed", self._usd_changed)
        self.idr_entry.connect("changed", self._idr_changed)

        sarcs = Gtk.Label(label="Kejatuhan Mata Uang Rupiah Terparah Sepanjang Sejarah")
        sarcs.add_css_class("sarcs-lbl")
        sarcs.set_halign(Gtk.Align.START)
        sarcs.set_wrap(True)

        for w in (sub, self.rate_lbl, src, hsep, conv, sarcs):
            info.append(w)

        # ── Chart kanan ─────────────────────────────────────────────────────
        chart_side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        chart_side.add_css_class("chart-side")
        chart_side.set_hexpand(True)
        chart_side.set_margin_top(12); chart_side.set_margin_bottom(10)
        chart_side.set_margin_end(14)

        # Time range tabs
        tab_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        tab_row.set_halign(Gtk.Align.END)
        for t in ("1DTK", "1HR", "5HR", "1BLN", "1TH", "5TH", "Maks"):
            b = Gtk.Button(label=t)
            b.add_css_class("time-tab")
            if t == "1DTK":
                b.add_css_class("active")
            b.set_focusable(False)
            b.set_focus_on_click(False)
            tab_row.append(b)

        self.chart = IDRChart(self.theme)
        self.chart.set_vexpand(True)

        chart_side.append(tab_row)
        chart_side.append(self.chart)

        vsep = Gtk.Box(); vsep.add_css_class("vsep"); vsep.set_size_request(1, -1)

        panel.append(info)
        panel.append(vsep)
        panel.append(chart_side)

        return panel

    # ═══════════════════════════════════════════════════════════
    #  SPECTRUM PANEL (kanan bawah)
    # ═══════════════════════════════════════════════════════════
    def _build_spectrum_panel(self):
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        panel.add_css_class("spec-panel")
        panel.set_vexpand(True)

        # Header
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hdr.add_css_class("spec-header")
        hdr.set_margin_start(14); hdr.set_margin_end(10)
        hdr.set_margin_top(8); hdr.set_margin_bottom(8)

        spec_lbl = Gtk.Label(label="SPEKTRUM")
        spec_lbl.add_css_class("section-cap")
        spec_lbl.set_hexpand(True)
        spec_lbl.set_halign(Gtk.Align.START)

        # View mode tabs
        tab_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self._view_btns = {}
        for mode in ("BASS", "MID", "FULL", "WAVE", "MAKS"):
            b = Gtk.Button(label=mode)
            b.add_css_class("view-tab")
            b.set_focusable(False)
            b.set_focus_on_click(False)
            if mode == "FULL":
                b.add_css_class("active")
            b.connect("clicked", self._switch_view, mode)
            tab_row.append(b)
            self._view_btns[mode] = b

        self.hide_spec_btn = Gtk.Button(label="⊟")
        self.hide_spec_btn.add_css_class("icon-pill")
        self.hide_spec_btn.set_tooltip_text("Tampilkan/Sembunyikan spektrum  [H]")
        self.hide_spec_btn.set_focusable(False)
        self.hide_spec_btn.set_focus_on_click(False)
        self.hide_spec_btn.connect("clicked", self._toggle_spectrum)

        hdr.append(spec_lbl)
        hdr.append(tab_row)
        hdr.append(self.hide_spec_btn)
        panel.append(hdr)

        hsep = Gtk.Box(); hsep.add_css_class("hsep"); hsep.set_size_request(-1, 1)
        panel.append(hsep)

        # Visualizer dengan revealer
        self.viz = SpectrumVisualizer(self.theme)
        self.viz.set_vexpand(True)
        self.viz.set_margin_start(6); self.viz.set_margin_end(6)
        self.viz.set_margin_top(6); self.viz.set_margin_bottom(4)

        self._viz_revealer = Gtk.Revealer()
        self._viz_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self._viz_revealer.set_transition_duration(200)
        self._viz_revealer.set_reveal_child(True)
        self._viz_revealer.set_vexpand(True)
        self._viz_revealer.set_child(self.viz)
        panel.append(self._viz_revealer)

        return panel

    # ═══════════════════════════════════════════════════════════
    #  PLAYER BAR (bawah, full-width)
    # ═══════════════════════════════════════════════════════════
    def _build_player_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        bar.add_css_class("player-bar")

        # ── Track info row ───────────────────────────────────────────────────
        track_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        track_row.set_margin_start(14); track_row.set_margin_end(14)
        track_row.set_margin_top(8)

        # Album art
        self._album_art = Gtk.DrawingArea()
        self._album_art.set_size_request(42, 42)
        self._album_art.set_draw_func(self._draw_album_art)
        self._album_art_pixbuf = None
        track_row.append(self._album_art)

        # Track label
        self.track_lbl = Gtk.Label(label="// tidak ada file yang dipilih")
        self.track_lbl.add_css_class("track-label")
        self.track_lbl.set_halign(Gtk.Align.START)
        self.track_lbl.set_hexpand(True)
        self.track_lbl.set_ellipsize(3)
        track_row.append(self.track_lbl)

        bar.append(track_row)

        # ── Seek row ─────────────────────────────────────────────────────────
        seek_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        seek_row.set_margin_start(14); seek_row.set_margin_end(14)
        seek_row.set_margin_top(6)

        self.seek_bar = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        self.seek_bar.set_range(0, 100)
        self.seek_bar.set_draw_value(False)
        self.seek_bar.set_hexpand(True)
        self.seek_bar.set_focusable(False)
        self.seek_bar.set_focus_on_click(False)
        self.seek_bar.set_tooltip_text("Posisi lagu  [← / → untuk ±5 detik]")
        self.seek_bar.add_css_class("seek-scale")
        self.seek_bar.connect("change-value", self._on_seek)

        self.time_lbl = Gtk.Label(label="0:00 / 0:00")
        self.time_lbl.set_width_chars(13)
        self.time_lbl.add_css_class("time-lbl")

        seek_row.append(self.seek_bar)
        seek_row.append(self.time_lbl)
        bar.append(seek_row)

        # ── Controls row ──────────────────────────────────────────────────────
        ctrl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        ctrl.set_margin_start(14); ctrl.set_margin_end(14)
        ctrl.set_margin_top(6); ctrl.set_margin_bottom(10)

        def _nb(btn):
            btn.set_focusable(False)
            btn.set_focus_on_click(False)
            return btn

        open_btn = _nb(Gtk.Button(label="☰"))
        open_btn.add_css_class("ctrl-btn")
        open_btn.set_tooltip_text("Buka file  [Ctrl+O]")
        open_btn.connect("clicked", self._open_file)

        self.prev_btn = _nb(Gtk.Button(label="⏮"))
        self.prev_btn.add_css_class("ctrl-btn")
        self.prev_btn.set_tooltip_text("Sebelumnya  [Ctrl+←]")
        self.prev_btn.connect("clicked", self._prev_track)

        self.play_btn = _nb(Gtk.Button(label="▶"))
        self.play_btn.add_css_class("play-btn")
        self.play_btn.set_sensitive(False)
        self.play_btn.set_tooltip_text("Play / Pause  [Space]")
        self.play_btn.connect("clicked", self._play_pause)

        self.next_btn = _nb(Gtk.Button(label="⏭"))
        self.next_btn.add_css_class("ctrl-btn")
        self.next_btn.set_tooltip_text("Berikutnya  [Ctrl+→]")
        self.next_btn.connect("clicked", self._next_track)

        self.shuffle_btn = _nb(Gtk.Button(label="⇄"))
        self.shuffle_btn.add_css_class("ctrl-btn")
        self.shuffle_btn.set_tooltip_text("Shuffle  [S]")
        self.shuffle_btn.connect("clicked", self._toggle_shuffle)

        self.repeat_btn = _nb(Gtk.Button(label="↺"))
        self.repeat_btn.add_css_class("ctrl-btn")
        self.repeat_btn.set_tooltip_text("Repeat  [R]")
        self.repeat_btn.connect("clicked", self._toggle_repeat)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)

        vol_lbl = Gtk.Label(label="Vol")
        vol_lbl.add_css_class("muted-lbl")

        self.vol_bar = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        self.vol_bar.set_range(0, 1)
        self.vol_bar.set_value(1.0)
        self.vol_bar.set_draw_value(False)
        self.vol_bar.set_size_request(80, -1)
        self.vol_bar.set_focusable(False)
        self.vol_bar.set_focus_on_click(False)
        self.vol_bar.set_tooltip_text("Volume  [Ctrl+↑ / Ctrl+↓]")
        self.vol_bar.add_css_class("vol-scale")
        self.vol_bar.connect("value-changed", self._on_vol)

        for w in (open_btn, self.prev_btn, self.play_btn, self.next_btn,
                  self.shuffle_btn, self.repeat_btn,
                  spacer, vol_lbl, self.vol_bar):
            ctrl.append(w)

        bar.append(ctrl)
        return bar

    # ═══════════════════════════════════════════════════════════
    #  ALBUM ART DRAW
    # ═══════════════════════════════════════════════════════════
    def _draw_album_art(self, _w, cr, width, height):
        import math as _m
        r = min(width, height) / 2
        cx, cy = width / 2, height / 2

        if self._album_art_pixbuf is not None:
            from gi.repository import GdkPixbuf
            pb = self._album_art_pixbuf
            scale = min(width / pb.get_width(), height / pb.get_height())
            sw = pb.get_width() * scale
            sh = pb.get_height() * scale
            ox = (width - sw) / 2
            oy = (height - sh) / 2
            cr.save()
            radius = 5.0
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
            cr.set_source_rgba(1, 1, 1, 0.10)
            cr.set_line_width(1.0)
            cr.new_sub_path()
            cr.arc(radius, radius, radius, _m.pi, 3 * _m.pi / 2)
            cr.arc(width - radius, radius, radius, 3 * _m.pi / 2, 0)
            cr.arc(width - radius, height - radius, radius, 0, _m.pi / 2)
            cr.arc(radius, height - radius, radius, _m.pi / 2, _m.pi)
            cr.close_path()
            cr.stroke()
        else:
            # Vinyl default
            cr.arc(cx, cy, r - 1, 0, 2 * _m.pi)
            cr.set_source_rgb(0.10, 0.11, 0.13)
            cr.fill()
            for ri in [r * 0.85, r * 0.70, r * 0.55]:
                cr.arc(cx, cy, ri, 0, 2 * _m.pi)
                cr.set_source_rgba(1, 1, 1, 0.04)
                cr.set_line_width(1)
                cr.stroke()
            cr.arc(cx, cy, r * 0.38, 0, 2 * _m.pi)
            cr.set_source_rgb(0.11, 0.18, 0.38 if self.is_dark else 0.72)
            cr.fill()
            cr.arc(cx, cy, r * 0.10, 0, 2 * _m.pi)
            cr.set_source_rgb(0.06, 0.06, 0.07)
            cr.fill()
            cr.set_source_rgba(0.48, 0.67, 1.0, 0.85)
            cr.set_font_size(r * 0.40)
            cr.select_font_face("sans-serif", 0, 0)
            ext = cr.text_extents("♫")
            cr.move_to(cx - ext.width / 2 - ext.x_bearing,
                       cy - ext.height / 2 - ext.y_bearing)
            cr.show_text("♫")
            cr.arc(cx, cy, r - 1, 0, 2 * _m.pi)
            cr.set_source_rgba(1, 1, 1, 0.08)
            cr.set_line_width(1.5)
            cr.stroke()

    def _update_album_art(self, idx: int):
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

    # ═══════════════════════════════════════════════════════════
    #  LIBRARY ACTIONS
    # ═══════════════════════════════════════════════════════════
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
            for f in dialog.get_files():
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
            self.lib_list.append(self._make_lib_row(i, path))
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
        del_btn.add_css_class("del-btn")
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

    # ═══════════════════════════════════════════════════════════
    #  PLAYBACK CONTROLS
    # ═══════════════════════════════════════════════════════════
    def _play_index(self, idx: int):
        if idx < 0 or idx >= len(self.library):
            return
        self.current_idx = idx
        self._load(self.library.tracks[idx])
        self._do_play()
        self._refresh_library_ui()
        self._update_album_art(idx)
        save_config(self._build_current_config())

    def _prev_track(self, _btn=None):
        n = len(self.library)
        if n == 0: return
        self._play_index((self.current_idx - 1) % n)

    def _next_track(self, _btn=None):
        n = len(self.library)
        if n == 0: return
        idx = random.randint(0, n - 1) if self.shuffle else (self.current_idx + 1) % n
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
            self, self._spec_color, self._chart_color,
            self._on_spec_color_changed, self._on_chart_color_changed,
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
        self.src.set_property("location", Path(path).as_posix())
        self.pipeline.set_state(Gst.State.PAUSED)
        self.is_playing = False
        self.play_btn.set_label("▶")
        self.play_btn.set_sensitive(True)
        fname = os.path.basename(path)
        self.track_lbl.set_text(f"// {fname}")
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
        dialog.add_button("Batal",   Gtk.ResponseType.CANCEL)
        dialog.add_button("▶  Buka", Gtk.ResponseType.ACCEPT)
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
            self.pipeline.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                int(value / 100 * self.duration_ns),
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

    # ═══════════════════════════════════════════════════════════
    #  CURRENCY HELPERS
    # ═══════════════════════════════════════════════════════════
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