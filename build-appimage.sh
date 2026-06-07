#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
#  IDR Spectrum Player — AppImage Builder
#  Jalankan di Arch Linux dari folder yang berisi idr_spectrum_player.py
# ──────────────────────────────────────────────────────────────────────────────

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
DIM='\033[2m'
NC='\033[0m'

APPDIR="IDRSpectrum.AppDir"
OUTPUT="IDR-Spectrum-Player-x86_64.AppImage"

echo -e "${CYAN}${BOLD}IDR Spectrum — AppImage Builder${NC}"
echo -e "${DIM}────────────────────────────────────────${NC}"

# ── Cek file wajib ──
for f in idr_spectrum_player.py id.ramdanolii.idrspectrum.svg; do
    if [ ! -f "$f" ]; then
        echo -e "${RED}✗ File tidak ditemukan: $f${NC}"
        echo "  Pastikan script ini dijalankan dari folder yang sama dengan idr_spectrum_player.py"
        exit 1
    fi
done

# ── Cek appimagetool ──
APPIMAGETOOL=""
if command -v appimagetool &>/dev/null; then
    APPIMAGETOOL="appimagetool"
elif [ -f "$HOME/appimagetool-x86_64.AppImage" ]; then
    APPIMAGETOOL="$HOME/appimagetool-x86_64.AppImage"
else
    echo -e "${YELLOW}⚠ appimagetool tidak ditemukan.${NC}"
    echo ""
    echo "Download dulu:"
    echo "  wget -O ~/appimagetool-x86_64.AppImage \\"
    echo "    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    echo "  chmod +x ~/appimagetool-x86_64.AppImage"
    echo ""
    echo "Atau dari AUR:"
    echo "  yay -S appimagetool-bin"
    exit 1
fi

echo -e "${GREEN}✔${NC} appimagetool ditemukan: $APPIMAGETOOL"

# ── Buat AppDir ──
echo -e "\n${BOLD}Membuat AppDir...${NC}"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$APPDIR/usr/share/icons/hicolor/128x128/apps"

# Salin player
cp idr_spectrum_player.py "$APPDIR/usr/bin/"
echo -e "  ${GREEN}✔${NC} idr_spectrum_player.py"

# Icon SVG
cp id.ramdanolii.idrspectrum.svg \
   "$APPDIR/usr/share/icons/hicolor/scalable/apps/"
cp id.ramdanolii.idrspectrum.svg "$APPDIR/"
echo -e "  ${GREEN}✔${NC} icon SVG"

# Icon PNG (opsional tapi disarankan)
if command -v rsvg-convert &>/dev/null; then
    rsvg-convert -w 128 -h 128 id.ramdanolii.idrspectrum.svg \
        -o "$APPDIR/usr/share/icons/hicolor/128x128/apps/id.ramdanolii.idrspectrum.png"
    cp "$APPDIR/usr/share/icons/hicolor/128x128/apps/id.ramdanolii.idrspectrum.png" \
       "$APPDIR/id.ramdanolii.idrspectrum.png"
    echo -e "  ${GREEN}✔${NC} icon PNG 128x128"
else
    echo -e "  ${YELLOW}⚠${NC} rsvg-convert tidak ada, skip PNG icon (install: sudo pacman -S librsvg)"
fi

# .desktop file — Categories wajib ada AudioVideo agar tidak error
cat > "$APPDIR/usr/share/applications/id.ramdanolii.idrspectrum.desktop" << 'DESK'
[Desktop Entry]
Version=1.1
Type=Application
Name=IDR Spectrum Player
GenericName=Music Player
Comment=Music player dengan visualizer spektrum dan grafik kurs IDR realtime
Exec=idr_spectrum_player
Icon=id.ramdanolii.idrspectrum
Terminal=false
Categories=AudioVideo;Audio;Music;Player;
MimeType=audio/mpeg;audio/ogg;audio/flac;audio/wav;audio/x-m4a;audio/opus;audio/aac;audio/x-ms-wma;
Keywords=music;player;spectrum;idr;rupiah;audio;visualizer;
StartupNotify=true
StartupWMClass=idr_spectrum_player
DESK

cp "$APPDIR/usr/share/applications/id.ramdanolii.idrspectrum.desktop" \
   "$APPDIR/id.ramdanolii.idrspectrum.desktop"
echo -e "  ${GREEN}✔${NC} .desktop file"

# AppStream metadata — hilangkan WARNING saat build
mkdir -p "$APPDIR/usr/share/metainfo"
cat > "$APPDIR/usr/share/metainfo/id.ramdanolii.idrspectrum.appdata.xml" << 'APPDATA'
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>id.ramdanolii.idrspectrum</id>
  <metadata_license>MIT</metadata_license>
  <project_license>MIT</project_license>
  <name>IDR Spectrum Player</name>
  <summary>Music player dengan visualizer spektrum dan grafik kurs IDR</summary>
  <description>
    <p>
      IDR Spectrum Player adalah music player berbasis GTK4 yang menampilkan
      visualizer spektrum audio realtime dan grafik kurs Rupiah (IDR) yang
      bergerak sesuai irama musik.
    </p>
    <p>Fitur utama:</p>
    <ul>
      <li>Visualizer spektrum dengan 5 mode tampilan (BASS, MID, FULL, WAVE, MAKS)</li>
      <li>8 preset warna spektrum yang bisa diganti</li>
      <li>Grafik kurs USD/IDR realtime bergaya Google Finance dengan 9 pilihan warna</li>
      <li>Library musik dengan dukungan folder</li>
      <li>Shuffle, repeat, dan kontrol volume</li>
      <li>Tema terang dan gelap</li>
    </ul>
  </description>
  <launchable type="desktop-id">id.ramdanolii.idrspectrum.desktop</launchable>
  <url type="homepage">https://ramdanolii.my.id</url>
  <provides>
    <mediatype>audio/mpeg</mediatype>
    <mediatype>audio/ogg</mediatype>
    <mediatype>audio/flac</mediatype>
    <mediatype>audio/wav</mediatype>
    <mediatype>audio/x-m4a</mediatype>
    <mediatype>audio/opus</mediatype>
    <mediatype>audio/aac</mediatype>
  </provides>
  <releases>
    <release version="1.1.0" date="2026-06-07">
      <description>
        <p>Rilis IDR Spectrum Player.</p>
      </description>
    </release>
  </releases>
  <content_rating type="oars-1.1"/>
</component>
APPDATA
echo -e "  ${GREEN}✔${NC} AppStream metadata (appdata.xml)"

# AppRun
cat > "$APPDIR/AppRun" << 'APPRUN'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
exec python3 "$HERE/usr/bin/idr_spectrum_player.py" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"
echo -e "  ${GREEN}✔${NC} AppRun"

# ── Build AppImage ──
echo -e "\n${BOLD}Building AppImage...${NC}"
ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$OUTPUT"

echo -e "\n${GREEN}${BOLD}✔ Selesai!${NC}"
echo -e "  File: ${BOLD}${OUTPUT}${NC}"
echo -e "  Size: $(du -sh "$OUTPUT" | cut -f1)"
echo ""
echo -e "${DIM}Cara uji coba:${NC}"
echo -e "  chmod +x $OUTPUT"
echo -e "  ./$OUTPUT"
echo ""
echo -e "${DIM}Cara publish ke GitHub:${NC}"
echo -e "  gh release create v1.1.0 $OUTPUT \\"
echo -e "    --title 'IDR Spectrum Player v1.1.0' \\"
echo -e "    --notes 'Music player dengan visualizer spektrum dan grafik kurs IDR'"