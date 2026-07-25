"""Path, file, GPU detection helpers."""

import os
import sys
from pathlib import Path


def detect_device():
    """Detect GPU availability via PaddlePaddle, fall back to CPU."""
    try:
        import paddle

        if paddle.is_compiled_with_cuda():
            return "gpu"
    except Exception:
        pass
    return "cpu"


def ensure_output_dir(path: str | Path) -> Path:
    """Create output directory if it doesn't exist, return resolved path."""
    p = Path(path).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def collect_pdf_files(path: str | Path) -> list[Path]:
    """Collect all .pdf files from a path (file or directory)."""
    p = Path(path)
    if p.is_file():
        return [p] if p.suffix.lower() == ".pdf" else []
    return sorted(p.rglob("*.pdf"))


def images_dir(output_dir: Path) -> Path:
    """Return/create the images subdirectory under output_dir."""
    d = output_dir / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d
