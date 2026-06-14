#!/usr/bin/env python3
# ============================================================
#  idr_spectrum_player.py
#  Entry point IDR Spectrum Player.
#
#  Menggabungkan WindowCore (idr_window_core) dan WindowUIMixin
#  (idr_window_ui) menjadi IDRSpectrumWindow, lalu menjalankan
#  Gtk.Application (IDRSpectrumApp).
#
#  Struktur modul:
#    idr_config.py       - konstanta, config persist, tema/warna
#    idr_widgets.py       - IDRChart, SpectrumVisualizer, MusicLibrary
#    idr_dialogs.py       - SettingsDialog, AboutDialog
#    idr_window_core.py   - WindowCore (state, pipeline, CSS, playback)
#    idr_window_ui.py     - WindowUIMixin (UI & handler interaksi)
#    idr_spectrum_player.py - file ini (entry point)
# ============================================================

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gst", "1.0")

from gi.repository import Gtk, Gst, Gio
import sys
from pathlib import Path

Gst.init(None)

from idr_config import AUDIO_EXTS, save_config
from idr_window_core import WindowCore
from idr_window_ui import WindowUIMixin


# ── Main Window (gabungan UI mixin + core engine) ────────────────────────────
class IDRSpectrumWindow(WindowUIMixin, WindowCore):
    """IDRSpectrumWindow = WindowUIMixin (UI & handler) + WindowCore (engine)."""
    pass


# ── Application ────────────────────────────────────────────────────────────────
class IDRSpectrumApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="id.ramdanolii.idrspectrum",
            # HANDLES_OPEN: Gio akan routing argv berisi path file ke do_open()
            # Ini yang membuat double-click file dari Windows Explorer bisa kerja
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )
        self._win: IDRSpectrumWindow | None = None

    def do_activate(self):
        if self._win is None:
            self._win = IDRSpectrumWindow(self)
        self._win.present()

    def do_open(self, files, n_files, hint):
        """Dipanggil saat app diluncurkan dengan argumen file (file association Windows)."""
        self.do_activate()  # pastikan window sudah ada
        win = self._win
        if win is None:
            return
        for gfile in files:
            path = gfile.get_path()
            if path and Path(path).suffix.lower() in AUDIO_EXTS:
                win.library.add(path)
        win._refresh_library_ui()
        # Mainkan file pertama dari argumen
        if files:
            first_path = files[0].get_path()
            if first_path:
                try:
                    idx = win.library.tracks.index(first_path)
                    win._play_index(idx)
                except ValueError:
                    pass
        save_config(win._build_current_config())


if __name__ == "__main__":
    app = IDRSpectrumApp()
    sys.exit(app.run(sys.argv))