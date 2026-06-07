#!/usr/bin/env python3
"""
IDR Spectrum Player — v1.0
Pemutar musik offline native Linux dengan visualisasi spektrum frekuensi real-time.
Dibuat sebagai kenangan pahit atas kejatuhan Rupiah terparah dalam sejarah.

Dibuat oleh: ramdanolii14
Lisensi: MIT

─── Dependensi (Arch Linux) ──────────────────────────────────────────────────
  sudo pacman -S python-gobject gtk4 gstreamer gst-plugins-good \
    gst-plugins-bad gst-plugins-ugly gst-libav gst-python

─── Jalankan ─────────────────────────────────────────────────────────────────
  chmod +x idr_spectrum_player.py
  ./idr_spectrum_player.py
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gst", "1.0")

from gi.repository import Gtk, Gdk, Gst, GLib
import os
import sys
import math

Gst.init(None)

# ── Constants ─────────────────────────────────────────────────────────────────
NUM_BANDS       = 80
DEFAULT_RATE    = 18_000.0      # IDR per 1 USD
SPECTRUM_NS     = 35_000_000    # ~35ms spectrum update interval


# ── Spectrum / Waveform Visualizer ────────────────────────────────────────────
class SpectrumVisualizer(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.magnitudes  = [-80.0] * NUM_BANDS
        self.peaks       = [-80.0] * NUM_BANDS
        self.peak_ttl    = [0]    * NUM_BANDS
        self.view_mode   = "FULL"
        self._smoothed   = [-80.0] * NUM_BANDS
        self.set_draw_func(self.on_draw)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_size_request(-1, 180)

    def update(self, magnitudes: list):
        # Smooth with exponential moving average
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

    def on_draw(self, _w, cr, width, height):
        # ── background ──
        cr.set_source_rgb(0.07, 0.08, 0.09)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        mags  = self._smoothed[:]
        peaks = self.peaks[:]
        n     = len(mags)

        if self.view_mode == "BASS":
            mags  = mags[:n // 4]
            peaks = peaks[:n // 4]
        elif self.view_mode == "MID":
            mags  = mags[n // 4 : n * 3 // 4]
            peaks = peaks[n // 4 : n * 3 // 4]
        elif self.view_mode == "WAVE":
            self._draw_wave(cr, mags, width, height)
            return
        # FULL / MAKS: all bands

        n = len(mags)
        if n == 0:
            return

        bw  = width / n
        gap = max(0.8, bw * 0.18)

        for i in range(n):
            v  = self._norm(mags[i])
            bh = max(1.0, v * (height - 6))
            x  = i * bw + gap
            y  = height - bh
            w  = bw - gap * 2

            # gradient bar: dark green bottom → bright phosphor green top
            pat = None
            try:
                import cairo
                pat = cairo.LinearGradient(0, height, 0, y)
                pat.add_color_stop_rgba(0.0, 0.02, 0.35, 0.18, 0.95)
                pat.add_color_stop_rgba(0.6, 0.05, 0.72, 0.35, 0.92)
                pat.add_color_stop_rgba(1.0, 0.20, 1.00, 0.50, 0.90)
                cr.set_source(pat)
            except Exception:
                cr.set_source_rgba(0.05 + v * 0.15, 0.4 + v * 0.6, 0.25, 0.9)

            cr.rectangle(x, y, w, bh)
            cr.fill()

            # peak marker
            if self.view_mode != "MAKS":
                pv = self._norm(peaks[i])
                py = height - pv * (height - 6) - 2
                cr.set_source_rgba(0.35, 1.0, 0.55, 0.75)
                cr.rectangle(x, py, w, 1.5)
                cr.fill()

        # horizontal grid
        cr.set_line_width(0.5)
        for ratio in (0.25, 0.50, 0.75):
            cr.set_source_rgba(1, 1, 1, 0.04)
            y = height * ratio
            cr.move_to(0, y); cr.line_to(width, y); cr.stroke()

        # freq axis labels
        cr.set_source_rgba(0.38, 0.40, 0.44, 1.0)
        cr.set_font_size(9)
        for lbl, xr in (("0Hz", 0.01), ("5k", 0.25), ("10k", 0.50), ("20k", 0.97)):
            cr.move_to(xr * width, height - 3)
            cr.show_text(lbl)

        # dB labels
        for lbl, yr in (("0dB", 0.02), ("-20", 0.25), ("-40", 0.50), ("-60", 0.75)):
            cr.move_to(width - 26, yr * height + 8)
            cr.show_text(lbl)

    def _draw_wave(self, cr, mags, width, height):
        n = len(mags)
        if n == 0:
            return
        step = width / n
        mid  = height / 2

        # fill shape
        cr.move_to(0, mid)
        for i, db in enumerate(mags):
            v = self._norm(db)
            cr.line_to(i * step, mid - v * mid * 0.88)
        for i in range(n - 1, -1, -1):
            v = self._norm(mags[i])
            cr.line_to(i * step, mid + v * mid * 0.88)
        cr.close_path()
        cr.set_source_rgba(0.10, 0.90, 0.45, 0.12)
        cr.fill_preserve()
        cr.set_source_rgba(0.10, 0.90, 0.45, 0.85)
        cr.set_line_width(1.5)
        cr.stroke()

        # centre line
        cr.set_source_rgba(0.10, 0.90, 0.45, 0.15)
        cr.set_line_width(1)
        cr.move_to(0, mid); cr.line_to(width, mid); cr.stroke()


# ── Main Window ───────────────────────────────────────────────────────────────
class IDRSpectrumWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="IDR Spectrum Player")
        self.idr_rate       = DEFAULT_RATE
        self.is_playing     = False
        self.duration_ns    = 0
        self.current_file   = None
        self._upd_pos       = False   # guard: prevents seek feedback

        self._setup_css()
        self._build_pipeline()
        self._build_ui()
        self.set_default_size(980, 600)

        GLib.timeout_add(400, self._tick)

    # ── CSS ───────────────────────────────────────────────────────────────────
    def _setup_css(self):
        css = b"""
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=IBM+Plex+Sans:wght@400;600;700&display=swap');

        window {
            background-color: #0e0f10;
            color: #c8ccd4;
            font-family: 'IBM Plex Sans', sans-serif;
        }
        .card {
            background-color: #141618;
            border-radius: 14px;
            padding: 20px;
            border: 1px solid #1f2226;
        }
        .rate-display {
            font-size: 30px;
            font-weight: 700;
            color: #f5f5f5;
            letter-spacing: -0.03em;
            line-height: 1.2;
        }
        .mono {
            font-family: 'Share Tech Mono', monospace;
        }
        .dim {
            font-size: 11px;
            color: #555;
        }
        .conv-entry {
            background-color: #1a1c1f;
            color: #d8dae0;
            border: 1px solid #2b2e35;
            border-radius: 8px;
            padding: 7px 10px;
            min-width: 110px;
            font-family: 'Share Tech Mono', monospace;
            font-size: 13px;
        }
        .conv-entry:focus {
            border-color: #2a4fa8;
            background-color: #1d2028;
        }
        .tab-pill {
            background: none;
            border: 1px solid transparent;
            color: #555;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.08em;
        }
        .tab-pill:hover {
            color: #aaa;
            border-color: #2a2d34;
            background-color: #1a1c1f;
        }
        .tab-pill.active {
            background-color: #1d2e5c;
            border-color: #2a4fa8;
            color: #7aacff;
        }
        .player-bar {
            background-color: #141618;
            border-radius: 12px;
            padding: 10px 16px;
            border: 1px solid #1f2226;
        }
        .ctrl-btn {
            background: none;
            border: 1px solid #252830;
            color: #777;
            border-radius: 8px;
            min-width: 36px;
            min-height: 36px;
            padding: 0;
            font-size: 15px;
        }
        .ctrl-btn:hover {
            background-color: #1d2028;
            color: #bbb;
            border-color: #3a3e48;
        }
        .play-btn {
            background-color: #1d2e5c;
            border: 1px solid #2a4fa8;
            color: #7aacff;
            border-radius: 50%;
            min-width: 42px;
            min-height: 42px;
            padding: 0;
            font-size: 16px;
        }
        .play-btn:hover {
            background-color: #233672;
            color: #aaccff;
        }
        .track-label {
            font-size: 11px;
            color: #4a4e58;
            font-style: italic;
        }
        .sarcasm-tag {
            font-size: 10px;
            color: #3a3e48;
            font-family: 'Share Tech Mono', monospace;
            letter-spacing: 0.06em;
        }
        scale trough {
            background-color: #1a1c1f;
            min-height: 3px;
            border-radius: 2px;
        }
        scale highlight {
            background-color: #2a4fa8;
            border-radius: 2px;
        }
        scale slider {
            background-color: #4a80e8;
            border-radius: 50%;
            min-width: 11px;
            min-height: 11px;
            border: none;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

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

        # src → decode (dynamic pad linking)
        self.src.link(self.decode)
        self.decode.connect("pad-added", self._on_pad_added)

        # convert → resample → volume → tee
        self.convert.link(self.resample)
        self.resample.link(self.volume_el)
        self.volume_el.link(self.tee)

        # tee → q_audio → audiosink
        t1 = self.tee.get_request_pad("src_%u")
        t1.link(self.q_audio.get_static_pad("sink"))
        self.q_audio.link(self.audiosink)

        # tee → q_spec → spectrum → fakesink
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
                    GLib.idle_add(self.viz.update, list(mags))

    def _on_eos(self):
        self.pipeline.set_state(Gst.State.READY)
        self.is_playing = False
        self.play_btn.set_label("▶")
        self._upd_pos = True
        self.seek_bar.set_value(0)
        self._upd_pos = False
        self.time_lbl.set_text("0:00 / 0:00")
        return False

    def _query_duration(self):
        ok, d = self.pipeline.query_duration(Gst.Format.TIME)
        if ok and d > 0:
            self.duration_ns = d
        return False

    def _tick(self):
        """Called every 400ms to update seek bar and time label."""
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

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.set_margin_top(14); root.set_margin_bottom(14)
        root.set_margin_start(14); root.set_margin_end(14)

        # ────────────────────────────────── TOP ROW ────────────────────────────
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # ── Left: currency card ──
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        left.add_css_class("card")
        left.set_size_request(310, -1)

        sub_lbl = Gtk.Label(label="1 Dolar Amerika Serikat sama dengan")
        sub_lbl.set_halign(Gtk.Align.START)
        sub_lbl.add_css_class("dim")

        self.rate_lbl = Gtk.Label()
        self.rate_lbl.set_halign(Gtk.Align.START)
        self.rate_lbl.set_wrap(True)
        self.rate_lbl.add_css_class("rate-display")
        self.rate_lbl.add_css_class("mono")
        self._refresh_rate_lbl()

        src_lbl = Gtk.Label(label="7 Jun · Dari Kenangan Pahit · Penafian")
        src_lbl.set_halign(Gtk.Align.START)
        src_lbl.add_css_class("dim")

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(2); sep.set_margin_bottom(2)

        # Converter grid
        grid = Gtk.Grid()
        grid.set_row_spacing(7); grid.set_column_spacing(10)

        self.usd_entry = Gtk.Entry()
        self.usd_entry.set_text("1")
        self.usd_entry.add_css_class("conv-entry")
        usd_lbl = Gtk.Label(label="USD  Dollar Amerika")
        usd_lbl.set_halign(Gtk.Align.START)
        usd_lbl.add_css_class("dim")

        self.idr_entry = Gtk.Entry()
        self.idr_entry.set_text(f"{self.idr_rate:,.2f}")
        self.idr_entry.add_css_class("conv-entry")
        idr_lbl = Gtk.Label(label="IDR  Rupiah Indonesia")
        idr_lbl.set_halign(Gtk.Align.START)
        idr_lbl.add_css_class("dim")

        grid.attach(self.usd_entry, 0, 0, 1, 1)
        grid.attach(usd_lbl,        1, 0, 1, 1)
        grid.attach(self.idr_entry, 0, 1, 1, 1)
        grid.attach(idr_lbl,        1, 1, 1, 1)

        self.usd_entry.connect("changed", self._usd_changed)
        self.idr_entry.connect("changed", self._idr_changed)

        # Custom rate row
        rate_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        rl = Gtk.Label(label="Kurs: 1 USD =")
        rl.add_css_class("dim")
        self.rate_entry = Gtk.Entry()
        self.rate_entry.set_text(f"{self.idr_rate:,.0f}")
        self.rate_entry.set_width_chars(10)
        self.rate_entry.add_css_class("conv-entry")
        self.rate_entry.connect("changed", self._rate_changed)
        rl2 = Gtk.Label(label="IDR")
        rl2.add_css_class("dim")
        rate_row.append(rl)
        rate_row.append(self.rate_entry)
        rate_row.append(rl2)

        sarcs = Gtk.Label(label="// mata uang paling dalam sejarah kejatuhan")
        sarcs.set_halign(Gtk.Align.START)
        sarcs.add_css_class("sarcasm-tag")
        sarcs.set_margin_top(4)

        left.append(sub_lbl)
        left.append(self.rate_lbl)
        left.append(src_lbl)
        left.append(sep)
        left.append(grid)
        left.append(rate_row)
        left.append(sarcs)

        # ── Right: spectrum card ──
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right.add_css_class("card")
        right.set_hexpand(True)

        # Tab row
        tab_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        tab_row.set_halign(Gtk.Align.END)
        self._view_btns: dict = {}
        for mode in ("BASS", "MID", "FULL", "WAVE", "MAKS"):
            b = Gtk.Button(label=mode)
            b.add_css_class("tab-pill")
            if mode == "FULL":
                b.add_css_class("active")
            b.connect("clicked", self._switch_view, mode)
            tab_row.append(b)
            self._view_btns[mode] = b

        self.viz = SpectrumVisualizer()

        right.append(tab_row)
        right.append(self.viz)

        top.append(left)
        top.append(right)

        # ────────────────────────────── PLAYER BAR ────────────────────────────
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bar.add_css_class("player-bar")

        open_btn = Gtk.Button(label="☰")
        open_btn.add_css_class("ctrl-btn")
        open_btn.set_tooltip_text("Buka file musik")
        open_btn.connect("clicked", self._open_file)

        self.play_btn = Gtk.Button(label="▶")
        self.play_btn.add_css_class("play-btn")
        self.play_btn.set_sensitive(False)
        self.play_btn.connect("clicked", self._play_pause)

        self.seek_bar = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        self.seek_bar.set_range(0, 100)
        self.seek_bar.set_draw_value(False)
        self.seek_bar.set_hexpand(True)
        self.seek_bar.connect("change-value", self._on_seek)

        self.time_lbl = Gtk.Label(label="0:00 / 0:00")
        self.time_lbl.set_width_chars(14)
        self.time_lbl.add_css_class("dim")
        self.time_lbl.add_css_class("mono")

        vol_lbl = Gtk.Label(label="Vol")
        vol_lbl.add_css_class("dim")
        self.vol_bar = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        self.vol_bar.set_range(0, 1)
        self.vol_bar.set_value(1.0)
        self.vol_bar.set_draw_value(False)
        self.vol_bar.set_size_request(80, -1)
        self.vol_bar.connect("value-changed", self._on_vol)

        bar.append(open_btn)
        bar.append(self.play_btn)
        bar.append(self.seek_bar)
        bar.append(self.time_lbl)
        bar.append(vol_lbl)
        bar.append(self.vol_bar)

        # Track name strip
        self.track_lbl = Gtk.Label(label="// tidak ada file yang dipilih")
        self.track_lbl.set_halign(Gtk.Align.CENTER)
        self.track_lbl.add_css_class("track-label")
        self.track_lbl.add_css_class("mono")

        root.append(top)
        root.append(self.track_lbl)
        root.append(bar)
        self.set_child(root)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _refresh_rate_lbl(self):
        self.rate_lbl.set_text(f"Rp{self.idr_rate:,.2f}\nRupiah Indonesia")

    def _switch_view(self, _btn, mode: str):
        for m, b in self._view_btns.items():
            b.remove_css_class("active")
        self._view_btns[mode].add_css_class("active")
        self.viz.view_mode = mode
        self.viz.queue_draw()

    @staticmethod
    def _pf(s: str) -> float:
        """Parse float from display string (remove thousand-separator commas)."""
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

    def _rate_changed(self, entry):
        try:
            rate = self._pf(entry.get_text())
            if rate > 0:
                self.idr_rate = rate
                self._refresh_rate_lbl()
                self._usd_changed(self.usd_entry)
        except ValueError:
            pass

    def _open_file(self, _btn):
        dialog = Gtk.FileChooserDialog(
            title="Pilih File Musik",
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.set_transient_for(self)
        dialog.add_button("Batal",     Gtk.ResponseType.CANCEL)
        dialog.add_button("▶  Buka",  Gtk.ResponseType.ACCEPT)

        audio_filter = Gtk.FileFilter()
        audio_filter.set_name("File Audio (mp3, flac, ogg, wav, m4a, opus, aac)")
        for pat in ("*.mp3", "*.flac", "*.ogg", "*.wav", "*.m4a", "*.opus", "*.aac", "*.wma"):
            audio_filter.add_pattern(pat)
        dialog.add_filter(audio_filter)

        all_filter = Gtk.FileFilter()
        all_filter.set_name("Semua file (*)")
        all_filter.add_pattern("*")
        dialog.add_filter(all_filter)

        dialog.connect("response", self._file_chosen)
        dialog.present()

    def _file_chosen(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            path = dialog.get_file().get_path()
            self._load(path)
        dialog.destroy()

    def _load(self, path: str):
        self.current_file = path
        self.pipeline.set_state(Gst.State.NULL)
        self.src.set_property("location", path)
        self.pipeline.set_state(Gst.State.PAUSED)
        self.is_playing = False
        self.play_btn.set_label("▶")
        self.play_btn.set_sensitive(True)
        self.track_lbl.set_text(f"// {os.path.basename(path)}")
        self.duration_ns = 0
        GLib.timeout_add(300, self._query_duration)

    def _play_pause(self, _btn):
        if self.is_playing:
            self.pipeline.set_state(Gst.State.PAUSED)
            self.is_playing = False
            self.play_btn.set_label("▶")
        else:
            self.pipeline.set_state(Gst.State.PLAYING)
            self.is_playing = True
            self.play_btn.set_label("⏸")
            GLib.timeout_add(400, self._query_duration)

    def _on_seek(self, _scale, _scroll_type, value):
        if self._upd_pos:
            return False
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


# ── Application ───────────────────────────────────────────────────────────────
class IDRSpectrumApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="id.ramdanolii.idrspectrum")

    def do_activate(self):
        win = IDRSpectrumWindow(self)
        win.present()


if __name__ == "__main__":
    app = IDRSpectrumApp()
    sys.exit(app.run(sys.argv))