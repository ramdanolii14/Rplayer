# IDR Spectrum Player — Struktur Modular

Script `idr_spectrum_player.py` (2398 baris) telah dipecah menjadi 6 modul
agar lebih mudah dikelola. Semua tetap berada di **direktori yang sama**
(project root, sejajar dengan `assets/`, `scripts/`, `nsis/`).

```
project_root/
├── idr_spectrum_player.py   ← entry point (80 baris)
├── idr_config.py            ← konstanta, config persist, tema & preset warna (286 baris)
├── idr_widgets.py            ← IDRChart, SpectrumVisualizer, MusicLibrary (369 baris)
├── idr_dialogs.py            ← SettingsDialog, AboutDialog (254 baris)
├── idr_window_core.py        ← "engine": state, GStreamer pipeline, CSS, keyboard,
│                                playback inti, helper kurs (684 baris)
├── idr_window_ui.py          ← UI builder + handler interaksi (mixin) (870 baris)
├── build_windows.ps1
├── assets/
│   └── idr_spectrum.ico
├── scripts/
│   ├── idr_spectrum.spec     ← sudah diupdate
│   ├── rthook_gtk_windows.py
│   └── make_icon.sh
└── nsis/
    └── installer.nsi
```

## Pembagian Modul

1. **idr_config.py** — `NUM_BANDS`, `AUDIO_EXTS`, `load_config`/`save_config`,
   `DEFAULT_MUSIC_SVG`, `SPECTRUM_COLORS`, `CHART_COLORS`, `DARK_THEME`,
   `LIGHT_THEME`. Tidak butuh GTK selain `import gi` ringan — modul paling
   "bawah" yang di-import semua modul lain.

2. **idr_widgets.py** — Widget gambar kustom (`IDRChart`, `SpectrumVisualizer`)
   dan model data (`MusicLibrary`, termasuk parser cover art MP3/FLAC/M4A).
   Import dari `idr_config`.

3. **idr_dialogs.py** — `SettingsDialog` (pilih warna spektrum/grafik) dan
   `AboutDialog` (info app + cek versi GitHub). Import dari `idr_config`.

4. **idr_window_core.py** — class `WindowCore(Gtk.ApplicationWindow)`.
   Berisi `__init__`, build pipeline GStreamer, CSS builder, keyboard
   shortcut, bus message handler, spectrum→IDR logic, kontrol play/pause/seek,
   dan helper konversi USD↔IDR. Ini adalah "mesin" jendela.

5. **idr_window_ui.py** — class `WindowUIMixin` (mixin murni, tanpa base
   class). Berisi semua `_build_*` (navbar, panel library, kartu kurs, kartu
   spektrum, player bar), drawing album art, serta handler library/playback
   navigation, toggle tema/shuffle/repeat/spektrum, dan pembuka dialog.

6. **idr_spectrum_player.py** — entry point. Menggabungkan keduanya:

   ```python
   class IDRSpectrumWindow(WindowUIMixin, WindowCore):
       pass
   ```

   lalu mendefinisikan `IDRSpectrumApp(Gtk.Application)` dan blok
   `if __name__ == "__main__":`.

Semua modul sudah dicek dengan `python3 -m py_compile` (lolos tanpa error
sintaks). Karena GTK4/GStreamer tidak tersedia di sandbox ini, runtime test
penuh (membuka jendela) tidak bisa dijalankan di sini — jalankan seperti
biasa di mesin dev MSYS2/Linux kamu.

## Perubahan untuk Build Windows

`scripts/idr_spectrum.spec` diupdate agar PyInstaller bisa menemukan
modul-modul baru:

- `PROJECT_ROOT = Path(SPECPATH).parent` ditambahkan ke `pathex`, sehingga
  `from idr_config import ...` dkk bisa di-resolve sebagai hidden import.
- `hidden_imports` ditambah:
  `idr_config`, `idr_widgets`, `idr_dialogs`, `idr_window_core`, `idr_window_ui`.

Tidak ada perubahan lain yang diperlukan di `build_windows.ps1`,
`installer.nsi`, `rthook_gtk_windows.py`, maupun `make_icon.sh` — semuanya
tetap kompatibel karena PyInstaller akan membundel kelima modul tambahan
otomatis ke dalam satu folder `dist/IDRSpectrum/` seperti sebelumnya
(hanya source-nya yang sekarang terpisah jadi beberapa file).

## Cara Build (sama seperti sebelumnya)

```powershell
# dari project root, PowerShell sebagai Administrator
.\build_windows.ps1 -AppVersion 1.1.0
```

Pastikan semua 6 file `idr_*.py` ada di project root (sejajar dengan
`assets/`, `scripts/`, `nsis/`) sebelum menjalankan build.
