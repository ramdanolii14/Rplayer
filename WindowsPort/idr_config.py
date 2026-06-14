#!/usr/bin/env python3
# ============================================================
#  idr_config.py
#  Konstanta global, persistent config (JSON), preset warna
#  spektrum & grafik, serta definisi tema Dark/Light.
#
#  Bagian dari IDR Spectrum Player — dipecah dari
#  idr_spectrum_player.py agar lebih mudah dikelola.
# ============================================================

import os
import sys
import json
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────
NUM_BANDS       = 80
DEFAULT_RATE    = 18_000.0
SPECTRUM_NS     = 35_000_000
IDR_MIN         = 18_000.0
IDR_MAX         = 18_999.0
HISTORY_LEN     = 120        # titik di grafik kurs

AUDIO_EXTS = {".mp3", ".flac", ".ogg", ".wav", ".m4a", ".opus", ".aac", ".wma"}

# ── Persistent Config ─────────────────────────────────────────────────────────
# Windows: %APPDATA%\idr-spectrum  |  Linux/macOS: ~/.config/idr-spectrum
if sys.platform == "win32":
    _cfg_base = Path(os.environ.get("APPDATA", Path.home()))
else:
    _cfg_base = Path.home() / ".config"
CONFIG_DIR  = _cfg_base / "idr-spectrum"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "is_dark":       True,
    "spec_color":    "Hijau",
    "chart_color":   "Biru",
    "spec_visible":  True,
    "shuffle":       False,
    "repeat_mode":   "none",
    "volume":        1.0,
    "library":       [],
    "current_idx":   -1,
}

def load_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # merge dengan default agar key baru selalu ada
            cfg = dict(DEFAULT_CONFIG)
            cfg.update(data)
            return cfg
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Config] Gagal menyimpan: {e}")

# ── Default Music SVG Icon ────────────────────────────────────────────────────
DEFAULT_MUSIC_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 56 56">
  <rect width="56" height="56" rx="10" fill="#1a1c20"/>
  <circle cx="28" cy="28" r="20" fill="#212429"/>
  <circle cx="28" cy="28" r="12" fill="#141618"/>
  <circle cx="28" cy="28" r="4" fill="#2a4fa8"/>
  <path d="M22 20 L22 36 L38 28 Z" fill="#7aacff" opacity="0.7"/>
</svg>"""

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
