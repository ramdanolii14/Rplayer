# ============================================================
#  Runtime hook — dieksekusi sebelum app dimulai
#  Pastikan GTK4, GStreamer, dan GI menemukan data di dalam bundle
# ============================================================

import os
import sys

def _frozen_base() -> str:
    """Return folder tempat executable / bundle berada."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS  # PyInstaller temp dir
    return os.path.dirname(os.path.abspath(__file__))

BASE = _frozen_base()

# ── GLib schemas ──────────────────────────────────────────────────────────────
os.environ["GSETTINGS_SCHEMA_DIR"] = os.path.join(BASE, "share", "glib-2.0", "schemas")

# ── GDK Pixbuf loaders ───────────────────────────────────────────────────────
loaders_cache = os.path.join(BASE, "lib", "gdk-pixbuf-2.0", "2.10.0", "loaders.cache")
if os.path.exists(loaders_cache):
    os.environ["GDK_PIXBUF_MODULE_FILE"] = loaders_cache

# ── GStreamer plugin path ─────────────────────────────────────────────────────
gst_plugin_path = os.path.join(BASE, "lib", "gstreamer-1.0")
os.environ["GST_PLUGIN_PATH"]          = gst_plugin_path
os.environ["GST_PLUGIN_PATH_1_0"]      = gst_plugin_path
os.environ["GST_PLUGIN_SYSTEM_PATH"]   = gst_plugin_path
os.environ["GST_PLUGIN_SYSTEM_PATH_1_0"] = gst_plugin_path
# Nonaktifkan registry scanning agar startup lebih cepat
os.environ.setdefault("GST_REGISTRY_FORK", "no")

# ── GI typelib path ───────────────────────────────────────────────────────────
typelib_path = os.path.join(BASE, "lib", "girepository-1.0")
existing = os.environ.get("GI_TYPELIB_PATH", "")
os.environ["GI_TYPELIB_PATH"] = (
    f"{typelib_path}{os.pathsep}{existing}" if existing else typelib_path
)

# ── GTK icons ─────────────────────────────────────────────────────────────────
os.environ["GTK_DATA_PREFIX"] = BASE

# ── PATH: tambahkan bin bundle ke depan supaya DLL ditemukan ─────────────────
bundle_bin = BASE
existing_path = os.environ.get("PATH", "")
os.environ["PATH"] = f"{bundle_bin}{os.pathsep}{existing_path}"

# ── Librsvg loaders ──────────────────────────────────────────────────────────
os.environ.setdefault(
    "RSVG_LOADERS_PATH",
    os.path.join(BASE, "lib", "librsvg-2")
)
