"""IoU-based matcher: align PyMuPDF-extracted images with OCR-detected figure regions."""

from typing import Any

import fitz


def iou(a: fitz.Rect, b: list[float]) -> float:
    """Intersection-over-Union between a fitz.Rect and a [x0,y0,x1,y1] list."""
    rb = fitz.Rect(b)
    inter = a & rb
    if not inter or inter.is_empty:
        return 0.0
    union = a | rb
    return inter.get_area() / union.get_area()


def match_images_to_figures(
    pdf_images: list[dict[str, Any]],
    ocr_blocks: list[dict[str, Any]],
    iou_threshold: float = 0.3,
) -> dict[int, dict[str, Any]]:
    """Match PyMuPDF extracted images to OCR figure blocks by IoU.

    Parameters
    ----------
    pdf_images : list[dict]
        From PdfReader.extract_images() — each has "bbox" (fitz.Rect), index, etc.
    ocr_blocks : list[dict]
        From OcrEngine.analyze_page() — each has "bbox" ([x0,y0,x1,y1]), type.
    iou_threshold : float
        Minimum IoU to consider a match.

    Returns
    -------
    dict[int -> dict]
        Mapping from OCR block index (in ocr_blocks) → the matched pdf_image dict.
        Unmatched figure blocks are not included.
    """
    matches: dict[int, dict] = {}
    for img in pdf_images:
        best_idx, best_iou = -1, 0.0
        for i, block in enumerate(ocr_blocks):
            if block["type"] != "figure":
                continue
            if block["bbox"] is None:
                continue
            score = iou(img["bbox"], block["bbox"])
            if score > best_iou:
                best_iou = score
                best_idx = i

        if best_idx >= 0 and best_iou >= iou_threshold:
            # Higher IoU wins: don't replace if already matched with higher score
            if best_idx not in matches or best_iou > iou(matches[best_idx]["bbox"], ocr_blocks[best_idx]["bbox"]):
                matches[best_idx] = img

    return matches
