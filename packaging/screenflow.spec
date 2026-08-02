# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — ScreenFlow Studio (windowed onedir)."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).resolve().parent

block_cipher = None

# Avoid collect_all("PySide6") — pulls deploy scripts and fights PyQt5 hooks.
datas = []
binaries = []
hiddenimports = collect_submodules("screenflow") + collect_submodules("studio")

for pkg in ("cv2", "mss"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# Host env may have PyQt5 installed; freeze must stay on PySide6 only.
excludes = [
    "pytest",
    "unittest",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "tkinter",
    "_tkinter",
    "matplotlib",
]

a = Analysis(
    [str(ROOT / "run_app.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ScreenFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ScreenFlow",
)
