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

# Spec file dir — PyInstaller runs this via exec(), __file__ not available
_SPEC_DIR = Path(os.path.dirname(os.path.abspath("build.spec")))


block_cipher = None

a = Analysis(
    ["pdf2md.py"],
    pathex=[str(_SPEC_DIR)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # core app
        "pdf2md",
        "pdf2md.cli",
        "pdf2md.web",
        "pdf2md.gui",
        "pdf2md.converter",
        "pdf2md.extractor.pdf_reader",
        "pdf2md.extractor.ocr_engine",
        "pdf2md.extractor.model_manager",
        "pdf2md.aligner.matcher",
        "pdf2md.aligner.sorter",
        "pdf2md.generator.markdown",
        "pdf2md.utils.helpers",
        # deps
        "fitz",
        "flask",
        "webview",
        "werkzeug",
        "paddleocr",
        "paddle",
        "cv2",
        "numpy",
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

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
