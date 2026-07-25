"""PyMuPDF-based PDF reader: render pages, extract images, extract text blocks."""

from pathlib import Path
from typing import Any

import fitz  # PyMuPDF


class PdfReader:
    """Read a PDF and extract per-page content blocks + embedded images."""

    def __init__(self, pdf_path: str | Path, dpi: int = 300):
        self.pdf_path = Path(pdf_path)
        self.dpi = dpi
        self.doc: fitz.Document = fitz.open(str(self.pdf_path))

    @property
    def page_count(self) -> int:
        return len(self.doc)

    def close(self):
        self.doc.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ── page metadata ────────────────────────────────────────────────

    def page_size(self, page_num: int) -> tuple[float, float]:
        """Return (width, height) in points for page *page_num* (0-based)."""
        page = self.doc[page_num]
        rect = page.rect
        return rect.width, rect.height

    # ── embedded images ──────────────────────────────────────────────

    def extract_images(self, page_num: int) -> list[dict[str, Any]]:
        """Extract embedded images from *page_num*.

        Returns
        -------
        list[dict]
            Each dict has keys: index, bbox (fitz.Rect), width, height,
            image_bytes, ext (e.g. "png", "jpg").
        """
        page = self.doc[page_num]
        images = []
        # Collect all image xrefs on this page via get_text("dict")
        seen_xrefs = set()
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 1:  # image block
                continue
            xref = block.get("xref", 0)
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            base_image = self.doc.extract_image(xref)
            if base_image is None:
                continue
            bbox = fitz.Rect(block["bbox"])
            images.append({
                "index": len(images),
                "bbox": bbox,
                "width": base_image["width"],
                "height": base_image["height"],
                "image_bytes": base_image["image"],
                "ext": base_image["ext"],
            })
        return images

    # ── text blocks ──────────────────────────────────────────────────

    def extract_text_blocks(self, page_num: int) -> list[dict[str, Any]]:
        """Extract text blocks with bounding boxes from *page_num*.

        Returns
        -------
        list[dict]
            Each dict has keys: bbox (fitz.Rect), text, type (0=block).
        """
        page = self.doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        results = []
        for block in blocks:
            if block["type"] == 0:  # text block
                text = "".join(
                    span["text"]
                    for line in block["lines"]
                    for span in line["spans"]
                ).strip()
                if text:
                    results.append({
                        "bbox": fitz.Rect(block["bbox"]),
                        "text": text,
                        "type": 0,
                    })
        return results

    # ── full page content dict ───────────────────────────────────────

    def page_content(self, page_num: int) -> dict[str, Any]:
        """Return everything from *page_num* as a single dict."""
        return {
            "page": page_num,
            "size": self.page_size(page_num),
            "images": self.extract_images(page_num),
            "text_blocks": self.extract_text_blocks(page_num),
        }
