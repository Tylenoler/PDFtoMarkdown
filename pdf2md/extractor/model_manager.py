"""PaddleOCR model download manager — auto-downloads models on first run."""

import os
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve


def _appdata_dir() -> Path:
    """Data directory: user's AppData for exe, project dir for dev."""
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local"))
    else:
        base = Path(__file__).resolve().parent.parent.parent
    d = base / "pdf2md_data" / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


MODELS = {
    # PP-OCRv4 detection model
    "det_model_dir": {
        "url": "https://paddleocr.bj.bcebos.com/PP-OCRv4/ch/ch_PP-OCRv4_det_infer.tar",
        "dir": "ch_PP-OCRv4_det_infer",
    },
    # PP-OCRv4 recognition model
    "rec_model_dir": {
        "url": "https://paddleocr.bj.bcebos.com/PP-OCRv4/ch/ch_PP-OCRv4_rec_infer.tar",
        "dir": "ch_PP-OCRv4_rec_infer",
    },
    # PP-StructureV3 layout model
    "layout_model_dir": {
        "url": "https://paddleocr.bj.bcebos.com/ppstructure/models/layout/picodet_lcnet_x1_0_fgd_layout_infer.tar",
        "dir": "picodet_lcnet_x1_0_fgd_layout_infer",
    },
    # PP-Structure table model
    "table_model_dir": {
        "url": "https://paddleocr.bj.bcebos.com/ppstructure/models/table/ch_ppstructure_mobile_v2.0_SLANet_infer.tar",
        "dir": "ch_ppstructure_mobile_v2.0_SLANet_infer",
    },
}


def ensure_models(progress_callback=None) -> dict[str, str]:
    """Download missing models, return dict of model_dir → absolute path.

    Parameters
    ----------
    progress_callback : callable or None
        Called with (current, total) after each model check/download.

    Returns
    -------
    dict[str, str]
        Mapping of PaddleOCR config keys to local absolute paths.
    """
    data_dir = _appdata_dir()
    result = {}
    total = len(MODELS)
    for i, (key, info) in enumerate(MODELS.items()):
        model_path = data_dir / info["dir"]
        if not model_path.exists():
            # Download tar
            tar_path = data_dir / f"{info['dir']}.tar"
            print(f"Downloading {info['dir']} ...")
            urlretrieve(info["url"], str(tar_path))
            # Extract
            import tarfile

            with tarfile.open(str(tar_path), "r") as tar:
                tar.extractall(path=str(data_dir))
            tar_path.unlink()
        result[key] = str(model_path)
        if progress_callback:
            progress_callback(i + 1, total)
    return result


def model_config() -> dict[str, str]:
    """Return config dict for PPStructure, downloading models if needed."""
    models = ensure_models()
    return {
        "det_model_dir": models["det_model_dir"],
        "rec_model_dir": models["rec_model_dir"],
        "layout_model_dir": models["layout_model_dir"],
        "table_model_dir": models["table_model_dir"],
        "rec_char_dict_path": None,  # use built-in
    }
