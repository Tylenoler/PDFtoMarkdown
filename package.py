"""Build helper for pdf2md exe packaging."""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
SPEC = ROOT / "build.spec"


def clean():
    """Remove build artifacts."""
    for d in [ROOT / "build", ROOT / "__pycache__"]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
    for p in [DIST]:
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)


def build_exe():
    """Run PyInstaller."""
    subprocess.check_call(
        [sys.executable, "-m", "PyInstaller", str(SPEC), "--clean", "-y"],
        cwd=str(ROOT),
    )
    print(f"\nBuild complete. exe at: {DIST / 'pdf2md' / 'pdf2md.exe'}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build pdf2md exe")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts")
    parser.add_argument("--build", action="store_true", help="Run PyInstaller build")
    args = parser.parse_args()

    if args.clean:
        clean()
        print("Cleaned build artifacts.")
    if args.build:
        build_exe()
    if not args.clean and not args.build:
        parser.print_help()
