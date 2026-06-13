# IDR Spectrum Player — Windows Build Guide

## Struktur Folder

```
idr-windows/
├── build_windows.ps1          ← Main script (jalankan ini)
├── LICENSE.txt
├── idr_spectrum_player.py     ← Copy source app ke sini
├── assets/
│   └── idr_spectrum.ico       ← Di-generate oleh make_icon.sh
├── scripts/
│   ├── idr_spectrum.spec      ← PyInstaller spec
│   ├── rthook_gtk_windows.py  ← Runtime hook GTK env vars
│   └── make_icon.sh           ← Generate .ico dari SVG
└── nsis/
    └── installer.nsi          ← NSIS installer script
```

## Prerequisite (install sekali saja)

| Tool | Link |
|------|------|
| MSYS2 | https://www.msys2.org — install ke `C:\msys64` |
| NSIS 3.x | https://nsis.sourceforge.io/Download — install default path |

## Langkah Build

### 1. Persiapan
```
# Copy source file ke root folder ini
cp /path/to/idr_spectrum_player.py .
```

### 2. Buat icon (dari MSYS2 mingw64 shell)
```bash
# Install imagemagick dulu jika belum
pacman -S --needed mingw-w64-x86_64-imagemagick

# Generate .ico
bash scripts/make_icon.sh
```

### 3. Jalankan build (PowerShell sebagai Administrator)
```powershell
# Full build (install MSYS2 packages + PyInstaller + NSIS)
.\build_windows.ps1 -AppVersion "1.1.0"

# Skip MSYS2 package install (kalau sudah pernah)
.\build_windows.ps1 -SkipPackages

# Skip semua, hanya rebuild installer
.\build_windows.ps1 -SkipMSYS2Install -SkipPackages -SkipBuild
```

### 4. Output
```
IDRSpectrum-Setup-1.1.0.exe   ← Installer siap distribusi
dist/IDRSpectrum/             ← Folder portable (bisa jalan tanpa install)
```

## Yang dilakukan Installer

- Install ke `C:\Program Files\IDRSpectrum\`
- Buat shortcut di Start Menu dan Desktop
- Daftar di **Settings → Apps → Installed Apps** (bisa uninstall dari sana)
- Register file association untuk `.mp3 .flac .ogg .wav .m4a .opus .aac`
- Saat uninstall: tanya apakah hapus config/playlist user

## Troubleshooting

### App tidak mau start
```powershell
# Jalankan dari cmd untuk lihat error
cd "C:\Program Files\IDRSpectrum"
IDRSpectrum.exe
```

### GStreamer tidak play audio
Pastikan plugin `libgstwasapi` atau `libgstdirectsound` ada di `lib\gstreamer-1.0\`.
Cek via MSYS2:
```bash
gst-inspect-1.0 wasapisink
```

### GTK error "Could not load schema"
Jalankan manual:
```bash
glib-compile-schemas "C:\Program Files\IDRSpectrum\share\glib-2.0\schemas"
```

### Build error: Python version
Spec file pakai `python3.12` di pathex. Cek versi Python di MSYS2:
```bash
python --version
```
Kalau beda, edit baris `pathex` di `idr_spectrum.spec`.

## Size Estimasi Bundle

| Komponen | Ukuran |
|----------|--------|
| Python runtime | ~15 MB |
| GTK4 + deps | ~80 MB |
| GStreamer + plugins | ~60 MB |
| App code | ~0.5 MB |
| **Total compressed** | **~70–90 MB** |

> Bundle akan besar karena GTK4 + GStreamer membawa banyak DLL.
> Ini normal untuk aplikasi GTK native di Windows.
