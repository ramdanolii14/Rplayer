#!/usr/bin/env python3
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gst", "1.0")

from gi.repository import Gtk, Gdk, Gst, GLib, Gio
import os, sys, math, json, random

Gst.init(None)

# ── Constants ─────────────────────────────────────────────────────────────────
NUM_BANDS       = 80
DEFAULT_RATE    = 18_000.0
SPECTRUM_NS     = 35_000_000
IDR_MIN         = 18_000.0
IDR_MAX         = 18_999.0
HISTORY_LEN     = 120        # titik di grafik kurs

AUDIO_EXTS = {".mp3", ".flac", ".ogg", ".wav", ".m4a", ".opus", ".aac", ".wma"}

# ── Spectrum Color Presets ────────────────────────────────────────────────────
SPECTRUM_COLORS = {
    "Hijau":   {
        "stops":  [(0.0, 0.02, 0.35, 0.18, 0.95),
                   (0.6, 0.05, 0.72, 0.35, 0.92),
                   (1.0, 0.20, 1.00, 0.50, 0.90)],
        "peak":   (0.35, 1.00, 0.55, 0.75),
        "wave_f": (0.10, 0.90, 0.45, 0.12),
        "wave_l": (0.10, 0.90, 0.45, 0.85),
        "fallbk": lambda v: (0.05 + v*0.15, 0.4 + v*0.6, 0.25, 0.9),
    },
    "Biru":    {
        "stops":  [(0.0, 0.02, 0.15, 0.50, 0.95),
                   (0.6, 0.05, 0.40, 0.88, 0.92),
                   (1.0, 0.20, 0.65, 1.00, 0.90)],
        "peak":   (0.30, 0.70, 1.00, 0.80),
        "wave_f": (0.10, 0.50, 0.95, 0.12),
        "wave_l": (0.10, 0.55, 1.00, 0.85),
        "fallbk": lambda v: (0.05, 0.3 + v*0.5, 0.7 + v*0.3, 0.9),
    },
    "Ungu":    {
        "stops":  [(0.0, 0.25, 0.02, 0.45, 0.95),
                   (0.6, 0.55, 0.05, 0.85, 0.92),
                   (1.0, 0.80, 0.20, 1.00, 0.90)],
        "peak":   (0.90, 0.45, 1.00, 0.80),
        "wave_f": (0.60, 0.10, 0.95, 0.12),
        "wave_l": (0.70, 0.15, 1.00, 0.85),
        "fallbk": lambda v: (0.4 + v*0.4, 0.05, 0.6 + v*0.4, 0.9),
    },
    "Oranye":  {
        "stops":  [(0.0, 0.45, 0.15, 0.02, 0.95),
                   (0.6, 0.90, 0.42, 0.05, 0.92),
                   (1.0, 1.00, 0.70, 0.10, 0.90)],
        "peak":   (1.00, 0.75, 0.20, 0.80),
        "wave_f": (0.95, 0.55, 0.10, 0.12),
        "wave_l": (1.00, 0.60, 0.10, 0.85),
        "fallbk": lambda v: (0.7 + v*0.3, 0.3 + v*0.35, 0.02, 0.9),
    },
    "Merah":   {
        "stops":  [(0.0, 0.40, 0.02, 0.05, 0.95),
                   (0.6, 0.85, 0.08, 0.12, 0.92),
                   (1.0, 1.00, 0.25, 0.25, 0.90)],
        "peak":   (1.00, 0.35, 0.35, 0.80),
        "wave_f": (0.95, 0.10, 0.15, 0.12),
        "wave_l": (1.00, 0.15, 0.20, 0.85),
        "fallbk": lambda v: (0.6 + v*0.4, 0.05, 0.05, 0.9),
    },
    "Cyan":    {
        "stops":  [(0.0, 0.02, 0.35, 0.45, 0.95),
                   (0.6, 0.05, 0.80, 0.90, 0.92),
                   (1.0, 0.10, 1.00, 1.00, 0.90)],
        "peak":   (0.20, 1.00, 1.00, 0.80),
        "wave_f": (0.05, 0.90, 0.95, 0.12),
        "wave_l": (0.05, 0.95, 1.00, 0.85),
        "fallbk": lambda v: (0.05, 0.6 + v*0.4, 0.7 + v*0.3, 0.9),
    },
    "Pink":    {
        "stops":  [(0.0, 0.45, 0.02, 0.30, 0.95),
                   (0.6, 0.90, 0.10, 0.60, 0.92),
                   (1.0, 1.00, 0.30, 0.75, 0.90)],
        "peak":   (1.00, 0.50, 0.85, 0.80),
        "wave_f": (0.95, 0.20, 0.65, 0.12),
        "wave_l": (1.00, 0.25, 0.70, 0.85),
        "fallbk": lambda v: (0.7 + v*0.3, 0.05, 0.5 + v*0.3, 0.9),
    },
    "Putih":   {
        "stops":  [(0.0, 0.35, 0.37, 0.42, 0.95),
                   (0.6, 0.65, 0.68, 0.74, 0.92),
                   (1.0, 0.90, 0.92, 0.96, 0.90)],
        "peak":   (1.00, 1.00, 1.00, 0.85),
        "wave_f": (0.80, 0.82, 0.88, 0.12),
        "wave_l": (0.90, 0.92, 0.97, 0.85),
        "fallbk": lambda v: (0.5 + v*0.4, 0.52 + v*0.4, 0.56 + v*0.4, 0.9),
    },
}
SPECTRUM_COLOR_NAMES = list(SPECTRUM_COLORS.keys())
DEFAULT_SPEC_COLOR = "Hijau"

# ── Chart Color Presets ───────────────────────────────────────────────────────
# Setiap preset: (line_rgb, fill_rgba, grid_rgba, text_rgb)
CHART_COLORS = {
    "Biru":    {
        "line":  (0.102, 0.451, 0.910),
        "fill":  (0.102, 0.451, 0.910, 0.15),
        "grid":  (1.0,   1.0,   1.0,   0.05),
        "text":  (0.4,   0.4,   0.4),
    },
    "Hijau":   {
        "line":  (0.05, 0.78, 0.40),
        "fill":  (0.05, 0.78, 0.40, 0.15),
        "grid":  (1.0,  1.0,  1.0,  0.05),
        "text":  (0.4,  0.4,  0.4),
    },
    "Ungu":    {
        "line":  (0.68, 0.28, 0.95),
        "fill":  (0.68, 0.28, 0.95, 0.15),
        "grid":  (1.0,  1.0,  1.0,  0.05),
        "text":  (0.4,  0.4,  0.4),
    },
    "Oranye":  {
        "line":  (1.00, 0.58, 0.08),
        "fill":  (1.00, 0.58, 0.08, 0.15),
        "grid":  (1.0,  1.0,  1.0,  0.05),
        "text":  (0.4,  0.4,  0.4),
    },
    "Merah":   {
        "line":  (0.95, 0.15, 0.20),
        "fill":  (0.95, 0.15, 0.20, 0.15),
        "grid":  (1.0,  1.0,  1.0,  0.05),
        "text":  (0.4,  0.4,  0.4),
    },
    "Cyan":    {
        "line":  (0.05, 0.90, 0.95),
        "fill":  (0.05, 0.90, 0.95, 0.15),
        "grid":  (1.0,  1.0,  1.0,  0.05),
        "text":  (0.4,  0.4,  0.4),
    },
    "Pink":    {
        "line":  (1.00, 0.30, 0.70),
        "fill":  (1.00, 0.30, 0.70, 0.15),
        "grid":  (1.0,  1.0,  1.0,  0.05),
        "text":  (0.4,  0.4,  0.4),
    },
    "Kuning":  {
        "line":  (0.95, 0.82, 0.05),
        "fill":  (0.95, 0.82, 0.05, 0.15),
        "grid":  (1.0,  1.0,  1.0,  0.05),
        "text":  (0.4,  0.4,  0.4),
    },
    "Putih":   {
        "line":  (0.88, 0.90, 0.95),
        "fill":  (0.88, 0.90, 0.95, 0.15),
        "grid":  (1.0,  1.0,  1.0,  0.05),
        "text":  (0.4,  0.4,  0.4),
    },
}
CHART_COLOR_NAMES    = list(CHART_COLORS.keys())
DEFAULT_CHART_COLOR  = "Biru"

# ── Theme Definitions ─────────────────────────────────────────────────────────
DARK_THEME = {
    "window_bg":      "#0e0f10",
    "card_bg":        "#141618",
    "card_border":    "#1f2226",
    "text_primary":   "#f0f2f5",
    "text_muted":     "#555b68",
    "text_dim":       "#3a3e48",
    "entry_bg":       "#1a1c1f",
    "entry_border":   "#2b2e35",
    "entry_text":     "#d8dae0",
    "tab_active_bg":  "#1d2e5c",
    "tab_active_bd":  "#2a4fa8",
    "tab_active_fg":  "#7aacff",
    "play_bg":        "#1d2e5c",
    "play_border":    "#2a4fa8",
    "play_fg":        "#7aacff",
    "ctrl_border":    "#252830",
    "ctrl_fg":        "#777",
    "track_color":    "#4a4e58",
    "bar_bg":         "#141618",
    "bar_border":     "#1f2226",
    "scale_trough":   "#1a1c1f",
    "scale_hl":       "#2a4fa8",
    "scale_slider":   "#4a80e8",
    "sarcasm":        "#3a3e48",
    "sep_color":      "#1f2226",
    "list_bg":        "#141618",
    "list_item_bg":   "#1a1c1f",
    "list_item_hover":"#212429",
    "list_sel_bg":    "#1d2e5c",
    "list_sel_fg":    "#7aacff",
    "chart_bg_rgb":   (0.055, 0.059, 0.063),
    "spec_bg":        "#0a0b0c",
}

LIGHT_THEME = {
    "window_bg":      "#f4f6fb",
    "card_bg":        "#ffffff",
    "card_border":    "#dde1ea",
    "text_primary":   "#1a1d24",
    "text_muted":     "#888fa0",
    "text_dim":       "#b0b7c6",
    "entry_bg":       "#f0f2f7",
    "entry_border":   "#cdd2de",
    "entry_text":     "#1a1d24",
    "tab_active_bg":  "#e8eeff",
    "tab_active_bd":  "#4a7cf7",
    "tab_active_fg":  "#1a4fc4",
    "play_bg":        "#e8eeff",
    "play_border":    "#4a7cf7",
    "play_fg":        "#1a4fc4",
    "ctrl_border":    "#cdd2de",
    "ctrl_fg":        "#444",
    "track_color":    "#888fa0",
    "bar_bg":         "#ffffff",
    "bar_border":     "#dde1ea",
    "scale_trough":   "#e0e4ef",
    "scale_hl":       "#4a7cf7",
    "scale_slider":   "#2a5ef5",
    "sarcasm":        "#b0b7c6",
    "sep_color":      "#dde1ea",
    "list_bg":        "#ffffff",
    "list_item_bg":   "#f8f9fc",
    "list_item_hover":"#eef0f8",
    "list_sel_bg":    "#e8eeff",
    "list_sel_fg":    "#1a4fc4",
    "chart_bg_rgb":   (1.0, 1.0, 1.0),
    "spec_bg":        "#f0f2f7",
}


# ── IDR Currency Chart (Google-style) ─────────────────────────────────────────
class IDRChart(Gtk.DrawingArea):
    """Grafik kurs seperti Google Finance — spektrum menggerakkan nilai IDR."""
    def __init__(self, theme):
        super().__init__()
        self.theme        = theme
        self.history      = [IDR_MIN] * HISTORY_LEN
        self.current      = IDR_MIN
        self.color_preset = DEFAULT_CHART_COLOR
        self.set_draw_func(self.on_draw)
        self.set_hexpand(True)
        self.set_size_request(-1, 110)

    def push(self, value: float):
        self.history.append(value)
        if len(self.history) > HISTORY_LEN:
            self.history.pop(0)
        self.current = value
        self.queue_draw()

    def on_draw(self, _w, cr, width, height):
        t = self.theme
        cr.set_source_rgb(*t["chart_bg_rgb"])
        cr.rectangle(0, 0, width, height)
        cr.fill()

        cp     = CHART_COLORS[self.color_preset]
        data   = self.history
        n      = len(data)
        lo, hi = IDR_MIN, IDR_MAX
        pad    = 8
        lw     = 46  # label width on right

        def xt(i): return i / max(n - 1, 1) * (width - pad * 2 - lw) + pad
        def yt(v): return height - pad - (v - lo) / (hi - lo) * (height - pad * 2 - 14)

        # grid lines
        gr, gg, gb, ga = cp["grid"]
        cr.set_line_width(0.5)
        for val in [18000, 18500, 19000, 19500, 20000]:
            y = yt(val)
            cr.set_source_rgba(gr, gg, gb, ga)
            cr.move_to(0, y)
            cr.line_to(width - lw, y)
            cr.stroke()

        if n >= 2:
            fr, fg_, fb, fa = cp["fill"]
            lr, lg, lb      = cp["line"]

            # fill
            cr.move_to(xt(0), height - pad)
            for i, v in enumerate(data):
                cr.line_to(xt(i), yt(v))
            cr.line_to(xt(n - 1), height - pad)
            cr.close_path()
            cr.set_source_rgba(fr, fg_, fb, fa)
            cr.fill()

            # line
            cr.move_to(xt(0), yt(data[0]))
            for i, v in enumerate(data[1:], 1):
                cr.line_to(xt(i), yt(v))
            cr.set_source_rgb(lr, lg, lb)
            cr.set_line_width(2.0)
            cr.stroke()

            # dot
            ex, ey = xt(n - 1), yt(data[-1])
            cr.arc(ex, ey, 4.5, 0, 2 * math.pi)
            cr.set_source_rgb(lr, lg, lb)
            cr.fill()
            cr.arc(ex, ey, 8, 0, 2 * math.pi)
            cr.set_source_rgba(lr, lg, lb, 0.18)
            cr.fill()

        # Y labels
        tr, tg, tb = cp["text"]
        cr.set_source_rgb(tr, tg, tb)
        cr.set_font_size(9)
        for val, label in [(18000, "18.000"), (19000, "19.000"), (20000, "20.000")]:
            y = yt(val)
            cr.move_to(width - lw + 4, y + 3)
            cr.show_text(label)


# ── Spectrum Visualizer ────────────────────────────────────────────────────────
class SpectrumVisualizer(Gtk.DrawingArea):
    def __init__(self, theme):
        super().__init__()
        self.theme        = theme
        self.magnitudes   = [-80.0] * NUM_BANDS
        self.peaks        = [-80.0] * NUM_BANDS
        self.peak_ttl     = [0]    * NUM_BANDS
        self.view_mode    = "FULL"
        self._smoothed    = [-80.0] * NUM_BANDS
        self.color_preset = DEFAULT_SPEC_COLOR
        self.set_draw_func(self.on_draw)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_size_request(-1, 160)

    def update(self, magnitudes: list):
        alpha = 0.55
        for i, m in enumerate(magnitudes):
            self._smoothed[i] = alpha * m + (1 - alpha) * self._smoothed[i]
            if m > self.peaks[i]:
                self.peaks[i]   = m
                self.peak_ttl[i] = 40
            elif self.peak_ttl[i] > 0:
                self.peak_ttl[i] -= 1
            else:
                self.peaks[i] = max(self.peaks[i] - 0.6, self._smoothed[i])
        self.magnitudes = magnitudes
        self.queue_draw()

    @staticmethod
    def _norm(db: float) -> float:
        return max(0.0, min(1.0, (db + 80.0) / 80.0))

    @staticmethod
    def _hex(h):
        h = h.lstrip("#")
        if len(h) == 6:
            return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4))
        return (0.2, 0.6, 0.4)

    def on_draw(self, _w, cr, width, height):
        t = self.theme
        r, g, b = self._hex(t["spec_bg"])
        cr.set_source_rgb(r, g, b)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        mags  = self._smoothed[:]
        peaks = self.peaks[:]
        n     = len(mags)

        if self.view_mode == "BASS":
            mags  = mags[:n // 4]
            peaks = peaks[:n // 4]
        elif self.view_mode == "MID":
            mags  = mags[n // 4: n * 3 // 4]
            peaks = peaks[n // 4: n * 3 // 4]
        elif self.view_mode == "WAVE":
            self._draw_wave(cr, mags, width, height, t)
            return

        n = len(mags)
        if n == 0: return

        bw  = width / n
        gap = max(0.8, bw * 0.18)

        for i in range(n):
            v  = self._norm(mags[i])
            bh = max(1.0, v * (height - 6))
            x  = i * bw + gap
            y  = height - bh
            w  = bw - gap * 2

            preset = SPECTRUM_COLORS[self.color_preset]
            try:
                import cairo
                pat = cairo.LinearGradient(0, height, 0, y)
                for pos, pr, pg, pb, pa in preset["stops"]:
                    pat.add_color_stop_rgba(pos, pr, pg, pb, pa)
                cr.set_source(pat)
            except Exception:
                cr.set_source_rgba(*preset["fallbk"](v))

            cr.rectangle(x, y, w, bh)
            cr.fill()

            if self.view_mode != "MAKS":
                pv = self._norm(peaks[i])
                py = height - pv * (height - 6) - 2
                cr.set_source_rgba(*preset["peak"])
                cr.rectangle(x, py, w, 1.5)
                cr.fill()

        cr.set_line_width(0.5)
        for ratio in (0.25, 0.50, 0.75):
            cr.set_source_rgba(1, 1, 1, 0.04)
            y = height * ratio
            cr.move_to(0, y); cr.line_to(width, y); cr.stroke()

        cr.set_source_rgba(0.38, 0.40, 0.44, 1.0)
        cr.set_font_size(9)
        for lbl, xr in (("0Hz", 0.01), ("5k", 0.25), ("10k", 0.50), ("20k", 0.97)):
            cr.move_to(xr * width, height - 3)
            cr.show_text(lbl)

    def _draw_wave(self, cr, mags, width, height, t):
        n = len(mags)
        if n == 0: return
        step = width / n
        mid  = height / 2

        cr.move_to(0, mid)
        for i, db in enumerate(mags):
            v = self._norm(db)
            cr.line_to(i * step, mid - v * mid * 0.88)
        for i in range(n - 1, -1, -1):
            v = self._norm(mags[i])
            cr.line_to(i * step, mid + v * mid * 0.88)
        cr.close_path()
        preset = SPECTRUM_COLORS[self.color_preset]
        cr.set_source_rgba(*preset["wave_f"])
        cr.fill_preserve()
        cr.set_source_rgba(*preset["wave_l"])
        cr.set_line_width(1.5)
        cr.stroke()

        wfr, wfg, wfb, _ = preset["wave_f"]
        cr.set_source_rgba(wfr, wfg, wfb, 0.15)
        cr.set_line_width(1)
        cr.move_to(0, mid); cr.line_to(width, mid); cr.stroke()


# ── Library Store ──────────────────────────────────────────────────────────────
class MusicLibrary:
    def __init__(self):
        self.tracks: list[str] = []

    def add(self, path: str):
        if path not in self.tracks and os.path.isfile(path):
            self.tracks.append(path)
            return True
        return False

    def add_folder(self, folder: str):
        added = 0
        for root, _, files in os.walk(folder):
            for f in sorted(files):
                if os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                    if self.add(os.path.join(root, f)):
                        added += 1
        return added

    def remove(self, idx: int):
        if 0 <= idx < len(self.tracks):
            self.tracks.pop(idx)

    def clear(self):
        self.tracks.clear()

    def get_name(self, idx: int) -> str:
        if 0 <= idx < len(self.tracks):
            return os.path.basename(self.tracks[idx])
        return ""

    def __len__(self): return len(self.tracks)


# ── Settings Dialog ────────────────────────────────────────────────────────────
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


# ── Main Window ────────────────────────────────────────────────────────────────
class IDRSpectrumWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="IDR Spectrum Player")

        # Set icon — akan muncul di taskbar / dock
        self.set_icon_name("id.ramdanolii.idrspectrum")

        self.is_dark        = True
        self.theme          = DARK_THEME
        self.idr_rate       = DEFAULT_RATE
        self.is_playing     = False
        self.duration_ns    = 0
        self.current_file   = None
        self._upd_pos       = False
        self.spec_visible   = True
        self.shuffle        = False
        self.repeat_mode    = "none"
        self.library        = MusicLibrary()
        self.current_idx    = -1
        self._idr_history   = [IDR_MIN] * HISTORY_LEN
        self._spec_color    = DEFAULT_SPEC_COLOR
        self._chart_color   = DEFAULT_CHART_COLOR

        self._setup_css()
        self._build_pipeline()
        self._build_ui()
        self.set_default_size(1050, 680)

        GLib.timeout_add(400, self._tick)
        GLib.timeout_add(100, self._spectrum_idr_tick)

    # ── CSS ───────────────────────────────────────────────────────────────────
    def _build_css(self):
        t = self.theme
        return f"""
        window {{
            background-color: {t['window_bg']};
            color: {t['text_primary']};
            font-family: 'IBM Plex Sans', 'Noto Sans', sans-serif;
        }}
        .card {{
            background-color: {t['card_bg']};
            border-radius: 14px;
            padding: 16px;
            border: 1px solid {t['card_border']};
        }}
        .rate-display {{
            font-size: 28px;
            font-weight: 700;
            color: {t['text_primary']};
            letter-spacing: -0.03em;
            line-height: 1.2;
        }}
        .mono {{
            font-family: 'Share Tech Mono', 'Monospace', monospace;
        }}
        .dim {{
            font-size: 11px;
            color: {t['text_muted']};
        }}
        .conv-entry {{
            background-color: {t['entry_bg']};
            color: {t['entry_text']};
            border: 1px solid {t['entry_border']};
            border-radius: 8px;
            padding: 6px 10px;
            min-width: 100px;
            font-family: 'Share Tech Mono', 'Monospace', monospace;
            font-size: 13px;
        }}
        .conv-entry:focus {{
            border-color: {t['tab_active_bd']};
        }}
        .tab-pill {{
            background: none;
            border: 1px solid transparent;
            color: {t['text_muted']};
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.08em;
        }}
        .tab-pill:hover {{
            color: {t['text_primary']};
            border-color: {t['card_border']};
            background-color: {t['entry_bg']};
        }}
        .tab-pill.active {{
            background-color: {t['tab_active_bg']};
            border-color: {t['tab_active_bd']};
            color: {t['tab_active_fg']};
        }}
        .player-bar {{
            background-color: {t['bar_bg']};
            border-radius: 12px;
            padding: 10px 14px;
            border: 1px solid {t['bar_border']};
        }}
        .ctrl-btn {{
            background: none;
            border: 1px solid {t['ctrl_border']};
            color: {t['ctrl_fg']};
            border-radius: 8px;
            min-width: 34px;
            min-height: 34px;
            padding: 0;
            font-size: 14px;
        }}
        .ctrl-btn:hover {{
            background-color: {t['entry_bg']};
            color: {t['text_primary']};
            border-color: {t['entry_border']};
        }}
        .ctrl-btn.active {{
            background-color: {t['tab_active_bg']};
            border-color: {t['tab_active_bd']};
            color: {t['tab_active_fg']};
        }}
        .icon-btn {{
            background: none;
            border: 1px solid {t['ctrl_border']};
            color: {t['ctrl_fg']};
            border-radius: 8px;
            min-width: 30px;
            min-height: 28px;
            padding: 0 6px;
            font-size: 15px;
        }}
        .icon-btn:hover {{
            background-color: {t['entry_bg']};
            color: {t['text_primary']};
            border-color: {t['entry_border']};
        }}
        .icon-btn.active {{
            background-color: {t['tab_active_bg']};
            border-color: {t['tab_active_bd']};
            color: {t['tab_active_fg']};
        }}
        .play-btn {{
            background-color: {t['play_bg']};
            border: 1px solid {t['play_border']};
            color: {t['play_fg']};
            border-radius: 50%;
            min-width: 42px;
            min-height: 42px;
            padding: 0;
            font-size: 16px;
        }}
        .play-btn:hover {{
            background-color: {t['tab_active_bg']};
            color: {t['text_primary']};
        }}
        .track-label {{
            font-size: 11px;
            color: {t['track_color']};
            font-style: italic;
        }}
        .sarcasm-tag {{
            font-size: 10px;
            color: {t['sarcasm']};
            font-family: 'Share Tech Mono', 'Monospace', monospace;
            letter-spacing: 0.06em;
        }}
        scale trough {{
            background-color: {t['scale_trough']};
            min-height: 3px;
            border-radius: 2px;
        }}
        scale highlight {{
            background-color: {t['scale_hl']};
            border-radius: 2px;
        }}
        scale slider {{
            background-color: {t['scale_slider']};
            border-radius: 50%;
            min-width: 11px;
            min-height: 11px;
            border: none;
        }}
        .lib-row {{
            background-color: {t['list_item_bg']};
            border-radius: 8px;
            padding: 6px 10px;
            border: 1px solid {t['card_border']};
        }}
        .lib-row:hover {{
            background-color: {t['list_item_hover']};
        }}
        .lib-row-active {{
            background-color: {t['list_sel_bg']};
            border-color: {t['tab_active_bd']};
        }}
        .lib-row label {{
            color: {t['text_primary']};
        }}
        .lib-row-active label {{
            color: {t['list_sel_fg']};
        }}
        .lib-num {{
            font-size: 10px;
            color: {t['text_muted']};
            font-family: 'Share Tech Mono', 'Monospace', monospace;
            min-width: 22px;
        }}
        .lib-name {{
            font-size: 12px;
        }}
        .section-title {{
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.12em;
            color: {t['text_muted']};
        }}
        .separator {{
            background-color: {t['sep_color']};
            min-height: 1px;
        }}
        .theme-btn {{
            background: none;
            border: 1px solid {t['ctrl_border']};
            color: {t['ctrl_fg']};
            border-radius: 20px;
            padding: 4px 12px;
            font-size: 11px;
        }}
        .theme-btn:hover {{
            background-color: {t['entry_bg']};
            color: {t['text_primary']};
        }}
        dialog {{
            background-color: {t['window_bg']};
            color: {t['text_primary']};
        }}
        dialog .card {{
            background-color: {t['card_bg']};
        }}
        """

    def _setup_css(self):
        css = self._build_css().encode()
        self._css_provider = Gtk.CssProvider()
        self._css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self._css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _reload_css(self):
        css = self._build_css().encode()
        self._css_provider.load_from_data(css)
        self.chart.theme = self.theme
        self.chart.queue_draw()
        self.viz.theme = self.theme
        self.viz.queue_draw()

    # ── GStreamer Pipeline ────────────────────────────────────────────────────
    def _build_pipeline(self):
        self.pipeline = Gst.Pipeline.new("idr-player")

        def make(factory, name):
            el = Gst.ElementFactory.make(factory, name)
            if not el:
                print(f"[FATAL] Tidak bisa membuat elemen GStreamer: {factory}")
                sys.exit(1)
            return el

        self.src       = make("filesrc",       "src")
        self.decode    = make("decodebin",     "decode")
        self.convert   = make("audioconvert",  "convert")
        self.resample  = make("audioresample", "resample")
        self.volume_el = make("volume",        "vol")
        self.tee       = make("tee",           "tee")
        self.q_audio   = make("queue",         "q_audio")
        self.q_spec    = make("queue",         "q_spec")
        self.audiosink = make("autoaudiosink", "audiosink")
        self.spectrum  = make("spectrum",      "spectrum")
        self.fakesink  = make("fakesink",      "fakesink")

        self.spectrum.set_property("bands",         NUM_BANDS)
        self.spectrum.set_property("threshold",     -80)
        self.spectrum.set_property("post-messages", True)
        self.spectrum.set_property("interval",      SPECTRUM_NS)
        self.fakesink.set_property("sync",          True)

        for el in (self.src, self.decode, self.convert, self.resample,
                   self.volume_el, self.tee, self.q_audio, self.q_spec,
                   self.audiosink, self.spectrum, self.fakesink):
            self.pipeline.add(el)

        self.src.link(self.decode)
        self.decode.connect("pad-added", self._on_pad_added)

        self.convert.link(self.resample)
        self.resample.link(self.volume_el)
        self.volume_el.link(self.tee)

        t1 = self.tee.get_request_pad("src_%u")
        t1.link(self.q_audio.get_static_pad("sink"))
        self.q_audio.link(self.audiosink)

        t2 = self.tee.get_request_pad("src_%u")
        t2.link(self.q_spec.get_static_pad("sink"))
        self.q_spec.link(self.spectrum)
        self.spectrum.link(self.fakesink)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_bus_msg)

    def _on_pad_added(self, _elem, pad):
        caps = pad.get_current_caps()
        if caps and caps.get_structure(0).get_name().startswith("audio"):
            sink = self.convert.get_static_pad("sink")
            if not sink.is_linked():
                pad.link(sink)

    def _on_bus_msg(self, _bus, msg):
        t = msg.type
        if t == Gst.MessageType.EOS:
            GLib.idle_add(self._on_eos)
        elif t == Gst.MessageType.ERROR:
            err, dbg = msg.parse_error()
            print(f"[GST] {err}\n{dbg}")
        elif t == Gst.MessageType.DURATION_CHANGED:
            GLib.idle_add(self._query_duration)
        elif t == Gst.MessageType.ELEMENT:
            s = msg.get_structure()
            if s and s.get_name() == "spectrum":
                mags = s.get_value("magnitude")
                if mags:
                    captured = list(mags)
                    GLib.idle_add(lambda m=captured: self._on_spectrum(m))

    def _on_spectrum(self, mags):
        if not mags:
            return False
        mags = list(mags)
        if self.spec_visible:
            self.viz.update(mags)
        avg  = sum(mags) / len(mags)
        norm = max(0.0, min(1.0, (avg + 80.0) / 80.0))
        mx   = max(mags)
        norm = max(0.0, min(1.0, 0.6 * norm + 0.4 * (mx + 80.0) / 80.0))
        target = IDR_MIN + norm * (IDR_MAX - IDR_MIN)
        self.idr_rate = 0.65 * target + 0.35 * self.idr_rate
        self.chart.push(self.idr_rate)
        self._refresh_rate_lbl()
        self._usd_changed(self.usd_entry)
        return False

    def _on_eos(self):
        self._advance_track()
        return False

    def _advance_track(self):
        n = len(self.library)
        if n == 0:
            self._stop_reset()
            return
        if self.repeat_mode == "one":
            self._play_index(self.current_idx)
            return
        if self.shuffle:
            idx = random.randint(0, n - 1)
        else:
            idx = (self.current_idx + 1) % n
        if idx == 0 and self.repeat_mode == "none" and not self.shuffle:
            self._stop_reset()
            return
        self._play_index(idx)

    def _stop_reset(self):
        self.pipeline.set_state(Gst.State.READY)
        self.is_playing = False
        self.play_btn.set_label("▶")
        self._upd_pos = True
        self.seek_bar.set_value(0)
        self._upd_pos = False
        self.time_lbl.set_text("0:00 / 0:00")

    def _query_duration(self):
        ok, d = self.pipeline.query_duration(Gst.Format.TIME)
        if ok and d > 0:
            self.duration_ns = d
        return False

    def _tick(self):
        if self.is_playing:
            ok, pos = self.pipeline.query_position(Gst.Format.TIME)
            if ok and self.duration_ns > 0:
                self._upd_pos = True
                self.seek_bar.set_value(pos / self.duration_ns * 100)
                self._upd_pos = False
                ps = pos / Gst.SECOND
                ds = self.duration_ns / Gst.SECOND
                self.time_lbl.set_text(
                    f"{int(ps//60)}:{int(ps%60):02d} / {int(ds//60)}:{int(ds%60):02d}"
                )
        return True

    def _spectrum_idr_tick(self):
        if not self.is_playing:
            drift = random.gauss(0, 8)
            self.idr_rate = max(IDR_MIN, min(IDR_MAX, self.idr_rate + drift))
            self.chart.push(self.idr_rate)
            self._refresh_rate_lbl()
        return True

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

        # Settings button (⚙)
        settings_btn = Gtk.Button(label="⚙")
        settings_btn.add_css_class("icon-btn")
        settings_btn.set_tooltip_text("Pengaturan warna")
        settings_btn.connect("clicked", self._open_settings)

        # Theme toggle
        self.theme_btn = Gtk.Button(label="☀")
        self.theme_btn.add_css_class("icon-btn")
        self.theme_btn.set_tooltip_text("Ganti tema")
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

        self.lib_count_lbl = Gtk.Label(label="0")
        self.lib_count_lbl.add_css_class("dim")

        hdr.append(lbl)
        hdr.append(self.lib_count_lbl)
        panel.append(hdr)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        panel.append(sep)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        add_file_btn = Gtk.Button(label="+ File")
        add_file_btn.add_css_class("ctrl-btn")
        add_file_btn.connect("clicked", self._lib_add_file)

        add_folder_btn = Gtk.Button(label="+ Folder")
        add_folder_btn.add_css_class("ctrl-btn")
        add_folder_btn.connect("clicked", self._lib_add_folder)

        clear_btn = Gtk.Button(label="✕")
        clear_btn.add_css_class("ctrl-btn")
        clear_btn.set_tooltip_text("Hapus semua")
        clear_btn.connect("clicked", self._lib_clear)

        btn_row.append(add_file_btn)
        btn_row.append(add_folder_btn)
        btn_row.append(clear_btn)
        panel.append(btn_row)

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
            if mode == "FULL":
                b.add_css_class("active")
            b.connect("clicked", self._switch_view, mode)
            tab_row.append(b)
            self._view_btns[mode] = b

        # Toggle spektrum — ICON saja, bukan teks panjang
        self.hide_spec_btn = Gtk.Button(label="⊟")
        self.hide_spec_btn.add_css_class("icon-btn")
        self.hide_spec_btn.set_tooltip_text("Sembunyikan spektrum")
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

        open_btn = Gtk.Button(label="☰")
        open_btn.add_css_class("ctrl-btn")
        open_btn.set_tooltip_text("Buka file musik")
        open_btn.connect("clicked", self._open_file)

        self.prev_btn = Gtk.Button(label="⏮")
        self.prev_btn.add_css_class("ctrl-btn")
        self.prev_btn.connect("clicked", self._prev_track)

        self.play_btn = Gtk.Button(label="▶")
        self.play_btn.add_css_class("play-btn")
        self.play_btn.set_sensitive(False)
        self.play_btn.connect("clicked", self._play_pause)

        self.next_btn = Gtk.Button(label="⏭")
        self.next_btn.add_css_class("ctrl-btn")
        self.next_btn.connect("clicked", self._next_track)

        self.shuffle_btn = Gtk.Button(label="⇄")
        self.shuffle_btn.add_css_class("ctrl-btn")
        self.shuffle_btn.set_tooltip_text("Shuffle")
        self.shuffle_btn.connect("clicked", self._toggle_shuffle)

        self.repeat_btn = Gtk.Button(label="↺")
        self.repeat_btn.add_css_class("ctrl-btn")
        self.repeat_btn.set_tooltip_text("Repeat")
        self.repeat_btn.connect("clicked", self._toggle_repeat)

        self.seek_bar = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        self.seek_bar.set_range(0, 100)
        self.seek_bar.set_draw_value(False)
        self.seek_bar.set_hexpand(True)
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
        self.vol_bar.connect("value-changed", self._on_vol)

        for w in (open_btn, self.prev_btn, self.play_btn, self.next_btn,
                  self.shuffle_btn, self.repeat_btn,
                  self.seek_bar, self.time_lbl, vol_lbl, self.vol_bar):
            ctrl.append(w)

        bar.append(ctrl)
        return bar

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
        dialog.destroy()

    def _lib_clear(self, _btn):
        self.library.clear()
        self.current_idx = -1
        self._refresh_library_ui()

    def _refresh_library_ui(self):
        child = self.lib_list.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.lib_list.remove(child)
            child = nxt

        for i, path in enumerate(self.library.tracks):
            row = self._make_lib_row(i, path)
            self.lib_list.append(row)

        self.lib_count_lbl.set_text(str(len(self.library)))

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

    # ── Playback ──────────────────────────────────────────────────────────────
    def _play_index(self, idx: int):
        if idx < 0 or idx >= len(self.library):
            return
        self.current_idx = idx
        path = self.library.tracks[idx]
        self._load(path)
        self._do_play()
        self._refresh_library_ui()

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

    def _toggle_repeat(self, _btn):
        modes  = ["none", "all", "one"]
        labels = {"none": "↺", "all": "↺↺", "one": "①"}
        self.repeat_mode = modes[(modes.index(self.repeat_mode) + 1) % 3]
        self.repeat_btn.set_label(labels[self.repeat_mode])
        if self.repeat_mode != "none":
            self.repeat_btn.add_css_class("active")
        else:
            self.repeat_btn.remove_css_class("active")

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

    def _toggle_theme(self, _btn):
        self.is_dark = not self.is_dark
        self.theme = DARK_THEME if self.is_dark else LIGHT_THEME
        self.theme_btn.set_label("☀" if self.is_dark else "☾")
        self.theme_btn.set_tooltip_text("Ganti ke Light" if self.is_dark else "Ganti ke Dark")
        self._reload_css()

    def _open_settings(self, _btn):
        dlg = SettingsDialog(
            self,
            self._spec_color,
            self._chart_color,
            self._on_spec_color_changed,
            self._on_chart_color_changed,
        )
        dlg.present()

    def _on_spec_color_changed(self, name: str):
        self._spec_color = name
        self.viz.color_preset = name
        self.viz.queue_draw()

    def _on_chart_color_changed(self, name: str):
        self._chart_color = name
        self.chart.color_preset = name
        self.chart.queue_draw()

    def _load(self, path: str):
        self.current_file = path
        self.pipeline.set_state(Gst.State.NULL)
        self.src.set_property("location", path)
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


# ── Application ────────────────────────────────────────────────────────────────
class IDRSpectrumApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="id.ramdanolii.idrspectrum",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

    def do_activate(self):
        win = IDRSpectrumWindow(self)
        win.present()


if __name__ == "__main__":
    app = IDRSpectrumApp()
    sys.exit(app.run(sys.argv))