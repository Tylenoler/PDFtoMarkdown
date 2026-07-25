"""Conversion orchestrator: ties PDF reader, OCR, aligner, generator together."""

import json
from pathlib import Path
from typing import Any

from pdf2md.aligner.matcher import match_images_to_figures
from pdf2md.aligner.sorter import reading_order_sort
from pdf2md.extractor.ocr_engine import OcrEngine
from pdf2md.extractor.pdf_reader import PdfReader
from pdf2md.generator.markdown import MarkdownGenerator
from pdf2md.utils.helpers import ensure_output_dir, images_dir


class Converter:
    """High-level orchestrator for PDF → Markdown conversion."""

    def __init__(
        self,
        output_dir: str | Path,
        lang: str = "ch",
        use_gpu: bool | None = None,
        dpi: int = 300,
    ):
        self.output_dir = ensure_output_dir(output_dir)
        self.images_dir = images_dir(self.output_dir)
        self.lang = lang
        self.use_gpu = use_gpu
        self.dpi = dpi

    def convert(self, pdf_path: str | Path) -> dict[str, Any]:
        """Convert a single PDF to Markdown.

        Returns
        -------
        dict with keys: pdf, page_count, output_md, output_dir.
        """
        pdf_path = Path(pdf_path)
        ocr = OcrEngine(lang=self.lang, use_gpu=self.use_gpu)
        gen = MarkdownGenerator(self.output_dir)

        with PdfReader(pdf_path, dpi=self.dpi) as reader:
            pages_md = []
            report_pages = []

            for page_num in range(reader.page_count):
                # 1. Render page as image for OCR
                page = reader.doc[page_num]
                pix = page.get_pixmap(dpi=self.dpi)
                img_bytes = pix.tobytes("png")

                # 2. OCR layout analysis
                ocr_blocks = ocr.analyze_page(img_bytes)

                # 3. Extract embedded images from PyMuPDF
                pdf_images = reader.extract_images(page_num)

                # 4. Match high-res images to OCR figure regions
                matched = match_images_to_figures(pdf_images, ocr_blocks)

                # 5. Annotate blocks with original index, then sort in reading order
                annotated = [
                    dict(block, _orig_idx=i)
                    for i, block in enumerate(ocr_blocks)
                ]
                sorted_blocks = reading_order_sort(annotated)

                # 6. Assemble page Markdown
                page_md = gen.assemble_page(page_num, sorted_blocks, matched)
                pages_md.append(page_md)

                # Debug report per page
                report_pages.append({
                    "page": page_num,
                    "ocr_blocks": [
                        {"type": b["type"], "bbox": b["bbox"]}
                        for b in ocr_blocks
                    ],
                    "extracted_images": len(pdf_images),
                    "matched_images": len(matched),
                })

            # 7. Write output
            full_md = gen.write_output(pages_md)

        # Write report
        report = {
            "pdf": str(pdf_path),
            "page_count": reader.page_count,
            "output_md": str(self.output_dir / "output.md"),
            "output_dir": str(self.output_dir),
            "pages": report_pages,
        }
        report_path = self.output_dir / "report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        return report
