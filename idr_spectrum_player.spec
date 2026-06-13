# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['idr_spectrum_player.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'gi',
        'gi.repository.Gtk',
        'gi.repository.Gdk',
        'gi.repository.Gst',
        'gi.repository.GLib',
        'gi.repository.Gio',
        'gi.repository.GObject',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='IDR Spectrum Player',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/id.ramdanolii.idrspectrum.ico',
)
