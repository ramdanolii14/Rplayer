#!/usr/bin/env bash
# ============================================================
#  Buat idr_spectrum.ico dari SVG default
#  Jalankan dari MSYS2 mingw64 shell
#  Requires: imagemagick (pacman -S mingw-w64-x86_64-imagemagick)
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ASSETS_DIR="$SCRIPT_DIR/../assets"
mkdir -p "$ASSETS_DIR"

# SVG inline (sama dengan DEFAULT_MUSIC_SVG di app)
SVG_CONTENT='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <rect width="256" height="256" rx="40" fill="#1a1c20"/>
  <circle cx="128" cy="128" r="90" fill="#212429"/>
  <circle cx="128" cy="128" r="54" fill="#141618"/>
  <circle cx="128" cy="128" r="18" fill="#2a4fa8"/>
  <path d="M100 90 L100 166 L170 128 Z" fill="#7aacff" opacity="0.85"/>
  <text x="128" y="230" font-family="monospace" font-size="28"
        text-anchor="middle" fill="#3a3e48">IDR</text>
</svg>'

echo "$SVG_CONTENT" > /tmp/idr_icon.svg

# Convert ke berbagai ukuran lalu gabung jadi .ico
magick /tmp/idr_icon.svg \
    \( -clone 0 -resize 16x16   \) \
    \( -clone 0 -resize 24x24   \) \
    \( -clone 0 -resize 32x32   \) \
    \( -clone 0 -resize 48x48   \) \
    \( -clone 0 -resize 64x64   \) \
    \( -clone 0 -resize 128x128 \) \
    \( -clone 0 -resize 256x256 \) \
    -delete 0 \
    "$ASSETS_DIR/idr_spectrum.ico"

echo "Icon dibuat: $ASSETS_DIR/idr_spectrum.ico"
