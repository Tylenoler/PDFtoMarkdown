# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build script for pdf2md (exe packaging).

Usage:
    pyinstaller build.spec --clean -y

Output: dist/pdf2md/pdf2md.exe (one-folder bundle).
"""

import sys
import os
from pathlib import Path


# ── Find PaddleOCR package data ───────────────────────────────────────
def _paddle_pkg_data():
    """Return (source_dir, target_dir) tuples for PaddleOCR data files."""
    import paddleocr

    pkg = Path(paddleocr.__file__).parent
    data = []
    # fonts, configs, etc.
    for sub in ["ppocr", "ppstructure"]:
        src = pkg / sub
        if src.is_dir():
            data.append((str(src), sub))
    return data


# ── Options ───────────────────────────────────────────────────────────
block_cipher = None

a = Analysis(
    ["pdf2md.py"],
    pathex=[os.path.dirname(os.path.abspath(__file__))],
    binaries=[],
    datas=[(str(p), t) for p, t in _paddle_pkg_data()],
    hiddenimports=[
        "paddleocr",
        "paddle",
        "paddle.nn",
        "paddle.nn.functional",
        "paddle.tensor",
        "paddle.fluid",
        "paddle.fluid.core",
        "paddleocr.ppocr",
        "paddleocr.ppstructure",
        "paddleocr.tools",
        "fitz",
        "flask",
        "webview",
        "werkzeug",
        "numpy",
        "cv2",
        "PIL",
        "PIL._imaging",
        "PIL.Image",
        "pkg_resources",
        "pkgutil",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "sympy",
        "notebook",
        "jupyter",
        "PIL.ImageShow",
        "PIL.ImageQt",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="pdf2md",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no console window for GUI mode
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,             # can add a .ico later
)

# Also produce a console variant for CLI mode
exe_console = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="pdf2md-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="pdf2md",
)

coll_console = COLLECT(
    exe_console,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="pdf2md-cli",
)
