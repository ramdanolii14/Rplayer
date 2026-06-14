#!/usr/bin/env python3
# ============================================================
#  idr_widgets.py
#  Widget GTK kustom: grafik kurs IDR (IDRChart), visualizer
#  spektrum audio (SpectrumVisualizer), dan model library musik
#  (MusicLibrary, termasuk ekstraksi cover art dari metadata).
#
#  Bagian dari IDR Spectrum Player.
# ============================================================

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

import os
import math

from idr_config import (
    IDR_MIN, IDR_MAX, HISTORY_LEN,
    NUM_BANDS,
    SPECTRUM_COLORS, DEFAULT_SPEC_COLOR,
    CHART_COLORS, DEFAULT_CHART_COLOR,
    AUDIO_EXTS,
)


class IDRChart(Gtk.DrawingArea):
    """Grafik kurs seperti Google Finance — spektrum menggerakkan nilai IDR."""
    __gtype_name__ = "IDRChart"

    def __init__(self, theme):
        super().__init__()
        self.theme        = theme
        self.history      = [IDR_MIN] * HISTORY_LEN
        self.current      = IDR_MIN
        self.color_preset = DEFAULT_CHART_COLOR
        self.set_draw_func(self.on_draw)
        self.set_hexpand(True)
        self.set_size_request(-1, 110)

    def push(self, value: float):
        self.history.append(value)
        if len(self.history) > HISTORY_LEN:
            self.history.pop(0)
        self.current = value
        self.queue_draw()

    def on_draw(self, _w, cr, width, height):
        t = self.theme
        cr.set_source_rgb(*t["chart_bg_rgb"])
        cr.rectangle(0, 0, width, height)
        cr.fill()

        cp     = CHART_COLORS[self.color_preset]
        data   = self.history
        n      = len(data)
        lo, hi = IDR_MIN, IDR_MAX
        pad    = 8
        lw     = 46  # label width on right

        def xt(i): return i / max(n - 1, 1) * (width - pad * 2 - lw) + pad
        def yt(v): return height - pad - (v - lo) / (hi - lo) * (height - pad * 2 - 14)

        # grid lines
        gr, gg, gb, ga = cp["grid"]
        cr.set_line_width(0.5)
        for val in [18000, 18500, 19000, 19500, 20000]:
            y = yt(val)
            cr.set_source_rgba(gr, gg, gb, ga)
            cr.move_to(0, y)
            cr.line_to(width - lw, y)
            cr.stroke()

        if n >= 2:
            fr, fg_, fb, fa = cp["fill"]
            lr, lg, lb      = cp["line"]

            # fill
            cr.move_to(xt(0), height - pad)
            for i, v in enumerate(data):
                cr.line_to(xt(i), yt(v))
            cr.line_to(xt(n - 1), height - pad)
            cr.close_path()
            cr.set_source_rgba(fr, fg_, fb, fa)
            cr.fill()

            # line
            cr.move_to(xt(0), yt(data[0]))
            for i, v in enumerate(data[1:], 1):
                cr.line_to(xt(i), yt(v))
            cr.set_source_rgb(lr, lg, lb)
            cr.set_line_width(2.0)
            cr.stroke()

            # dot
            ex, ey = xt(n - 1), yt(data[-1])
            cr.arc(ex, ey, 4.5, 0, 2 * math.pi)
            cr.set_source_rgb(lr, lg, lb)
            cr.fill()
            cr.arc(ex, ey, 8, 0, 2 * math.pi)
            cr.set_source_rgba(lr, lg, lb, 0.18)
            cr.fill()

        # Y labels
        tr, tg, tb = cp["text"]
        cr.set_source_rgb(tr, tg, tb)
        cr.set_font_size(9)
        for val, label in [(18000, "18.000"), (19000, "19.000"), (20000, "20.000")]:
            y = yt(val)
            cr.move_to(width - lw + 4, y + 3)
            cr.show_text(label)


# ── Spectrum Visualizer ────────────────────────────────────────────────────────
class SpectrumVisualizer(Gtk.DrawingArea):
    __gtype_name__ = "SpectrumVisualizer"

    def __init__(self, theme):
        super().__init__()
        self.theme        = theme
        self.magnitudes   = [-80.0] * NUM_BANDS
        self.peaks        = [-80.0] * NUM_BANDS
        self.peak_ttl     = [0]    * NUM_BANDS
        self.view_mode    = "FULL"
        self._smoothed    = [-80.0] * NUM_BANDS
        self.color_preset = DEFAULT_SPEC_COLOR
        self.set_draw_func(self.on_draw)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_size_request(-1, 160)

    def update(self, magnitudes: list):
        alpha = 0.55
        for i, m in enumerate(magnitudes):
            self._smoothed[i] = alpha * m + (1 - alpha) * self._smoothed[i]
            if m > self.peaks[i]:
                self.peaks[i]   = m
                self.peak_ttl[i] = 40
            elif self.peak_ttl[i] > 0:
                self.peak_ttl[i] -= 1
            else:
                self.peaks[i] = max(self.peaks[i] - 0.6, self._smoothed[i])
        self.magnitudes = magnitudes
        self.queue_draw()

    @staticmethod
    def _norm(db: float) -> float:
        return max(0.0, min(1.0, (db + 80.0) / 80.0))

    @staticmethod
    def _hex(h):
        h = h.lstrip("#")
        if len(h) == 6:
            return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4))
        return (0.2, 0.6, 0.4)

    def on_draw(self, _w, cr, width, height):
        t = self.theme
        r, g, b = self._hex(t["spec_bg"])
        cr.set_source_rgb(r, g, b)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        mags  = self._smoothed[:]
        peaks = self.peaks[:]
        n     = len(mags)

        if self.view_mode == "BASS":
            mags  = mags[:n // 4]
            peaks = peaks[:n // 4]
        elif self.view_mode == "MID":
            mags  = mags[n // 4: n * 3 // 4]
            peaks = peaks[n // 4: n * 3 // 4]
        elif self.view_mode == "WAVE":
            self._draw_wave(cr, mags, width, height, t)
            return

        n = len(mags)
        if n == 0: return

        bw  = width / n
        gap = max(0.8, bw * 0.18)

        for i in range(n):
            v  = self._norm(mags[i])
            bh = max(1.0, v * (height - 6))
            x  = i * bw + gap
            y  = height - bh
            w  = bw - gap * 2

            preset = SPECTRUM_COLORS[self.color_preset]
            try:
                import cairo
                pat = cairo.LinearGradient(0, height, 0, y)
                for pos, pr, pg, pb, pa in preset["stops"]:
                    pat.add_color_stop_rgba(pos, pr, pg, pb, pa)
                cr.set_source(pat)
            except Exception:
                cr.set_source_rgba(*preset["fallbk"](v))

            cr.rectangle(x, y, w, bh)
            cr.fill()

            if self.view_mode != "MAKS":
                pv = self._norm(peaks[i])
                py = height - pv * (height - 6) - 2
                cr.set_source_rgba(*preset["peak"])
                cr.rectangle(x, py, w, 1.5)
                cr.fill()

        cr.set_line_width(0.5)
        for ratio in (0.25, 0.50, 0.75):
            cr.set_source_rgba(1, 1, 1, 0.04)
            y = height * ratio
            cr.move_to(0, y); cr.line_to(width, y); cr.stroke()

        cr.set_source_rgba(0.38, 0.40, 0.44, 1.0)
        cr.set_font_size(9)
        for lbl, xr in (("0Hz", 0.01), ("5k", 0.25), ("10k", 0.50), ("20k", 0.97)):
            cr.move_to(xr * width, height - 3)
            cr.show_text(lbl)

    def _draw_wave(self, cr, mags, width, height, t):
        n = len(mags)
        if n == 0: return
        step = width / n

        # Hanya gambar bagian atas (bukan mirror)
        cr.move_to(0, height)
        for i, db in enumerate(mags):
            v = self._norm(db)
            cr.line_to(i * step, height - v * height * 0.90)
        cr.line_to((n - 1) * step, height)
        cr.close_path()

        preset = SPECTRUM_COLORS[self.color_preset]
        cr.set_source_rgba(*preset["wave_f"])
        cr.fill_preserve()
        cr.set_source_rgba(*preset["wave_l"])
        cr.set_line_width(1.5)
        cr.stroke()

        wfr, wfg, wfb, _ = preset["wave_f"]
        cr.set_source_rgba(wfr, wfg, wfb, 0.12)
        cr.set_line_width(1)
        cr.move_to(0, height); cr.line_to(width, height); cr.stroke()


# ── Library Store ──────────────────────────────────────────────────────────────
class MusicLibrary:
    def __init__(self):
        self.tracks: list[str] = []

    def add(self, path: str):
        if path not in self.tracks and os.path.isfile(path):
            self.tracks.append(path)
            return True
        return False

    def add_folder(self, folder: str):
        added = 0
        for root, _, files in os.walk(folder):
            for f in sorted(files):
                if os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                    if self.add(os.path.join(root, f)):
                        added += 1
        return added

    def remove(self, idx: int):
        if 0 <= idx < len(self.tracks):
            self.tracks.pop(idx)

    def clear(self):
        self.tracks.clear()

    def get_name(self, idx: int) -> str:
        if 0 <= idx < len(self.tracks):
            return os.path.basename(self.tracks[idx])
        return ""

    def get_cover_bytes(self, idx: int) -> bytes | None:
        """Coba ekstrak cover art dari metadata file audio."""
        if not (0 <= idx < len(self.tracks)):
            return None
        path = self.tracks[idx]
        ext  = os.path.splitext(path)[1].lower()
        try:
            if ext in (".mp3",):
                from gi.repository import GLib as _GL
                import struct
                with open(path, "rb") as f:
                    header = f.read(10)
                if header[:3] != b"ID3":
                    return None
                size = (header[6] & 0x7f) << 21 | (header[7] & 0x7f) << 14 | \
                       (header[8] & 0x7f) << 7  | (header[9] & 0x7f)
                with open(path, "rb") as f:
                    f.read(10)
                    tag_data = f.read(size)
                i = 0
                while i < len(tag_data) - 10:
                    fid  = tag_data[i:i+4].decode("latin-1", errors="replace")
                    fsz  = struct.unpack(">I", tag_data[i+4:i+8])[0]
                    i   += 10
                    if fid == "APIC" and fsz > 0:
                        raw = tag_data[i:i+fsz]
                        # skip encoding byte, mime, pic type, desc
                        j = 1
                        while j < len(raw) and raw[j] != 0: j += 1
                        j += 1  # skip null
                        j += 1  # skip picture type
                        while j < len(raw) and raw[j] != 0: j += 1
                        j += 1  # skip null after desc
                        return raw[j:]
                    i += fsz
            elif ext in (".flac",):
                with open(path, "rb") as f:
                    if f.read(4) != b"fLaC":
                        return None
                    while True:
                        hdr = f.read(4)
                        if len(hdr) < 4: break
                        btype = hdr[0] & 0x7f
                        last  = (hdr[0] & 0x80) != 0
                        bsize = (hdr[1] << 16) | (hdr[2] << 8) | hdr[3]
                        data  = f.read(bsize)
                        if btype == 6:  # PICTURE
                            import struct as _s
                            off  = 0
                            _pt  = _s.unpack_from(">I", data, off)[0]; off += 4
                            ml   = _s.unpack_from(">I", data, off)[0]; off += 4
                            off += ml  # skip mime
                            dl   = _s.unpack_from(">I", data, off)[0]; off += 4
                            off += dl  # skip desc
                            off += 16  # width,height,depth,colors
                            pl   = _s.unpack_from(">I", data, off)[0]; off += 4
                            return data[off:off+pl]
                        if last: break
            elif ext in (".m4a", ".aac"):
                with open(path, "rb") as f:
                    raw = f.read(1 << 20)  # baca max 1MB
                import struct as _s
                i = 0
                def find_atom(data, name, start=0):
                    pos = start
                    while pos < len(data) - 8:
                        sz = _s.unpack_from(">I", data, pos)[0]
                        nm = data[pos+4:pos+8]
                        if sz < 8: break
                        if nm == name: return pos, sz
                        pos += sz
                    return -1, 0
                # Cari ilst → covr
                p, _ = find_atom(raw, b"moov")
                if p < 0: return None
                p2, _ = find_atom(raw, b"udta", p+8)
                p3, _ = find_atom(raw, b"meta", p2+8 if p2 >= 0 else p+8)
                p4, _ = find_atom(raw, b"ilst", p3+12 if p3 >= 0 else p+8)
                p5, s5 = find_atom(raw, b"covr", p4+8 if p4 >= 0 else p+8)
                if p5 >= 0 and s5 > 16:
                    # data atom inside covr
                    dp = p5 + 8
                    dsz = _s.unpack_from(">I", raw, dp)[0]
                    return raw[dp+16:dp+dsz] if dsz > 16 else None
        except Exception:
            pass
        return None

    def __len__(self): return len(self.tracks)
