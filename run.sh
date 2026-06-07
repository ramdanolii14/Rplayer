#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
#  IDR Spectrum Player — Setup Script
#  Arch Linux / Manjaro
# ──────────────────────────────────────────────────────────────────────────────

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
DIM='\033[2m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}"
echo "  ██╗██████╗ ██████╗     ███████╗██████╗ ███████╗ ██████╗████████╗██████╗ ██╗   ██╗███╗   ███╗"
echo "  ██║██╔══██╗██╔══██╗    ██╔════╝██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔══██╗██║   ██║████╗ ████║"
echo "  ██║██║  ██║██████╔╝    ███████╗██████╔╝█████╗  ██║        ██║   ██████╔╝██║   ██║██╔████╔██║"
echo "  ██║██║  ██║██╔══██╗    ╚════██║██╔═══╝ ██╔══╝  ██║        ██║   ██╔══██╗██║   ██║██║╚██╔╝██║"
echo "  ██║██████╔╝██║  ██║    ███████║██║     ███████╗╚██████╗   ██║   ██║  ██║╚██████╔╝██║ ╚═╝ ██║"
echo "  ╚═╝╚═════╝ ╚═╝  ╚═╝    ╚══════╝╚═╝     ╚══════╝ ╚═════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝"
echo -e "${NC}"
echo -e "${DIM}  // kenangan pahit rupiah terparah dalam sejarah${NC}"
echo ""

# ── Dependency check ──────────────────────────────────────────────────────────
PKGS=(
    "python-gobject"
    "gtk4"
    "gstreamer"
    "gst-plugins-base"
    "gst-plugins-good"
    "gst-plugins-bad"
    "gst-plugins-ugly"
    "gst-libav"
    "gst-python"
)

MISSING=()
for pkg in "${PKGS[@]}"; do
    if ! pacman -Q "$pkg" &>/dev/null; then
        MISSING+=("$pkg")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "${BOLD}Paket yang dibutuhkan belum terpasang:${NC}"
    for p in "${MISSING[@]}"; do
        echo -e "  ${RED}✗${NC} $p"
    done
    echo ""
    read -rp "Install sekarang? [Y/n] " yn
    yn=${yn:-Y}
    if [[ "$yn" =~ ^[Yy]$ ]]; then
        sudo pacman -S --needed "${MISSING[@]}"
    else
        echo -e "${RED}Dibatalkan.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✔${NC} Semua dependensi sudah terpasang."
fi

# ── Run ───────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAYER="$SCRIPT_DIR/idr_spectrum_player.py"

if [ ! -f "$PLAYER" ]; then
    echo -e "${RED}File tidak ditemukan: $PLAYER${NC}"
    exit 1
fi

chmod +x "$PLAYER"
echo -e "\n${GREEN}▶  Menjalankan IDR Spectrum Player...${NC}\n"
python3 "$PLAYER" "$@"