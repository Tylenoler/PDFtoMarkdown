"""PaddleOCR (PP-StructureV3) wrapper for layout analysis."""

from pathlib import Path
from typing import Any

from pdf2md.utils.helpers import detect_device


class OcrEngine:
    """Layout analysis via PaddleOCR PP-StructureV3.

    Detects text regions, tables, and figures on each page, returning
    structured blocks with bounding boxes and content.
    """

    def __init__(self, lang: str = "ch", use_gpu: bool | None = None):
        self.lang = lang
        self.use_gpu = detect_device() == "gpu" if use_gpu is None else use_gpu
        self._table_engine = None
        self._layout_engine = None

    def _lazy_init(self):
        """Import & init PaddleOCR components on first use (lazy)."""
        if self._layout_engine is not None:
            return
        from paddleocr import PPStructure

        self._layout_engine = PPStructure(
            lang=self.lang,
            use_gpu=self.use_gpu,
            show_log=False,
        )

    def analyze_page(self, image_bytes: bytes) -> list[dict[str, Any]]:
        """Run layout analysis on a rendered page image (bytes).

        Returns
        -------
        list[dict]
            Each dict has keys:
              - type: str — "text", "table", "figure", "header", "footer"
              - bbox: list[float] — [x0, y0, x1, y1] in image coords
              - content: str — extracted text or table markdown
              - conf: float — confidence
        """
        self._lazy_init()
        import cv2
        import numpy as np

        # Decode bytes → opencv image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        results = self._layout_engine(img)
        blocks = []
        for res in results:
            typ = res.get("type", "text")
            bbox = res.get("bbox", None) or res.get("res", {}).get("bbox", None)
            content = ""
            if typ in ("table",):
                content = res.get("res", {}).get("html", "")
            elif typ in ("text", "header", "footer"):
                content = res.get("res", {}).get("text", "")
            elif typ == "figure":
                content = res.get("res", {}).get("text", "")

            blocks.append({
                "type": typ.lower(),
                "bbox": bbox,
                "content": content,
                "conf": res.get("conf", 0.0),
            })
        return blocks
