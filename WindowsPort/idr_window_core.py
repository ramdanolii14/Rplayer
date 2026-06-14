#!/usr/bin/env python3
# ============================================================
#  idr_window_core.py
#  "Engine" jendela utama: state, konfigurasi, GStreamer
#  pipeline, CSS, keyboard shortcut, playback control inti,
#  dan helper konversi mata uang.
#
#  Digabung dengan idr_window_ui.WindowUIMixin di
#  idr_spectrum_player.py untuk membentuk IDRSpectrumWindow.
#
#  Bagian dari IDR Spectrum Player.
# ============================================================

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gst", "1.0")
from gi.repository import Gtk, Gdk, Gst, GLib, GdkPixbuf

import sys
import random
from pathlib import Path

from idr_config import (
    DARK_THEME, LIGHT_THEME,
    load_config, save_config,
    NUM_BANDS, SPECTRUM_NS, DEFAULT_RATE,
    IDR_MIN, IDR_MAX, HISTORY_LEN,
)
from idr_widgets import MusicLibrary


class WindowCore(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="IDR Spectrum Player")

        # Set icon — akan muncul di taskbar / dock
        # Di Windows tidak ada XDG icon theme; load .ico dari bundle secara eksplisit
        if sys.platform == "win32":
            _ico_candidates = [
                # PyInstaller frozen bundle
                Path(getattr(sys, "_MEIPASS", "")) / "idr_spectrum.ico",
                # Development tree
                Path(__file__).parent / "assets" / "idr_spectrum.ico",
                Path(__file__).parent.parent / "assets" / "idr_spectrum.ico",
            ]
            for _ico in _ico_candidates:
                if _ico.exists():
                    try:
                        self.set_icon_name(None)
                        _pb = GdkPixbuf.Pixbuf.new_from_file(str(_ico))
                        _tex = Gdk.Texture.new_for_pixbuf(_pb)
                        self.set_icon_paintable(_tex)  # GTK4
                    except Exception:
                        pass
                    break
        else:
            self.set_icon_name("id.ramdanolii.idrspectrum")

        # ── Load persistent config ──
        self._cfg           = load_config()
        self.is_dark        = self._cfg["is_dark"]
        self.theme          = DARK_THEME if self.is_dark else LIGHT_THEME
        self.idr_rate       = DEFAULT_RATE
        self.is_playing     = False
        self.duration_ns    = 0
        self.current_file   = None
        self._upd_pos       = False
        self.spec_visible   = self._cfg["spec_visible"]
        self.shuffle        = self._cfg["shuffle"]
        self.repeat_mode    = self._cfg["repeat_mode"]
        self.library        = MusicLibrary()
        self.current_idx    = -1
        self._idr_history   = [IDR_MIN] * HISTORY_LEN
        self._spec_color    = self._cfg["spec_color"]
        self._chart_color   = self._cfg["chart_color"]

        self._setup_css()
        self._build_pipeline()
        self._build_ui()
        self.set_default_size(1050, 680)

        # ── Restore library from config ──
        saved_lib = self._cfg.get("library", [])
        for path in saved_lib:
            self.library.add(path)
        if self.library.tracks:
            self._refresh_library_ui()

        # Restore volume
        vol = self._cfg.get("volume", 1.0)
        self.vol_bar.set_value(vol)
        self.volume_el.set_property("volume", vol)

        # Restore spectrum visibility
        self._viz_revealer.set_reveal_child(self.spec_visible)
        if not self.spec_visible:
            self.hide_spec_btn.set_label("⊞")
            self.hide_spec_btn.set_tooltip_text("Tampilkan spektrum")
            self.hide_spec_btn.add_css_class("active")

        # Restore shuffle/repeat UI state
        if self.shuffle:
            self.shuffle_btn.add_css_class("active")
        modes  = ["none", "all", "one"]
        labels = {"none": "↺", "all": "↺↺", "one": "①"}
        self.repeat_btn.set_label(labels[self.repeat_mode])
        if self.repeat_mode != "none":
            self.repeat_btn.add_css_class("active")

        # Restore theme button label
        self.theme_btn.set_label("☀" if self.is_dark else "☾")

        # ── Restore warna spektrum & grafik dari config ──
        self.viz.color_preset = self._spec_color
        self.chart.color_preset = self._chart_color

        # Auto-save config setiap 30 detik
        GLib.timeout_add(30_000, self._autosave_config)

        GLib.timeout_add(400, self._tick)
        GLib.timeout_add(100, self._spectrum_idr_tick)

        # ── Keyboard shortcuts (window-level CAPTURE agar tidak dibajak button) ──
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrl)

    # ── Keyboard Shortcuts ────────────────────────────────────────────────────
    def _on_key_pressed(self, _ctrl, keyval, _keycode, state):
        """Handle global keyboard shortcuts. Dipanggil SEBELUM widget manapun."""
        ctrl  = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        # Abaikan modifier lain selain Ctrl dan Shift
        only_ctrl  = ctrl and not shift
        no_mod     = not ctrl and not shift


        # ── Play / Pause ── Space
        if keyval == Gdk.KEY_space and no_mod:
            if self.current_file:
                self._play_pause(None)
            return True

        # ── Navigasi track ──
        if keyval == Gdk.KEY_Right and only_ctrl:
            self._next_track(None)
            return True
        if keyval == Gdk.KEY_Left and only_ctrl:
            self._prev_track(None)
            return True

        # ── Seek ± 5 detik ── ← → tanpa modifier
        if keyval == Gdk.KEY_Right and no_mod:
            self._seek_relative(+5)
            return True
        if keyval == Gdk.KEY_Left and no_mod:
            self._seek_relative(-5)
            return True

        # ── Volume ── Ctrl+↑ / Ctrl+↓
        if keyval == Gdk.KEY_Up and only_ctrl:
            v = min(1.0, self.vol_bar.get_value() + 0.1)
            self.vol_bar.set_value(v)
            return True
        if keyval == Gdk.KEY_Down and only_ctrl:
            v = max(0.0, self.vol_bar.get_value() - 0.1)
            self.vol_bar.set_value(v)
            return True

        # ── Shuffle ── S
        if keyval in (Gdk.KEY_s, Gdk.KEY_S) and no_mod:
            self._toggle_shuffle(None)
            return True

        # ── Repeat ── R
        if keyval in (Gdk.KEY_r, Gdk.KEY_R) and no_mod:
            self._toggle_repeat(None)
            return True

        # ── Toggle spektrum ── H (Hide)
        if keyval in (Gdk.KEY_h, Gdk.KEY_H) and no_mod:
            self._toggle_spectrum(None)
            return True

        # ── Buka file ── Ctrl+O
        if keyval in (Gdk.KEY_o, Gdk.KEY_O) and only_ctrl:
            self._open_file(None)
            return True

        return False

    def _seek_relative(self, seconds: float):
        """Seek maju/mundur sejumlah detik dari posisi saat ini."""
        if self.duration_ns <= 0:
            return
        ok, pos = self.pipeline.query_position(Gst.Format.TIME)
        if not ok:
            return
        new_pos = max(0, min(self.duration_ns, pos + int(seconds * Gst.SECOND)))
        self.pipeline.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            new_pos,
        )

    # ── Config Persistence ────────────────────────────────────────────────────
    def _build_current_config(self) -> dict:
        return {
            "is_dark":      self.is_dark,
            "spec_color":   self._spec_color,
            "chart_color":  self._chart_color,
            "spec_visible": self.spec_visible,
            "shuffle":      self.shuffle,
            "repeat_mode":  self.repeat_mode,
            "volume":       self.vol_bar.get_value(),
            "library":      list(self.library.tracks),
            "current_idx":  self.current_idx,
        }

    def _autosave_config(self):
        save_config(self._build_current_config())
        return True  # terus berulang

    # ── CSS ───────────────────────────────────────────────────────────────────
    def _build_css(self):
        t = self.theme
        return f"""
        window {{
            background-color: {t['window_bg']};
            color: {t['text_primary']};
            font-family: 'IBM Plex Sans', 'Noto Sans', 'Segoe UI', Arial, sans-serif;
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
            font-family: 'Share Tech Mono', 'Consolas', 'Courier New', monospace;
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
            font-family: 'Share Tech Mono', 'Consolas', 'Courier New', monospace;
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
            font-family: 'Share Tech Mono', 'Consolas', 'Courier New', monospace;
            letter-spacing: 0.06em;
        }}
        scale trough,
        scale > trough {{
            background-color: {t['scale_trough']};
            min-height: 3px;
            border-radius: 2px;
        }}
        scale highlight,
        scale > trough > highlight {{
            background-color: {t['scale_hl']};
            border-radius: 2px;
        }}
        scale slider,
        scale > trough > slider {{
            background-color: {t['scale_slider']};
            border-radius: 50%;
            min-width: 11px;
            min-height: 11px;
            border: none;
            box-shadow: none;
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
            font-family: 'Share Tech Mono', 'Consolas', 'Courier New', monospace;
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
        .lib-add-btn {{
            background-color: {t['entry_bg']};
            border: 1px solid {t['entry_border']};
            border-radius: 8px;
            padding: 7px 10px;
            color: {t['text_primary']};
            font-size: 12px;
        }}
        .lib-add-btn:hover {{
            background-color: {t['list_item_hover']};
            border-color: {t['tab_active_bd']};
            color: {t['tab_active_fg']};
        }}
        .lib-clear-btn {{
            background: none;
            border: none;
            color: {t['text_muted']};
            font-size: 10px;
            padding: 2px 4px;
            border-radius: 4px;
        }}
        .lib-clear-btn:hover {{
            color: #e05555;
            background-color: rgba(224,85,85,0.08);
        }}
        dialog {{
            background-color: {t['window_bg']};
            color: {t['text_primary']};
        }}
        dialog > .dialog-vbox,
        dialog .dialog-vbox,
        dialog contents,
        dialog > contents {{
            background-color: {t['window_bg']};
            color: {t['text_primary']};
        }}
        dialog .card {{
            background-color: {t['card_bg']};
        }}
        menubutton button {{
            background: none;
            border: 1px solid {t['ctrl_border']};
            color: {t['ctrl_fg']};
            border-radius: 8px;
            min-width: 30px;
            min-height: 28px;
            padding: 0 6px;
            font-size: 15px;
            box-shadow: none;
            outline: none;
        }}
        menubutton button:hover {{
            background-color: {t['entry_bg']};
            color: {t['text_primary']};
            border-color: {t['entry_border']};
            box-shadow: none;
        }}
        menubutton button:active,
        menubutton button:checked {{
            background-color: {t['entry_bg']};
            color: {t['text_primary']};
            border-color: {t['entry_border']};
            box-shadow: none;
        }}
        menubutton button:focus {{
            box-shadow: none;
            outline: none;
        }}
        popover contents,
        popover > contents {{
            background-color: {t['card_bg']};
            border: 1px solid {t['card_border']};
            border-radius: 10px;
            padding: 2px;
        }}
        popover arrow,
        popover > arrow {{
            background-color: {t['card_bg']};
        }}
        popover button.flat {{
            background: none;
            border: none;
            border-radius: 6px;
            color: {t['text_primary']};
            padding: 8px 14px;
            font-size: 12px;
            min-width: 180px;
        }}
        popover button.flat:hover {{
            background-color: {t['list_item_hover']};
            color: {t['text_primary']};
        }}
        popover button.flat:active {{
            background-color: {t['tab_active_bg']};
            color: {t['tab_active_fg']};
        }}

        /* ── Scrollbar dark mode (Win32 GTK4 sering bocor putih) ──────────── */
        scrollbar {{
            background-color: {t['card_bg']};
            border: none;
        }}
        scrollbar trough {{
            background-color: {t['card_bg']};
            border-radius: 6px;
            min-width: 6px;
            min-height: 6px;
        }}
        scrollbar slider {{
            background-color: {t['text_dim']};
            border-radius: 6px;
            min-width: 6px;
            min-height: 40px;
            border: 2px solid {t['card_bg']};
        }}
        scrollbar slider:hover {{
            background-color: {t['text_muted']};
        }}
        scrollbar.vertical slider {{
            min-width: 6px;
        }}
        scrollbar.horizontal slider {{
            min-height: 6px;
        }}

        /* ── ScrolledWindow container ──────────────────────────────────────── */
        scrolledwindow {{
            background-color: {t['list_bg']};
            border: none;
        }}
        scrolledwindow undershoot.top,
        scrolledwindow undershoot.bottom,
        scrolledwindow undershoot.left,
        scrolledwindow undershoot.right {{
            background: none;
        }}
        scrolledwindow overshoot.top,
        scrolledwindow overshoot.bottom {{
            background: none;
        }}

        /* ── Entry / SearchEntry ────────────────────────────────────────────── */
        entry {{
            background-color: {t['entry_bg']};
            color: {t['entry_text']};
            border: 1px solid {t['entry_border']};
            border-radius: 8px;
            padding: 6px 10px;
            caret-color: {t['text_primary']};
            box-shadow: none;
        }}
        entry:focus {{
            border-color: {t['tab_active_bd']};
            box-shadow: none;
        }}
        entry selection {{
            background-color: {t['tab_active_bg']};
            color: {t['tab_active_fg']};
        }}
        text {{
            background-color: {t['entry_bg']};
            color: {t['entry_text']};
        }}

        /* ── ListView / ListBox (library list) ─────────────────────────────── */
        listview,
        listbox {{
            background-color: {t['list_bg']};
            color: {t['text_primary']};
            border: none;
        }}
        listview > row,
        listbox > row {{
            background-color: {t['list_item_bg']};
            color: {t['text_primary']};
            border: none;
            padding: 0;
        }}
        listview > row:hover,
        listbox > row:hover {{
            background-color: {t['list_item_hover']};
        }}
        listview > row:selected,
        listbox > row:selected {{
            background-color: {t['list_sel_bg']};
            color: {t['list_sel_fg']};
        }}

        /* ── Viewport (container dalam ScrolledWindow) ──────────────────────── */
        viewport {{
            background-color: {t['list_bg']};
            border: none;
        }}

        /* ── HeaderBar (titlebar Windows bisa bocor terang) ─────────────────── */
        headerbar {{
            background-color: {t['card_bg']};
            color: {t['text_primary']};
            border-bottom: 1px solid {t['card_border']};
            box-shadow: none;
        }}
        headerbar .title {{
            color: {t['text_primary']};
        }}

        /* ── Tooltip ────────────────────────────────────────────────────────── */
        tooltip {{
            background-color: {t['card_bg']};
            color: {t['text_primary']};
            border: 1px solid {t['card_border']};
            border-radius: 6px;
            padding: 4px 8px;
        }}
        tooltip label {{
            color: {t['text_primary']};
        }}

        /* ── Label default fallback ─────────────────────────────────────────── */
        label {{
            color: {t['text_primary']};
        }}

        /* ── Box & Frame ─────────────────────────────────────────────────────── */
        frame {{
            background-color: {t['card_bg']};
            border: 1px solid {t['card_border']};
            border-radius: 8px;
        }}
        frame > border {{
            border: none;
        }}

        /* ── Revealer / Overlay ─────────────────────────────────────────────── */
        revealer > * {{
            background-color: transparent;
        }}

        /* ── Check & Radio button ───────────────────────────────────────────── */
        checkbutton,
        radiobutton {{
            color: {t['text_primary']};
            background: none;
        }}
        check,
        radio {{
            background-color: {t['entry_bg']};
            border: 1px solid {t['entry_border']};
            border-radius: 4px;
        }}
        check:checked,
        radio:checked {{
            background-color: {t['tab_active_bg']};
            border-color: {t['tab_active_bd']};
            color: {t['tab_active_fg']};
        }}

        /* ── Separator ──────────────────────────────────────────────────────── */
        separator {{
            background-color: {t['sep_color']};
            min-height: 1px;
            min-width: 1px;
        }}

        /* ── SpinButton ─────────────────────────────────────────────────────── */
        spinbutton {{
            background-color: {t['entry_bg']};
            color: {t['entry_text']};
            border: 1px solid {t['entry_border']};
            border-radius: 8px;
        }}
        spinbutton button {{
            background: none;
            border: none;
            color: {t['text_muted']};
        }}
        spinbutton button:hover {{
            background-color: {t['list_item_hover']};
            color: {t['text_primary']};
        }}

        /* ── ComboBox / DropDown ────────────────────────────────────────────── */
        combobox,
        dropdown {{
            background-color: {t['entry_bg']};
            color: {t['entry_text']};
            border: 1px solid {t['entry_border']};
            border-radius: 8px;
        }}
        combobox button,
        dropdown button {{
            background-color: {t['entry_bg']};
            color: {t['entry_text']};
            border: none;
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
        self._album_art.queue_draw()

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

    @staticmethod
    def _parse_gst_float_list(s: "Gst.Structure", field: str) -> list:
        """
        Parse GstValueList dari Gst.Structure secara aman di semua platform.

        Di Linux PyGObject, s.get_value("magnitude") langsung mengembalikan list.
        Di Windows PyGObject (binding lebih tua / build MSYS2), tipe GstValueList
        tidak terdaftar sehingga get_value() melempar TypeError.

        Workaround: serialisasi structure ke string lalu parse manual.
        Format: ... magnitude=(GValueArray){ -80.0, -75.3, ... } ...
        """
        # ── Coba cara normal dulu (Linux/versi baru) ──────────────────────────
        try:
            result = s.get_value(field)
            if result is not None:
                return list(result)
        except TypeError:
            pass  # fallthrough ke string parsing

        # ── Fallback: parse dari repr string structure ────────────────────────
        try:
            text = s.to_string()
            # Cari field, ambil isi antara { ... }
            marker = f"{field}="
            idx = text.find(marker)
            if idx == -1:
                return []
            rest = text[idx + len(marker):]
            # Lewati tipe opsional misal "(GValueArray)" atau "< float, ... >"
            brace_start = rest.find("{")
            brace_end   = rest.find("}")
            if brace_start == -1 or brace_end == -1:
                return []
            inner = rest[brace_start + 1 : brace_end]
            values = []
            for token in inner.split(","):
                token = token.strip().rstrip(";")
                if not token:
                    continue
                try:
                    values.append(float(token))
                except ValueError:
                    pass
            return values
        except Exception:
            return []

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
                mags = self._parse_gst_float_list(s, "magnitude")
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
        # Hanya drift saat tidak ada file yang di-load (bukan saat pause)
        if not self.is_playing and self.current_file is None:
            drift = random.gauss(0, 8)
            self.idr_rate = max(IDR_MIN, min(IDR_MAX, self.idr_rate + drift))
            self.chart.push(self.idr_rate)
            self._refresh_rate_lbl()
        return True