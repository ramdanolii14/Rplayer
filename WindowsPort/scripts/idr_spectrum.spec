# -*- mode: python ; coding: utf-8 -*-
# ============================================================
#  IDR Spectrum Player — PyInstaller Spec (MSYS2 / MinGW64)
#  Jalankan dari dalam MSYS2 mingw64 shell:
#    python -m PyInstaller scripts/idr_spectrum.spec --noconfirm
# ============================================================

import os
import sys
import glob
from pathlib import Path

# ── Resolve MSYS2 prefix ──────────────────────────────────────────────────────
MINGW = Path(os.environ.get("MINGW_PREFIX", "/mingw64"))
assert MINGW.exists(), f"MINGW_PREFIX not found: {MINGW}"

# ── Helper: collect directory tree as datas tuples ───────────────────────────
def collect_dir(src: Path, dst: str):
    result = []
    for f in src.rglob("*"):
        if f.is_file():
            rel = f.relative_to(src.parent)
            result.append((str(f), str(Path(dst) / rel.parent)))
    return result

# ── Source script ─────────────────────────────────────────────────────────────
src_script = "idr_spectrum_player.py"   # letakkan 1 level di atas scripts/

# ── Hidden imports ────────────────────────────────────────────────────────────
hidden_imports = [
    "gi",
    "gi.repository.Gtk",
    "gi.repository.Gdk",
    "gi.repository.Gst",
    "gi.repository.GLib",
    "gi.repository.Gio",
    "gi.repository.GObject",
    "gi.repository.Cairo",
    "gi.repository.Pango",
    "gi.repository.PangoCairo",
    "gi.repository.GdkPixbuf",
    "gi.repository.Rsvg",
    "cairo",
    "json",
    "math",
    "random",
    "pathlib",
    "mutagen",
    "mutagen.mp3",
    "mutagen.flac",
    "mutagen.oggvorbis",
    "mutagen.mp4",
    "mutagen.asf",
    "mutagen.id3",
    "email",
]

# ── Binaries: GStreamer plugins ───────────────────────────────────────────────
gst_plugin_dir = MINGW / "lib" / "gstreamer-1.0"
binaries = []

# Plugin yang diperlukan untuk audio playback
needed_plugins = [
    "libgstcoreelements*",
    "libgstplayback*",
    "libgstaudioconvert*",
    "libgstaudioresample*",
    "libgstvolume*",
    "libgstautodetect*",
    "libgstaudiotestsrc*",
    "libgstspectrum*",
    "libgstlevel*",
    "libgstwasapi*",
    "libgstdirectsound*",
    "libgstlibav*",
    "libgstflac*",
    "libgstogg*",
    "libgstvorbis*",
    "libgstopus*",
    "libgstmpg123*",
    "libgstwavparse*",
    "libgstisomp4*",
    "libgstasf*",
    "libgsttypefindfunctions*",
    "libgstapp*",
    "libgstgio*",
    "libgstid3demux*",
    "libgstapetag*",
]

for pattern in needed_plugins:
    for found in gst_plugin_dir.glob(pattern):
        binaries.append((str(found), "lib/gstreamer-1.0"))

# ── Datas: GTK schemas, icons, locale ─────────────────────────────────────────
datas = []

# GLib schemas (wajib untuk GTK4)
schemas_src = MINGW / "share" / "glib-2.0" / "schemas"
datas.append((str(schemas_src), "share/glib-2.0/schemas"))

# GTK4 default icons (minimal — Adwaita)
icons_src = MINGW / "share" / "icons" / "Adwaita"
if icons_src.exists():
    datas += collect_dir(icons_src, "share/icons/Adwaita")

# GDK pixbuf loaders
loaders_dir = MINGW / "lib" / "gdk-pixbuf-2.0"
if loaders_dir.exists():
    datas += collect_dir(loaders_dir, "lib/gdk-pixbuf-2.0")

# Typelibs (gi introspection)
typelib_dir = MINGW / "lib" / "girepository-1.0"
needed_typelibs = [
    "Gtk-4.0.typelib",
    "Gdk-4.0.typelib",
    "GdkWin32-4.0.typelib",
    "Gst-1.0.typelib",
    "GstBase-1.0.typelib",
    "GstPbutils-1.0.typelib",
    "GstAudio-1.0.typelib",
    "GLib-2.0.typelib",
    "GObject-2.0.typelib",
    "Gio-2.0.typelib",
    "cairo-1.0.typelib",
    "Pango-1.0.typelib",
    "PangoCairo-1.0.typelib",
    "GdkPixbuf-2.0.typelib",
    "Rsvg-2.0.typelib",
    "Graphene-1.0.typelib",
]
for tl in needed_typelibs:
    p = typelib_dir / tl
    if p.exists():
        datas.append((str(p), "lib/girepository-1.0"))

# GTK4 settings (dark theme support)
gtk4_settings = MINGW / "share" / "gtk-4.0"
if gtk4_settings.exists():
    datas += collect_dir(gtk4_settings, "share/gtk-4.0")

# Librsvg (untuk SVG album art default)
rsvg_loaders = MINGW / "lib" / "librsvg-2"
if rsvg_loaders.exists():
    datas += collect_dir(rsvg_loaders, "lib/librsvg-2")

# ── Runtime hooks ─────────────────────────────────────────────────────────────
runtime_hooks = ["scripts/rthook_gtk_windows.py"]

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    [f"../{src_script}"],
    pathex=[str(MINGW / "lib" / "python3.12" / "site-packages")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=["tkinter", "unittest", "test", "xmlrpc"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="IDRSpectrum",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # tidak ada cmd window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
   icon="../assets/idr_spectrum.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="IDRSpectrum",
)
