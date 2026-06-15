# IDR Spectrum 🎵

Pemutar musik berbasis Chromium (Electron) dengan visualisasi chart IDR/USD historis.

---

## Fitur

- **Playlist** — scan rekursif folder musik (mp3, flac, wav, ogg, m4a, aac, opus, wma, alac, ape)
- **Cover art otomatis** — embedded metadata → iTunes → MusicBrainz/CAA → Deezer → Last.fm
- **Player bar** — play/pause, prev/next, seek, volume, shuffle, repeat
- **IDR/USD Chart** — visualisasi Chart.js data historis kurs Rupiah 1990–2024
- **Custom titlebar** — minimize/maximize/close
- **Keyboard shortcuts** — Space, ←→ (seek ±5s), ↑↓ (volume), S (shuffle), R (repeat), M (mute), ,/. (prev/next)

---

## Cara Pakai

### 1. Install dependencies

```bash
npm install
```

> Butuh: Node.js ≥18, npm, dan Electron (diinstall otomatis via npm).

### 2. Taruh logo SVG

Copy file logo kamu ke folder `assets/`:

```bash
cp /path/ke/id.ramdanolii.idrspectrum.svg assets/
```

### 3. Jalankan

```bash
npm start
```

---

## Build AppImage (opsional)

```bash
npm run build-linux
```

Output ada di `dist/`.

---

## Struktur

```
idr-spectrum/
├── assets/
│   └── id.ramdanolii.idrspectrum.svg   ← taruh logo di sini
├── main.js          ← Electron main process
├── preload.js       ← IPC bridge (contextBridge)
├── index.html       ← UI utama
├── styles.css       ← Styling dark editorial
├── renderer.js      ← Logic: playlist, audio, cover, chart
└── package.json
```

---

## Cover Art Sources

Urutan fallback jika tidak ada embedded cover:
1. **iTunes Search API** — `itunes.apple.com` (free, no key)
2. **MusicBrainz** + **Cover Art Archive** — `coverartarchive.org` (free, no key)
3. **Deezer** — `api.deezer.com` (free, no key)
4. **Last.fm** — `ws.audioscrobbler.com` (public demo key)
5. **iTunes album search** — fallback via album name

---

*IDR Spectrum by Alycia (ramdanolii14) — github.com/ramdanolii14/Rplayer*
